import feedparser
import openai
import logging
import asyncio
import html
import pytz
from datetime import datetime
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

# Replace with your actual keys and IDs
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHANNEL_ID = "@YourChannelName"
OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"
RSS_FEED_URL = "https://example.com/rss"  # Replace with actual RSS URL

# Setup
openai.api_key = OPENAI_API_KEY
bot = Bot(token=TELEGRAM_BOT_TOKEN)
last_published = None
CHECK_INTERVAL = 180  # seconds

logging.basicConfig(level=logging.INFO)

def translate_to_somali(text):
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": f"Tarjum qoraalkan af Soomaali: {text}"}],
        max_tokens=300
    )
    return response.choices[0].message.content.strip()

async def check_feed():
    global last_published
    logging.info("Checking RSS feed...")

    feed = feedparser.parse(RSS_FEED_URL)
    for entry in reversed(feed.entries):
        entry_time = datetime(*entry.published_parsed[:6], tzinfo=pytz.utc)
        if last_published is None or entry_time > last_published:
            title = html.unescape(entry.title)
            link = entry.link
            summary = html.unescape(entry.summary)

            translated_summary = translate_to_somali(summary)

            message = f"📰 <b>{html.escape(title)}</b>\n\n{translated_summary}\n\n<a href=\"{link}\">Akhriso Warkan</a>"
            try:
                await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=message, parse_mode=ParseMode.HTML)
                logging.info("Posted to Telegram.")
            except TelegramError as e:
                logging.error(f"Telegram error: {e}")

            last_published = entry_time

async def main():
    while True:
        try:
            await check_feed()
        except Exception as e:
            logging.error(f"Error checking feed: {e}")
        await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
