import os
import imaplib
import email
from email.header import decode_header
import time
import re
import telebot
from threading import Thread

# Configuration - Set these as environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN', '8330676908:AAG4XYDiejlhErKCYLYtFrG-YiR6F8JP5PM')
CHANNEL_ID = os.getenv('CHANNEL_ID', '-1002045295402')
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS', 'harusenpaiweeb@gmail.com')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', 'rywojirfvczffqi')
IMAP_SERVER = os.getenv('IMAP_SERVER', 'imap.gmail.com')

bot = telebot.TeleBot(BOT_TOKEN)

def extract_otp(text):
    """Extract OTP from email text using multiple patterns"""
    if not text:
        return None
    
    patterns = [
        r'\b\d{6}\b',  # 6 digit OTP
        r'\b\d{4}\b',  # 4 digit OTP
        r'OTP[:\s]+(\d{4,6})',
        r'code[:\s]+(\d{4,6})',
        r'verification code[:\s]+(\d{4,6})',
        r'(?:OTP|code|verification)\s*(?:is|:)?\s*(\d{4,6})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1) if match.lastindex else match.group(0)
    return None

def decode_text(text):
    """Decode email text"""
    if isinstance(text, bytes):
        try:
            return text.decode('utf-8', errors='ignore')
        except:
            return text.decode('latin-1', errors='ignore')
    return text

def get_email_body(msg):
    """Extract email body from message"""
    body = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            
            if content_type == "text/plain" and "attachment" not in content_disposition:
                try:
                    body = part.get_payload(decode=True)
                    body = decode_text(body)
                    break
                except:
                    pass
            elif content_type == "text/html" and not body:
                try:
                    body = part.get_payload(decode=True)
                    body = decode_text(body)
                except:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True)
            body = decode_text(body)
        except:
            pass
    
    return body

def check_emails():
    """Monitor email inbox for OTPs"""
    print("🔍 Starting email monitoring...")
    seen_ids = set()
    
    while True:
        try:
            # Connect to email server
            mail = imaplib.IMAP4_SSL(IMAP_SERVER)
            mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            mail.select('INBOX')
            
            # Search for unread emails from last 5 minutes
            status, messages = mail.search(None, 'UNSEEN')
            email_ids = messages[0].split()
            
            for email_id in email_ids:
                if email_id in seen_ids:
                    continue
                    
                seen_ids.add(email_id)
                
                # Fetch email
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        # Get subject
                        subject = decode_header(msg["Subject"])[0][0]
                        if isinstance(subject, bytes):
                            subject = subject.decode()
                        
                        # Get sender
                        from_ = msg.get("From")
                        
                        # Get email body
                        body = get_email_body(msg)
                        
                        # Extract OTP from both subject and body
                        otp = extract_otp(body) or extract_otp(subject)
                        
                        if otp:
                            # Send to Telegram
                            message = f"🔐 *New OTP Received*\n\n"
                            message += f"*Code:* `{otp}`\n"
                            message += f"*From:* {from_}\n"
                            message += f"*Subject:* {subject[:100]}"
                            
                            try:
                                bot.send_message(CHANNEL_ID, message, parse_mode='Markdown')
                                print(f"✅ Sent OTP {otp} to Telegram channel")
                            except Exception as e:
                                print(f"❌ Error sending to Telegram: {e}")
                        else:
                            print(f"📧 Email received but no OTP found - Subject: {subject[:50]}")
            
            # Keep only last 100 IDs to prevent memory issues
            if len(seen_ids) > 100:
                seen_ids = set(list(seen_ids)[-100:])
            
            mail.close()
            mail.logout()
            
        except Exception as e:
            print(f"❌ Error checking emails: {e}")
            time.sleep(30)  # Wait longer if there's an error
            continue
        
        # Wait before checking again
        time.sleep(10)  # Check every 10 seconds

def keep_alive():
    """Keep the bot alive and handle commands"""
    @bot.message_handler(commands=['start', 'status'])
    def send_status(message):
        status_msg = "✅ *OTP Forwarder Bot is running!*\n\n"
        status_msg += f"📧 Monitoring: {EMAIL_ADDRESS}\n"
        status_msg += f"📱 Channel: {CHANNEL_ID}\n"
        status_msg += f"🔄 Checking emails every 10 seconds"
        bot.reply_to(message, status_msg, parse_mode='Markdown')
    
    @bot.message_handler(commands=['help'])
    def send_help(message):
        help_msg = "🤖 *OTP Forwarder Bot Help*\n\n"
        help_msg += "/start - Check bot status\n"
        help_msg += "/status - Check bot status\n"
        help_msg += "/help - Show this help message\n\n"
        help_msg += "The bot automatically forwards OTP codes from your email to the channel."
        bot.reply_to(message, help_msg, parse_mode='Markdown')
    
    # Start bot polling in a separate thread
    print("🤖 Starting Telegram bot...")
    Thread(target=lambda: bot.infinity_polling(timeout=60, long_polling_timeout=60)).start()

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 Starting OTP Forwarder Bot")
    print("=" * 50)
    
    # Verify configuration
    if not all([BOT_TOKEN, CHANNEL_ID, EMAIL_ADDRESS, EMAIL_PASSWORD]):
        print("❌ Missing configuration! Set environment variables:")
        print("BOT_TOKEN, CHANNEL_ID, EMAIL_ADDRESS, EMAIL_PASSWORD")
        exit(1)
    
    print(f"📧 Email: {EMAIL_ADDRESS}")
    print(f"📱 Channel: {CHANNEL_ID}")
    print(f"🌐 IMAP Server: {IMAP_SERVER}")
    print("=" * 50)
    
    # Start Telegram bot
    keep_alive()
    
    # Start email monitoring
    check_emails()
