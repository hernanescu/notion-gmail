"""
Utilities module with helper functions.
"""
import os
import logging
import re
from typing import Dict, List, Optional
from datetime import datetime, timedelta

# Setup logging helpers
def setup_logging(log_file="app.log", log_level=logging.INFO):
    """Set up logging with file and console handlers."""
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # Return the root logger
    return logging.getLogger("gmail_notion_manager")

# Time helpers
def get_datetime_range(days_back: int) -> Dict:
    """Get a datetime range from now to N days back."""
    now = datetime.now()
    start = now - timedelta(days=days_back)
    return {
        "start": start,
        "end": now
    }

def format_timestamp(timestamp: int) -> str:
    """Format a unix timestamp to ISO format."""
    return datetime.fromtimestamp(timestamp / 1000).isoformat()

# String helpers
def truncate_text(text: str, max_length: int) -> str:
    """Truncate text to a maximum length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."

def clean_html(html_content: str) -> str:
    """Remove HTML tags and clean up whitespace."""
    # Simple HTML tag removal (a more robust solution would use a library like BeautifulSoup)
    text = re.sub(r'<[^>]+>', ' ', html_content)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# Environment helpers
def check_environment() -> List[str]:
    """Check if all required environment variables are set."""
    required_vars = ["NOTION_TOKEN", "NOTION_DATABASE_ID"]
    missing = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
            
    return missing 