import os
import logging
import time
import re
import urllib.request
import urllib.parse
import json
import xml.etree.ElementTree as ET

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

def get_cik_number(company_name):
    search_url = f"https://www.sec.gov/cgi-bin/browse-edgar?company={urllib.parse.quote(company_name)}&owner=exclude&action=getcompany&output=atom"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }
    try:
        req = urllib.request.Request(search_url, headers=headers)
        with urllib.request.urlopen(req) as response:
            time.sleep(REQUEST_INTERVAL)
            if response.status == 200:
                feed = ET.fromstring(response.read().decode('utf-8'))
                cik_numbers = feed.findall('.//{http://www.w3.org/2005/Atom}company-info/{http://www.w3.org/2005/Atom}cik')
                if cik_numbers:
                    return cik_numbers[0].text
                else:
                    logger.error(f"No CIK number found for company: {company_name}")
                    return None
            else:
                logger.error(f"Failed to fetch CIK number. Status code: {response.status}")
                return None
    except Exception as e:
        logger.error(f"Error retrieving CIK number: {e}")
        return None

def get_ticker_symbol(cik_number):
    url = f"https://data.sec.gov/submissions/CIK{cik_number}.json"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': 'application/json',
        'Connection': 'keep-alive'
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            time.sleep(REQUEST_INTERVAL)
            if response.status == 200:
                data = json.loads(response.read().decode())
                ticker_symbol = data.get('tickers', [])[0] if data.get('tickers') else None
                return ticker_symbol
            else:
                logger.error(f"Error fetching ticker symbol for CIK: {cik_number}")
                return None
    except Exception as e:
        logger.error(f"Error retrieving ticker symbol: {e}")
        return None

def inspect_document_for_cybersecurity(link):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }
    search_terms = ["Material Cybersecurity Incidents", "Item 1.05", "ITEM 1.05", "MATERIAL CYBERSECURITY INCIDENTS", "unauthorized access", "unauthorized activity", "cybersecurity incident", "cyber-attack", "cyberattack", "threat actor", "security incident", "ransomware attack", "cyber incident"]

    try:
        req = urllib.request.Request(link, headers=headers)
        with urllib.request.urlopen(req) as response:
            time.sleep(REQUEST_INTERVAL)
            if response.status == 200:
                document_text = response.read().decode('utf-8')
                document_text = re.sub(r'Forward-Looking Statements.*?(?=(Item\s+\d+\.\d+|$))', '', document_text, flags=re.IGNORECASE | re.DOTALL)
                if re.search(r'\b\s*Item 8.01\s*\b', document_text, re.IGNORECASE):
                    for term in search_terms[4:]:
                        if re.search(r'\b\s*' + re.escape(term) + r'\s*\b', document_text, re.IGNORECASE) or re.search(re.escape(term), document_text, re.IGNORECASE):
                            return True
                for term in search_terms[:4]:
                    if re.search(r'\b\s*' + re.escape(term) + r'\s*\b', document_text, re.IGNORECASE) or re.search(re.escape(term), document_text, re.IGNORECASE):
                        return True
    except Exception as e:
        logger.error(f"Failed to inspect document at {link}: {e}")
    return False

def fetch_filings_for_company(cik_number):
    search_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik_number}&type=8-K&dateb=&owner=exclude&count=100"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }
    try:
        req = urllib.request.Request(search_url, headers=headers)
        with urllib.request.urlopen(req) as response:
            time.sleep(REQUEST_INTERVAL)
            if response.status == 200:
                soup = response.read().decode('utf-8')
                document_links = re.findall(r'<a href="(/Archives/edgar/data/\d+/\d+/\d+-index.htm)" id="documentsbutton">Documents</a>', soup)
                for document_link in document_links:
                    full_link = f"https://www.sec.gov{document_link}"
                    if inspect_document_for_cybersecurity(full_link):
                        ticker_symbol = get_ticker_symbol(cik_number)
                        logger.info(f"Cybersecurity Incident Disclosure found: (Ticker: ${ticker_symbol}) (CIK: {cik_number}) - {full_link}")
            else:
                logger.error(f"Failed to fetch filings for CIK: {cik_number}. Status code: {response.status}")
    except Exception as e:
        logger.critical(f"Error fetching filings: {e}")

if __name__ == "__main__":
    company_name = input("Enter the company name: ")
    cik_number = get_cik_number(company_name)
    if cik_number:
        fetch_filings_for_company(cik_number)
    else:
        logger.error("No CIK number found for the given company.")
