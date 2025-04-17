"""
Gmail service module for handling Gmail API interactions.
"""
import os
import base64
import email
import re
import html
import logging
from datetime import datetime
from typing import Dict, List, Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config

logger = logging.getLogger("gmail_notion_manager.gmail")

class GmailService:
    """Handles all Gmail API operations."""
    
    def __init__(self):
        """Initialize the Gmail service."""
        self.service = self._setup_gmail_service()
    
    def _setup_gmail_service(self):
        """Set up Gmail API service."""
        creds = None
        if os.path.exists('token.json'):
            try:
                creds = Credentials.from_authorized_user_file('token.json', config.SCOPES)
            except Exception as e:
                logger.error(f"Error loading credentials: {str(e)}")
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Error refreshing credentials: {str(e)}")
                    creds = None
            
            if not creds:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', config.SCOPES)
                    creds = flow.run_local_server(port=0)
                    with open('token.json', 'w') as token:
                        token.write(creds.to_json())
                except Exception as e:
                    logger.error(f"Error creating new credentials: {str(e)}")
                    raise

        return build('gmail', 'v1', credentials=creds)
    
    def _extract_links(self, text: str) -> List[str]:
        """Extract URLs from text content."""
        # Simple regex for URL extraction
        url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+(?<=[\w/])'
        return re.findall(url_pattern, text)

    def _decode_body(self, part) -> Optional[str]:
        """Safely decode email body parts."""
        if 'body' not in part or 'data' not in part['body']:
            return None
            
        try:
            data = part['body']['data']
            decoded_bytes = base64.urlsafe_b64decode(data)
            
            # Try different encodings
            try:
                return decoded_bytes.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    return decoded_bytes.decode('latin-1')
                except UnicodeDecodeError:
                    return decoded_bytes.decode('ascii', errors='ignore')
        except Exception as e:
            logger.warning(f"Error decoding email body: {str(e)}")
            return None

    def _clean_html_content(self, html_content: str) -> str:
        """Better HTML to text conversion that preserves newsletter structure."""
        if not html_content:
            return ""
            
        # Remove style tags and their contents completely
        cleaned_text = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL)
        
        # Remove script tags and their contents
        cleaned_text = re.sub(r'<script[^>]*>.*?</script>', '', cleaned_text, flags=re.DOTALL)
        
        # Remove invisible characters often used in newsletters for spacing
        cleaned_text = re.sub(r'[\u200B-\u200D\uFEFF\u00A0\u2000-\u200F\u2028-\u202F\u205F-\u206F]', '', cleaned_text)
        
        # Replace <div>, <p>, and <br> with newlines to preserve structure
        cleaned_text = re.sub(r'<(?:div|p)[^>]*>', '\n', cleaned_text)
        cleaned_text = re.sub(r'</(?:div|p)>', '\n', cleaned_text)
        cleaned_text = re.sub(r'<br\s*/?>|<br>|<hr\s*/?>|<hr>', '\n', cleaned_text)
        
        # Convert heading tags to uppercase with newlines before and after
        for i in range(1, 7):
            cleaned_text = re.sub(f'<h{i}[^>]*>(.*?)</h{i}>', r'\n\n\1\n', cleaned_text)
        
        # Preserve list items
        cleaned_text = re.sub(r'<li[^>]*>(.*?)</li>', r'\n• \1', cleaned_text)
        
        # Remove all remaining HTML tags
        cleaned_text = re.sub(r'<[^>]+>', ' ', cleaned_text)
        
        # Decode HTML entities
        cleaned_text = html.unescape(cleaned_text)
        
        # Fix extra spacing
        cleaned_text = re.sub(r'\n\s+\n', '\n\n', cleaned_text)  # Remove lines with just whitespace
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)   # Limit to two consecutive newlines
        cleaned_text = re.sub(r' {2,}', ' ', cleaned_text)       # Remove multiple spaces
        
        # Detect and preserve common newsletter section headers
        section_headers = [
            r'(WHAT\'S NEW)',
            r'(IN THE NEWS)',
            r'(RELEASES)',
            r'(TOOLS)',
            r'(RESOURCES)',
            r'(ATTACKS[\s&]*VULNERABILITIES)',
            r'(STRATEGIES[\s&]*TACTICS)',
            r'(LAUNCHES)',
            r'(UPCOMING EVENTS)',
            r'(FUNDING)',
            r'(T\s*L\s*D\s*R)'
        ]
        
        for pattern in section_headers:
            cleaned_text = re.sub(pattern, r'\n\n\1\n', cleaned_text, flags=re.IGNORECASE)
        
        # Preserve links when numbered like: "Sign up [1]" and convert to Notion-readable format
        cleaned_text = re.sub(r'\[(\d+)\]', r'[^\1]', cleaned_text)
        
        return cleaned_text.strip()
    
    def get_email_content(self, message_id: str) -> Dict:
        """Extract content from email message."""
        try:
            message = self.service.users().messages().get(
                userId='me', id=message_id, format='full'
            ).execute()
            
            headers = message['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), "No Subject")
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), "Unknown Sender")
            
            # Initialize body content
            plain_body = ""
            html_body = ""
            links = []
            
            # Process message parts
            if 'parts' in message['payload']:
                parts = message['payload']['parts']
                
                # First prioritize HTML content for newsletters
                for part in parts:
                    mime_type = part.get('mimeType', '')
                    if mime_type == 'text/html':
                        content = self._decode_body(part)
                        if content:
                            html_body = content
                            # Convert HTML to structured plain text with our improved method
                            plain_body = self._clean_html_content(html_body)
                            break
                
                # If no HTML, try to get plain text
                if not html_body:
                    for part in parts:
                        mime_type = part.get('mimeType', '')
                        if mime_type == 'text/plain':
                            content = self._decode_body(part)
                            if content:
                                plain_body = content
                                break
                
                # Handle multipart/alternative or nested parts
                if not plain_body and not html_body:
                    for part in parts:
                        if 'parts' in part:
                            for subpart in part['parts']:
                                mime_type = subpart.get('mimeType', '')
                                if mime_type == 'text/html' and not html_body:
                                    content = self._decode_body(subpart)
                                    if content:
                                        html_body = content
                                        plain_body = self._clean_html_content(html_body)
                                elif mime_type == 'text/plain' and not plain_body and not html_body:
                                    content = self._decode_body(subpart)
                                    if content:
                                        plain_body = content
            
            # If no parts, try body directly
            elif 'body' in message['payload'] and 'data' in message['payload']['body']:
                content = self._decode_body(message['payload'])
                if content:
                    if message['payload'].get('mimeType') == 'text/html':
                        html_body = content
                        plain_body = self._clean_html_content(html_body)
                    else:
                        plain_body = content
            
            # Extract links from HTML or plain text
            if html_body:
                links = self._extract_links(html_body)
            if not links and plain_body:
                links = self._extract_links(plain_body)
            
            return {
                'subject': subject,
                'sender': sender,
                'body': plain_body,
                'html': html_body,
                'links': links,
                'date': datetime.fromtimestamp(int(message['internalDate'])/1000).isoformat()
            }
            
        except HttpError as error:
            logger.error(f"Error retrieving message {message_id}: {str(error)}")
            return {
                'subject': "Error retrieving message",
                'sender': "Unknown",
                'body': f"Error: {str(error)}",
                'html': "",
                'links': [],
                'date': datetime.now().isoformat()
            }
    
    def query_messages(self, query: str, max_results: int = 50) -> List[Dict]:
        """Query Gmail for messages matching the criteria."""
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            return results.get('messages', [])
        except HttpError as e:
            logger.error(f"Gmail API Error in query: {str(e)}")
            return [] 