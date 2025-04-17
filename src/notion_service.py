"""
Notion service module for handling Notion API interactions.
"""
import os
import logging
from typing import Dict, List
from notion_client import Client
from notion_client.errors import APIResponseError
from datetime import datetime
import re

import config

logger = logging.getLogger("gmail_notion_manager.notion")

class NotionService:
    """Handles all Notion API operations."""
    
    def __init__(self):
        """Initialize the Notion service."""
        self.client = Client(auth=os.getenv("NOTION_TOKEN"))
        self.database_id = os.getenv("NOTION_DATABASE_ID")
        # Verify database properties on init
        self.available_properties = self._get_database_properties()
    
    def _get_database_properties(self) -> Dict:
        """Get the actual properties available in the Notion database."""
        try:
            database = self.client.databases.retrieve(self.database_id)
            return database.get("properties", {})
        except Exception as e:
            logger.error(f"Error retrieving database properties: {str(e)}")
            return {}
    
    def create_entry(self, email_data: Dict, category: str, confidence: float, all_scores: Dict[str, float]):
        """Create a new entry in Notion database."""
        try:
            # Prepare source links
            email_link = f"https://mail.google.com/mail/u/0/#inbox/{email_data['message_id']}"
            
            # Format other category scores for reference
            other_categories = ", ".join([f"{cat}: {score:.2f}" for cat, score in all_scores.items() if cat != category and score > 0])
            
            # Extract first link from email if available
            content_link = email_data['links'][0] if email_data['links'] else ""
            
            # Prepare properties based on configuration
            properties = {}
            
            # Set "Name" property using title type (according to config.py)
            if "Name" in self.available_properties:
                properties["Name"] = {"title": [{"text": {"content": email_data['subject']}}]}
            
            # Add other properties from config, but only if they exist in the database
            if "Category" in config.NOTION_DATABASE_PROPERTIES and "Category" in self.available_properties:
                properties["Category"] = {"select": {"name": category}}
            
            # Prioritize the web URL as the primary Source if available
            if "Source" in config.NOTION_DATABASE_PROPERTIES and "Source" in self.available_properties:
                # Use the web URL as primary source if available, otherwise use email link
                if email_data.get('source_url'):
                    properties["Source"] = {"url": email_data['source_url']}
                    logger.debug(f"Using source URL as primary source: {email_data['source_url']}")
                else:
                    properties["Source"] = {"url": email_link}
                    logger.debug(f"Using email link as primary source: {email_link}")
                
            if "Date" in config.NOTION_DATABASE_PROPERTIES and "Date" in self.available_properties:
                properties["Date"] = {"date": {"start": email_data['date']}}
            
            # Add the email URL as secondary source if we used web scraping
            if "Web Source" in config.NOTION_DATABASE_PROPERTIES and "Web Source" in self.available_properties:
                if email_data.get('was_scraped') or email_data.get('source_url'):
                    # If we used web scraping or have a source URL, use email link as secondary source
                    properties["Web Source"] = {"url": email_link}
                    logger.debug(f"Setting Web Source to email link: {email_link}")
                else:
                    # Otherwise leave it unset or set to None
                    properties["Web Source"] = {"url": None}
            
            # We'll move the full content to the page body, but still keep a short preview in the Description field
            if "Description" in config.NOTION_DATABASE_PROPERTIES and "Description" in self.available_properties:
                # Clean up the preview to remove any formatting characters or newlines
                cleaned_preview = re.sub(r'[\n\r\t]+', ' ', email_data['body'])
                cleaned_preview = re.sub(r'\s{2,}', ' ', cleaned_preview)
                cleaned_preview = re.sub(r'[*#\-_]+', '', cleaned_preview)
                # Ensure preview is under 2000 chars (Notion limit)
                preview = cleaned_preview[:1900] + "..." if len(cleaned_preview) > 1900 else cleaned_preview
                properties["Description"] = {"rich_text": [{"text": {"content": preview}}]}
                
            # Add optional properties if configured AND if they exist in the database
            if "Content Link" in config.NOTION_DATABASE_PROPERTIES and "Content Link" in self.available_properties:
                properties["Content Link"] = {"url": content_link} if content_link else {"url": None}
                
            if "Confidence" in config.NOTION_DATABASE_PROPERTIES and "Confidence" in self.available_properties:
                properties["Confidence"] = {"number": confidence}
                
            if "Other Categories" in config.NOTION_DATABASE_PROPERTIES and "Other Categories" in self.available_properties:
                other_cats_text = other_categories[:1900] if len(other_categories) > 1900 else other_categories
                properties["Other Categories"] = {"rich_text": [{"text": {"content": other_cats_text}}]}
                
            if "Sender" in config.NOTION_DATABASE_PROPERTIES and "Sender" in self.available_properties:
                sender_text = email_data['sender'][:1900] if len(email_data['sender']) > 1900 else email_data['sender']
                properties["Sender"] = {"rich_text": [{"text": {"content": sender_text}}]}
                
            if "Source Type" in config.NOTION_DATABASE_PROPERTIES and "Source Type" in self.available_properties:
                source_type = "Web Scraped" if email_data.get('was_scraped') else "Email"
                properties["Source Type"] = {"select": {"name": source_type}}
            
            # Prepare the page content blocks with enhanced formatting
            children = []
            
            # Add a header with sender and date
            sender_name = email_data['sender'].split('<')[0].strip()
            email_date = datetime.fromisoformat(email_data['date']).strftime("%B %d, %Y")
            
            # Add a divider and metadata section at the top
            children.extend([
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "Newsletter Details"
                                }
                            }
                        ],
                        "color": "blue_background"
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "From: "
                                },
                                "annotations": {
                                    "bold": True
                                }
                            },
                            {
                                "type": "text",
                                "text": {
                                    "content": sender_name
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "Date: "
                                },
                                "annotations": {
                                    "bold": True
                                }
                            },
                            {
                                "type": "text",
                                "text": {
                                    "content": email_date
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "Category: "
                                },
                                "annotations": {
                                    "bold": True
                                }
                            },
                            {
                                "type": "text",
                                "text": {
                                    "content": category
                                },
                                "annotations": {
                                    "color": "blue"
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "Source: "
                                },
                                "annotations": {
                                    "bold": True
                                }
                            },
                            {
                                "type": "text",
                                "text": {
                                    "content": "Web Scraped" if email_data.get('was_scraped') else "Email Content"
                                },
                                "annotations": {
                                    "color": "green" if email_data.get('was_scraped') else "gray"
                                }
                            }
                        ]
                    }
                }
            ])
            
            # Add source links
            if email_data.get('source_url'):
                # Add web version link
                children.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "Newsletter URL: "
                                },
                                "annotations": {
                                    "bold": True
                                }
                            },
                            {
                                "type": "text",
                                "text": {
                                    "content": "Web Version",
                                    "link": {"url": email_data['source_url']}
                                },
                                "annotations": {
                                    "color": "blue"
                                }
                            }
                        ]
                    }
                })
                
                # Add original email link
                children.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "Original Email: "
                                },
                                "annotations": {
                                    "bold": True
                                }
                            },
                            {
                                "type": "text",
                                "text": {
                                    "content": "Gmail Link",
                                    "link": {"url": email_link}
                                }
                            }
                        ]
                    }
                })
            
            # Add separator
            children.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })
            
            # Add content header
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Newsletter Content"
                            }
                        }
                    ],
                    "color": "blue_background"
                }
            })
            
            # Reserve slots for content (Notion has 100 block limit)
            # Header section took up 7 blocks, leave some room for links section
            max_content_blocks = 80
            
            # Initialize content section blocks
            content_blocks = []
            
            # Determine how to process the content based on whether we have scraped sections
            if email_data.get('sections'):
                # Use the pre-scraped sections (from web scraping)
                content_blocks = self._create_blocks_from_scraped_sections(email_data['sections'])
            else:
                # Process the content from email body (traditional method)
                content_blocks = self._create_blocks_from_email_body(email_data['body'])
            
            # Limit content blocks to max allowed
            if len(content_blocks) > max_content_blocks:
                logger.warning(f"Content has {len(content_blocks)} blocks, limiting to {max_content_blocks}")
                content_blocks = content_blocks[:max_content_blocks]
                # Add a note about truncation
                content_blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "Note: Content was truncated due to Notion's block limit."
                                },
                                "annotations": {
                                    "italic": True,
                                    "color": "orange"
                                }
                            }
                        ]
                    }
                })
            
            # Add all content blocks
            children.extend(content_blocks)
            
            # If we have links and space for them, add them in a better formatted section
            if email_data['links'] and (len(children) < 95):  # Leave some margin
                # Add a divider before links section
                children.extend([
                    {
                        "object": "block",
                        "type": "divider",
                        "divider": {}
                    },
                    {
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": "Links"
                                    }
                                }
                            ]
                        }
                    }
                ])
                
                # Add links as bullet points (up to the limit)
                links_to_add = min(len(email_data['links']), 95 - len(children))
                for i in range(links_to_add):
                    link = email_data['links'][i]
                    # Skip empty links
                    if not link or link == "#" or link.startswith("javascript:"):
                        continue
                        
                    # Create a bullet with the link
                    children.append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": link,
                                        "link": {"url": link}
                                    }
                                }
                            ]
                        }
                    })
                    
                    # Break if we're getting too close to the limit
                    if len(children) >= 98:
                        break
            
            # Final check to ensure we don't exceed the block limit
            if len(children) > 100:
                logger.warning(f"Total blocks: {len(children)}, truncating to 100")
                children = children[:99]
                children.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "Content truncated due to Notion's block limit."
                                },
                                "annotations": {
                                    "italic": True,
                                    "color": "red"
                                }
                            }
                        ]
                    }
                })
            
            # Create the page
            try:
                response = self.client.pages.create(
                    parent={"database_id": self.database_id},
                    properties=properties,
                    children=children
                )
                logger.info(f"Created Notion entry: {email_data['subject']}")
                return response
            except APIResponseError as e:
                logger.error(f"Notion API Error: {str(e)}")
                # Fall back to creating a basic entry
                return self._create_basic_entry(email_data, category)
                
        except Exception as e:
            logger.error(f"Error creating Notion entry: {str(e)}")
            return None
    
    def _create_blocks_from_scraped_sections(self, sections: List[Dict]) -> List[Dict]:
        """Create Notion blocks from scraped sections with length limits handling."""
        blocks = []
        
        for section in sections:
            # Add section heading if it has a name
            if section.get("name") and section["name"] != "Newsletter Content":
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": section["name"]
                                }
                            }
                        ]
                    }
                })
            
            # Add content paragraphs with length limits
            for content_item in section.get("content", []):
                # Skip empty content
                if not content_item.strip():
                    continue
                
                # Check if content is a bullet point
                if content_item.startswith('•') or content_item.startswith('*') or content_item.startswith('-'):
                    # Split long bullet points
                    for chunk in self._split_text_into_chunks(content_item[1:].strip(), 1900):
                        blocks.append({
                            "object": "block",
                            "type": "bulleted_list_item",
                            "bulleted_list_item": {
                                "rich_text": [
                                    {
                                        "type": "text",
                                        "text": {
                                            "content": chunk
                                        }
                                    }
                                ]
                            }
                        })
                else:
                    # Split long paragraphs into multiple paragraph blocks
                    for chunk in self._split_text_into_chunks(content_item, 1900):
                        blocks.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [
                                    {
                                        "type": "text",
                                        "text": {
                                            "content": chunk
                                        }
                                    }
                                ]
                            }
                        })
        
        return blocks
    
    def _create_blocks_from_email_body(self, body: str) -> List[Dict]:
        """Create Notion blocks from email body with length limits handling."""
        blocks = []
        
        # Split the body by double newlines to separate paragraphs
        paragraphs = re.split(r'\n\s*\n', body)
        
        for paragraph in paragraphs:
            # Skip empty paragraphs
            if not paragraph.strip():
                continue
            
            # Check if paragraph is a heading (starting with # or ##)
            if re.match(r'^#+\s+', paragraph):
                heading_level = len(re.match(r'^(#+)\s+', paragraph).group(1))
                heading_text = re.sub(r'^#+\s+', '', paragraph)
                
                if heading_level <= 3:  # h1, h2, h3
                    heading_type = f"heading_{heading_level}"
                    blocks.append({
                        "object": "block",
                        "type": heading_type,
                        heading_type: {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": heading_text[:1900]
                                    }
                                }
                            ]
                        }
                    })
                else:  # treat as paragraph for h4+
                    for chunk in self._split_text_into_chunks(heading_text, 1900):
                        blocks.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [
                                    {
                                        "type": "text",
                                        "text": {
                                            "content": chunk
                                        },
                                        "annotations": {
                                            "bold": True
                                        }
                                    }
                                ]
                            }
                        })
            # Check if paragraph is a bullet list
            elif paragraph.strip().startswith(('•', '*', '-')):
                # Split into bullet items
                bullet_items = re.split(r'\n\s*[•*-]\s*', paragraph)
                # Remove first empty item if it exists
                if bullet_items and not bullet_items[0].strip():
                    bullet_items = bullet_items[1:]
                    
                for item in bullet_items:
                    if not item.strip():
                        continue
                        
                    # Split long bullet points
                    for chunk in self._split_text_into_chunks(item, 1900):
                        blocks.append({
                            "object": "block",
                            "type": "bulleted_list_item",
                            "bulleted_list_item": {
                                "rich_text": [
                                    {
                                        "type": "text",
                                        "text": {
                                            "content": chunk
                                        }
                                    }
                                ]
                            }
                        })
            else:
                # Regular paragraph, split into chunks if needed
                for chunk in self._split_text_into_chunks(paragraph, 1900):
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": chunk
                                    }
                                }
                            ]
                        }
                    })
        
        return blocks
    
    def _split_text_into_chunks(self, text: str, max_length: int = 1900) -> List[str]:
        """Split text into chunks that are under the max_length limit."""
        if not text:
            return []
            
        if len(text) <= max_length:
            return [text]
            
        chunks = []
        current_text = text
        
        while len(current_text) > max_length:
            # Find a good breaking point
            split_point = current_text[:max_length].rfind('. ')
            if split_point == -1:
                split_point = current_text[:max_length].rfind(' ')
            if split_point == -1:
                split_point = max_length - 1
            
            # Add chunk and continue with remaining text
            chunks.append(current_text[:split_point+1])
            current_text = current_text[split_point+1:]
        
        # Add the final chunk
        if current_text:
            chunks.append(current_text)
            
        return chunks
    
    def _create_basic_entry(self, email_data: Dict, category: str):
        """Create a basic Notion entry with minimal content when primary method fails."""
        try:
            # Just the essential properties
            properties = {
                "Name": {"title": [{"text": {"content": email_data['subject']}}]}
            }
            
            # Add category if available
            if "Category" in self.available_properties:
                properties["Category"] = {"select": {"name": category}}
                
            # Add date if available
            if "Date" in self.available_properties:
                properties["Date"] = {"date": {"start": email_data['date']}}
            
            # Create a simple paragraph with the content
            children = [{
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Content from: " + email_data['sender']
                            }
                        }
                    ]
                }
            }]
            
            # Add simple content blocks in chunks to avoid length issues
            content_chunks = self._split_text_into_chunks(email_data['body'], 1900)
            for chunk in content_chunks[:95]:  # Limit to avoid block limits
                children.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": chunk
                                }
                            }
                        ]
                    }
                })
            
            # Add note if content was truncated
            if len(content_chunks) > 95:
                children.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "Content truncated (too long for Notion)."
                                }
                            }
                        ]
                    }
                })
            
            response = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties,
                children=children
            )
            
            logger.info(f"Created basic Notion entry after error: {email_data['subject']}")
            return response
            
        except Exception as e:
            logger.error(f"Even basic entry creation failed: {str(e)}")
            return None 