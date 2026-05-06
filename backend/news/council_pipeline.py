"""
NewsFactCheckCouncil V2 — Multi-stage fact-checking pipeline.
Stage 1: Dynamic intent extraction (2-6 intents) via Gemini.
Stage 2: Async Tavily search across 3 API keys with retry logic.
Stage 3: Cohere Rerank — score and filter the best articles per intent.
Stage 4: Parallel LLM workers (Qwen, GPT, GLM via Cerebras; Gemini Flash)
         independently analyse each intent's top articles.
Stage 5: Gemini Flash acts as the Supreme Judge — synthesises all worker
         reports into a single, citation-rich JSON verdict.
"""

import asyncio
import functools
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from typing import Any

import cohere
from dotenv import load_dotenv
from google import genai
from google.genai import types
from tavily import TavilyClient

# ── Logging (colored) ────────────────────────────────────────────────────────
class _ColoredFormatter(logging.Formatter):
    """ANSI-colored log formatter."""
    COLORS = {
        logging.DEBUG:    "\033[36m",   # cyan
        logging.INFO:     "\033[37m",   # white
        logging.WARNING:  "\033[33m",   # yellow
        logging.ERROR:    "\033[31m",   # red
        logging.CRITICAL: "\033[91m",   # bright red
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, self.RESET)
        msg = super().format(record)
        return f"{color}{msg}{self.RESET}"


_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(
    _ColoredFormatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
)
logging.root.setLevel(logging.INFO)
logging.root.addHandler(_handler)
logger = logging.getLogger(__name__)


# ── Timing decorator (async-compatible) ──────────────────────────────────────
def _async_timer(func):
    """A decorator that measures and outputs the execution time of an asynchronous function after it completes."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = await func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        minutes, secs = divmod(elapsed, 60)
        print(
            f"\n⏱  [{func.__name__}] finished in "
            f"{int(minutes):02d}m {secs:05.2f}s ({elapsed:.2f}s total)"
        )
        return result
    return wrapper

# ── Environment ──────────────────────────────────────────────────────────────
# We assume Django settings already loaded .env, but we can do a fallback
load_dotenv(override=False)

def _load_tavily_keys() -> list[str]:
    """Load Tavily API keys from .env (comma-separated)."""
    raw = os.getenv("ARRAY_TAVILY_API_KEY", "").strip()
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    if not keys:
        raise ValueError("ARRAY_TAVILY_API_KEY is empty. Set it in .env.")
    return keys


def _load_cohere_keys() -> list[str]:
    """Load Cohere rerank API keys from .env (comma-separated)."""
    raw = os.getenv("ARRAY_COHERE_RERANKED_API_KEY", "").strip()
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    if not keys:
        raise ValueError("ARRAY_COHERE_RERANKED_API_KEY is empty. Set it in .env.")
    return keys


# ── Helpers ──────────────────────────────────────────────────────────────────
def _strip_code_fences(text: str) -> str:
    """Remove ```json ... ``` wrappers that LLMs sometimes add."""
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _safe_json_loads(text: str, fallback: Any) -> Any:
    """Parse JSON tolerantly; return *fallback* on any error."""
    try:
        return json.loads(_strip_code_fences(text))
    except (json.JSONDecodeError, TypeError, ValueError):
        return fallback


def _print_intents(intents: list[dict[str, str]]) -> None:
    """Pretty-print intents to the terminal."""
    print("\n" + "=" * 70)
    print(f"  STAGE 1 COMPLETE — {len(intents)} intent(s) extracted")
    print("=" * 70)
    for item in intents:
        print(f"\n  [{item['intent_id']}]")
        print(f"  Intent : {item['intent']}")
        print(f"  Guide  : {item['search_guidance']}")
    print("\n" + "=" * 70 + "\n")


def _print_search_results(results: list[dict[str, Any]]) -> None:
    """Pretty-print Stage 2 search results to the terminal."""
    print("\n" + "=" * 70)
    print(f"  STAGE 2 COMPLETE — searched {len(results)} intent(s)")
    print("=" * 70)
    for item in results:
        articles = item.get("articles", [])
        status = "✓" if articles else "✗ NO RESULTS"
        print(f"\n  [{item['intent_id']}] {status}")
        print(f"  Query  : {item['intent']}")
        print(f"  Found  : {len(articles)} article(s)")
        for idx, art in enumerate(articles[:5], 1):  # show first 5
            print(f"    {idx}. {art.get('title', '—')[:80]}")
            print(f"       {art.get('url', '')[:90]}")
        if len(articles) > 5:
            print(f"    ... and {len(articles) - 5} more")
    print("\n" + "=" * 70 + "\n")


def _sanitize_filename(text: str, max_len: int = 80) -> str:
    """Replace spaces/special chars with underscores for filesystem compatibility."""
    text = re.sub(r"[^\w\s-]", "", text)       # remove special chars
    text = re.sub(r"[\s]+", "_", text.strip())  # spaces → underscores
    return text[:max_len]


def _make_run_dir(news_title: str, base_dir: str = "factcheck_runs") -> str:
    """Create factcheck_runs/<datetime>_<news_title>/ folder and return its path."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    safe_title = _sanitize_filename(news_title)
    folder_name = f"{timestamp}_{safe_title}"
    run_dir = os.path.join(base_dir, folder_name)
    os.makedirs(run_dir, exist_ok=True)
    logger.info("Run directory created: %s", run_dir)
    return run_dir



# ── Raw-content cleaner ──────────────────────────────────────────────────────
def _clean_raw_content(raw: str) -> str:
    """
    Strip Markdown/HTML noise from a Tavily ``raw_content`` field and return
    plain prose suitable for an LLM prompt.

    Steps (applied in order):
    1. Remove Markdown image tags  ![alt](url)
    2. Remove Markdown hyperlinks  [text](url)  →  keep text only
    3. Remove bare URLs            https://...
    4. Remove Markdown headings    # / ## / ###
    5. Remove horizontal rules     ---  ===  ***
    6. Remove bold/italic markers  ** * __ _
    7. Remove inline code/fences   ` ``` ~~~
    8. Strip common nav / sidebar boilerplate patterns
       ("Related Topics", "Trending", "Breaking", "Cite This Page", etc.)
    9. Collapse 3+ consecutive blank lines into a single blank line.
    10. Strip leading/trailing whitespace per line.
    """
    if not raw:
        return ""

    text = raw

    # 1. Markdown images
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)

    # 2. Markdown links  [label](url)  →  label
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)

    # 3. Bare URLs
    text = re.sub(r"https?://\S+", "", text)

    # 4. Markdown headings (lines starting with #)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)

    # 5. Horizontal rules  (--- === *** alone on a line)
    text = re.sub(r"^[-=*_]{3,}\s*$", "", text, flags=re.MULTILINE)

    # 6. Bold / italic markers  ** * __ _
    text = re.sub(r"(\*{1,3}|_{1,3})", "", text)

    # 7. Inline code and fenced code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)   # fenced blocks
    text = re.sub(r"~~~[\s\S]*?~~~", "", text)   # tilde fences
    text = re.sub(r"`[^`]*`", "", text)           # inline code

    # 8. Common boilerplate blocks — remove whole lines that match
    boilerplate_patterns = [
        r"^\s*(Related (Stories|Topics|Terms|Multimedia)|Trending|Breaking|Strange & Offbeat)",
        r"^\s*(Cite This Page|Story Source|Journal Reference|Explore More)",
        r"^\s*(MLA|APA|Chicago)\s*$",
        r"^\s*(Share:|Follow:|Subscribe:)",
        r"^\s*(Print|Email|Share)\s*$",
        r"^\s*(this hour|this week)\s*$",
        r"^\s*[*+-]\s*$",                    # bare bullet with no text
        r"^\s*(DOI|doi)\s*:\s*\S+",          # DOI lines
        r"^\s*Retrieved .{5,60} from \S+",   # "Retrieved April … from …"
        r"^\s*Note:\s*Content may be edited",
    ]
    for pat in boilerplate_patterns:
        text = re.sub(pat, "", text, flags=re.MULTILINE | re.IGNORECASE)

    # 9. Collapse 3+ consecutive blank lines → single blank line
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 10. Strip trailing spaces from every line (keep the newlines themselves)
    lines = [line.rstrip() for line in text.splitlines()]
    text = "\n".join(lines).strip()

    return text


