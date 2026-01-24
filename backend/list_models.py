import os
import sys
from google import genai

def list_my_models():
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("Error: GEMINI_API_KEY not found")
        return

    try:
        client = genai.Client(api_key=api_key)
        print("--- Available Models ---")
        # В новому SDK перелік моделей може бути в client.models.list()
        for model in client.models.list():
            print(f"Model: {model.name} (Supported: {model.supported_actions})")
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_my_models()
