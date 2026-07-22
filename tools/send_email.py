#!/usr/bin/env python3
import os
import sys
import json
import smtplib
from datetime import datetime
from zoneinfo import ZoneInfo
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Load env variables (override=True ensures local .env updates take effect immediately)
load_dotenv(override=True)

# Define file paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR = os.path.join(BASE_DIR, ".tmp")
SYNTHESIZED_NEWS_FILE = os.path.join(TMP_DIR, "synthesized_news.json")
HTML_NEWSLETTER_FILE = os.path.join(TMP_DIR, "newsletter.html")

def parse_recipients(raw_recipients):
    if not raw_recipients:
        return []
    raw = raw_recipients.strip()
    # Support JSON arrays or objects
    if raw.startswith(("[", "{")):
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [str(addr).strip().strip("'\"") for addr in data if addr and str(addr).strip()]
            elif isinstance(data, dict):
                if "emails" in data and isinstance(data["emails"], list):
                    return [str(addr).strip().strip("'\"") for addr in data["emails"] if addr and str(addr).strip()]
                return [str(val).strip().strip("'\"") for val in data.values() if val and str(val).strip()]
        except Exception:
            pass
            
    # Support comma, semicolon, or newline separated strings
    import re
    tokens = re.split(r'[,;\n]+', raw)
    recipients = []
    for token in tokens:
        clean = token.strip().strip("'\"")
        if clean:
            recipients.append(clean)
    return recipients

def send_email():
    raw_recipient_email = os.getenv("RECIPIENT_EMAIL")
    smtp_email = os.getenv("GMAIL_SMTP_EMAIL")
    smtp_password = os.getenv("GMAIL_SMTP_PASSWORD") # Gmail App Password
    
    # Clean password if user copied with quotes or spaces
    if smtp_password:
        smtp_password = smtp_password.strip("'\"").replace(" ", "").replace("\xa0", "")

    recipients = parse_recipients(raw_recipient_email)
    if not recipients:
        print("CRITICAL ERROR: RECIPIENT_EMAIL environment variable is empty or invalid.")
        sys.exit(1)
        
    if not os.path.exists(SYNTHESIZED_NEWS_FILE):
        print(f"CRITICAL ERROR: {SYNTHESIZED_NEWS_FILE} not found. Cannot send email.")
        sys.exit(1)
        
    # Check synthesized JSON for items (Defect A3 guard)
    try:
        with open(SYNTHESIZED_NEWS_FILE, "r", encoding="utf-8") as f:
            synthesized_data = json.load(f)
            
        total_items = sum(
            len(synthesized_data.get(sec, []))
            for sec in ["launches", "prompting_and_technique", "head_to_head", "tech_shifts", "repo_radar", "articles"]
        )
        if total_items == 0:
            print("CRITICAL ERROR: Synthesized newsletter contains zero items. Refusing to send empty email.")
            sys.exit(1)
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to validate synthesized JSON before sending email: {e}")
        sys.exit(1)

    if not os.path.exists(HTML_NEWSLETTER_FILE):
        print(f"CRITICAL ERROR: {HTML_NEWSLETTER_FILE} not found. Run generate_html.py first.")
        sys.exit(1)
        
    # Read the HTML content
    with open(HTML_NEWSLETTER_FILE, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    # Setup SMTP configurations
    if not smtp_email or not smtp_password:
        print("CRITICAL ERROR: GMAIL_SMTP_EMAIL or GMAIL_SMTP_PASSWORD is missing in environment.")
        sys.exit(1)
        
    print(f"Preparing newsletter email for {len(recipients)} recipient(s): {', '.join(recipients)}...")
    
    # Build Subject using Asia/Kolkata date (Defect A5)
    kolkata_now = datetime.now(ZoneInfo("Asia/Kolkata"))
    formatted_date = f"{kolkata_now.day} {kolkata_now.strftime('%b %Y')}"
    subject_title = f"Daily Tech Brief — {formatted_date}"
    
    try:
        # Connect once to Gmail SMTP Server
        print("Connecting to Gmail SMTP server...")
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(smtp_email, smtp_password)
        
        # Send individual email to each recipient so Gmail SMTP accepts it without spam filtering
        successful_count = 0
        for recipient in recipients:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject_title
            msg["From"] = f"BUILDR.ai Daily Brief <{smtp_email}>"
            msg["To"] = recipient
            
            part = MIMEText(html_content, "html")
            msg.attach(part)
            
            server.sendmail(smtp_email, [recipient], msg.as_string())
            successful_count += 1
            print(f" Delivered to: {recipient}")
            
        server.close()
        print(f"\nNewsletter successfully sent to all {successful_count} recipient(s)!")
    except Exception as e:
        print(f"Failed to send email: {e}")
        sys.exit(1)

if __name__ == "__main__":
    send_email()