def _save_artifacts(
    run_dir: str,
    search_results: list[dict[str, Any]],
) -> None:
    """
    Save one STAGE_01-02 .md file per intent (all Tavily articles, with
    cohere_score if Stage 3 has already run).
    Filename: STAGE_01-02_[i1]_-_Intent_text_here.md
    """
    for item in search_results:
        intent_id = item["intent_id"]
        intent_text = item["intent"]
        guidance = item["search_guidance"]
        articles = item.get("articles", [])

        safe_intent = _sanitize_filename(intent_text)
        filename = f"STAGE_01-02_[{intent_id}]_-_{safe_intent}.md"
        filepath = os.path.join(run_dir, filename)

        header = (
            f"# [{intent_id}]\n"
            f"**Intent:** {intent_text}\n"
            f"**Guide:** {guidance}\n"
            f"\n---\n"
            f"## Tavily Search Results ({len(articles)} articles)\n\n"
        )

        rows: list[str] = []
        for art in articles:
            cohere_score = art.get("cohere_score")
            score_line = (
                f"- **Cohere score:** {cohere_score:.4f}\n"
                if cohere_score is not None
                else ""
            )
            rows.append(
                f"### {art.get('title', '(no title)')}\n"
                f"- **URL:** {art.get('url', '')}\n"
                f"- **Relevance score:** {art.get('score')}\n"
                f"{score_line}"
                f"- **Published:** {art.get('published_date', '')}\n\n"
                f"{art.get('content', '')}\n\n"
            )

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(header)
            f.write("\n".join(rows))

        logger.info("Saved artifact: %s", filename)


def _save_stage_3_files(
    run_dir: str,
    scored_results: list[dict[str, Any]],
) -> None:
    """
    Save one STAGE_03 .md file per intent showing the TOP-5 articles
    ranked by cohere_score (descending).
    Filename: STAGE_03_[i1]_-_Intent_text_here.md
    """
    for item in scored_results:
        intent_id = item["intent_id"]
        intent_text = item["intent"]
        guidance = item["search_guidance"]
        articles = item.get("articles", [])

        # sort by cohere_score desc and take top 5
        top5 = sorted(
            articles,
            key=lambda a: a.get("cohere_score", 0.0),
            reverse=True,
        )[:5]

        safe_intent = _sanitize_filename(intent_text)
        filename = f"STAGE_03_[{intent_id}]_-_{safe_intent}.md"
        filepath = os.path.join(run_dir, filename)

        header = (
            f"# [{intent_id}] Cohere Rerank — Top-5\n"
            f"**Intent:** {intent_text}\n"
            f"**Search guidance:** {guidance}\n"
            f"\n---\n\n"
        )

        rows: list[str] = []
        for rank, art in enumerate(top5, start=1):
            rows.append(
                f"## #{rank} — {art.get('title', '(no title)')}\n"
                f"- **URL:** {art.get('url', '')}\n"
                f"- **Cohere score:** {art.get('cohere_score', 0.0):.4f}\n"
                f"- **Tavily score:** {art.get('score')}\n"
                f"- **Published:** {art.get('published_date', '')}\n\n"
                f"{art.get('content', '')}\n\n"
            )

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(header)
            f.write("\n".join(rows))

        logger.info("Saved Stage-3 report: %s", filename)


