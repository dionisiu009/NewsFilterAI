# ==============================================================================
# NEWSFILTERAI - TELEGRAM BOT (Aiogram)
# ==============================================================================
# Підтримує два режими: polling (локально) та webhook (через ngrok)
# ==============================================================================

import asyncio
import os
import sys
import re
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse

import aiohttp

# Додаємо шлях до Django проєкту для доступу до моделей
sys.path.append(str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode

# Завантажуємо змінні середовища
load_dotenv()

# Конфігурація
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
BACKEND_API_URL = os.getenv('BACKEND_API_URL', 'http://backend:8000/api')
NGROK_API_URL = os.getenv('NGROK_API_URL', 'http://ngrok:4040/api/tunnels')
USE_WEBHOOK = os.getenv('USE_WEBHOOK', 'false').lower() == 'true'
WEBHOOK_URL = os.getenv('WEBHOOK_URL', None)

# Таймаути для HTTP запитів (секунди)
REQUEST_TIMEOUT = 30
POLLING_TIMEOUT = 150  # Максимальний час очікування результату
POLLING_INTERVAL = 2  # Інтервал між запитами статусу

# Ініціалізація бота та диспетчера
# Використовуємо кастомну сесію для збільшення таймауту та стабільності
session = AiohttpSession()
bot = Bot(token=TELEGRAM_BOT_TOKEN, session=session)
dp = Dispatcher()


# ==============================================================================
# API CLIENT - Взаємодія з Django Backend
# ==============================================================================

class NewsFilterAPIClient:
    """
    Клієнт для взаємодії з Django Backend API.
    Використовує aiohttp для асинхронних HTTP запитів.
    """

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Отримує або створює HTTP сесію"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def close(self):
        """Закриває HTTP сесію"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def check_news(self, url: str) -> Dict[str, Any]:
        """
        Відправляє запит на перевірку новини.

        Args:
            url: URL новини для перевірки

        Returns:
            Відповідь від API (cached result або task_id)
        """
        session = await self._get_session()
        endpoint = f"{self.base_url}/check/"

        try:
            async with session.post(endpoint, json={"url": url}) as response:
                data = await response.json()
                data['status_code'] = response.status
                return data
        except aiohttp.ClientError as e:
            return {
                'error': True,
                'message': f'Помилка з\'єднання з сервером: {str(e)}'
            }
        except asyncio.TimeoutError:
            return {
                'error': True,
                'message': 'Таймаут запиту. Сервер не відповідає.'
            }

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Отримує статус Celery задачі.

        Args:
            task_id: ID задачі

        Returns:
            Статус та результат задачі
        """
        session = await self._get_session()
        endpoint = f"{self.base_url}/task-status/{task_id}/"

        try:
            async with session.get(endpoint) as response:
                data = await response.json()
                data['status_code'] = response.status
                return data
        except aiohttp.ClientError as e:
            return {
                'error': True,
                'message': f'Помилка отримання статусу: {str(e)}'
            }
        except asyncio.TimeoutError:
            return {
                'error': True,
                'message': 'Таймаут запиту статусу.'
            }

    async def check_domain(self, domain: str) -> Dict[str, Any]:
        """
        Перевіряє репутацію домену.

        Args:
            domain: Домен для перевірки

        Returns:
            Інформація про репутацію домену
        """
        session = await self._get_session()
        endpoint = f"{self.base_url}/domain-check/"

        try:
            async with session.get(endpoint, params={"domain": domain}) as response:
                return await response.json()
        except Exception:
            return {'reputation': 'unknown'}

    async def debug_check(self, url: str) -> Dict[str, Any]:
        """
        Діагностична перевірка URL.
        Повертає детальну інформацію про кожен крок.

        Args:
            url: URL для діагностики

        Returns:
            Результат діагностики
        """
        session = await self._get_session()
        endpoint = f"{self.base_url}/debug/check/"

        try:
            async with session.post(endpoint, json={"url": url}) as response:
                data = await response.json()
                data['status_code'] = response.status
                return data
        except aiohttp.ClientError as e:
            return {
                'error': True,
                'message': f'Помилка з\'єднання: {str(e)}'
            }
        except asyncio.TimeoutError:
            return {
                'error': True,
                'message': 'Таймаут запиту діагностики.'
            }

    async def wait_for_result(
        self,
        task_id: str,
        timeout: int = POLLING_TIMEOUT,
        interval: int = POLLING_INTERVAL
    ) -> Dict[str, Any]:
        """
        Очікує завершення задачі з polling.

        Args:
            task_id: ID задачі
            timeout: Максимальний час очікування (секунди)
            interval: Інтервал між запитами (секунди)

        Returns:
            Результат задачі або помилка таймауту
        """
        elapsed = 0

        while elapsed < timeout:
            status_data = await self.get_task_status(task_id)

            if status_data.get('error'):
                return status_data

            status = status_data.get('status', '').lower()

            if status == 'success':
                return status_data
            elif status == 'failure':
                return {
                    'error': True,
                    'message': status_data.get('error', 'Помилка обробки задачі')
                }

            # Ще обробляється - чекаємо
            await asyncio.sleep(interval)
            elapsed += interval

        return {
            'error': True,
            'message': 'Перевищено час очікування. Спробуйте пізніше.'
        }


# Глобальний API клієнт
api_client = NewsFilterAPIClient(BACKEND_API_URL)


# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

def extract_url(text: str) -> Optional[str]:
    """
    Витягує URL з тексту повідомлення.

    Args:
        text: Текст повідомлення

    Returns:
        Знайдений URL або None
    """
    # Регулярний вираз для пошуку URL
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    match = re.search(url_pattern, text)

    if match:
        url = match.group(0)
        # Видаляємо можливі зайві символи в кінці
        url = url.rstrip('.,;:!?)')
        return url

    return None


def format_verdict_emoji(verdict: str) -> str:
    """Повертає emoji для вердикту"""
    emoji_map = {
        'true': '✅',
        'false': '🔴',
        'partial': '🟡',
        'unverifiable': '❓',
        'pending': '⏳',
        'error': '⚠️'
    }
    return emoji_map.get(verdict, '❓')


def format_result_message(result: Dict[str, Any]) -> str:
    """
    Форматує результат перевірки для Telegram.

    Args:
        result: Результат перевірки від API

    Returns:
        Відформатоване повідомлення
    """
    verdict = result.get('verdict', 'unknown')
    is_fake = result.get('is_fake', False)
    confidence = result.get('confidence_score', 0)
    title = result.get('title', 'Без заголовку')
    domain = result.get('source_domain', 'Невідомо')
    summary = result.get('summary', '')
    recommendation = result.get('recommendation', '')
    cached = result.get('cached', False)

    # Визначаємо emoji та текст вердикту
    verdict_emoji = format_verdict_emoji(verdict)

    verdict_text_map = {
        'true': 'ДОСТОВІРНА',
        'false': 'ФЕЙК',
        'partial': 'ЧАСТКОВО ПРАВДА',
        'unverifiable': 'НЕМОЖЛИВО ПЕРЕВІРИТИ',
        'error': 'ПОМИЛКА ПЕРЕВІРКИ'
    }
    verdict_text = verdict_text_map.get(verdict, 'НЕВІДОМО')

    # Формуємо повідомлення
    message_parts = [
        f"{verdict_emoji} <b>РЕЗУЛЬТАТ: {verdict_text}</b>",
        "",
        f"📰 <b>Заголовок:</b> {title[:100]}{'...' if len(title) > 100 else ''}",
        f"🌐 <b>Джерело:</b> {domain}",
        f"📊 <b>Впевненість:</b> {confidence:.0f}%",
    ]

    if summary:
        message_parts.extend([
            "",
            f"📝 <b>Аналіз:</b>",
            summary[:500] + ('...' if len(summary) > 500 else '')
        ])

    if recommendation:
        message_parts.extend([
            "",
            f"💡 <b>Рекомендація:</b>",
            recommendation[:300] + ('...' if len(recommendation) > 300 else '')
        ])

    if cached:
        message_parts.extend([
            "",
            "📦 <i>(результат з кешу)</i>"
        ])

    return "\n".join(message_parts)


# ==============================================================================
# NGROK HELPERS
# ==============================================================================

async def get_ngrok_url() -> str | None:
    """
    Отримує публічний URL ngrok тунелю.
    Ngrok надає API на порту 4040 для отримання інформації про тунелі.
    """
    try:
        async with aiohttp.ClientSession() as session:
            # Чекаємо поки ngrok запуститься (до 30 секунд)
            for attempt in range(30):
                try:
                    async with session.get(NGROK_API_URL, timeout=2) as response:
                        if response.status == 200:
                            data = await response.json()
                            tunnels = data.get('tunnels', [])
                            for tunnel in tunnels:
                                if tunnel.get('proto') == 'https':
                                    public_url = tunnel.get('public_url')
                                    print(f"✅ Ngrok URL знайдено: {public_url}")
                                    return public_url
                            # Якщо HTTPS не знайдено, використовуємо перший доступний
                            if tunnels:
                                public_url = tunnels[0].get('public_url')
                                print(f"✅ Ngrok URL знайдено: {public_url}")
                                return public_url
                except (aiohttp.ClientError, asyncio.TimeoutError):
                    pass
                print(f"⏳ Очікування ngrok... спроба {attempt + 1}/30")
                await asyncio.sleep(1)
    except Exception as e:
        print(f"❌ Помилка отримання ngrok URL: {e}")
    return None


async def setup_webhook(ngrok_url: str) -> bool:
    """
    Налаштовує webhook для Telegram бота.
    """
    webhook_url = f"{ngrok_url}/api/telegram/webhook/"
    try:
        # Видаляємо старий webhook
        await bot.delete_webhook(drop_pending_updates=True)

        # Встановлюємо новий webhook
        await bot.set_webhook(url=webhook_url)

        # Перевіряємо webhook
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url == webhook_url:
            print(f"✅ Webhook встановлено: {webhook_url}")
            return True
        else:
            print(f"❌ Webhook не встановлено. Поточний URL: {webhook_info.url}")
            return False
    except Exception as e:
        print(f"❌ Помилка налаштування webhook: {e}")
        return False


# ==============================================================================
# BOT HANDLERS
# ==============================================================================

@dp.message(Command('start'))
async def cmd_start(message: Message) -> None:
    """
    Обробник команди /start.
    Вітає користувача та пояснює як користуватися ботом.
    """
    welcome_text = (
        "👋 <b>Вітаю!</b>\n\n"
        "Я — <b>NewsFilter AI Bot</b> 🔍\n"
        "Допомагаю перевіряти новини на достовірність за допомогою штучного інтелекту.\n\n"
        "📌 <b>Як користуватися:</b>\n"
        "Просто надішліть мені посилання на новину, і я перевірю її!\n\n"
        "🔗 <b>Приклад:</b>\n"
        "<code>https://example.com/news/article</code>\n\n"
        "⚡ <b>Швидкість:</b>\n"
        "• Кешовані новини — миттєво\n"
        "• Нові новини — 10-30 секунд\n\n"
        "📚 Команди: /help"
    )
    await message.answer(welcome_text, parse_mode=ParseMode.HTML)


@dp.message(Command('help'))
async def cmd_help(message: Message) -> None:
    """
    Обробник команди /help.
    Показує список доступних команд.
    """
    help_text = (
        "📚 <b>Доступні команди:</b>\n\n"
        "🚀 /start — Почати роботу\n"
        "❓ /help — Показати цю довідку\n"
        "🔗 /check <url> — Перевірити новину\n"
        "🔧 /debug <url> — Діагностика перевірки\n\n"
        "💡 <b>Підказка:</b>\n"
        "Просто надішліть посилання на новину без команди!\n\n"
        "📊 <b>Вердикти:</b>\n"
        "✅ — Достовірна новина\n"
        "🔴 — Фейк\n"
        "🟡 — Частково правда\n"
        "❓ — Неможливо перевірити"
    )
    await message.answer(help_text, parse_mode=ParseMode.HTML)


@dp.message(Command('check'))
async def cmd_check(message: Message) -> None:
    """
    Обробник команди /check <url>.
    Перевіряє новину за вказаним URL.
    """
    # Витягуємо URL з аргументів команди
    text = message.text or ''
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer(
            "❌ <b>Вкажіть URL для перевірки!</b>\n\n"
            "Приклад: /check https://example.com/news/article",
            parse_mode=ParseMode.HTML
        )
        return

    url = extract_url(parts[1])
    if not url:
        await message.answer(
            "❌ <b>Невалідний URL!</b>\n\n"
            "Переконайтеся, що URL починається з http:// або https://",
            parse_mode=ParseMode.HTML
        )
        return

    # Перевіряємо новину
    await check_and_respond(message, url)


@dp.message(Command('ngrok'))
async def cmd_ngrok(message: Message) -> None:
    """
    Обробник команди /ngrok.
    Показує поточний публічний URL ngrok тунелю.
    """
    await message.answer("🔄 Отримую URL ngrok тунелю...", parse_mode=ParseMode.HTML)

    ngrok_url = await get_ngrok_url()
    if ngrok_url:
        await message.answer(
            f"🌐 <b>Ngrok тунель активний!</b>\n\n"
            f"URL: <code>{ngrok_url}</code>\n\n"
            f"🔗 Webhook URL:\n<code>{ngrok_url}/api/telegram/webhook/</code>",
            parse_mode=ParseMode.HTML
        )
    else:
        await message.answer(
            "❌ Не вдалося отримати ngrok URL.\n"
            "Переконайтеся, що ngrok сервіс запущено.",
            parse_mode=ParseMode.HTML
        )


@dp.message(Command('debug'))
async def cmd_debug(message: Message) -> None:
    """
    Обробник команди /debug <url>.
    Виконує покрокову діагностику перевірки новини.
    """
    # Витягуємо URL з аргументів команди
    text = message.text or ''
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer(
            "🔧 <b>Діагностика перевірки</b>\n\n"
            "Використання: /debug <url>\n\n"
            "Приклад:\n<code>/debug https://example.com/news/article</code>",
            parse_mode=ParseMode.HTML
        )
        return

    url = extract_url(parts[1])
    if not url:
        await message.answer(
            "❌ <b>Невалідний URL!</b>\n\n"
            "Переконайтеся, що URL починається з http:// або https://",
            parse_mode=ParseMode.HTML
        )
        return

    # Відправляємо повідомлення про початок діагностики
    status_message = await message.answer(
        "🔧 <b>Запускаю діагностику...</b>\n\n"
        f"URL: {url[:50]}...\n"
        "⏳ Зачекайте...",
        parse_mode=ParseMode.HTML
    )

    try:
        # Виконуємо діагностику
        result = await api_client.debug_check(url)

        if result.get('error'):
            await status_message.edit_text(
                f"⚠️ <b>Помилка діагностики!</b>\n\n{result.get('message', 'Невідома помилка')}",
                parse_mode=ParseMode.HTML
            )
            return

        # Форматуємо результат діагностики
        steps = result.get('steps', [])
        summary = result.get('summary', {})

        message_parts = [
            f"🔧 <b>Результат діагностики</b>\n",
            f"📊 Успішно: {summary.get('successful_steps', 0)}/{summary.get('total_steps', 0)}\n"
        ]

        for step in steps:
            emoji = "✅" if step.get('success') else "❌"
            message_parts.append(
                f"\n{emoji} <b>Крок {step.get('step')}: {step.get('name')}</b>\n"
                f"   {step.get('message', 'Немає повідомлення')}"
            )

        # Показуємо невдалі кроки
        failed_steps = summary.get('failed_steps', [])
        if failed_steps:
            message_parts.append(f"\n\n⚠️ <b>Проблемні кроки:</b> {', '.join(failed_steps)}")

        await status_message.edit_text(
            "\n".join(message_parts),
            parse_mode=ParseMode.HTML
        )

    except Exception as e:
        await status_message.edit_text(
            f"⚠️ <b>Помилка!</b>\n\n{str(e)}",
            parse_mode=ParseMode.HTML
        )


@dp.message()
async def handle_message(message: Message) -> None:
    """
    Обробник будь-яких текстових повідомлень.
    Шукає URL та перевіряє новину.
    """
    text = message.text or ''

    # Шукаємо URL в тексті
    url = extract_url(text)

    if url:
        await check_and_respond(message, url)
    else:
        await message.answer(
            "❓ <b>Не знайдено посилання</b>\n\n"
            "Надішліть мені URL новини для перевірки.\n"
            "Приклад: <code>https://example.com/news/article</code>",
            parse_mode=ParseMode.HTML
        )


async def check_and_respond(message: Message, url: str) -> None:
    """
    Основна функція перевірки новини та відправки відповіді.

    Args:
        message: Telegram повідомлення
        url: URL для перевірки
    """
    # Витягуємо домен для відображення
    try:
        domain = urlparse(url).netloc
    except Exception:
        domain = "unknown"

    # Відправляємо повідомлення "Перевіряю..."
    status_message = await message.answer(
        f"🔄 <b>Перевіряю новину...</b>\n\n"
        f"🌐 Джерело: {domain}\n"
        f"⏳ Зачекайте, будь ласка...",
        parse_mode=ParseMode.HTML
    )

    try:
        # Відправляємо запит на перевірку
        response = await api_client.check_news(url)

        # Перевіряємо на помилки
        if response.get('error'):
            error_msg = response.get('message', 'Невідома помилка')
            error_code = response.get('error_code', '')
            details = response.get('details', '')

            error_text = f"⚠️ <b>Помилка!</b>\n\n{error_msg}"
            if error_code:
                error_text += f"\n\n<b>Код:</b> {error_code}"
            if details:
                error_text += f"\n<b>Деталі:</b> {details[:200]}"
            error_text += "\n\n💡 <i>Використайте /debug &lt;url&gt; для діагностики</i>"

            await status_message.edit_text(error_text, parse_mode=ParseMode.HTML)
            return

        # Якщо результат з кешу - відразу відповідаємо
        if response.get('cached'):
            result = response.get('result', {})
            result_text = format_result_message(result)
            await status_message.edit_text(result_text, parse_mode=ParseMode.HTML)
            return

        # Якщо задача запущена - чекаємо на результат
        task_id = response.get('task_id')
        if task_id:
            # Оновлюємо статус
            await status_message.edit_text(
                f"🔄 <b>Аналізую новину...</b>\n\n"
                f"🌐 Джерело: {domain}\n"
                f"🤖 AI обробляє текст...\n"
                f"⏳ Це може зайняти до 30 секунд",
                parse_mode=ParseMode.HTML
            )

            # Чекаємо на результат
            final_result = await api_client.wait_for_result(task_id)

            if final_result.get('error'):
                error_msg = final_result.get('message', 'Невідома помилка')
                await status_message.edit_text(
                    f"⚠️ <b>Помилка обробки!</b>\n\n{error_msg}\n\n"
                    f"💡 <i>Використайте /debug {url[:30]}... для діагностики</i>",
                    parse_mode=ParseMode.HTML
                )
                return

            # Форматуємо та відправляємо результат
            result = final_result.get('result', {})
            result_text = format_result_message(result)
            await status_message.edit_text(result_text, parse_mode=ParseMode.HTML)
        else:
            await status_message.edit_text(
                "⚠️ <b>Неочікувана відповідь сервера</b>\n\n"
                "Спробуйте ще раз пізніше.",
                parse_mode=ParseMode.HTML
            )

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[ERROR] check_and_respond: {str(e)}\n{error_trace}")

        await status_message.edit_text(
            f"⚠️ <b>Виникла помилка!</b>\n\n"
            f"<b>Тип:</b> {type(e).__name__}\n"
            f"<b>Деталі:</b> {str(e)[:200]}\n\n"
            f"💡 <i>Використайте /debug &lt;url&gt; для діагностики</i>",
            parse_mode=ParseMode.HTML
        )


# ==============================================================================
# MAIN
# ==============================================================================

async def on_startup():
    """Виконується при запуску бота"""
    print("🤖 NewsFilter Telegram Bot запускається...")
    print(f"📡 API URL: {BACKEND_API_URL}")


async def on_shutdown():
    """Виконується при зупинці бота"""
    print("👋 Бот завершує роботу...")
    await api_client.close()


async def main() -> None:
    """Головна функція запуску бота."""

    if not TELEGRAM_BOT_TOKEN:
        print("❌ ПОМИЛКА: TELEGRAM_BOT_TOKEN не встановлено!")
        print("   Додайте токен бота в .env файл.")
        return

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    if USE_WEBHOOK:
        target_url = None
        
        if WEBHOOK_URL:
             print(f"🔗 Режим: Webhook (Static URL)")
             target_url = WEBHOOK_URL
        else:
             print("🔗 Режим: Webhook (через ngrok)")
             target_url = await get_ngrok_url()

        if target_url:
            webhook_success = await setup_webhook(target_url)
            if webhook_success:
                print("✅ Webhook режим активовано!")
                print(f"🌐 Публічний URL: {target_url}")
                print("📭 Запускаю веб-сервер для Webhook...")
                
                app = web.Application()
                
                webhook_requests_handler = SimpleRequestHandler(
                    dispatcher=dp,
                    bot=bot,
                )
                
                webhook_requests_handler.register(app, path="/api/telegram/webhook/")
                
                setup_application(app, dp, bot=bot)
                
                runner = web.AppRunner(app)
                await runner.setup()
                site = web.TCPSite(runner, host="0.0.0.0", port=8001)
                await site.start()
                
                print("🚀 Webhook сервер запущено на порту 8001")
                

                await asyncio.Event().wait()
            else:
                print("⚠️ Не вдалося налаштувати webhook, перемикаюсь на polling...")
                await bot.delete_webhook(drop_pending_updates=True)
                await dp.start_polling(bot)
        else:
            print("⚠️ URL для Webhook не знайдено (Ngrok/Static), перемикаюсь на polling...")
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(bot)
    else:
        print("🔄 Режим: Long Polling")
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Бот готовий до роботи!")
        await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())

