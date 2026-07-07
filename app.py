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
    return """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>WHATSAPP BOT</title><style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0a0a;overflow:hidden;height:100vh;font-family:'Share Tech Mono',monospace}
canvas#matrix{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0;opacity:.35}
.container{position:relative;z-index:1;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;padding:20px}
.terminal{background:rgba(0,20,0,.85);border:2px solid #00ff41;border-radius:12px;padding:30px 40px;max-width:750px;width:100%;box-shadow:0 0 40px rgba(0,255,65,.15),inset 0 0 60px rgba(0,255,65,.03);backdrop-filter:blur(4px)}
.terminal-header{display:flex;align-items:center;gap:12px;border-bottom:1px solid #00ff4144;padding-bottom:12px;margin-bottom:20px}
.dot{width:12px;height:12px;border-radius:50%}.dot.r{background:#ff3355;box-shadow:0 0 8px #ff3355}.dot.y{background:#ffcc00;box-shadow:0 0 8px #ffcc00}.dot.g{background:#00ff41;box-shadow:0 0 8px #00ff41}
.terminal-title{color:#00ff41;font-family:'Orbitron',sans-serif;font-size:13px;letter-spacing:3px;text-transform:uppercase;opacity:.7}
.status-line{display:flex;align-items:center;gap:14px;margin:8px 0;font-size:15px}
.blob{width:10px;height:10px;border-radius:50%;background:#00ff41;box-shadow:0 0 12px #00ff41;animation:pulse 1.2s infinite}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.3;transform:scale(.7)}}
.hacker-text{color:#00ff41;font-size:16px;line-height:1.7;text-shadow:0 0 8px rgba(0,255,65,.3)}
.glitch{font-family:'Orbitron',sans-serif;font-size:28px;font-weight:900;color:#00ff41;text-shadow:0 0 20px #00ff41,0 0 40px #00ff41,0 0 80px #00ff41;animation:glitch 3s infinite;letter-spacing:2px}
@keyframes glitch{0%,85%,100%{transform:translate(0)}87%{transform:translate(-3px,2px);text-shadow:-3px 0 #ff3355,3px 0 #00ccff}90%{transform:translate(3px,-1px);text-shadow:2px 0 #00ccff,-2px 0 #ff3355}93%{transform:translate(-1px,1px)}}
.typing{overflow:hidden;border-right:2px solid #00ff41;white-space:nowrap;animation:typing 2.5s steps(30) forwards,blink .75s step-end infinite;display:inline-block;font-size:15px}
@keyframes typing{from{width:0}to{width:100%}}
@keyframes blink{50%{border-color:transparent}}
.scanline{position:fixed;top:0;left:0;width:100%;height:100%;background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,255,65,.015) 2px,rgba(0,255,65,.015) 4px);pointer-events:none;z-index:2}
.badge{display:inline-block;background:#00ff4111;border:1px solid #00ff4144;border-radius:4px;padding:2px 10px;font-size:12px;color:#00ff41;margin:4px 0}
.footer{color:#00ff4144;font-size:11px;margin-top:20px;text-align:center;letter-spacing:1px}
a{color:#00ff41;text-decoration:none;border-bottom:1px dashed #00ff4144}
a:hover{text-shadow:0 0 12px #00ff41}
@media(max-width:600px){.terminal{padding:16px}.glitch{font-size:18px}.hacker-text{font-size:13px}.terminal-title{font-size:10px}}
</style></head><body>
<canvas id="matrix"></canvas>
<div class="scanline"></div>
<div class="container">
<div class="terminal">
<div class="terminal-header">
<span class="dot r"></span><span class="dot y"></span><span class="dot g"></span>
<span class="terminal-title">WHATSAPP-BOT://v2.4.1</span></div>
<div class="glitch">SYSTEM ACTIVE</div>
<div style="margin:14px 0">
<div class="status-line"><span class="blob"></span><span class="hacker-text"><span class="typing" style="width:0;animation:typing 2s 0.5s forwards,blink .75s step-end infinite">> AI_ENGINE: GROQ LLAMA-3.3-70B ONLINE</span></span></div>
<div class="status-line"><span class="blob"></span><span class="hacker-text">> WEBHOOK: FLASK ::SECURE::</span></div>
<div class="status-line"><span class="blob"></span><span class="hacker-text">> SCHEDULER: 5x DAILY BROADCASTS [08 12 16 19 21] EAT</span></div>
<div class="status-line"><span class="blob"></span><span class="hacker-text">> STATUS: <span style="color:#00ff41">OPERATIONAL</span></span></div>
</div>
<div style="margin-top:6px;display:flex;gap:8px;flex-wrap:wrap;justify-content:center">
<span class="badge">#Sheng</span><span class="badge">#Swahili</span><span class="badge">#GroqAI</span><span class="badge">#WhatsAppAPI</span><span class="badge">#Kenyan</span>
</div>
<div class="footer">
[<a href="/test-send?text=habari">/test-send</a>] [<a href="/test-broadcast">/test-broadcast</a>] [<a href="/webhook">/webhook</a>]<br>
REPUBLIC OF KENYA // 2026
</div></div></div>
<script>
const c=document.getElementById('matrix'),ctx=c.getContext('2d');
c.width=window.innerWidth;c.height=window.innerHeight;
const chars='アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン0123456789ABCDEF<>/{}[]|&^%$#@!';
const fontSize=14,cols=c.width/fontSize;
const drops=Array.from({length:cols},()=>1);
function draw(){ctx.fillStyle='rgba(10,10,10,.05)';ctx.fillRect(0,0,c.width,c.height);ctx.fillStyle='#00ff41';ctx.font=fontSize+'px monospace';for(let i=0;i<drops.length;i++){const ch=chars[Math.floor(Math.random()*chars.length)];ctx.fillText(ch,i*fontSize,drops[i]*fontSize);if(drops[i]*fontSize>c.height&&Math.random()>.975)drops[i]=0;drops[i]++}}
setInterval(draw,45);
window.onresize=()=>{c.width=window.innerWidth;c.height=window.innerHeight};
</script></body></html>""", 200


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