# ═════════════════════════════════════════════════════════════════════════════
# STAGE 1 — Extract 2-6 intents from a news article
# ═════════════════════════════════════════════════════════════════════════════
def stage_1_extract_intents(
    news_title: str,
    news_content: str,
    api_key: str,
) -> list[dict[str, str]]:
    """
    Ask Gemini to decompose a news article into 2-6 atomic, verifiable
    claims (intents).  The model itself decides how many intents are needed
    based on the article's complexity.

    Returns a list of dicts:
        [
            {
                "intent_id":        "i1",
                "intent":           "<atomic claim — doubles as Tavily search query>",
                "search_guidance":  "<what evidence to look for: supporting / refuting>"
            },
            ...
        ]
    """

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY_STAGE_1 is empty. "
            "Set it in .env or pass explicitly."
        )

    client = genai.Client(api_key=api_key)

    prompt = (
        "You are a professional fact-checker.\n"
        "Read the news article below and extract between 2 and 6 INTENTS — "
        "atomic, verifiable claims that can be checked against external sources.\n\n"
        "RULES:\n"
        "- If the article is short or straightforward, 2 intents may be enough.\n"
        "- If the article is long, complex, or contains multiple distinct claims, "
        "use up to 6 intents.\n"
        "- Each intent MUST be a concise, self-contained factual statement written "
        "as a natural-language search query (it will be sent directly to a search engine).\n"
        "- For each intent, write a 'search_guidance' field: a short instruction "
        "describing what kind of evidence a search engine should look for to "
        "CONFIRM or REFUTE this claim (e.g. official reports, statistics, "
        "press releases, court records, expert opinions).\n"
        "- Write everything in ENGLISH regardless of the article language.\n"
        "- Return STRICT JSON only, no markdown, no commentary.\n\n"
        "JSON schema:\n"
        "{\n"
        '  "intents": [\n'
        "    {\n"
        '      "intent_id": "i1",\n'
        '      "intent": "<atomic claim = search query>",\n'
        '      "search_guidance": "<what to look for to confirm or refute>"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        f"=== NEWS TITLE ===\n{news_title}\n\n"
        f"=== NEWS CONTENT ===\n{news_content[:30000]}\n"
    )

    # ── Call Gemini (with retry on 503 / 429) ─────────────────────────────
    MAX_RETRIES = 10
    RETRY_SLEEP = 10  # seconds
    payload = {}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info("Gemini request attempt %d/%d ...", attempt, MAX_RETRIES)
            resp = client.models.generate_content(
                model="gemini-3.1-flash-lite-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )
            payload = _safe_json_loads(resp.text, {})
            logger.info("Gemini responded successfully on attempt %d.", attempt)
            break  # success → exit retry loop

        except Exception as e:
            error_str = str(e)
            is_retryable = any(code in error_str for code in ["503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED"])

            if is_retryable and attempt < MAX_RETRIES:
                logger.warning(
                    "Gemini returned a retryable error (attempt %d/%d): %s. "
                    "Sleeping %d seconds before retry...",
                    attempt, MAX_RETRIES, e, RETRY_SLEEP,
                )
                time.sleep(RETRY_SLEEP)
            else:
                logger.error(
                    "Gemini intent extraction failed on attempt %d/%d: %s",
                    attempt, MAX_RETRIES, e,
                )
                payload = {}
                break

    # ── Validate & normalise ─────────────────────────────────────────────
    raw_intents = (
        payload.get("intents") if isinstance(payload, dict) else None
    )
    if not isinstance(raw_intents, list):
        raw_intents = []

    intents: list[dict[str, str]] = []
    for idx, item in enumerate(raw_intents):
        if not isinstance(item, dict):
            continue

        intent_id = str(item.get("intent_id") or f"i{idx + 1}")
        intent_text = str(item.get("intent") or "").strip()
        guidance = str(item.get("search_guidance") or "").strip()

        if not intent_text:
            continue  # skip empty intents

        intents.append({
            "intent_id": intent_id,
            "intent": intent_text,
            "search_guidance": guidance or "Look for official sources, news reports, or expert analysis confirming or denying this claim.",
        })

    # Enforce 2-6 range
    intents = intents[:6]

    if len(intents) < 2:
        logger.warning(
            "Gemini returned %d intent(s), which is below the minimum of 2. "
            "Raw payload: %s",
            len(intents),
            json.dumps(payload, ensure_ascii=False)[:500],
        )
        raise RuntimeError(
            f"Stage 1 failed: expected 2-6 intents, got {len(intents)}. "
            "Check API key and prompt."
        )

    _print_intents(intents)
    return intents


# ═════════════════════════════════════════════════════════════════════════════
# STAGE 2 — Async Tavily search (distribute intents across API keys)
# ═════════════════════════════════════════════════════════════════════════════
async def _search_one_intent(
    intent: dict[str, str],
    news_date: str,
    api_key: str,
    key_index: int,
    key_lock: asyncio.Lock,
) -> dict[str, Any]:
    """
    Search Tavily for a single intent.
    Uses a per-key lock to ensure at least ~1 second gap between requests
    on the same API key. Retries once after 10 seconds on failure.
    """
    intent_id = intent["intent_id"]
    query = intent["intent"]
    MAX_RETRIES = 10
    RETRY_SLEEP = 10  # seconds

    for attempt in range(1, MAX_RETRIES + 1):
        # Acquire the lock for this key so no two requests hit it at once
        async with key_lock:
            logger.info(
                "[Stage 2] Searching intent %s via Tavily key #%d (attempt %d/%d) ...",
                intent_id, key_index + 1, attempt, MAX_RETRIES,
            )
            try:
                # Tavily client is synchronous → run in thread pool
                loop = asyncio.get_running_loop()
                tavily = TavilyClient(api_key=api_key)

                response = await loop.run_in_executor(
                    None,
                    lambda: tavily.search(
                        query=f"{query} {news_date}",
                        search_depth="advanced",
                        include_raw_content=True,
                        max_results=20,
                    ),
                )

                articles = []
                for item in response.get("results", []) or []:
                    cleaned = _clean_raw_content(item.get("raw_content", ""))
                    articles.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", ""),
                        "score": item.get("score"),
                        "published_date": item.get("published_date", ""),
                        "full_content": cleaned,
                    })

                logger.info(
                    "[Stage 2] Intent %s — found %d article(s) on attempt %d.",
                    intent_id, len(articles), attempt,
                )

                # 1-second cooldown before releasing the lock,
                # so the next request on this key waits at least 1 second
                await asyncio.sleep(1)

                return {
                    "intent_id": intent_id,
                    "intent": query,
                    "search_guidance": intent["search_guidance"],
                    "articles": articles,
                }

            except Exception as e:
                logger.warning(
                    "[Stage 2] Tavily search failed for intent %s (key #%d, attempt %d/%d): %s",
                    intent_id, key_index + 1, attempt, MAX_RETRIES, e,
                )
                # Release the lock before sleeping on retry
                # (the `async with` will release it at this point)

        # Sleep OUTSIDE the lock so other intents can use this key
        if attempt < MAX_RETRIES:
            logger.info(
                "[Stage 2] Waiting %d seconds before retrying intent %s ...",
                RETRY_SLEEP, intent_id,
            )
            await asyncio.sleep(RETRY_SLEEP)

    # All retries exhausted
    logger.error("[Stage 2] All retries exhausted for intent %s.", intent_id)
    return {
        "intent_id": intent_id,
        "intent": query,
        "search_guidance": intent["search_guidance"],
        "articles": [],
        "error": "all_retries_exhausted",
    }


async def stage_2_search_intents(
    intents: list[dict[str, str]],
    news_date: str,
    tavily_keys: list[str],
) -> list[dict[str, Any]]:
    """
    Distribute intents across Tavily API keys (round-robin) and search
    them asynchronously. Each key gets its own lock to enforce a minimum
    1-second gap between requests on the same key.

    Returns a list of dicts (one per intent):
        [
            {
                "intent_id":        "i1",
                "intent":           "<search query>",
                "search_guidance":  "<what to look for>",
                "articles":         [{ "url", "title", "snippet", ... }, ...]
            },
            ...
        ]
    """
    logger.info(
        "[Stage 2] Starting async search: %d intent(s) across %d Tavily key(s).",
        len(intents), len(tavily_keys),
    )

    # One lock per API key → prevents simultaneous requests on the same key
    key_locks = [asyncio.Lock() for _ in tavily_keys]

    tasks = []
    for idx, intent in enumerate(intents):
        key_index = idx % len(tavily_keys)
        tasks.append(
            _search_one_intent(
                intent=intent,
                news_date=news_date,
                api_key=tavily_keys[key_index],
                key_index=key_index,
                key_lock=key_locks[key_index],
            )
        )

    results = await asyncio.gather(*tasks)
    return list(results)


