import os
import requests
import feedparser
import pytz
import datetime
import logging
from openai import OpenAI
from telegram import Bot

# Setup logging
logging.basicConfig(level=logging.INFO)

# Environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
RSS_FEED_URL = os.getenv("RSS_FEED_URL")  # Example: https://nitter.net/FinancialJuice/rss

# Setup OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Setup Telegram bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# For tracking posted tweets
POSTED = set()

def translate(text):
    try:
        logging.info(f"Translating: {text[:60]}")
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You translate financial news into Somali."},
                {"role": "user", "content": f"Translate to Somali: {text}"}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Translation error: {e}")
        return None

def fetch_and_post():
    feed = feedparser.parse(RSS_FEED_URL)
    for entry in feed.entries:
        if entry.id in POSTED:
            continue

        translated = translate(entry.title)
        if translated:
            try:
                bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=translated)
                POSTED.add(entry.id)
                logging.info(f"Posted: {translated}")
            except Exception as e:
                logging.error(f"Telegram error: {e}")

if __name__ == "__main__":
    logging.info("Bot started...")
    fetch_and_post()
