#!/usr/bin/env python3
import requests
import time
import logging
import sqlite3
from datetime import datetime, timedelta
from urllib.parse import quote

# -------------------------------------------------
# Configuration Section
# -------------------------------------------------
API_URL = "https://ooir.org/api.php"
# Default internal API parameters – these can be overridden if needed.
BASE_PARAMS = {
    "type": "paper-trends",
    # "day" will be added dynamically
    "field": "Clinical Medicine",       # Example default field
    "category": "Oncology",             # Example default category
    "email": "newsletter@example.com"   # Base email for internal API query
}

# For Crossref DOI resolution:
CROSSREF_BASE_URL = "https://api.crossref.org/works/"

# SQLite database to store paper trends
SQLITE_DB_PATH = "paper_trends.db"

# Rate limit: Delay (in seconds) between each Crossref call.
CROSSREF_DELAY = 1

# -------------------------------------------------
# Logging Configuration
# -------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("newsletter_generator.log"),
        logging.StreamHandler()
    ]
)

# -------------------------------------------------
# Helper Functions
# -------------------------------------------------
def get_query_date(days_offset=7):
    """
    Returns a date string (YYYY-MM-DD) for a date 'days_offset' days ago.
    """
    target_date = datetime.now() - timedelta(days=days_offset)
    date_str = target_date.strftime("%Y-%m-%d")
    logging.debug("Computed query date: %s", date_str)
    return date_str

def query_internal_api(day, field, category, email):
    """
    Queries the internal API with the provided parameters and returns the JSON response.
    """
    params = BASE_PARAMS.copy()
    params["day"] = day
    params["field"] = field
    params["category"] = category
    params["email"] = email
    logging.info("Querying internal API with parameters: %s", params)
    response = requests.get(API_URL, params=params, timeout=30)
    response.raise_for_status()
    json_data = response.json()
    logging.debug("Internal API response: %s", json_data)
    return json_data

def resolve_doi(doi):
    """
    Resolves a DOI via the Crossref API to extract the paper title, journal, and publishing date.
    Returns a tuple: (title, journal, published_date).
    The publishing date is formatted as '22 January 2025'.
    On failure, returns fallback strings.
    """
    encoded_doi = quote(doi, safe='')
    url = f"{CROSSREF_BASE_URL}{encoded_doi}"
    logging.info("Resolving DOI: %s", doi)
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        message = data.get("message", {})
        title_list = message.get("title", [])
        container_list = message.get("container-title", [])
        issued = message.get("issued", {})
        date_parts = issued.get("date-parts", [])
        if date_parts and len(date_parts) > 0:
            parts = date_parts[0]
            if len(parts) >= 3:
                # Format as: Day Month Year, e.g., "22 January 2025"
                published_date = datetime(parts[0], parts[1], parts[2]).strftime("%d %B %Y")
            elif len(parts) == 2:
                published_date = datetime(parts[0], parts[1], 1).strftime("%B %Y")
            else:
                published_date = str(parts[0])
        else:
            published_date = "Date unavailable"
        title = title_list[0] if title_list else "Title unavailable"
        journal = container_list[0] if container_list else "Journal unavailable"
        logging.debug("Resolved DOI %s to title: %s, journal: %s, published: %s",
                      doi, title, journal, published_date)
        return title, journal, published_date
    except Exception as e:
        logging.error("Error resolving DOI %s: %s", doi, e)
        return "Title unavailable", "Journal unavailable", "Date unavailable"

def ensure_table_schema():
    """
    Ensures that the SQLite table 'paper_trends' exists and contains the 'published_date' column.
    If the column is missing, it is added.
    """
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(paper_trends)")
    columns = [row[1] for row in cursor.fetchall()]
    if "published_date" not in columns:
        logging.info("Adding missing column 'published_date' to paper_trends table.")
        cursor.execute("ALTER TABLE paper_trends ADD COLUMN published_date TEXT")
    conn.commit()
    conn.close()