# ═════════════════════════════════════════════════════════════════════════════
# STAGE 3 — Cohere Rerank (parallel, round-robin across API keys)
# ═════════════════════════════════════════════════════════════════════════════
async def _rerank_one_intent(
    item: dict[str, Any],
    api_key: str,
    key_index: int,
) -> dict[str, Any]:
    """
    Call Cohere Rerank for a single intent.  The synchronous SDK call is
    offloaded to a thread-pool so all intents run concurrently.

    Query  = intent text + search_guidance (gives Cohere full context).
    Docs   = full_content if available, otherwise content (Tavily snippet).
    top_n  = total number of docs so every article receives a score.
    """
    intent_id   = item["intent_id"]
    intent_text = item["intent"]
    guidance    = item["search_guidance"]
    articles    = item.get("articles", [])

    query = f"{intent_text}. {guidance}"

    # Build document texts and keep a parallel index
    doc_texts: list[str] = []
    for art in articles:
        text = art.get("full_content") or art.get("content") or ""
        doc_texts.append(text[:4096])  # Cohere has a per-doc token limit

    # Default: no score
    for art in articles:
        art.setdefault("cohere_score", 0.0)

    if not doc_texts:
        logger.warning("[Stage 3] Intent %s has no articles to rerank.", intent_id)
        return item

    logger.info(
        "[Stage 3] Reranking %d doc(s) for intent %s via Cohere key #%d ...",
        len(doc_texts), intent_id, key_index + 1,
    )

    MAX_RETRIES = 5
    RETRY_SLEEP = 10

    loop = asyncio.get_running_loop()
    co   = cohere.ClientV2(api_key=api_key)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await loop.run_in_executor(
                None,
                lambda: co.rerank(
                    model="rerank-multilingual-v3.0",
                    query=query,
                    documents=doc_texts,
                    top_n=len(doc_texts),   # score ALL docs
                ),
            )

            # Map scores back by original index
            for result in response.results:
                articles[result.index]["cohere_score"] = float(
                    result.relevance_score
                )

            # Sort articles inside the intent by score desc
            item["articles"] = sorted(
                articles,
                key=lambda a: a.get("cohere_score", 0.0),
                reverse=True,
            )

            logger.info(
                "[Stage 3] Intent %s — reranked %d doc(s) on attempt %d.",
                intent_id, len(doc_texts), attempt,
            )
            return item

        except Exception as e:
            logger.warning(
                "[Stage 3] Cohere rerank failed for intent %s "
                "(key #%d, attempt %d/%d): %s",
                intent_id, key_index + 1, attempt, MAX_RETRIES, e,
            )
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_SLEEP)

    logger.error(
        "[Stage 3] All retries exhausted for intent %s. Scores left at 0.",
        intent_id,
    )
    return item


async def stage_3_score_intents(
    search_results: list[dict[str, Any]],
    cohere_keys: list[str],
) -> list[dict[str, Any]]:
    """
    Rerank all intents in parallel, distributing them across Cohere API keys
    in round-robin fashion.

    Returns the same list with each article dict enriched by ``cohere_score``
    and each intent's ``articles`` sorted by that score (desc).
    All articles are kept — nothing is filtered here.
    """
    logger.info(
        "[Stage 3] Starting Cohere rerank: %d intent(s) across %d key(s).",
        len(search_results), len(cohere_keys),
    )

    tasks = [
        _rerank_one_intent(
            item=item,
            api_key=cohere_keys[idx % len(cohere_keys)],
            key_index=idx % len(cohere_keys),
        )
        for idx, item in enumerate(search_results)
    ]

    scored = await asyncio.gather(*tasks)
    return list(scored)


# ── Filter helper ─────────────────────────────────────────────────────────────
def _filter_top_articles(
    scored_results: list[dict[str, Any]],
    threshold: float = 0.5,
    max_per_intent: int = 3,
) -> list[dict[str, Any]]:
    """
    Return a copy of *scored_results* where each intent's ``articles`` list
    contains only articles with ``cohere_score >= threshold``, capped at
    *max_per_intent* (best-scoring first).

    Used to pass a clean, concise evidence set to Stage 4.
    """
    filtered: list[dict[str, Any]] = []
    for item in scored_results:
        passing = [
            art for art in item.get("articles", [])
            if art.get("cohere_score", 0.0) >= threshold
        ][:max_per_intent]
        filtered.append({**item, "articles": passing})

    total = sum(len(i["articles"]) for i in filtered)
    logger.info(
        "[Stage 3] Filter (threshold=%.2f, max=%d): %d article(s) kept across %d intent(s).",
        threshold, max_per_intent, total, len(filtered),
    )
    return filtered


# ═════════════════════════════════════════════════════════════════════════════
# STAGE 4 — Independent Worker LLMs (Groq Llama + Google Gemini)
# ═════════════════════════════════════════════════════════════════════════════

# Groq Llama model used by the Stage-4 worker
_GROQ_LLAMA_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

_WORKER_SYSTEM_PROMPT = (
    "You are an independent fact-checking analyst. "
    "You will receive the full text of a news article along with a set of "
    "verifiable claims (intents) extracted from it, each paired with the top "
    "relevant reference articles found on the web. "
    "Analyse ALL claims together using ONLY the provided reference material. "
    "Be rigorous, critical and logical — do not use external knowledge. "
    "At the end of your analysis you MUST issue a single verdict for the entire "
    "news article chosen strictly from this list: "
    "fact, partial, false-fake, clickbait, opinion, satire, unverifiable. "
    "Use 'fact' when all or nearly all key claims are confirmed as true. "
    "Use 'partial' when there is a mix: some claims are confirmed TRUE, while others are explicitly proven FALSE or MISLEADING. "
    "Do NOT use 'partial' if a claim is simply missing evidence (use 'unverifiable' or 'fact' instead). "
    "Use 'false-fake' when the majority of key claims are disproven. "
    "Use 'unverifiable' when most claims lack enough evidence to be confirmed or denied. "
    "Format the verdict on its own line as: VERDICT: <verdict>"
)


def _build_worker_user_prompt(
    news_content: str,
    intents: list[dict[str, str]],
    top_articles: list[dict[str, Any]],
) -> str:
    """
    Build a single unified prompt for a Stage-4 worker model.

    Parameters
    ----------
    news_content  : Full original news text.
    intents       : All extracted intents with intent_id, intent, search_guidance.
    top_articles  : Filtered/reranked results — one entry per intent,
                    each with .articles list (top-3 after Cohere filter).
    """
    # Build a lookup: intent_id -> article list
    articles_by_id: dict[str, list[dict[str, Any]]] = {
        item["intent_id"]: item.get("articles", []) for item in top_articles
    }

    intent_blocks: list[str] = []
    for intent in intents:
        iid  = intent["intent_id"]
        text = intent["intent"]
        guid = intent["search_guidance"]
        arts = articles_by_id.get(iid, [])

        art_lines: list[str] = []
        for i, art in enumerate(arts[:3], start=1):
            body = (art.get("full_content") or art.get("content") or "").strip()
            body = body[:5000]
            art_lines.append(
                f"  [Article {i}]\n"
                f"  Title: {art.get('title', '(no title)')}\n"
                f"  URL: {art.get('url', '')}\n"
                f"  Content:\n{body}"
            )

        arts_text = ("\n\n".join(art_lines)) if art_lines else "  (no articles found for this claim)"

        intent_blocks.append(
            f"--- CLAIM [{iid}] ---\n"
            f"Claim: {text}\n"
            f"Search guidance: {guid}\n\n"
            f"Reference articles:\n{arts_text}"
        )

    claims_section = "\n\n".join(intent_blocks)

    return (
        f"=== ORIGINAL NEWS ARTICLE ===\n"
        f"{news_content[:8000]}\n\n"
        f"=== CLAIMS TO VERIFY ===\n"
        f"{claims_section}\n\n"
        "=== YOUR TASK ===\n"
        "1. For EACH claim above, write 1-2 paragraphs: "
        "what the reference articles confirm, refute, or leave unresolved.\n"
        "2. Note any contradictions between sources.\n"
        "3. After analysing all claims, write an overall reasoning paragraph "
        "summarising your impression of the entire article.\n"
        "4. On the very last line, state your verdict in EXACTLY this format:\n"
        "   VERDICT: <one of: fact, false-fake, clickbait, opinion, satire, unverifiable>"
    )


