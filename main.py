import asyncio
import logging
import os
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
import openai
from openai import OpenAIError
import httpx

# Print OpenAI version
print(f"OpenAI version: {openai.__version__}")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SOURCE_CHANNEL = os.getenv("SOURCE_CHANNEL")  # e.g. 'FinancialJuice'
DEST_CHANNEL = os.getenv("DEST_CHANNEL")      # e.g. 'HagarlaaweMarkets'

# Initialize OpenAI client
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Initialize Telegram client
client = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

async def translate_to_somali(text: str) -> str:
    try:
        logger.info(f"Translating: {text}")
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You translate short English financial headlines to Somali. Be accurate and simple."},
                {"role": "user", "content": text}
            ],
            temperature=0.4,
            timeout=10,
        )
        return response.choices[0].message.content.strip()
    except OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        return f"Translation failed due to OpenAI error. Original: {text}"
    except httpx.TimeoutException:
        logger.error("OpenAI request timed out.")
        return f"Translation timed out. Original: {text}"
    except Exception as e:
        logger.exception("Unexpected error during translation")
        return f"Translation failed due to an internal error. Original: {text}"

async def forward_and_translate():
    last_message_id = 0

    while True:
        try:
            history = await client(GetHistoryRequest(
                peer=SOURCE_CHANNEL,
                limit=5,
                offset_id=0,
                max_id=0,
                min_id=last_message_id,
                add_offset=0,
                hash=0
            ))

            messages = reversed(history.messages)  # oldest to newest

            for message in messages:
                if message.id <= last_message_id:
                    continue

                original_text = message.message
                if not original_text:
                    continue

                logger.info(f"New message from {SOURCE_CHANNEL}: {original_text}")

                translated_text = await translate_to_somali(original_text)

                await client.send_message(DEST_CHANNEL, f"DEGDEG 🔴\n\n{translated_text}")
                last_message_id = message.id
                await asyncio.sleep(3)

        except Exception as e:
            logger.exception("Unexpected error in main loop")

        await asyncio.sleep(10)

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(forward_and_translate())
