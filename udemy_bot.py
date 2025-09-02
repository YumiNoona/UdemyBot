# udemy_bot_async.py
import asyncio
import imaplib
import email
import os
from email.header import decode_header
from telegram import Bot

EMAIL_USER = os.environ["EMAIL_USER"]
EMAIL_PASS = os.environ["EMAIL_PASS"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])

bot = Bot(token=TELEGRAM_TOKEN)

IMAP_SERVER = "imap.gmail.com"

async def check_email():
    while True:
        try:
            mail = imaplib.IMAP4_SSL(IMAP_SERVER)
            mail.login(EMAIL_USER, EMAIL_PASS)
            mail.select("inbox")

            # Search for unseen Udemy emails
            status, messages = mail.search(None, '(UNSEEN FROM "noreply@udemy.com")')
            email_ids = messages[0].split()

            for eid in email_ids:
                status, msg_data = mail.fetch(eid, "(RFC822)")
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Extract email subject
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else "utf-8")

                # Extract the email body
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            break
                else:
                    body = msg.get_payload(decode=True).decode()

                # Send code to Telegram
                await bot.send_message(chat_id=CHAT_ID, text=f"Udemy Code:\n{body}")

                # Mark as seen
                mail.store(eid, '+FLAGS', '\\Seen')

            mail.logout()

        except Exception as e:
            print("Error:", e)

        await asyncio.sleep(20)  # check every 20s

async def main():
    await check_email()

if __name__ == "__main__":
    asyncio.run(main())