async def _call_groq_worker(
    api_key: str,
    system_prompt: str,
    user_prompt: str,
) -> str:
    """
    Call Groq Llama (meta-llama/llama-4-scout-17b-16e-instruct) as a
    Stage-4 worker via the official ``groq`` async SDK.
    Returns the model's text reply, or an error string on failure.
    """
    from groq import AsyncGroq

    MAX_RETRIES = 5
    RETRY_SLEEP = 10

    client = AsyncGroq(api_key=api_key)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                "[Stage 4 / GROQ-LLAMA] Calling '%s' (attempt %d/%d) ...",
                _GROQ_LLAMA_MODEL, attempt, MAX_RETRIES,
            )
            response = await client.chat.completions.create(
                model=_GROQ_LLAMA_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=0.3,
                max_completion_tokens=2048,
                stream=False,
            )
            text = response.choices[0].message.content or ""
            logger.info(
                "[Stage 4 / GROQ-LLAMA] Responded (%d chars).", len(text)
            )
            return text

        except Exception as e:
            logger.warning(
                "[Stage 4 / GROQ-LLAMA] Call failed (attempt %d/%d): %s",
                attempt, MAX_RETRIES, e,
            )
            if attempt < MAX_RETRIES:
                logger.info(
                    "[Stage 4 / GROQ-LLAMA] Waiting %d s before retry...", RETRY_SLEEP
                )
                await asyncio.sleep(RETRY_SLEEP)

    return "[ERROR] Groq-Llama worker failed after all retries."


async def _call_gemini_worker(
    api_key: str,
    system_prompt: str,
    user_prompt: str,
) -> str:
    """
    Call Gemini Flash as the fourth Stage-4 worker.
    Returns the model's text reply, or an error string on failure.
    """
    MAX_RETRIES = 5
    RETRY_SLEEP = 10

    client = genai.Client(api_key=api_key)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                "[Stage 4 / GEMINI] Calling Gemini Flash worker (attempt %d/%d) ...",
                attempt, MAX_RETRIES,
            )
            resp = client.models.generate_content(
                model="gemini-3.1-flash-lite-preview",
                contents=f"{system_prompt}\n\n{user_prompt}",
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=1024,
                ),
            )
            text = resp.text or ""
            logger.info(
                "[Stage 4 / GEMINI] Gemini worker responded (%d chars).", len(text)
            )
            return text

        except Exception as e:
            logger.warning(
                "[Stage 4 / GEMINI] Call failed (attempt %d/%d): %s",
                attempt, MAX_RETRIES, e,
            )
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_SLEEP)

    return "[ERROR] Gemini worker failed after all retries."


