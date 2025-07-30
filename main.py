import os
import time
import re
import asyncio

import feedparser
import pytz
import requests
from telegram import Bot
import openai
import httpx # Import the httpx library

# --- Configuration ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN_HERE")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@HagarlaaweMarkets")
FINANCIAL_JUICE_RSS_FEED_URL = os.getenv("FINANCIAL_JUICE_RSS_FEED_URL", "YOUR_FINANCIAL_JUICE_RSS_FEED_URL_HERE")

# --- OpenAI API Key Configuration ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set. Please set it in Render Dashboard.")

# --- EXPLICITLY INITIALIZE THE OPENAI CLIENT HERE ---
try:
    openai_client = openai.OpenAI(
        api_key=OPENAI_API_KEY,
        http_client=httpx.Client(proxies={})
    )
    print("OpenAI client initialized with explicit httpx.Client.")
except Exception as e:
    print(f"Error initializing explicit OpenAI client: {e}. Falling back to default client.")
    openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)


# --- Persistent Storage Configuration ---
PERSISTENT_STORAGE_PATH = "/bot-data"
LAST_LINK_FILE = os.path.join(PERSISTENT_STORAGE_PATH, "last_posted_link.txt")

# --- Global Variables ---
last_posted_link = None

# --- Keyword Filtering (NOW EMPTY - ALL HEADLINES WILL BE PROCESSED) ---
# The filtering logic below will now ensure all headlines are processed.
KEYWORDS = [] 

# --- List of Somali prefixes to remove from translation ---
SOMALI_PREFIXES_TO_REMOVE = [
    "Qeybta Abaalmarinta:", "Qeyb-qabad:", "Qeyb-dhaqameedka", "Qeyb-dhaqaale:",
    "Fieldinice:", "Fieldjuice:", "Dhaqaale:", "Abuurjuice:",
]

def contains_keywords(text, keywords):
    """Checks if the text contains any of the specified keywords (case-insensitive).
    This function is effectively bypassed below now that keywords are removed.
    """
    if not keywords: # If keywords list is empty, always return True
        return True
    text_lower = text.lower()
    for keyword in keywords:
        if keyword.lower() in text_lower:
            return True
    return False

def remove_flag_emojis(text):
    """
    Removes common flag emojis (regional indicator symbol pairs)
    and their associated colons/whitespace from the text.
    """
    flag_pattern = r'[\U0001F1E6-\U0001F1FF]{2}:?\s*'
    cleaned_text = re.sub(flag_pattern, '', text, flags=re.UNICODE)
    return cleaned_text.strip()

# --- Functions for Persistence ---
def load_last_posted_link():
    """Loads the last posted link from the persistent file."""
    if os.path.exists(LAST_LINK_FILE):
        try:
            with open(LAST_LINK_FILE, 'r') as f:
                link = f.readline().strip()
                print(f"Loaded last_posted_link: {link}")
                return link if link else None
        except Exception as e:
            print(f"Error loading last_posted_link from file: {e}")
            return None
    print("No last_posted_link file found.")
    return None

def save_last_posted_link(link):
    """Saves the last posted link to the persistent file."""
    try:
        os.makedirs(PERSISTENT_STORAGE_PATH, exist_ok=True)
        with open(LAST_LINK_FILE, 'w') as f:
            f.write(link)
        print(f"Saved last_posted_link: {link}")
    except Exception as e:
        print(f"Error saving last_posted_link to file: {e}")

# --- OpenAI Translation Function ---
async def translate_text_with_gpt(text: str, target_language: str = "Somali") -> str:
    """
    Translates the given English text to the target language using OpenAI GPT.
    """
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are a highly accurate and professional translator. Translate the following English financial news text into {target_language}. Maintain the original meaning, tone, and format."},
                {"role": "user", "content": text}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        translated_text = response.choices[0].message.content.strip()
        return translated_text
    except openai.APIError as e:
        print(f"OpenAI API Error during translation: {e}")
        return f"Translation service currently unavailable due to API error. Original text: {text}"
    except Exception as e:
        print(f"An unexpected error occurred during translation: {e}")
        return f"Translation failed due to an internal error. Original text: {text}"

# --- Main Bot Logic Functions ---

