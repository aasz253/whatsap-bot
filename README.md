# WhatsApp Marketing Bot

An autonomous WhatsApp marketing and auto-reply bot powered by Groq AI (llama-3.3-70b-versatile) and the WhatsApp Cloud API.

## Deploy on Render (Free Tier)

### 1. Push to GitHub
```bash
git init && git add . && git commit -m "initial"
gh repo create your-repo --public --push
```

### 2. Create a Render Web Service
- Go to [render.com](https://render.com) → **New Web Service**
- Connect your GitHub repo
- Set: **Name** `whatsapp-bot`, **Runtime** `Python 3`, **Start Command** (leave default — uses Procfile)
- Plan: **Free**

### 3. Add Environment Variables
In the Render dashboard under **Environment**, add:

| Key | Value |
|---|---|
| `GROQ_API_KEY` | Your Groq API key |
| `WHATSAPP_ACCESS_TOKEN` | Meta WhatsApp permanent access token |
| `WHATSAPP_PHONE_NUMBER_ID` | Your WhatsApp Business phone number ID |
| `WHATSAPP_RECIPIENT_NUMBER` | Target number for broadcasts (e.g. `254712345678`) |
| `VERIFY_TOKEN` | Any random string (e.g. `mysecret123`) |

Click **Deploy**. Once live, point your Meta webhook URL to `https://your-app.onrender.com/webhook`.

> **Note:** Render's free tier sleeps after 15 min of inactivity. The scheduler only runs while the service is awake. Upgrade to a paid plan ($7/mo) for 24/7 uptime, or set up a free cron-job.org ping every 10 min to keep it alive.
