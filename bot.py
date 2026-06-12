import os
import telebot
import requests
import tempfile
import threading
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN provided.")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# This dummy route is required for Render's free tier health checks
@app.route('/')
def index():
    return "Bot is alive and running!"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Welcome! Send me an .mp4 link and I will download and upload it here.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()
    if not url.startswith('http'):
        bot.reply_to(message, "Please send a valid HTTP/HTTPS URL.")
        return

    bot.reply_to(message, "Downloading video... Please wait.")
    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    temp_video.write(chunk)
            temp_video_path = temp_video.name

        bot.reply_to(message, "Upload in progress to Telegram...")
        with open(temp_video_path, 'rb') as video_file:
            bot.send_video(message.chat.id, video_file)

    except Exception as e:
        bot.reply_to(message, f"An error occurred: {e}")
    finally:
        if 'temp_video_path' in locals() and os.path.exists(temp_video_path):
            os.remove(temp_video_path)

def run_bot():
    print("Starting bot polling...")
    bot.infinity_polling()

if __name__ == "__main__":
    # Start the bot in the background
    threading.Thread(target=run_bot, daemon=True).start()
    
    # Start the dummy web server on the port Render gives us
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
