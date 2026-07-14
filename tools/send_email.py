#!/usr/bin/env python3
import os
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Define file paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR = os.path.join(BASE_DIR, ".tmp")
HTML_NEWSLETTER_FILE = os.path.join(TMP_DIR, "newsletter.html")

def send_email():
    recipient_email = os.getenv("RECIPIENT_EMAIL")
    smtp_email = os.getenv("GMAIL_SMTP_EMAIL")
    smtp_password = os.getenv("GMAIL_SMTP_PASSWORD") # Gmail App Password
    
    # Clean password if user copied with quotes or spaces
    if smtp_password:
        smtp_password = smtp_password.strip("'\"").replace(" ", "").replace("\xa0", "")

    if not recipient_email:
        print("Error: RECIPIENT_EMAIL env variable is not set.")
        sys.exit(1)
        
    if not os.path.exists(HTML_NEWSLETTER_FILE):
        print(f"Error: {HTML_NEWSLETTER_FILE} not found. Run generate_html.py first.")
        sys.exit(1)
        
    # Read the HTML content
    with open(HTML_NEWSLETTER_FILE, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    # Setup SMTP configurations
    if not smtp_email or not smtp_password:
        print("SMTP Credentials not fully configured. Checking for local SMTP options...")
        print("Please configure GMAIL_SMTP_EMAIL and GMAIL_SMTP_PASSWORD in your .env file to enable mail dispatch.")
        sys.exit(1)
        
    print(f"Preparing newsletter email for {recipient_email}...")
    
    # Create Message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Daily Tech Brief: AI, Networks & Systems"
    msg["From"] = f"Tech Radar <{smtp_email}>"
    msg["To"] = recipient_email
    
    # Attach HTML
    part = MIMEText(html_content, "html")
    msg.attach(part)
    
    try:
        # Connect to Gmail SMTP Server
        print("Connecting to Gmail SMTP server...")
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(smtp_email, smtp_password)
        
        # Send mail
        server.sendmail(smtp_email, recipient_email, msg.as_string())
        server.close()
        print("Newsletter successfully sent!")
    except Exception as e:
        print(f"Failed to send email: {e}")
        sys.exit(1)

if __name__ == "__main__":
    send_email()
