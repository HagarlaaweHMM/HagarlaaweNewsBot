import os
import asyncio
import logging
import feedparser
import openai
from datetime import datetime, timezone
from telegram import Bot
from telegram.constants import ParseMode

# Setup logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")  # Format: @channelusername

# ✅ Hardcoded FinancialJuice RSS feed (replace with a working link if you have a different one)
RSS_FEED_URL = "https://financialjuice.com/home/rss"

LAST_TIMESTAMP_FILE = "last_processed.txt"

openai.api_key = OPENAI_API_KEY
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Load last timestamp from file
def load_last_processed_time():
    if os.path.exists(LAST_TIMESTAMP_FILE):
        with open(LAST_TIMESTAMP_FILE, "r") as f:
            return datetime.fromisoformat(f.read().strip())
    return datetime.min.replace(tzinfo=timezone.utc)

def save_last_processed_time(timestamp):
    with open(LAST_TIMESTAMP_FILE, "w") as f:
        f.write(timestamp.isoformat())

# Translate text using GPT
async def translate_to_somali(text):
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You translate English news into Somali, simply and clearly."},
                {"role": "user", "content": f"Translate this to Somali:\n\n{text}"}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Translation failed: {e}")
        return text

# Process RSS Feed
async def process_feed():
    logging.info(f"🔄 Checking RSS feed: {RSS_FEED_URL}")
    feed = feedparser.parse(RSS_FEED_URL)
    last_time = load_last_processed_time()
    new_last_time = last_time

    for entry in sorted(feed.entries, key=lambda x: x.published_parsed):
        published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        if published > last_time:
            title = entry.title
            link = entry.link
            translated = await translate_to_somali(title)
            message = f"📰 <b>{translated}</b>\n<a href='{link}'>Akhriso Warbixinta</a>"

            try:
                await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=message, parse_mode=ParseMode.HTML)
                logging.info(f"✅ Sent: {title}")
                if published > new_last_time:
                    new_last_time = published
            except Exception as e:
                logging.error(f"Failed to send message: {e}")

    save_last_processed_time(new_last_time)

# Main loop
async def main():
    while True:
        await process_feed()
        await asyncio.sleep(300)  # Check every 5 minutes

if __name__ == "__main__":
    asyncio.run(main())
