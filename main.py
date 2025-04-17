"""
Main entry point for the Gmail to Notion Newsletter Manager.
"""
import time
import schedule
from dotenv import load_dotenv
import logging

from src.utils import setup_logging, check_environment
from src.newsletter_manager import NewsletterManager
import config

# Load environment variables
load_dotenv()

# Set up logging
logger = setup_logging(log_file="app.log")
# Set web scraper logger to DEBUG level for detailed scraping logs
logging.getLogger("gmail_notion_manager.scraper").setLevel(logging.DEBUG)

def main():
    """Main entry point for the application."""
    logger.info("Starting Gmail to Notion Newsletter Manager...")
    
    # Check environment variables
    missing_vars = check_environment()
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these variables in your .env file or environment")
        return
    
    # Initialize the newsletter manager
    manager = NewsletterManager()
    
    # Schedule the email processing to run every N minutes
    interval = config.SETTINGS["check_interval_minutes"]
    schedule.every(interval).minutes.do(manager.process_new_emails)
    
    # Run immediately on startup
    manager.process_new_emails()
    
    logger.info(f"Service is running. Checking emails every {interval} minutes. Press Ctrl+C to exit.")
    
    # Keep the script running
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")

if __name__ == "__main__":
    main() 