import pypdf
import requests
from bs4 import BeautifulSoup
import re
import logging

logger = logging.getLogger(__name__)

def extract_from_pdf(file):
    """
    Extracts text from a PDF file.
    """
    reader = pypdf.PdfReader(file)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    
    return sanitize_text(text)

def extract_from_url(url):
    """
    Scrapes text from a URL, stripping non-content tags.
    """
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Strip non-content tags
        for tag in soup(['script', 'style', 'nav', 'footer', 'svg', 'header']):
            tag.decompose()
            
        text = soup.get_text(separator=' ')
        return sanitize_text(text)
    except Exception as e:
        return f"Error extracting from URL: {str(e)}"

def sanitize_text(text):
    """
    Sanitizes text by removing excessive newlines and non-ascii characters.
    """
    # Remove non-ascii
    text = text.encode('ascii', 'ignore').decode('ascii')
    # Remove excessive newlines/whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text
