import os
import sys
import django
import json

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from news.ai_service import GeminiAIService

def get_raw_gemini_response(url):
    title = "Україна та Європа мають підстави для оптимізму після нової зустрічі Трампа і Зеленського — Le Monde"
    content = "Французьке видання Le Monde аналізує результати зустрічі Зеленського та Трампа..."
    
    service = GeminiAIService()
    prompt = service.VERIFICATION_PROMPT.format(
        current_date="29 грудня 2025 року",
        title=title,
        content=content,
        url=url
    )
    
    # We use the internal run_gemini_subprocess to get the raw text
    try:
        raw_response = service.run_gemini_subprocess(prompt)
        print("RAW RESPONSE FROM GEMINI:")
        print("-" * 50)
        print(raw_response)
        print("-" * 50)
        
        parsed = service._parse_response(raw_response)
        print("PARSED RESULT:")
        print(json.dumps(parsed, indent=4, ensure_ascii=False))
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_raw_gemini_response("https://nv.ua/ukr/world/geopolitics/zustrich-zelenskogo-i-trampa-28-grudnya-le-monde-nazvala-kilka-prichin-dlya-optimizmu-50571935.html")
