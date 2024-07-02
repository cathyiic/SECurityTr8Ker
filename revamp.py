import os
import requests
import logging
from bs4 import BeautifulSoup
import time
from datetime import datetime
import re
import xml.etree.ElementTree as ET
#this one doesn't use colorlog or xlmtodict lol

# Define request interval, log file path, and logs directory
REQUEST_INTERVAL = 0.3
logs_dir = 'logs'
log_file_path = os.path.join(logs_dir, 'debug.log')

# Ensure the logs directory exists
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Initialize the root logger to capture DEBUG level logs
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # Capture everything at DEBUG level and above

# Setting up logging to console
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
console_handler.setLevel(logging.INFO)  # Console to show INFO and above
logger.addHandler(console_handler)

# Setting up logging to file to capture DEBUG and above
file_handler = logging.FileHandler(log_file_path)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
file_handler.setLevel(logging.DEBUG)  # File to capture everything at DEBUG level
logger.addHandler(file_handler)

def get_ticker_symbol(cik_number, company_name):
    url = f"https://data.sec.gov/submissions/CIK{cik_number}.json"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        time.sleep(REQUEST_INTERVAL)
        if response.status_code == 200:
            data = response.json()
            ticker_symbol = data.get('tickers', [])[0] if data.get('tickers') else None
            return ticker_symbol
        else:
            logger.error(f"Error fetching ticker symbol for CIK: {cik_number}")
            return None
    except Exception as e:
        logger.error(f"Error retrieving ticker symbol: {e}")
        return None

def inspect_document_for_cybersecurity(link):
    headers = {'User-Agent': 'Mozilla/5.0'}
    # Define a list of search terms you're interested in
    search_terms = ["Material Cybersecurity Incidents", "Item 1.05", "ITEM 1.05", "MATERIAL CYBERSECURITY INCIDENTS", "unauthorized access", "unauthorized activity", "cybersecurity incident", "cyber-attack", "cyberattack", "threat actor", "security incident", "ransomware attack", "cyber incident"]
    
    try:
        response = requests.get(link, headers=headers)
        time.sleep(REQUEST_INTERVAL)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            document_text = soup.get_text()  # Keep the document text as is, respecting case
            
            # Exclude "Forward-Looking Statements" section
            document_text = re.sub(r'Forward-Looking Statements.*?(?=(Item\s+\d+\.\d+|$))', '', document_text, flags=re.IGNORECASE | re.DOTALL)

            # First, check if Item 8.01 is present in the document
            if re.search(r'\b\s*Item 8.01\s*\b', document_text, re.IGNORECASE):
                # If Item 8.01 is present, check for the other cybersecurity-related terms
                for term in search_terms[4:]:  # Check terms from index 4 onward (cybersecurity-related)
                    pattern_with_boundaries = r'\b\s*' + re.escape(term) + r'\s*\b'
                    pattern_without_boundaries = re.escape(term)
                    if re.search(pattern_with_boundaries, document_text, re.IGNORECASE) or re.search(pattern_without_boundaries, document_text, re.IGNORECASE):
                        return True
            
            # Additionally, check for the terms related to Item 1.05
            for term in search_terms[:4]:  # Only check the first four terms (related to Item 1.05)
                pattern_with_boundaries = r'\b\s*' + re.escape(term) + r'\s*\b'
                pattern_without_boundaries = re.escape(term)
                if re.search(pattern_with_boundaries, document_text, re.IGNORECASE) or re.search(pattern_without_boundaries, document_text, re.IGNORECASE):
                    return True

    except Exception as e:
        logger.error(f"Failed to inspect document at {link}: {e}")
    
    return False

def fetch_filings_from_rss(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        time.sleep(REQUEST_INTERVAL)
        if response.status_code == 200:
            feed = ET.fromstring(response.content)
            for item in feed.findall('./channel/item'):
                xbrlFiling = item.find('./{http://www.sec.gov/Archives/edgar}xbrlFiling')
                form_type = xbrlFiling.find('{http://www.sec.gov/Archives/edgar}formType').text
                pubDate = item.find('pubDate').text
                if form_type in ['8-K', '8-K/A', 'FORM 8-K']:
                    company_name = xbrlFiling.find('{http://www.sec.gov/Archives/edgar}companyName').text
                    cik_number = xbrlFiling.find('{http://www.sec.gov/Archives/edgar}cikNumber').text
                    document_links = [xbrlFile.get('{http://www.sec.gov/Archives/edgar}@url') for xbrlFile in xbrlFiling.findall('{http://www.sec.gov/Archives/edgar}xbrlFiles/{http://www.sec.gov/Archives/edgar}xbrlFile') if xbrlFile.get('{http://www.sec.gov/Archives/edgar}@url').endswith(('.htm', '.html'))]
                    
                    for document_link in document_links:
                        if inspect_document_for_cybersecurity(document_link):
                            ticker_symbol = get_ticker_symbol(cik_number, company_name)
                            logger.info(f"Cybersecurity Incident Disclosure found: {company_name} (Ticker:${ticker_symbol}) (CIK:{cik_number}) - {document_link} - Published on {pubDate}")
                            break  # Assuming we only need to log once per filing
            logger.info("Fetched and parsed RSS feed successfully.")
    except Exception as e:
        logger.critical(f"Error fetching filings: {e}")

def monitor_sec_feed():
    rss_url = 'https://www.sec.gov/Archives/edgar/usgaap.rss.xml'
    while True:
        logger.info("Checking SEC RSS feed for 8-K filings...")
        fetch_filings_from_rss(rss_url)
        logger.info("Sleeping for 10 minutes before next check...")
        time.sleep(600)  # Sleep for 10 minutes

if __name__ == "__main__":
    monitor_sec_feed()
