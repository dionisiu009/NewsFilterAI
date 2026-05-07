#!/usr/bin/env python3
"""
Невеликий CLI-раннер для безпечного виклику Google Gemini в окремому процесі.
Приймає JSON в stdin:
{
  "prompt": "...",
  "model": "gemini-...",
  "max_output_tokens": 512
}
Виводить в stdout сиру текстову генерацію (як response.text від SDK).
Ошибки виводяться в stderr у вигляді трасування; код повернення != 0 при помилці.

Мета: ізолювати нативні краші бібліотеки genai/залежностей в окремому процесі.
"""
import json
import os
import sys
import traceback

MAX_STDIN_BYTES = 200 * 1024  # 200 KB

try:
    raw = sys.stdin.buffer.read(MAX_STDIN_BYTES + 1)
except Exception as e:
    print(f"Failed to read stdin: {e}", file=sys.stderr)
    sys.exit(3)

if len(raw) == 0:
    print("No input provided to gemini runner", file=sys.stderr)
    sys.exit(2)

if len(raw) > MAX_STDIN_BYTES:
    print("Input too large for gemini runner", file=sys.stderr)
    sys.exit(2)

try:
    payload = json.loads(raw.decode('utf-8'))
except Exception as e:
    print(f"Invalid JSON input: {e}", file=sys.stderr)
    sys.exit(2)

prompt = payload.get('prompt')
model = payload.get('model')
max_output_tokens = payload.get('max_output_tokens')

if not prompt:
    print('Missing prompt in input', file=sys.stderr)
    sys.exit(2)

api_key = os.environ.get('GEMINI_API_KEY')
if not api_key:
    print('ERROR: GEMINI_API_KEY is not set in environment!', file=sys.stderr)
    sys.exit(2)

try:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    config_kwargs = {}
    if isinstance(max_output_tokens, int):
        config_kwargs['max_output_tokens'] = max_output_tokens

    generation_config = types.GenerateContentConfig(
        temperature=0.1,
        top_p=0.95,
        top_k=40,
        **config_kwargs
    )

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=generation_config
    )

    output_text = None
    if hasattr(response, 'text'):
        output_text = response.text
    else:
        try:
            output_text = json.dumps(response, default=str)
        except Exception:
            output_text = str(response)

    if output_text is not None:
        try:
            sys.stdout.buffer.write(output_text.encode('utf-8'))
        except Exception:
            sys.stdout.write(output_text)
    
    sys.stdout.flush()
    sys.exit(0)

except Exception as e:
    print("\n" + "="*50, file=sys.stderr)
    print(f"GEMINI RUNNER EXCEPTION: {type(e).__name__}", file=sys.stderr)
    print(f"MESSAGE: {str(e)}", file=sys.stderr)
    print("="*50, file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.stderr.flush()
    sys.exit(3)

