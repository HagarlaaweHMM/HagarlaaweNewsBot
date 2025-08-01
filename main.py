import os
import feedparser
import asyncio
import logging
from datetime import datetime
from pytz import timezone
import openai
from telegram import Bot

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL = os.getenv("TELEGRAM_CHANNEL_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RSS_FEED_URL = "https://www.bloomberg.com/feed/podcast/etf-iq.xml"  # change if needed

# Clients
bot = Bot(token=TELEGRAM_TOKEN)
openai.api_key = OPENAI_API_KEY

# Timezone
tz = timezone("Africa/Mogadishu")

# Track already posted entries
posted_links = set()

async def translate_to_somali(text):
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You translate financial and economic news into Somali in a natural, professional tone."},
                {"role": "user", "content": f"Translate this into Somali:\n\n{text}"}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return None

async def check_rss_and_post():
    logger.info("Checking RSS feed...")
    feed = feedparser.parse(RSS_FEED_URL)

    for entry in feed.entries[:5]:  # limit to 5 latest
        if entry.link in posted_links:
            continue

        title = entry.title
        summary = entry.get("summary", "")
        link = entry.link
        published = entry.get("published", "")

        content_to_translate = f"{title}\n\n{summary}\n\nLink: {link}"
        translated = await translate_to_somali(content_to_translate)

        if translated:
            timestamp = datetime.now(tz).strftime("%Y-%m-%d %H:%M")
            message = f"📰 {timestamp}\n\n{translated}"
            try:
                await bot.send_message(chat_id=TELEGRAM_CHANNEL, text=message)
                logger.info(f"Posted: {title}")
                posted_links.add(link)
            except Exception as e:
                logger.error(f"Telegram post error: {e}")

async def run_loop():
    while True:
        await check_rss_and_post()
        await asyncio.sleep(900)  # 15 minutes

if __name__ == "__main__":
    asyncio.run(run_loop())