async def stage_4_workers_analysis(
    news_content: str,
    intents: list[dict[str, str]],
    top_articles: list[dict[str, Any]],
    api_keys: dict[str, str],
) -> dict[str, str]:
    """
    Call each of the 2 LLM workers EXACTLY ONCE for the entire news article.

    Builds a single unified prompt containing all intents + their top-3
    reference articles, then fires 2 parallel API calls:
      - groq_llama : Groq meta-llama/llama-4-scout-17b-16e-instruct
      - gemini     : Google Gemini Flash

    Parameters
    ----------
    news_content : Full original news text.
    intents      : All intents extracted in Stage 1.
    top_articles : Filtered reranked results from Stage 3 (one entry per intent).
    api_keys     : Must contain keys 'groq_llama' and 'gemini'.

    Returns
    -------
    dict mapping worker name -> full analytical report string::

        {
            "groq_llama": "<report with VERDICT: ...>",
            "gemini":     "<report with VERDICT: ...>",
        }
    """
    logger.info("[Stage 4] Building unified prompt for 2 workers...")

    user_prompt = _build_worker_user_prompt(news_content, intents, top_articles)

    logger.info(
        "[Stage 4] Unified prompt ready (%d chars). Launching 2 parallel worker calls...",
        len(user_prompt),
    )

    # Groq and Gemini are independent providers — no shared lock needed.
    groq_task = _call_groq_worker(
        api_key=api_keys["groq_llama"],
        system_prompt=_WORKER_SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )
    gemini_task = _call_gemini_worker(
        api_key=api_keys["gemini"],
        system_prompt=_WORKER_SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    groq_report, gemini_report = await asyncio.gather(groq_task, gemini_task)

    workers_data: dict[str, str] = {
        "groq_llama": groq_report,
        "gemini":     gemini_report,
    }

    logger.info("[Stage 4] All 2 workers completed.")
    return workers_data


# ── Stage 4: Markdown report helpers ─────────────────────────────────────────
def _save_stage_4_worker_reports(
    run_dir: str,
    workers_data: dict[str, str],
) -> None:
    """
    Save one .md file per worker (qwen, gpt, glm, gemini).
    workers_data is now a flat dict: {worker_name -> full_report_text}.

    Filename pattern: STAGE_04_WORKER_<NAME>.md
    """
    for name, report in workers_data.items():
        filename = f"STAGE_04_WORKER_{name.upper()}.md"
        filepath = os.path.join(run_dir, filename)

        content = (
            f"# Stage 4 — Worker Report: {name.upper()}\n"
            f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
            "\n---\n\n"
            f"{report}\n"
        )

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info("[Stage 4] Saved worker report: %s", filename)


# ═════════════════════════════════════════════════════════════════════════════
# STAGE 5 — Supreme Judge (Gemini Flash synthesises everything)
# ═════════════════════════════════════════════════════════════════════════════

_JUDGE_SYSTEM_PROMPT = (
    "You are the Supreme Fact-Checking Judge. "
    "Your goal is to analyze a news article, evaluate multiple atomic claims (intents) "
    "based on evidence provided by search engines and preliminary reports from "
    "independent AI workers. "
    "You must output your final verdict in STRICT JSON format, following the required schema."
)

_JUDGE_JSON_SCHEMA = """
{
  "final_verdict": "false-fake",
  "overall_summary": "General summary of the fact-check for the entire news article...",
  "intents_analysis": [
    {
      "intent_id": "i1",
      "intent_verdict": "fact",
      "explanation": "The claim is supported by multiple sources. According to the geological survey [1], the amber was indeed found in the region. Furthermore, experts confirm the dating [2].",
      "references": {
        "1": "https://url1.com/article",
        "2": "https://url2.com/news"
      }
    }
  ]
}
"""


def _build_judge_user_prompt(
    news_title: str,
    news_content: str,
    intents: list[dict[str, str]],
    top_articles: list[dict[str, Any]],
    workers_data: dict[str, str],
) -> str:
    """
    Build the context prompt for the Stage-5 Judge model.

    Parameters
    ----------
    news_title    : Original news headline.
    news_content  : Original news body.
    intents       : All intents from Stage 1.
    top_articles  : Filtered articles from Stage 3 (one entry per intent).
    workers_data  : Flat dict {worker_name -> full_report_text} from Stage 4.
    """
    # Build a lookup: intent_id -> article list
    articles_by_id: dict[str, list[dict[str, Any]]] = {
        item["intent_id"]: item.get("articles", []) for item in top_articles
    }

    # Section 1: intents + their sources
    intent_blocks: list[str] = []
    for intent in intents:
        iid  = intent["intent_id"]
        text = intent["intent"]
        arts = articles_by_id.get(iid, [])

        source_lines: list[str] = []
        for src_num, art in enumerate(arts[:3], start=1):
            snippet = (
                art.get("full_content") or art.get("content") or ""
            ).strip()[:1200]
            source_lines.append(
                f"  [Source {src_num}] URL: {art.get('url', '')}\n"
                f"  Content: {snippet}"
            )
        sources_text = "\n".join(source_lines) if source_lines else "  (no sources)"

        intent_blocks.append(
            f"=== CLAIM [{iid}]: {text} ===\n"
            f"SOURCES:\n{sources_text}\n"
            "=========================================="
        )

    intents_section = "\n\n".join(intent_blocks)

    # Section 2: worker reports
    worker_section_lines: list[str] = []
    for worker_name, report in workers_data.items():
        worker_section_lines.append(
            f"--- {worker_name.upper()} REPORT ---\n{report}\n"
        )
    worker_section = "\n".join(worker_section_lines)

    return (
        f"**Original News Title:** {news_title}\n"
        f"**Original News Content:**\n{news_content[:4000]}\n\n"
        "Here is the breakdown of the claims (intents) with their source articles, "
        "followed by the independent analytical reports from two AI workers.\n\n"
        f"{intents_section}\n\n"
        "=== WORKER ANALYTICAL REPORTS ===\n"
        f"{worker_section}\n"
        "Based on all the information above, provide a final JSON response.\n\n"
        "**CRITICAL INSTRUCTIONS FOR JSON FORMAT:**\n"
        "1. `final_verdict` must be EXACTLY one of: fact, partial, false-fake, clickbait, opinion, satire, unverifiable.\n"
        "2. For each intent in `intents_analysis`, `intent_verdict` must also be one of those seven values.\n"
        "3. **LANGUAGE REQUIREMENT:** Write `overall_summary` and every `explanation` field "
        "in UKRAINIAN (українська мова). All other fields (verdict values, URLs, citation markers) remain as specified.\n"
        "4. For each intent, provide an `explanation` (1-2 paragraphs) citing evidence.\n"
        "5. **CITATIONS ARE MANDATORY:** In your `explanation` text, cite sources as [1], [2], etc., "
        "matching the Source numbers listed above for each claim.\n"
        "6. `references` object: map citation numbers to their exact URLs.\n"
        "7. **VERDICT SELECTION LOGIC:**\n"
        "   - Use 'fact' when ALL key claims are confirmed by sources. If most claims are true and only a minor one is unverifiable, 'fact' is still acceptable.\n"
        "   - Use 'partial' ONLY when the article contains a mix of confirmed TRUTH and confirmed LIES/MISINFORMATION. At least one claim must be true and at least one must be proven false/fake.\n"
        "   - Use 'false-fake' when the MAJORITY of key claims or the central thesis is disproven.\n"
        "   - Use 'unverifiable' when sources are insufficient to confirm OR deny the claims for the majority of the article.\n"
        "8. **UNVERIFIABLE CLAUSE:** If you return 'unverifiable' as the final_verdict, you MUST detail in 'overall_summary' "
        "exactly WHY the news cannot be verified (e.g., lack of reliable sources, contradicting data, or off-topic search results).\n"
        "9. Output ONLY valid JSON. No markdown, no code blocks.\n\n"
        f"**JSON SCHEMA:**\n{_JUDGE_JSON_SCHEMA}"
    )


async def stage_5_judge_synthesis(
    news_title: str,
    news_content: str,
    intents: list[dict[str, str]],
    top_articles: list[dict[str, Any]],
    workers_data: dict[str, str],
    judge_api_key: str,
) -> dict[str, Any]:
    """
    Send the full context (article, intents, sources, worker reports) to the
    Gemini Judge. Returns parsed JSON verdict dict (or error dict on failure).
    """
    MAX_RETRIES = 5
    RETRY_SLEEP = 15

    # Валідні вердикти для перевірки
    VALID_VERDICTS = {"fact", "partial", "false-fake", "clickbait", "opinion", "satire", "unverifiable"}

    client = genai.Client(api_key=judge_api_key)
    base_user_prompt = _build_judge_user_prompt(
        news_title, news_content, intents, top_articles, workers_data
    )

    logger.info("[Stage 5] Sending full context to Gemini Judge (%d chars)...", len(base_user_prompt))

    current_prompt = base_user_prompt
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                "[Stage 5] Judge request attempt %d/%d ...", attempt, MAX_RETRIES
            )
            resp = client.models.generate_content(
                model="gemini-3.1-flash-lite-preview",
                contents=f"{_JUDGE_SYSTEM_PROMPT}\n\n{current_prompt}",
                config=types.GenerateContentConfig(
                    temperature=0.1,           # low temp for consistent JSON
                    max_output_tokens=8192,
                ),
            )
            raw_text = resp.text or ""
            verdict  = _safe_json_loads(raw_text, {})

            if verdict and isinstance(verdict, dict) and "final_verdict" in verdict:
                fv = verdict.get("final_verdict")

                # Перевіряємо, чи вердикт є у дозволеному списку
                if fv in VALID_VERDICTS:
                    logger.info("[Stage 5] Judge verdict received: %s", fv)
                    return verdict
                else:
                    logger.warning("[Stage 5] Invalid final_verdict '%s'. Retrying...", fv)
                    # Додаємо повідомлення про помилку у промпт для наступної спроби
                    current_prompt = base_user_prompt + f"\n\nВАЖЛИВО: У твоїй попередній відповіді поле 'final_verdict' мало значення '{fv}'. Це НЕПРАВИЛЬНО. Значення 'final_verdict' має бути ТІЛЬКИ одним з наступних: 'fact', 'partial', 'false-fake', 'clickbait', 'opinion', 'satire', 'unverifiable'."
                    continue

            # Model returned something non-JSON or missing key
            logger.warning(
                "[Stage 5] Judge returned non-JSON or missing 'final_verdict' "
                "(attempt %d/%d). Raw (first 300 chars): %s",
                attempt, MAX_RETRIES, raw_text[:300],
            )
            # Вказуємо промпту виправити структуру JSON
            current_prompt = base_user_prompt + "\n\nВАЖЛИВО: Твоя попередня відповідь була з невірною структурою JSON або відсутнім полем 'final_verdict'. Поверни ЛИШЕ валідний JSON з полем 'final_verdict'."

        except Exception as e:
            logger.warning(
                "[Stage 5] Judge call failed (attempt %d/%d): %s",
                attempt, MAX_RETRIES, e,
            )

        if attempt < MAX_RETRIES:
            await asyncio.sleep(RETRY_SLEEP)

    logger.error("[Stage 5] All retries exhausted. Returning error dict.")
    return {
        "final_verdict": "unverifiable",
        "overall_summary": "Stage 5 failed: judge model did not respond with valid JSON or supported format.",
        "intents_analysis": [],
        "error": "judge_failed_all_retries",
    }


