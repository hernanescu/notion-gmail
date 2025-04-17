"""
Newsletter Manager module for coordinating the entire workflow.
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Set, Dict, List

import config
from src.gmail_service import GmailService
from src.notion_service import NotionService
from src.content_processor import ContentProcessor
from src.data_storage import DataStorage

logger = logging.getLogger("gmail_notion_manager.manager")

class NewsletterManager:
    """Main manager class that coordinates the entire workflow."""
    
    def __init__(self):
        """Initialize the newsletter manager and its components."""
        self.gmail = GmailService()
        self.notion = NotionService()
        self.processor = ContentProcessor()
        self.storage = DataStorage()
        
        self.processed_ids = self.storage.load_processed_ids()
        self.last_check_time = datetime.now() - timedelta(days=config.SETTINGS["history_days"])
        self.processed_count = 0
    
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
            for message in messages:
                # Skip if already processed
                if message['id'] in self.processed_ids:
                    logger.debug(f"Skipping already processed message: {message['id']}")
                    continue
                    
                logger.info(f"Processing message ID: {message['id']}")
                email_data = self.gmail.get_email_content(message['id'])
                email_data['message_id'] = message['id']
                
                # Categorize the content
                category, confidence, all_scores = self.processor.categorize_content(
                    email_data['subject'], email_data['body']
                )
                
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
                
            logger.info(f"Processed {self.processed_count} new emails")
            
        except Exception as e:
            logger.error(f"Error processing emails: {str(e)}")
            
    def get_stats(self) -> Dict:
        """Get statistics about the processed emails."""
        return {
            "processed_ids_count": len(self.processed_ids),
            "last_check_time": self.last_check_time.isoformat(),
            "processed_count": self.processed_count
        } 