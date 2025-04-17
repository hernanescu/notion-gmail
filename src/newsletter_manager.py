"""
Newsletter Manager module for coordinating the entire workflow.
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Set, Dict, List, Optional, Tuple

import config
from src.gmail_service import GmailService
from src.notion_service import NotionService
from src.content_processor import ContentProcessor
from src.data_storage import DataStorage
from src.web_scraper import WebScraper

logger = logging.getLogger("gmail_notion_manager.manager")

class NewsletterManager:
    """Main manager class that coordinates the entire workflow."""
    
    def __init__(self):
        """Initialize the newsletter manager and its components."""
        self.gmail = GmailService()
        self.notion = NotionService()
        self.processor = ContentProcessor()
        self.storage = DataStorage()
        self.scraper = WebScraper()
        
        self.processed_ids = self.storage.load_processed_ids()
        self.last_check_time = datetime.now() - timedelta(days=config.SETTINGS["history_days"])
        self.processed_count = 0
        self.web_scraped_count = 0
        self.fallback_count = 0
    
    def process_new_emails(self):
        """Process new emails from monitored senders."""
        if not config.MONITORED_SENDERS:
            logger.warning("No monitored senders configured. Please add email addresses to MONITORED_SENDERS in config.py")
            return
            
        try:
            # Create query for monitored senders
            sender_query = " OR ".join([f"from:{sender}" for sender in config.MONITORED_SENDERS])
            
            # Add time filter to only get emails since last check
            time_filter = f"after:{int(self.last_check_time.timestamp())}"
            query = f"({sender_query}) {time_filter}"
            
            logger.info(f"Querying for new emails with: {query}")
            
            # Get messages matching query
            messages = self.gmail.query_messages(query, config.SETTINGS["max_emails_per_run"])
            logger.info(f"Found {len(messages)} new messages")
            
            self.processed_count = 0
            self.web_scraped_count = 0
            self.fallback_count = 0
            
            for message in messages:
                # Skip if already processed
                if message['id'] in self.processed_ids:
                    logger.debug(f"Skipping already processed message: {message['id']}")
                    continue
                    
                logger.info(f"Processing message ID: {message['id']}")
                email_data = self.gmail.get_email_content(message['id'])
                email_data['message_id'] = message['id']
                
                # Try to use web scraping first
                web_content = self._try_web_scraping(email_data)
                
                if web_content:
                    # Use web-scraped content for Notion
                    logger.info(f"Using web-scraped content for message: {message['id']}")
                    self.web_scraped_count += 1
                    
                    # Update email data with improved content
                    email_data['body'] = web_content['body']
                    email_data['links'] = web_content['links']
                    email_data['sections'] = web_content['sections']
                    email_data['was_scraped'] = True
                    
                    # Categorize the web-scraped content
                    category, confidence, all_scores = self.processor.categorize_content(
                        email_data['subject'], email_data['body']
                    )
                else:
                    # Use original email content as fallback
                    logger.info(f"Using original email content for message: {message['id']}")
                    self.fallback_count += 1
                    
                    # Categorize the email content
                    category, confidence, all_scores = self.processor.categorize_content(
                        email_data['subject'], email_data['body']
                    )
                    
                    # Flag that this wasn't web-scraped
                    email_data['was_scraped'] = False
                    email_data['sections'] = None
                
                # Create Notion entry
                self.notion.create_entry(email_data, category, confidence, all_scores)
                
                # Mark as processed
                self.processed_ids.add(message['id'])
                self.processed_count += 1
                
                # Save processed IDs periodically
                if self.processed_count % config.SETTINGS["batch_save_count"] == 0:
                    self.storage.save_processed_ids(self.processed_ids)
            
            # Update the last check time
            self.last_check_time = datetime.now()
            
            # Save processed IDs to persistent storage
            if self.processed_count > 0:
                self.storage.save_processed_ids(self.processed_ids)
                
            logger.info(f"Processed {self.processed_count} new emails (Web scraped: {self.web_scraped_count}, Fallback: {self.fallback_count})")
            
        except Exception as e:
            logger.error(f"Error processing emails: {str(e)}")
    
    def _try_web_scraping(self, email_data: Dict) -> Optional[Dict]:
        """
        Try to scrape the newsletter content from the web version.
        Returns dict with improved content or None if web scraping failed.
        """
        try:
            # Try to extract a "View Online" link
            if not email_data.get('html'):
                logger.debug("No HTML content to extract 'View Online' link")
                return None
            
            online_link = self.scraper.extract_view_online_link(email_data['html'])
            
            if not online_link:
                logger.debug("No 'View Online' link found in the email")
                return None
            
            # Try to scrape content from the web version
            logger.info(f"Trying to scrape content from: {online_link}")
            sections, links, final_url = self.scraper.scrape_newsletter_content(online_link)
            
            if not sections:
                logger.warning(f"Failed to extract sections from web version: {online_link}")
                return None
            
            # Combine the sections into a structured text
            combined_text = ""
            for section in sections:
                section_name = section['name'].strip()
                if section_name:
                    combined_text += f"\n\n### {section_name}\n\n"
                
                for content_item in section['content']:
                    combined_text += f"{content_item}\n\n"
            
            # Return the improved content
            return {
                'body': combined_text.strip(),
                'links': links or email_data.get('links', []),
                'sections': sections,
                'source_url': final_url
            }
            
        except Exception as e:
            logger.error(f"Error in web scraping: {str(e)}")
            return None
            
    def get_stats(self) -> Dict:
        """Get statistics about the processed emails."""
        return {
            "processed_ids_count": len(self.processed_ids),
            "last_check_time": self.last_check_time.isoformat(),
            "processed_count": self.processed_count,
            "web_scraped_count": self.web_scraped_count,
            "fallback_count": self.fallback_count
        } 