def _save_stage_5_verdict(
    run_dir: str,
    verdict: dict[str, Any],
) -> None:
    """
    Save the Stage-5 judge verdict as a JSON blob inside a .md file.
    Filename: STAGE_05_JUDGE_VERDICT.md
    """
    filename = "STAGE_05_JUDGE_VERDICT.md"
    filepath = os.path.join(run_dir, filename)

    header = (
        f"# Stage 5 — Supreme Judge Verdict\n"
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
        f"*Final Verdict: **{verdict.get('final_verdict', 'N/A')}***\n"
        "\n---\n"
        "```json\n"
    )
    footer = "\n```\n"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(json.dumps(verdict, ensure_ascii=False, indent=2))
        f.write(footer)

    logger.info("[Stage 5] Verdict saved: %s", filename)


# ═════════════════════════════════════════════════════════════════════════════
# MAIN — entry point
# ═════════════════════════════════════════════════════════════════════════════

async def execute_pipeline(news_title: str, news_content: str, news_date: str = None, on_progress=None) -> dict[str, Any]:
    """
    Головний інтерфейс (асинхронний) для запуску всього процесу перевірки.
    Повертає фінальний вердикт як словник.
    """
    if not news_date:
        news_date = datetime.now().strftime("%Y-%m-%d")

    artifacts = {}

    def _trigger_progress():
        if on_progress:
            try:
                on_progress(artifacts)
            except Exception as e:
                logger.warning(f"Error in progress callback: {e}")

    # ── Stage 1: Extract intents ─────────────────────────────────────────
    logger.info("Stage 1 — Extracting intents from the news article...")
    intents = stage_1_extract_intents(
        news_title=news_title,
        news_content=news_content,
        api_key=os.getenv("GEMINI_API_KEY_STAGE_1", ""),
    )

    if not intents:
        # Якщо інтентів взагалі немає
        return {
            "final_verdict": "unverifiable",
            "overall_summary": "Не вдалося виділити ключові твердження (intents) зі статті.",
            "intents_analysis": [],
        }

    # ── Stage 2: Search intents via Tavily ───────────────────────────────
    logger.info("Stage 2 — Searching intents via Tavily...")
    tavily_keys = _load_tavily_keys()
    search_results = await stage_2_search_intents(
        intents=intents,
        news_date=news_date,
        tavily_keys=tavily_keys,
    )
    _print_search_results(search_results)

    # ── Stage 3: Cohere Rerank ───────────────────────────────────────────
    logger.info("Stage 3 — Reranking articles via Cohere...")
    cohere_keys = _load_cohere_keys()
    scored_results = await stage_3_score_intents(
        search_results=search_results,
        cohere_keys=cohere_keys,
    )
    top_articles = _filter_top_articles(scored_results, threshold=0.5, max_per_intent=3)

    # Populate artifacts for Stages 1-3
    for item in scored_results:
        intent_id = item["intent_id"]
        intent_text = item["intent"]
        guidance = item["search_guidance"]
        articles = item.get("articles", [])
        safe_intent = _sanitize_filename(intent_text)
        
        # Stage 1-2
        filename_12 = f"STAGE_01-02_[{intent_id}]_-_{safe_intent}.md"
        header_12 = f"# [{intent_id}]\n**Intent:** {intent_text}\n**Guide:** {guidance}\n\n---\n## Tavily Search Results ({len(articles)} articles)\n\n"
        rows_12 = []
        for art in articles:
            cohere_score = art.get("cohere_score")
            score_line = f"- **Cohere score:** {cohere_score:.4f}\n" if cohere_score is not None else ""
            rows_12.append(f"### {art.get('title', '(no title)')}\n- **URL:** {art.get('url', '')}\n- **Relevance score:** {art.get('score')}\n{score_line}- **Published:** {art.get('published_date', '')}\n\n{art.get('content', '')}\n\n")
        artifacts[filename_12] = header_12 + "\n".join(rows_12)

        # Stage 3
        top5 = sorted(articles, key=lambda a: a.get("cohere_score", 0.0), reverse=True)[:5]
        filename_3 = f"STAGE_03_[{intent_id}]_-_{safe_intent}.md"
        header_3 = f"# [{intent_id}] Cohere Rerank — Top-5\n**Intent:** {intent_text}\n**Search guidance:** {guidance}\n\n---\n\n"
        rows_3 = []
        for rank, art in enumerate(top5, start=1):
            rows_3.append(f"## #{rank} — {art.get('title', '(no title)')}\n- **URL:** {art.get('url', '')}\n- **Cohere score:** {art.get('cohere_score', 0.0):.4f}\n- **Tavily score:** {art.get('score')}\n- **Published:** {art.get('published_date', '')}\n\n{art.get('content', '')}\n\n")
        artifacts[filename_3] = header_3 + "\n".join(rows_3)
    
    _trigger_progress()

    logger.info("Stage 3 complete. Top articles ready for Stage 4: %d intent(s).", len(top_articles))

    # ── Stage 4: Workers analysis ────────────────────────────────────────
    logger.info("Stage 4 — Running parallel LLM worker analysis...")
    worker_api_keys = {
        "groq_llama": os.getenv("COUNCIL_GROQ_LLAMA_API_KEY", ""),
        "gemini":     os.getenv("COUNCIL_GEMINI_API_KEY", ""),
    }
    workers_data = await stage_4_workers_analysis(
        news_content=news_content,
        intents=intents,
        top_articles=top_articles,
        api_keys=worker_api_keys,
    )

    # Populate artifacts for Stage 4
    for name, report in workers_data.items():
        filename = f"STAGE_04_WORKER_{name.upper()}.md"
        artifacts[filename] = f"# Stage 4 — Worker Report: {name.upper()}\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n---\n\n{report}\n"
    
    _trigger_progress()
    logger.info("Stage 4 complete.")

    # ── Stage 5: Judge synthesis ─────────────────────────────────────────
    logger.info("Stage 5 — Sending everything to the Supreme Judge...")
    judge_verdict = await stage_5_judge_synthesis(
        news_title=news_title,
        news_content=news_content,
        intents=intents,
        top_articles=top_articles,
        workers_data=workers_data,
        judge_api_key=os.getenv("COUNCIL_SUMMARY_GEMINI_API_KEY", ""),
    )

    # Populate artifact for Stage 5
    filename_5 = "STAGE_05_JUDGE_VERDICT.md"
    header_5 = f"# Stage 5 — Supreme Judge Verdict\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n*Final Verdict: **{judge_verdict.get('final_verdict', 'N/A')}***\n\n---\n```json\n"
    artifacts[filename_5] = header_5 + json.dumps(judge_verdict, ensure_ascii=False, indent=2) + "\n```\n"
    
    judge_verdict["artifacts"] = artifacts
    _trigger_progress()

    return judge_verdict


