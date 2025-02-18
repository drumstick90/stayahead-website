#!/usr/bin/env python3
import sqlite3
import subprocess
import os
import json
import urllib.parse
import requests
from datetime import datetime

# --- Configuration ---
CUSTOMERS_DB = '/var/db/stayahead/customers.db'
SENDGRID_API_URL = 'https://api.sendgrid.com/v3/mail/send'
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
FROM_EMAIL = 'info@stayahead.guru'
SUBJECT_TEMPLATE = "Trending {field} - {category} Articles - {date}"

# --- Helper Functions ---

def get_customers():
    """Open the customers.db and return all customer records."""
    conn = sqlite3.connect(CUSTOMERS_DB)
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers")
    rows = cur.fetchall()
    conn.close()
    return rows

def parse_parameters(param_str):
    """
    Parse a query-string parameter value.
    Example: "field=Biology+%26+Biochemistry&category=Agriculture%2C+Multidisciplinary"
    Returns a tuple: (field, category)
    """
    parsed = urllib.parse.parse_qs(param_str)
    field = parsed.get('field', [''])[0]
    category = parsed.get('category', [''])[0]
    return field, category

def generate_newsletter(field, category):
    """
    Runs newsletter_generator.py with the customer's field and category.
    Assumes that newsletter_generator.py uses environment variables BASE_FIELD and BASE_CATEGORY.
    Returns the HTML output as a string.
    """
    env = os.environ.copy()
    env["BASE_FIELD"] = field
    env["BASE_CATEGORY"] = category
    try:
        output = subprocess.check_output(["python3", "newsletter_generator.py"], env=env)
        return output.decode('utf-8')
    except subprocess.CalledProcessError as e:
        print(f"Error generating newsletter for field {field}, category {category}: {e}")
        return ""

def send_email(to_email, html_content, subject):
    """
    Sends an email via the SendGrid API with the given HTML content.
    """
    payload = {
        "personalizations": [{
            "to": [{"email": to_email}]
        }],
        "from": {"email": FROM_EMAIL},
        "subject": subject,
        "content": [{
            "type": "text/html",
            "value": html_content
        }]
    }
    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.post(SENDGRID_API_URL, headers=headers, json=payload)
    return response

def main():
    customers = get_customers()
    for row in customers:
        # Assuming the columns in your customers table are:
        # id | email | display_field | param_str | timestamp
        customer_id, email, display_field, param_str, timestamp = row
        field, category = parse_parameters(param_str)
        print(f"Processing customer {email}: field={field}, category={category}")
        
        # Generate the newsletter for this customer.
        newsletter_html = generate_newsletter(field, category)
        if not newsletter_html:
            print(f"Skipping {email} due to newsletter generation error.")
            continue

        # You can dynamically compute today's date or use a fixed date as needed.
        date_str = datetime.now().strftime("%Y-%m-%d")
        subject = SUBJECT_TEMPLATE.format(field=field, category=category, date=date_str)
        
        # Send the email via SendGrid.
        response = send_email(email, newsletter_html, subject)
        if response.status_code in (200, 202):
            print(f"Email sent successfully to {email}")
        else:
            print(f"Error sending email to {email}: {response.status_code} {response.text}")

if __name__ == '__main__':
    main()