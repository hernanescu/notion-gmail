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
    
    def create_entry(self, email_data: Dict, category: str, confidence: float, all_scores: Dict[str, float]):
        """Create a new entry in Notion database."""
        try:
            # Prepare source links
            source_link = f"https://mail.google.com/mail/u/0/#inbox/{email_data['message_id']}"
            
            # Format other category scores for reference
            other_categories = ", ".join([f"{cat}: {score:.2f}" for cat, score in all_scores.items() if cat != category and score > 0])
            
            # Extract first link from email if available
            content_link = email_data['links'][0] if email_data['links'] else ""
            
            # Prepare properties based on configuration
            properties = {}
            
            # Set "Name" property using title type (according to config.py)
            properties["Name"] = {"title": [{"text": {"content": email_data['subject']}}]}
            
            # Add other properties from config
            if "Category" in config.NOTION_DATABASE_PROPERTIES:
                properties["Category"] = {"select": {"name": category}}
            
            if "Source" in config.NOTION_DATABASE_PROPERTIES:
                properties["Source"] = {"url": source_link}
                
            if "Date" in config.NOTION_DATABASE_PROPERTIES:
                properties["Date"] = {"date": {"start": email_data['date']}}
                
            # We'll move the full content to the page body, but still keep a short preview in the Description field
            if "Description" in config.NOTION_DATABASE_PROPERTIES:
                # Create a short preview (100 characters) for the description property
                preview = email_data['body'][:100] + "..." if len(email_data['body']) > 100 else email_data['body']
                properties["Description"] = {"rich_text": [{"text": {"content": preview}}]}
                
            # Add optional properties if configured
            if "Content Link" in config.NOTION_DATABASE_PROPERTIES:
                properties["Content Link"] = {"url": content_link} if content_link else {"url": None}
                
            if "Confidence" in config.NOTION_DATABASE_PROPERTIES:
                properties["Confidence"] = {"number": confidence}
                
            if "Other Categories" in config.NOTION_DATABASE_PROPERTIES:
                properties["Other Categories"] = {"rich_text": [{"text": {"content": other_categories}}]}
                
            if "Sender" in config.NOTION_DATABASE_PROPERTIES:
                properties["Sender"] = {"rich_text": [{"text": {"content": email_data['sender']}}]}
            
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
                    "type": "divider",
                    "divider": {}
                },
                {
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
                }
            ])
            
            # Initialize content section blocks (we'll need to limit these)
            content_blocks = []
            
            # Split the text by line breaks
            lines = email_data['body'].split('\n')
            
            # Process content line by line for better structure
            current_section = None
            is_in_list = False
            section_content = []
            current_section_name = "Main Content"
            sections = []
            
            # First pass: organize lines into sections for better consolidation
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if this is a section header
                is_section_header = (
                    line.isupper() and len(line) > 3 and len(line) < 60 or
                    re.match(r'^[=#\*]+\s+.+\s+[=#\*]+$', line) or
                    re.match(r'^\s*\d+\.\s+[A-Z]', line) or
                    re.match(r'^T\s*L\s*D\s*R', line, re.IGNORECASE) or
                    re.match(r'^📱|^📈|^🔍|^🚀|^💡|^📊', line) or  # Common emoji section markers
                    any(section.lower() in line.lower() for section in [
                        "WHAT'S NEW", "IN THE NEWS", "RELEASES", "TOOLS", "RESOURCES",
                        "ATTACKS", "VULNERABILITIES", "STRATEGIES", "TACTICS",
                        "LAUNCHES", "EVENTS", "FUNDING", "News & Trends", "TLDR"
                    ])
                )
                
                if is_section_header:
                    # Save the previous section if it exists
                    if section_content:
                        sections.append({"name": current_section_name, "content": section_content})
                    
                    # Start a new section
                    current_section_name = line
                    section_content = []
                else:
                    section_content.append(line)
            
            # Add the last section if it exists
            if section_content:
                sections.append({"name": current_section_name, "content": section_content})
            
            # Second pass: create blocks from sections, but limit the total
            max_sections = min(len(sections), 10)  # Limit to 10 sections max
            links_block_count = min(len(email_data['links']), 10) + 1  # Links + header
            
            # Reserve blocks for headers, metadata, and links
            reserved_blocks = 6 + links_block_count  # 6 header blocks + links
            max_content_blocks = 100 - reserved_blocks
            
            # Calculate blocks per section
            blocks_per_section = max_content_blocks // max_sections if max_sections > 0 else 0
            
            # Process each section with block limits
            processed_sections = 0
            for section in sections[:max_sections]:
                processed_sections += 1
                
                # Add section header
                content_blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": section["name"]
                                },
                                "annotations": {
                                    "bold": True,
                                    "color": "blue"
                                }
                            }
                        ]
                    }
                })
                
                # Determine how to handle section content based on length
                section_lines = section["content"]
                blocks_left = blocks_per_section - 1  # -1 for the header
                
                if len(section_lines) <= blocks_left:
                    # We can include all lines individually
                    for line in section_lines:
                        # Try to format as list item if applicable
                        if line.startswith('•') or line.startswith('-') or line.startswith('*') or re.match(r'^\s*\d+\.\s+', line):
                            content = re.sub(r'^\s*[•\-\*\d\.]+\s*', '', line)
                            content_blocks.append({
                                "object": "block",
                                "type": "bulleted_list_item",
                                "bulleted_list_item": {
                                    "rich_text": [
                                        {
                                            "type": "text",
                                            "text": {
                                                "content": content
                                            }
                                        }
                                    ]
                                }
                            })
                        else:
                            content_blocks.append({
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [
                                        {
                                            "type": "text",
                                            "text": {
                                                "content": line
                                            }
                                        }
                                    ]
                                }
                            })
                else:
                    # Consolidate content to fit in available blocks
                    consolidated_text = "\n\n".join(section_lines)
                    
                    # Split into roughly equal chunks to fit in available blocks
                    max_chunk_size = 1990  # Keep under Notion's text content limit
                    avg_chunk_size = min(max_chunk_size, len(consolidated_text) // blocks_left + 1)
                    
                    # Split text into paragraphs of appropriate size
                    current_chunk = ""
                    for line in section_lines:
                        if len(current_chunk) + len(line) + 2 > avg_chunk_size:
                            # Add current chunk as a block
                            content_blocks.append({
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [
                                        {
                                            "type": "text",
                                            "text": {
                                                "content": current_chunk.strip()
                                            }
                                        }
                                    ]
                                }
                            })
                            current_chunk = line
                            blocks_left -= 1
                            # If we're out of blocks, break
                            if blocks_left <= 0:
                                break
                        else:
                            if current_chunk:
                                current_chunk += "\n\n" + line
                            else:
                                current_chunk = line
                    
                    # Add the last chunk if there's anything left and we have space
                    if current_chunk and blocks_left > 0:
                        content_blocks.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [
                                    {
                                        "type": "text",
                                        "text": {
                                            "content": current_chunk.strip()
                                        }
                                    }
                                ]
                            }
                        })
            
            # Add all content blocks
            children.extend(content_blocks)
            
            # If we have links, add them in a better formatted section
            if email_data['links']:
                # Add a divider before links section
                children.extend([
                    {
                        "object": "block",
                        "type": "divider",
                        "divider": {}
                    },
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": "Links from Newsletter"
                                    }
                                }
                            ],
                            "color": "blue_background"
                        }
                    }
                ])
                
                # Add each link as a separate item with better formatting (limit to 10 links)
                for i, link in enumerate(email_data['links'][:10], 1):
                    # Try to create a cleaner display text
                    display_text = link
                    if '?' in link:
                        display_text = link.split('?')[0]
                    
                    # Truncate very long URLs for display
                    if len(display_text) > 80:
                        display_text = display_text[:77] + "..."
                        
                    children.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": f"[{i}] "
                                    },
                                    "annotations": {
                                        "bold": True
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": {
                                        "content": display_text,
                                        "link": {"url": link}
                                    },
                                    "annotations": {
                                        "color": "blue"
                                    }
                                }
                            ]
                        }
                    })
            
            # Ensure we don't exceed 100 blocks (Notion API limit)
            if len(children) > 100:
                logger.warning(f"Trimming content blocks from {len(children)} to 100 (Notion API limit)")
                # Keep header (6 blocks) + some content + links section (up to 12 blocks)
                content_end = 100 - 12 if len(email_data['links']) > 0 else 100
                children = children[:6] + children[6:content_end] + (children[-12:] if len(email_data['links']) > 0 else [])
            
            new_page = {
                "parent": {"database_id": self.database_id},
                "properties": properties,
                "children": children
            }
            
            response = self.client.pages.create(**new_page)
            logger.info(f"Created Notion entry: {email_data['subject']} - {category} (confidence: {confidence:.2f})")
            return response
            
        except APIResponseError as e:
            logger.error(f"Notion API Error: {str(e)}")
            # Check if it's a property that doesn't exist
            if "does not exist" in str(e):
                return self._create_basic_entry(email_data, category)
            return None
        except Exception as e:
            logger.error(f"Error creating Notion entry: {str(e)}")
            return None
    
    def _create_basic_entry(self, email_data: Dict, category: str):
        """Create a basic entry with minimal properties when the main create fails."""
        try:
            # Prepare basic properties
            basic_properties = {}
            
            # Use "Name" for the title field as configured in config.py
            basic_properties["Name"] = {"title": [{"text": {"content": email_data['subject']}}]}
            
            # Add only the essential properties that should exist
            if "Category" in config.NOTION_DATABASE_PROPERTIES:
                basic_properties["Category"] = {"select": {"name": category}}
            
            if "Source" in config.NOTION_DATABASE_PROPERTIES:
                basic_properties["Source"] = {"url": f"https://mail.google.com/mail/u/0/#inbox/{email_data['message_id']}"}
            
            if "Date" in config.NOTION_DATABASE_PROPERTIES:
                basic_properties["Date"] = {"date": {"start": email_data['date']}}
            
            # Create a short preview for description
            preview = email_data['body'][:100] + "..." if len(email_data['body']) > 100 else email_data['body']
            
            if "Description" in config.NOTION_DATABASE_PROPERTIES:
                basic_properties["Description"] = {"rich_text": [{"text": {"content": preview}}]}
            
            # Create simplified but well-formatted content blocks for the page body
            basic_children = []
            
            # Add simplified header section (3 blocks)
            sender_name = email_data['sender'].split('<')[0].strip()
            
            basic_children.extend([
                {
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
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"From: {sender_name}"
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "divider",
                    "divider": {}
                }
            ])
            
            # Calculate how many content blocks we can add
            reserved_blocks = 3  # Header blocks
            links_blocks = min(5, len(email_data['links'])) + 2  # Links (max 5) + header + divider
            max_content_blocks = 95 - links_blocks  # Reserve 95 blocks total (safety margin)
            
            # Process the body text with basic formatting
            body_text = email_data['body']
            paragraphs = body_text.split('\n\n')
            
            # Consolidate paragraphs to fit within block limit
            if len(paragraphs) > max_content_blocks:
                # Combine into larger chunks to fit in the available blocks
                consolidated_text = "\n\n".join(paragraphs)
                avg_chunk_size = min(1990, len(consolidated_text) // max_content_blocks + 1)
                
                chunks = []
                current_chunk = ""
                
                for paragraph in paragraphs:
                    if len(current_chunk) + len(paragraph) + 4 > avg_chunk_size and current_chunk:
                        chunks.append(current_chunk)
                        current_chunk = paragraph
                    else:
                        if current_chunk:
                            current_chunk += "\n\n" + paragraph
                        else:
                            current_chunk = paragraph
                
                if current_chunk:
                    chunks.append(current_chunk)
                
                # Create blocks from chunks (limited to max_content_blocks)
                for chunk in chunks[:max_content_blocks]:
                    basic_children.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": chunk.strip()
                                    }
                                }
                            ]
                        }
                    })
            else:
                # We can include all paragraphs directly (still limited to max_content_blocks)
                for i, paragraph in enumerate(paragraphs):
                    if i >= max_content_blocks:
                        break
                        
                    if not paragraph.strip():
                        continue
                        
                    basic_children.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": paragraph.strip()
                                    }
                                }
                            ]
                        }
                    })
            
            # Add a simple links section if we have links
            if email_data['links']:
                basic_children.extend([
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
                
                # Add simplified links (first 5 only in fallback mode)
                for i, link in enumerate(email_data['links'][:5], 1):
                    basic_children.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": f"[{i}] ",
                                    },
                                    "annotations": {
                                        "bold": True
                                    }
                                },
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
            
            # Final check to ensure we're under the 100 block limit
            if len(basic_children) > 100:
                logger.warning(f"Trimming fallback content from {len(basic_children)} to 100 blocks")
                basic_children = basic_children[:100]
            
            basic_page = {
                "parent": {"database_id": self.database_id},
                "properties": basic_properties,
                "children": basic_children
            }
            
            response = self.client.pages.create(**basic_page)
            logger.info(f"Created basic Notion entry after error: {email_data['subject']}")
            return response
        except Exception as e:
            logger.error(f"Failed to create basic Notion entry: {str(e)}")
            return None 