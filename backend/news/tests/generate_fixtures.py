import os
import json
from pathlib import Path
import sys

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, backend_dir)

from news.parser_service import (
    TrafilaturaParser, NewspaperParser, ReadabilityParser, 
    GooseParser, BS4Parser
)

FIXTURES_DIR = Path(os.path.join(os.path.dirname(__file__), 'fixtures'))

parsers = [
    TrafilaturaParser(),
    NewspaperParser(),
    ReadabilityParser(),
    GooseParser(),
    BS4Parser()
]

def generate_markdown(file_path: Path):
    with open(file_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # Mock URL
    url = f"http://mock.local/{file_path.name}"

    md_content = f"# Парсинг результати для: {file_path.name}\n\n"

    for parser in parsers:
        parser_name = parser.__class__.__name__
        try:
            result = parser.parse(html, url)
        except Exception as e:
            result = {"error": str(e)}

        md_content += f"## {parser_name}\n\n"
        md_content += "```json\n"
        md_content += json.dumps(result, ensure_ascii=False, indent=2, default=str)
        md_content += "\n```\n\n"

    md_file_path = file_path.with_suffix('.md')
    with open(md_file_path, 'w', encoding='utf-8') as f:
        f.write(md_content)

    print(f"Generated {md_file_path.name}")

def main():
    if not FIXTURES_DIR.exists():
        print(f"Fixtures directory not found: {FIXTURES_DIR}")
        return

    html_files = list(FIXTURES_DIR.glob('*.html'))
    if not html_files:
        print("No .html files found in fixtures directory.")
        return

    for html_file in html_files:
        print(f"Processing {html_file.name}...")
        generate_markdown(html_file)

if __name__ == '__main__':
    main()
