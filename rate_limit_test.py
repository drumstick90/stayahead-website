#!/usr/bin/env python3
"""
NATIONAL SECURITY LEVEL ASYNC API RATE LIMIT & DATA EXTRACTION SCRIPT

This script loads field/category pairs from a JSON file (fields_and_categories.json),
computes the target query date (e.g., 7 days ago), and concurrently queries the 
ooir.org API endpoint for each field/category combination using asynchronous HTTP 
requests via aiohttp.

Each request uses a randomly generated email to help avoid blocking. Debugging 
information is logged in detail to both console and file.
"""

import asyncio
import aiohttp
import json
import logging
import random
import string
import sys
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

# -----------------------------------------------------------
# Configuration Section
# -----------------------------------------------------------
API_URL = "https://ooir.org/api.php"
# The base query parameters for the API (except for dynamic parts).
BASE_PARAMS = {
    "type": "paper-trends",
    # "day" will be added dynamically
    # "field" and "category" will be extracted from each entry in the JSON
    # "email" will be randomly generated
}

# Path to the fields_and_categories.json file
FIELDS_CATEGORIES_FILE = "./public/fields_and_categories.json"

# Set the target date offset (e.g., 7 days ago)
DAYS_OFFSET = 7

# Optional per-request delay (in seconds); set to 0 if not needed.
PER_REQUEST_DELAY = 0  # e.g., 60 for 1 minute delay between individual queries

# Maximum concurrent requests (set as needed)
MAX_CONCURRENT_REQUESTS = 10

# -----------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("async_rate_limit_test.log")
    ]
)

# -----------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------
def get_query_date(days_offset=DAYS_OFFSET):
    """
    Returns a date string (YYYY-MM-DD) for a date 'days_offset' days ago.
    """
    target_date = datetime.now() - timedelta(days=days_offset)
    date_str = target_date.strftime("%Y-%m-%d")
    logging.debug("Computed query date: %s", date_str)
    return date_str

def generate_random_email():
    """
    Generates a random email address using an 8-character random string
    and one of many possible domains.
    """
    random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    # Enriched list of 100 domains can be loaded or hardcoded here.
    domains = [
        "example.com", "mail.com", "test.org", "demo.net", "gmail.com", "yahoo.com", "outlook.com", "hotmail.com",
        "live.com", "msn.com", "aol.com", "icloud.com", "protonmail.com", "zoho.com", "gmx.com", "fastmail.com",
        "yandex.com", "rediffmail.com", "inbox.com", "mail.ru", "bigpond.com", "cox.net", "comcast.net", "verizon.net",
        "bellsouth.net", "earthlink.net", "sbcglobal.net", "charter.net", "mailinator.com", "sharklasers.com",
        # ... (Add up to 100 domains as desired)
        "domain91.com", "domain92.com", "domain93.com", "domain94.com", "domain95.com", "domain96.com", "domain97.com",
        "domain98.com", "domain99.com", "domain100.com"
    ]
    domain = random.choice(domains)
    email = f"{random_string}@{domain}"
    return email

async def query_api(session, params):
    """
    Sends an asynchronous GET request to the API with given parameters.
    Returns a tuple of (params, json_data) on success, or logs and returns None.
    """
    try:
        async with session.get(API_URL, params=params, timeout=30) as response:
            status = response.status
            text = await response.text()
            logging.debug("Request with params %s returned status %s", params, status)
            if status == 200:
                try:
                    json_data = await response.json()
                    return params, json_data
                except Exception as e:
                    logging.error("Failed to parse JSON for params %s: %s", params, e)
                    return params, None
            elif status == 429:
                logging.warning("Rate limited for params %s: 429 Too Many Requests", params)
                return params, None
            else:
                logging.warning("Unexpected status %s for params %s: %s", status, params, text)
                return params, None
    except Exception as e:
        logging.error("Exception during request with params %s: %s", params, e)
        return params, None

async def run_queries_concurrently():
    """
    Loads field/category data from JSON, constructs query parameters for each combination,
    and runs asynchronous queries concurrently with a semaphore limiting max concurrent requests.
    """
    query_date = get_query_date()
    tasks = []
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    # Load fields and categories from file.
    try:
        with open(FIELDS_CATEGORIES_FILE, "r", encoding="utf-8") as f:
            fields_data = json.load(f)
        logging.info("Loaded fields and categories data from %s", FIELDS_CATEGORIES_FILE)
    except Exception as e:
        logging.error("Error loading %s: %s", FIELDS_CATEGORIES_FILE, e)
        sys.exit(1)
    
    # Prepare a list of tasks for each field/category combination.
    for field_key, field_info in fields_data.items():
        base_field = field_info.get("field")
        categories = field_info.get("categories", {})
        for category_label, query_string in categories.items():
            # Parse query_string into parameters; our API_URL expects "field", "category", etc.
            qs_params = dict(parse_qs(query_string))
            # Flatten each value from list to string (since parse_qs returns lists)
            qs_params = {k: v[0] for k, v in qs_params.items()}
            # Build complete parameters for this query.
            params = BASE_PARAMS.copy()
            params["day"] = query_date
            # Merge the parameters from the JSON; they already include proper URL encoding.
            params.update(qs_params)
            # Use a random email to vary the request.
            params["email"] = generate_random_email()
            
            # Wrap the API query in a semaphore to limit concurrency.
            async def sem_query(p=params):
                async with semaphore:
                    result = await query_api(session, p)
                    if PER_REQUEST_DELAY > 0:
                        await asyncio.sleep(PER_REQUEST_DELAY)
                    return result
            
            tasks.append(sem_query())
    
    # Create a persistent session for all requests.
    async with aiohttp.ClientSession() as session:
        # Run all tasks concurrently.
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return results

# -----------------------------------------------------------
# Main Execution Section
# -----------------------------------------------------------
async def main():
    logging.info("Starting asynchronous API queries for multiple field/category pairs")
    start_time = datetime.now()
    results = await run_queries_concurrently()
    duration = (datetime.now() - start_time).total_seconds()
    logging.info("Completed all queries in %.2f seconds", duration)
    
    # Process and print results: Here we simply log the parameters and the size of the returned JSON.
    for params, json_data in results:
        if json_data is not None:
            logging.info("Query for params %s returned JSON with %d top-level keys", params, len(json_data))
        else:
            logging.warning("Query for params %s returned no data", params)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Script interrupted by user")