@_async_timer
async def main() -> None:
    news = {
        "title": "Янтарь нашли подо льдами Антарктиды: ученые объяснили, что это значит",       # Заголовок новости
        "content": """Скрытый подо льдом Антарктиды фрагмент янтаря намекает на существование древних лесов там, где их быть не должно. Фрагмент янтаря, найденный в Пайн-Айлендской впадине, поменял  представление ученых о прошлом Антарктиды. Он показал, что смолистые деревья когда-то росли недалеко от Южного полюса. Фрагменту примерно от 92 до 83 млн лет и датируется он серединой мелового периода, пишет Daily Galaxy. Он обеспечивает прямую связь со временем, когда Антарктида была покрыта лесами. Отмечается, что это первый янтарь, когда-либо найденный в Антарктиде, что сразу же выделяет эту находку. Обнаружение янтаря в Антарктиде заполняет давний пробел в палеонтологической летописи. До этого самые южные известные месторождения датировались серединой мелового периода в южной Австралии и Новой Зеландии. По словам исследовательской группы под руководством Йоханны Клагес из Бременского университета, эта находка подтверждает, что подходящие условия для образования смолы когда-то существовали даже в полярных регионах. Янтарь образуется из растительной смолы, обычно выделяемой голосеменными растениями. Клагес отметила, что смола представляет собой жирорастворимую смесь соединений, способных окаменевать при благоприятных условиях.\"Некоторые растительные смолы способны окаменевать при определенных условиях и сохраняться в геологической летописи в виде янтаря\", - сказал он. Антарктический образец указывает на то, что когда-то в болотистой среде умеренного тропического леса около Южного полюса росли хвойные леса.\"Антарктический янтарь, вероятно, содержит остатки коры деревьев в виде микроскопических включений\", - допустил соавтор исследования, ученый из Саксонского государственного управления по окружающей среде, сельскому хозяйству и геологии Хенни Гершель. Сам образец содержит прозрачные и полупрозрачные частицы, что указывает на хорошую сохранность. Как отметил Гершель, это, вероятно, означает, что янтарь был захоронен на небольшой глубине, избегая воздействия тепла и давления, которые могли бы его повредить. Исследователи также заметили признаки патологического выделения смолы - реакции деревьев, возникающей при повреждении паразитами или лесными пожарами. Этот процесс помогает запечатать кору и может задерживать частицы материала внутри смолы. Эти детали важны, потому что янтарь может действовать как капсула времени. Даже небольшой фрагмент может содержать подсказки об окружающей среде, в которой он образовался.\"Было очень интересно осознать, что в какой-то момент своей истории на всех семи континентах существовали климатические условия, позволявшие выживать деревьям, производящим смолу... Это открытие позволяет совершить путешествие в прошлое еще одним, более прямым способом\", - прокомментировала Клагес. Под водами озера Цяньдао в Китае дайверы нашли город, которому 600 лет. Он известный как Ши Чэн и сравнивается с Атлантидой из-за того, что  хорошо сохранился. Ши Чэн восходит к династии Восточная Хань и расширялся во времена династий Мин и Цин. В период своего расцвета это был региональный центр с полноценной городской структурой. Ши Чэн не исчез естественным образом. Его затопили в 1959 году, когда строили гидроэлектростанцию, создавшую озеро Цяньдао.""",     # Полный текст новости
        "date": "2026-04-27",
    }

    # ── Stage 1: Extract intents ─────────────────────────────────────────
    logger.info("Stage 1 — Extracting intents from the news article...")

    intents = stage_1_extract_intents(
        news_title=news["title"],
        news_content=news["content"],
        api_key=os.getenv("GEMINI_API_KEY_STAGE_1", ""),
    )

    # ── Stage 2: Search intents via Tavily ───────────────────────────────
    logger.info("Stage 2 — Searching intents via Tavily...")

    tavily_keys = _load_tavily_keys()

    search_results = await stage_2_search_intents(
        intents=intents,
        news_date=news["date"],
        tavily_keys=tavily_keys,
    )

    _print_search_results(search_results)

    # ── Create run directory (shared by all stages) ──────────────────────
    run_dir = _make_run_dir(news["title"])

    # ── Stage 3: Cohere Rerank ───────────────────────────────────────────
    logger.info("Stage 3 — Reranking articles via Cohere...")

    cohere_keys = _load_cohere_keys()

    scored_results = await stage_3_score_intents(
        search_results=search_results,
        cohere_keys=cohere_keys,
    )

    # Save ALL articles (with cohere_score) as Stage 1-2 artifacts
    _save_artifacts(run_dir, scored_results)

    # Save Stage-3 top-5-per-intent reports
    _save_stage_3_files(run_dir, scored_results)

    # Filter best articles for Stage 4
    top_articles = _filter_top_articles(scored_results, threshold=0.5, max_per_intent=3)

    logger.info(
        "Stage 3 complete. Top articles ready for Stage 4: %d intent(s).",
        len(top_articles),
    )

    # ── Stage 4: Workers analysis ────────────────────────────────────────
    logger.info("Stage 4 — Running parallel LLM worker analysis...")

    worker_api_keys = {
        "groq_llama": os.getenv("COUNCIL_GROQ_LLAMA_API_KEY", ""),
        "gemini":     os.getenv("COUNCIL_GEMINI_API_KEY", ""),
    }

    workers_data = await stage_4_workers_analysis(
        news_content=news["content"],
        intents=intents,
        top_articles=top_articles,
        api_keys=worker_api_keys,
    )

    # Save per-worker .md reports
    _save_stage_4_worker_reports(run_dir, workers_data)

    logger.info("Stage 4 complete. Worker reports saved (4 models × 1 call each).")

    # ── Stage 5: Judge synthesis ─────────────────────────────────────────
    logger.info("Stage 5 — Sending everything to the Supreme Judge...")

    judge_verdict = await stage_5_judge_synthesis(
        news_title=news["title"],
        news_content=news["content"],
        intents=intents,
        top_articles=top_articles,
        workers_data=workers_data,
        judge_api_key=os.getenv("COUNCIL_SUMMARY_GEMINI_API_KEY", ""),
    )

    # Save final verdict .md
    _save_stage_5_verdict(run_dir, judge_verdict)

    # ── Final summary ────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  PIPELINE COMPLETE")
    print(f"  Final verdict : {judge_verdict.get('final_verdict', 'N/A')}")
    print(f"  Run directory : {run_dir}")
    print("=" * 70 + "\n")


# ── Entry point ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    asyncio.run(main())
