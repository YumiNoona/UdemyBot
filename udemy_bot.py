import os
import imaplib
import email
import re
import time
from telegram import Bot

# --- Load secrets from environment variables ---
EMAIL_USER = os.getenv("EMAIL_USER")         # e.g. "harusenpaiweeb@gmail.com"
EMAIL_PASS = os.getenv("EMAIL_PASS")         # your Gmail app password
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") # from @BotFather
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") # your group/user ID

IMAP_SERVER = "imap.gmail.com"

bot = Bot(token=TELEGRAM_TOKEN)

def get_latest_udemy_code():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("inbox")

    # Search unread mails from Udemy
    status, data = mail.search(None, '(UNSEEN FROM "noreply@udemy.com")')
    mail_ids = data[0].split()

    if not mail_ids:
        mail.logout()
        return None

    # Fetch the newest one
    latest_id = mail_ids[-1]
    status, data = mail.fetch(latest_id, "(RFC822)")
    raw_email = data[0][1]

    msg = email.message_from_bytes(raw_email)
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body += part.get_payload(decode=True).decode(errors="ignore")
    else:
        body = msg.get_payload(decode=True).decode(errors="ignore")

    mail.logout()

    # Extract 6-digit code
    match = re.search(r"\b\d{6}\b", body)
    return match.group(0) if match else None

def main():
    print("✅ Udemy Code Bot started...")
    while True:
        try:
            code = get_latest_udemy_code()
            if code:
                bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"🎟 Udemy Login Code: {code}")
                print(f"Sent code: {code}")
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(20)  # check every 20s

if __name__ == "__main__":
    main()
