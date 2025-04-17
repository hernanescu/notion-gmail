"""
Newsletter Manager module for coordinating the entire workflow.
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Set, Dict, List, Optional, Tuple, Any
import re

import config
from src.gmail_service import GmailService
from src.notion_service import NotionService
from src.content_processor import ContentProcessor
from src.data_storage import DataStorage
from src.web_scraper import WebScraper
from src.llm_service import LLMService

logger = logging.getLogger("gmail_notion_manager.manager")

class NewsletterManager:
    """Main manager class that coordinates the entire workflow."""
    
    def __init__(self):
        """Initialize the newsletter manager and its components."""
        # Initialize core services
        self.gmail = GmailService()
        self.storage = DataStorage()
        self.scraper = WebScraper()
        
        # Initialize LLM service if enabled
        self.use_llm = os.getenv("USE_LLM_CATEGORIZATION", "false").lower() == "true"
        self.llm_service = LLMService() if self.use_llm else None
        
        # Initialize processor with LLM service to avoid duplication
        self.processor = ContentProcessor(llm_service=self.llm_service)
        
        # Initialize Notion service
        self.notion = NotionService()
        
        # Log service initialization
        if self.use_llm:
            logger.info("Newsletter Manager initialized with LLM capabilities")
        else:
            logger.info("Newsletter Manager initialized with keyword-based categorization")
        
        # State tracking
        self.processed_ids = self.storage.load_processed_ids()
        self.last_check_time = datetime.now() - timedelta(days=config.SETTINGS["history_days"])
        self.processed_count = 0
        self.web_scraped_count = 0
        self.fallback_count = 0
    
    def process_new_emails(self):
        """Process new emails from monitored senders."""
        if not self.gmail or not self.notion:
            logger.error("Services not initialized properly")
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
                try:
                    self._process_single_email(message)
                except Exception as e:
                    logger.error(f"Error processing message {message.get('id', 'unknown')}: {type(e).__name__} - {str(e)}")
                    continue
            
            # Update the last check time
            self.last_check_time = datetime.now()
            
            # Save processed IDs to persistent storage
            if self.processed_count > 0:
                self.storage.save_processed_ids(self.processed_ids)
                
            logger.info(f"Processed {self.processed_count} new emails (Web scraped: {self.web_scraped_count}, Fallback: {self.fallback_count})")
            
        except Exception as e:
            logger.error(f"Error in email processing workflow: {type(e).__name__} - {str(e)}")
    
    def _process_single_email(self, message: Dict[str, Any]) -> None:
        """
        Process a single email message.
        
        Args:
            message: The email message data from Gmail API
        """
        # Skip if already processed
        if message['id'] in self.processed_ids:
            logger.debug(f"Skipping already processed message: {message['id']}")
            return
            
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
            email_data['source_url'] = web_content['source_url']
            
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
            
            # Extract first content link from email to use as source URL if available
            content_link = email_data['links'][0] if email_data['links'] else None
            if content_link:
                # Check if it's a likely newsletter link (heuristic based on URL patterns)
                newsletter_patterns = [
                    r'newsletter', r'campaign', r'bulletin', r'digest', r'update',
                    r'news\.', r'blog\.', r'article', r'post'
                ]
                
                is_newsletter_link = any(re.search(pattern, content_link, re.IGNORECASE) for pattern in newsletter_patterns)
                
                if is_newsletter_link:
                    logger.info(f"Using first link as source URL: {content_link}")
                    email_data['source_url'] = content_link
        
        # Generate a summary for the Description field if LLM is enabled
        if self.use_llm and self.llm_service:
            try:
                logger.info("Generating LLM summary for Description field")
                summary = self.llm_service.summarize_content(email_data['subject'], email_data['body'], max_words=100)
                email_data['summary'] = summary
                logger.debug(f"Generated summary: {summary}")
            except Exception as e:
                logger.error(f"Error generating summary: {type(e).__name__} - {str(e)}")
                email_data['summary'] = None
        
        # Create Notion entry
        self.notion.create_entry(email_data, category, confidence, all_scores)
        
        # Mark as processed
        self.processed_ids.add(message['id'])
        self.processed_count += 1
        
        # Save processed IDs periodically
        if self.processed_count % config.SETTINGS["batch_save_count"] == 0:
            self.storage.save_processed_ids(self.processed_ids)
    
    def _try_web_scraping(self, email_data: Dict) -> Optional[Dict]:
        """
        Try to scrape the newsletter content from the web version.
        
        Args:
            email_data: Dictionary containing email content
            
        Returns:
            Dictionary with improved content or None if web scraping failed
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
                    # Handle both string and dictionary content items
                    if isinstance(content_item, dict):
                        combined_text += f"{content_item.get('text', '')}\n\n"
                    else:
                        combined_text += f"{content_item}\n\n"
            
            # Ensure we have a valid source URL
            if not final_url:
                logger.warning("Final URL is empty, using original online link")
                final_url = online_link
            
            logger.info(f"Web scraping successful, using source URL: {final_url}")
            
            # Return the improved content
            return {
                'body': combined_text.strip(),
                'links': links or email_data.get('links', []),
                'sections': sections,
                'source_url': final_url
            }
            
        except Exception as e:
            logger.error(f"Error in web scraping: {type(e).__name__} - {str(e)}")
            return None
            
    def get_stats(self) -> Dict:
        """
        Get statistics about the processed emails.
        
        Returns:
            Dictionary containing processing statistics
        """
        return {
            "processed_ids_count": len(self.processed_ids),
            "last_check_time": self.last_check_time.isoformat(),
            "processed_count": self.processed_count,
            "web_scraped_count": self.web_scraped_count,
            "fallback_count": self.fallback_count
        } 