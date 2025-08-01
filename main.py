import logging
import feedparser
import pytz
import datetime
import openai
import requests
import html
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, JobQueue

# Set your tokens and keys here
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1001234567890")  # Replace with your channel ID

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

openai.api_key = OPENAI_API_KEY

# List of RSS feeds
RSS_FEEDS = [
    "https://www.financialjuice.com/rss/news",
    "https://www.forexlive.com/feed/news/",
    "https://www.zerohedge.com/fullrss.xml"
]

# Function to fetch and summarize articles
async def fetch_and_post_news(context: ContextTypes.DEFAULT_TYPE):
    utc = pytz.UTC
    now = datetime.datetime.now(utc)
    one_hour_ago = now - datetime.timedelta(hours=1)

    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            published = getattr(entry, 'published_parsed', None)
            if not published:
                continue

            published_dt = datetime.datetime(*published[:6], tzinfo=utc)
            if published_dt < one_hour_ago:
                continue

            title = html.unescape(entry.title)
            summary_input = f"Translate to Somali and summarize the news:\n\n{title}"
            logger.info(f"Summarizing: {title}")

            try:
                completion = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful Somali news translator and summarizer."},
                        {"role": "user", "content": summary_input}
                    ],
                    max_tokens=300
                )

                translated_summary = completion.choices[0].message.content.strip()
                message = f"📰 {title}\n\n{translated_summary}"

                await context.bot.send_message(chat_id=CHANNEL_ID, text=message)
            except Exception as e:
                logger.error(f"Error posting: {e}")

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot is working and ready!")

# Main function
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))

    job_queue = application.job_queue
    job_queue.run_repeating(fetch_and_post_news, interval=3600, first=10)

    application.run_polling()

if __name__ == "__main__":
    main()
