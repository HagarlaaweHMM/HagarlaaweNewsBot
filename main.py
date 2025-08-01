import os
import logging
import feedparser
import openai
import httpx
import pytz
import datetime
from telegram import Bot

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI client
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Telegram Bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Feed URL
FEED_URL = "https://www.financialjuice.com/home/rss"

# Track posted links
posted_links = set()

# Timezone
TIMEZONE = pytz.timezone("Africa/Mogadishu")

def translate_to_somali(text: str) -> str:
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a professional Somali financial news translator."},
                {"role": "user", "content": f"Translate this to Somali clearly and accurately:\n\n{text}"}
            ],
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI translation error: {e}")
        return "Translation failed."

def fetch_and_translate():
    try:
        feed = feedparser.parse(FEED_URL)
        for entry in feed.entries:
            link = entry.link
            title = entry.title
            if link not in posted_links:
                translated = translate_to_somali(title)
                message = f"📰 {translated}\n🔗 {link}"
                bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=message)
                posted_links.add(link)
                logger.info(f"Posted: {title}")
    except Exception as e:
        logger.error(f"Error fetching or sending news: {e}")

if __name__ == "__main__":
    logger.info("HagarlaaweNewsBot started.")
    fetch_and_translate()
