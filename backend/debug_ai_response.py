import os
import sys
import django
import json
from datetime import datetime, timezone

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from news.ai_service import GeminiAIService, get_current_time_from_internet

def test_ai_verification(url):
    print(f"Testing URL: {url}")
    
    # Mock content for the specific NV.ua article to speed up (or we can use real scrapers if available)
    # The article is about meeting between Zelensky and Trump on Dec 28.
    title = "Україна та Європа мають підстави для оптимізму після нової зустрічі Трампа і Зеленського — Le Monde"
    content = """
    Французьке видання Le Monde аналізує результати зустрічі президента України Володимира Зеленського та новообраного президента США Дональда Трампа, що відбулася 28 грудня у Флориді. 
    Видання зазначає, що попри побоювання, зустріч пройшла у конструктивній атмосфері. 
    Основними темами були мирний план, військова допомога та майбутні гарантії безпеки для України.
    Зеленський наголосив на важливості "сили через мир", а Трамп висловив готовність сприяти завершенню війни.
    """
    
    service = GeminiAIService()
    
    # Check internet time first
    print("\n--- Checking Internet Time ---")
    try:
        current_time = get_current_time_from_internet()
        print(f"Internet Time (UTC): {current_time}")
    except Exception as e:
        print(f"Error getting internet time: {e}")
        current_time = datetime.now(timezone.utc)
    
    print("\n--- Sending request to Gemini ---")
    # We'll need to monkeypatch or capture the raw response
    # Let's just modify verify_news momentarily or use a trick
    
    # Actually, let's just use the service and if we want the raw response, 
    # we can see it in the logs if we set log level to DEBUG
    import logging
    logging.getLogger('news.ai_service').setLevel(logging.DEBUG)
    
    result = service.verify_news(title=title, content=content, url=url)
    
    # If the response was stored in the object during the call (it's not currently)
    # let's just look at the logs we already have from the previous run.
    
    print("\n--- Result from verify_news ---")
    print(json.dumps(result, indent=4, ensure_ascii=False))
    
    print("\n--- Analysis of fields ---")
    print(f"Verdict: {result.get('verdict')}")
    print(f"Summary length: {len(result.get('summary', ''))}")
    print(f"Has Analysis object: {'analysis' in result}")
    if 'analysis' in result:
        print(f"Analysis fields: {list(result['analysis'].keys())}")

if __name__ == "__main__":
    target_url = "https://nv.ua/ukr/world/geopolitics/zustrich-zelenskogo-i-trampa-28-grudnya-le-monde-nazvala-kilka-prichin-dlya-optimizmu-50571935.html"
    test_ai_verification(target_url)