def store_results_in_sqlite(records):
    """
    Stores a list of paper trend records (each a dict) in an SQLite database.
    Creates the table if it doesn't exist, and ensures the schema is up-to-date.
    """
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paper_trends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            field TEXT,
            category TEXT,
            day TEXT,
            doi TEXT,
            score INTEGER,
            title TEXT,
            journal TEXT,
            published_date TEXT,
            retrieved_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    # Ensure the published_date column exists
    ensure_table_schema()

    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    insert_sql = """
        INSERT INTO paper_trends (field, category, day, doi, score, title, journal, published_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    for record in records:
        cursor.execute(insert_sql, (
            record.get("field"),
            record.get("category"),
            record.get("day"),
            record.get("doi"),
            int(record.get("score", 0)),
            record.get("resolved_title", "N/A"),
            record.get("resolved_journal", "N/A"),
            record.get("resolved_published_date", "N/A")
        ))
    conn.commit()
    conn.close()
    logging.info("Stored %d records in SQLite database.", len(records))

def compose_email(articles, query_date, field, category):
    """
    Composes an HTML email newsletter from the enriched articles.
    Adjustments: Renames 'Date' to 'Publishing Date', removes score/ISSN,
    and makes the title clickable (linking to the DOI) using the Crossref published date.
    """
    subject = f"Trending {field} - {category} Articles - {query_date}"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{subject}</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      background-color: #f4f4f4;
      margin: 0;
      padding: 0;
      color: #333;
    }}
    .container {{
      max-width: 600px;
      margin: 20px auto;
      background: #ffffff;
      border: 1px solid #ddd;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }}
    .header {{
      background-color: #2c3e50;
      color: #fff;
      padding: 20px;
      text-align: center;
    }}
    .header h1 {{
      margin: 0;
      font-size: 24px;
    }}
    .content {{
      padding: 20px;
    }}
    .article {{
      border-bottom: 1px solid #eee;
      padding: 10px 0;
    }}
    .article:last-child {{
      border-bottom: none;
    }}
    .article h2 {{
      margin: 0 0 5px;
      font-size: 18px;
    }}
    .article h2 a {{
      color: #2980b9;
      text-decoration: none;
    }}
    .article h2 a:hover {{
      text-decoration: underline;
    }}
    .article p {{
      margin: 5px 0;
      font-size: 14px;
      color: #555;
    }}
    .footer {{
      background-color: #ecf0f1;
      padding: 15px;
      text-align: center;
      font-size: 12px;
      color: #7f8c8d;
    }}
    a {{
      color: #2980b9;
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>{subject}</h1>
      <p>Your weekly roundup of trending {category} articles in {field}</p>
    </div>
    <div class="content">
      <p>Dear Colleague,</p>
      <p>Below are the top trending {category} articles in {field} for the past 7 days:</p>
"""
    for article in articles:
        doi = article.get("doi", "N/A")
        title = article.get("resolved_title", "Title unavailable")
        journal = article.get("resolved_journal", "Journal unavailable")
        published_date = article.get("resolved_published_date", "Date unavailable")
        doi_link = f"https://doi.org/{doi}"
        html += f"""      <div class="article">
        <h2><a href="{doi_link}">{title}</a></h2>
        <p><strong>Journal:</strong> {journal}</p>
        <p><strong>Publishing Date:</strong> {published_date}</p>
      </div>
"""
    html += """      <p>We hope these articles inspire new insights and robust discussions in your research.</p>
      <p>Best regards,<br>Your Research Trends Team</p>
    </div>
    <div class="footer">
      <p>You are receiving this email because you subscribed to the newsletter.</p>
      <p><a href="#">Unsubscribe</a> | <a href="#">Manage Preferences</a></p>
      <p>&copy; 2025 Research Trends Inc. All rights reserved.</p>
    </div>
  </div>
</body>
</html>
"""
    return html

# -------------------------------------------------
# Main Execution Section
# -------------------------------------------------
def main():
    # Compute query date dynamically (e.g., 7 days ago)
    query_date = get_query_date(days_offset=7)
    
    # Load dynamic parameters from BASE_PARAMS.
    field = BASE_PARAMS.get("field")
    category = BASE_PARAMS.get("category")
    email = BASE_PARAMS.get("email")
    
    logging.info("Starting internal API query for date: %s, field: %s, category: %s", query_date, field, category)
    
    try:
        articles = query_internal_api(query_date, field, category, email)
        logging.info("Internal API returned %d records.", len(articles))
    except Exception as e:
        logging.error("Error querying internal API: %s", e)
        return

    enriched_articles = []
    for record in articles:
        # Skip records that don't match our dynamic parameters.
        if record.get("field") != field or record.get("category") != category or record.get("day") != query_date:
            logging.debug("Skipping record due to mismatched parameters: %s", record)
            continue
        
        doi = record.get("doi")
        if doi:
            title, journal, published_date = resolve_doi(doi)
            record["resolved_title"] = title
            record["resolved_journal"] = journal
            record["resolved_published_date"] = published_date
            enriched_articles.append(record)
            logging.info("Enriched record for DOI %s", doi)
            time.sleep(CROSSREF_DELAY)  # Respect Crossref rate limits.
        else:
            enriched_articles.append(record)
    
    # Store enriched results in SQLite for archival purposes.
    store_results_in_sqlite(enriched_articles)
    
    # Compose the HTML email newsletter using dynamic field and category.
    email_html = compose_email(enriched_articles, query_date, field, category)
    
    # Output the final email HTML.
    print(email_html)

if __name__ == "__main__":
    main()