async def fetch_and_post_headlines():
    """
    Fetches new headlines from the RSS feed, filters them by keywords,
    translates them to Somali via GPT API, and posts them to the Telegram channel.
    """
    global last_posted_link

    current_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    print(f"[{current_time_str}] Checking RSS feed from: {FINANCIAL_JUICE_RSS_FEED_URL}")
    feed = feedparser.parse(FINANCIAL_JUICE_RSS_FEED_URL)
    
    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    new_entries_to_process = []

    for entry in feed.entries:
        if hasattr(entry, 'link') and entry.link == last_posted_link:
            print(f"Reached last posted link: {last_posted_link}. Stopping.")
            break
        new_entries_to_process.append(entry)

    new_entries_to_process.reverse()

    if not new_entries_to_process:
        print("No new headlines to post.")
        return

    print(f"Found {len(new_entries_to_process)} new headlines. Applying filters and translating...")

    headlines_posted_count = 0
    for entry in new_entries_to_process:
        english_headline_raw = entry.title
        link = entry.link if hasattr(entry, 'link') else None

        cleaned_english_headline = english_headline_raw.replace("FinancialJuice:", "").replace("Abuurjuice:", "").strip()
        cleaned_english_headline = remove_flag_emojis(cleaned_english_headline)

        # --- KEYWORDS FILTERING REMOVED ---
        # The 'if not contains_keywords' block has been removed,
        # so all headlines will proceed to translation attempt.
        # However, to maintain the spirit, we can still use the contains_keywords
        # function which will now always return True if KEYWORDS list is empty.
        if not contains_keywords(cleaned_english_headline, KEYWORDS):
            # This block will technically not be hit if KEYWORDS is empty
            print(f"Skipping (no keywords): '{cleaned_english_headline}'")
            continue

        print(f"Processing: '{cleaned_english_headline}'") # Changed log to reflect no keyword check
        headlines_posted_count += 1 # Renamed from filtered_headlines_count

        try:
            somali_headline = await translate_text_with_gpt(cleaned_english_headline, "Somali")

            for prefix in SOMALI_PREFIXES_TO_REMOVE:
                if somali_headline.startswith(prefix):
                    somali_headline = somali_headline[len(prefix):].strip()
            somali_headline = somali_headline.strip()

            message_to_send = (
                f"**DEGDEG 🔴**\n\n"
                f"*{cleaned_english_headline}*\n\n"
                f"{somali_headline}"
            )
            
            # --- "Read more" link REMOVED ---
            # if link:
            #     message_to_send += f"\n\n[Read more]({link})"

            await bot.send_message(
                chat_id=TELEGRAM_CHANNEL_ID,
                text=message_to_send,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            print(f"Posted translated: '{cleaned_english_headline}'")

            if link:
                last_posted_link = link
                save_last_posted_link(last_posted_link)

            await asyncio.sleep(1)

        except Exception as e:
            print(f"Error processing or posting headline '{english_headline_raw}': {e}")
            try:
                fallback_message = (
                    f"**DEGDEG 🔴 (Translation Error)**\n\n"
                    f"{cleaned_english_headline}"
                )
                # --- "Read more" link REMOVED from fallback too ---
                # if link:
                #     fallback_message += f"\n\n[Read more]({link})"

                await bot.send_message(
                    chat_id=TELEGRAM_CHANNEL_ID,
                    text=fallback_message,
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
                print(f"Posted original English due to error: '{cleaned_english_headline}'")
                if link:
                    last_posted_link = link
                    save_last_posted_link(last_posted_link)
            except Exception as inner_e:
                print(f"Failed to post even original English headline '{cleaned_english_headline}': {inner_e}")

    if headlines_posted_count == 0 and len(new_entries_to_process) > 0:
        print("No new headlines were processed (this shouldn't happen if keyword filter is removed).")


# --- Main Execution Loop ---
if __name__ == "__main__":
    print("Bot starting...")
    os.makedirs(PERSISTENT_STORAGE_PATH, exist_ok=True)
    print(f"Persistent storage path ensured: {PERSISTENT_STORAGE_PATH}")
    
    last_posted_link = load_last_posted_link()

    while True:
        try:
            asyncio.run(fetch_and_post_headlines())
        except Exception as e:
            print(f"An error occurred in the main fetch loop: {e}")

        current_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        print(f"[{current_time_str}] Sleeping for 1 minute before next check...")
        time.sleep(60)
