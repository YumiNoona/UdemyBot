import imaplib
import email
import re
import time
import requests
import json
from email.header import decode_header
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class HealthHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for health checks"""
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Udemy Bot is running!')
    
    def log_message(self, format, *args):
        # Suppress HTTP server logs
        pass

class UdemyCodeBot:
    def __init__(self, email_config, telegram_config):
        self.email_config = email_config
        self.telegram_config = telegram_config
        self.processed_emails = set()  # Keep track of processed emails
        
    def connect_to_email(self):
        """Connect to email server"""
        try:
            mail = imaplib.IMAP4_SSL(self.email_config['imap_server'])
            mail.login(self.email_config['email'], self.email_config['password'])
            mail.select('inbox')
            return mail
        except Exception as e:
            logging.error(f"Failed to connect to email: {e}")
            return None
    
    def extract_udemy_code(self, email_body):
        """Extract verification code from Udemy email"""
        # Common patterns for Udemy verification codes
        patterns = [
            r'verification code[:\s]*(\d{6})',
            r'code[:\s]*(\d{6})',
            r'Your code[:\s]*(\d{6})',
            r'(\d{6})',  # Any 6-digit number as fallback
        ]
        
        for pattern in patterns:
            match = re.search(pattern, email_body, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def send_telegram_message(self, message):
        """Send message to Telegram group"""
        url = f"https://api.telegram.org/bot{self.telegram_config['bot_token']}/sendMessage"
        data = {
            'chat_id': self.telegram_config['chat_id'],
            'text': message,
            'parse_mode': 'HTML'
        }
        
        try:
            response = requests.post(url, data=data)
            if response.status_code == 200:
                logging.info("Message sent successfully to Telegram")
                return True
            else:
                logging.error(f"Failed to send message: {response.text}")
                return False
        except Exception as e:
            logging.error(f"Error sending Telegram message: {e}")
            return False
    
    def get_email_body(self, msg):
        """Extract email body from message"""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    try:
                        body = part.get_payload(decode=True).decode()
                        break
                    except:
                        pass
                elif content_type == "text/html" and "attachment" not in content_disposition and not body:
                    try:
                        body = part.get_payload(decode=True).decode()
                    except:
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode()
            except:
                pass
        
        return body
    
    def check_emails(self):
        """Check for new Udemy emails and extract codes"""
        mail = self.connect_to_email()
        if not mail:
            return
        
        try:
            # Search for emails from Udemy
            status, messages = mail.search(None, 'FROM "udemy" UNSEEN')
            
            if status == 'OK':
                email_ids = messages[0].split()
                
                for email_id in email_ids:
                    if email_id in self.processed_emails:
                        continue
                    
                    status, msg_data = mail.fetch(email_id, '(RFC822)')
                    
                    if status == 'OK':
                        email_message = email.message_from_bytes(msg_data[0][1])
                        
                        # Get subject
                        subject = decode_header(email_message["Subject"])[0][0]
                        if isinstance(subject, bytes):
                            subject = subject.decode()
                        
                        # Check if it's a verification email
                        if any(keyword in subject.lower() for keyword in ['verification', 'code', 'login', 'sign in']):
                            body = self.get_email_body(email_message)
                            code = self.extract_udemy_code(body)
                            
                            if code:
                                message = f"🎓 <b>Udemy Verification Code</b>\n\n" \
                                         f"Code: <code>{code}</code>\n" \
                                         f"Subject: {subject}\n\n" \
                                         f"<i>Auto-forwarded from email</i>"
                                
                                if self.send_telegram_message(message):
                                    self.processed_emails.add(email_id)
                                    logging.info(f"Sent code {code} to Telegram")
                                else:
                                    logging.error("Failed to send to Telegram")
                            else:
                                logging.info(f"No code found in email: {subject}")
                        
                        self.processed_emails.add(email_id)
            
        except Exception as e:
            logging.error(f"Error checking emails: {e}")
        finally:
            mail.close()
            mail.logout()
    
    def run_bot(self):
        """Run the email checking bot"""
        logging.info("Starting Udemy Code Bot...")
        
        # Send startup message
        startup_msg = "🤖 <b>Udemy Code Bot Started</b>\n\nBot is now monitoring for Udemy verification codes!"
        self.send_telegram_message(startup_msg)
        
        while True:
            try:
                self.check_emails()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logging.error(f"Bot error: {e}")
                time.sleep(60)  # Wait longer on error

def start_health_server():
    """Start HTTP server for health checks"""
    port = int(os.getenv('PORT', 8000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logging.info(f"Health server starting on port {port}")
    server.serve_forever()

def main():
    # Email configuration
    email_config = {
        'email': 'harusenpaiweeb@gmail.com',
        'password': 'ytew vyhk hclq sjjc',  # Your new Gmail app password
        'imap_server': 'imap.gmail.com'
    }
    
    # Telegram configuration
    telegram_config = {
        'bot_token': '8347731744:AAGRdAp32eWzfnbbzdafMpYWkSduTXBv4P4',
        'chat_id': '-1002045295402'
    }
    
    # Create bot
    bot = UdemyCodeBot(email_config, telegram_config)
    
    # Start health server in background thread
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    # Run bot
    bot.run_bot()

if __name__ == "__main__":
    main()
