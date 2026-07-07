import os
import logging

from flask import Flask, request
from groq import Groq
from apscheduler.schedulers.background import BackgroundScheduler
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_RECIPIENT_NUMBER = os.getenv("WHATSAPP_RECIPIENT_NUMBER")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
DRY_MODE = os.getenv("DRY_MODE", "false").lower() == "true"

groq_client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = (
    "You are a hilarious, street-smart Kenyan marketer. "
    "You speak Kenyan Sheng and Swahili. Reply to the user's question "
    "with humor, specific Kenyan slang, and casually promote a school "
    "management system. Keep replies under 200 words."
)

BROADCAST_PROMPT = (
    "Write a short, hilarious Sheng/Swahili marketing joke or funny tip "
    "about managing a school or paying school fees. "
    "Keep it under 250 characters to fit a WhatsApp broadcast."
)

BROADCAST_HOURS = [8, 12, 16, 19, 21]


def send_whatsapp_message(to, text):
    if DRY_MODE:
        logger.info("DRY MODE — would send to %s: %s", to, text)
        return {"dry_run": True, "to": to, "text": text}

    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        logger.info("Message sent to %s", to)
        return resp.json()
    except Exception as e:
        logger.error("Failed to send WhatsApp message: %s", e)
        return None


def ask_groq(prompt, system_prompt=None):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=300,
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error("Groq API error: %s", e)
        return None


def process_incoming_message(phone, text):
    reply = ask_groq(text, system_prompt=SYSTEM_PROMPT)
    if reply:
        send_whatsapp_message(phone, reply)


def broadcast_post():
    content = ask_groq(BROADCAST_PROMPT)
    if content:
        send_whatsapp_message(WHATSAPP_RECIPIENT_NUMBER, content)
    else:
        logger.error("Broadcast skipped: Groq returned no content")


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == VERIFY_TOKEN:
            logger.info("Webhook verified successfully")
            return challenge, 200
        logger.warning("Webhook verification failed: token mismatch")
        return "Verification failed", 403

    try:
        data = request.get_json()
        logger.info("Webhook POST received")

        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for msg in value.get("messages", []):
                    if msg.get("type") == "text":
                        process_incoming_message(
                            msg["from"], msg["text"]["body"]
                        )
    except Exception as e:
        logger.error("Webhook processing error: %s", e)

    return "OK", 200


@app.route("/")
def index():
    return "WhatsApp Bot is running!", 200


@app.route("/test-send")
def test_send():
    phone = request.args.get("phone", "254700000000")
    text = request.args.get("text", "Habari")
    reply = ask_groq(text, system_prompt=SYSTEM_PROMPT)
    if reply:
        logger.info("Test reply: %s", reply)
        return {"phone": phone, "user_message": text, "bot_reply": reply}
    return {"error": "Groq returned no reply"}, 500


@app.route("/test-broadcast")
def test_broadcast():
    content = ask_groq(BROADCAST_PROMPT)
    if content:
        if DRY_MODE:
            logger.info("DRY MODE — broadcast would send: %s", content)
        return {"broadcast_content": content}
    return {"error": "Groq returned no content"}, 500


scheduler = BackgroundScheduler()
for hour in BROADCAST_HOURS:
    scheduler.add_job(
        broadcast_post,
        "cron",
        hour=hour,
        minute=0,
        timezone="Africa/Nairobi",
    )
scheduler.start()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
