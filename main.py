import logging
import os
import time
import openai
import telegram
from telegram.error import TelegramError
import requests

# Set up logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")  # should be in format: "@YourChannelName"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI
openai.api_key = OPENAI_API_KEY
logging.info("OpenAI version: %s", openai.__version__)

# Initialize Telegram bot
bot = telegram.Bot(token=BOT_TOKEN)

# Fetch tweets from your source
def fetch_latest_news():
    # Replace this with your own API, Twitter scraper, or webhook
    return [
        {
            "text": "Q3 Atlanta Fed GDPNow Index 2.15% vs Est 0.88%",
            "timestamp": time.time()
        }
    ]

# Translate with OpenAI
def translate_to_somali(text):
    try:
        prompt = f"Translate this economic news into Somali:\n\n{text}\n\nSomali:"
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a translator who translates economic and financial news into Somali."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        logging.error(f"Translation failed: {e}")
        return f"❌ Tarjumiddu way guuldarreysatay.\n\nOriginal: {text}"

# Send to Telegram
def send_to_telegram(message):
    try:
        bot.send_message(chat_id=CHANNEL_ID, text=message)
        logging.info("Sent to Telegram: %s", message)
    except TelegramError as e:
        logging.error(f"Telegram error: {e}")

# Main loop
def main():
    logging.info("Bot is running...")
    while True:
        news_items = fetch_latest_news()
        for item in news_items:
            translated = translate_to_somali(item["text"])
            send_to_telegram(translated)
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()
