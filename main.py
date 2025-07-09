import requests

# === CONFIGURATION ===
bot_token = "8131661650:AAEOdal3Y1pNCQXWTdjQmn624402adQXof4"       # Replace with your bot token
chat_id = "7674848022"           # Replace with your chat ID
message = "🚀 Hello from your Python script!"

# === SEND MESSAGE ===
url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
payload = {
    "chat_id": chat_id,
    "text": message,
    "parse_mode": "Markdown"
}

try:
    response = requests.post(url, data=payload)
    response.raise_for_status()
    print("✅ Message sent successfully!")
except Exception as e:
    print("❌ Failed to send message:", e)
