"""
Web scraper module to extract newsletter content from online versions.
"""
import re
import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Tuple
import json

import config

logger = logging.getLogger("gmail_notion_manager.scraper")

class WebScraper:
    """Handles web scraping of online newsletter versions."""
    
    def __init__(self):
        """Initialize the web scraper."""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9'
        }
    
    def extract_view_online_link(self, html_content: str) -> Optional[str]:
        """Extract the 'View Online' link from newsletter HTML."""
        if not html_content:
            logger.warning("No HTML content provided to extract View Online link")
            return None
            
        # Common patterns for "view online" links
        patterns = [
            r'href="(https?://[^"]*(?:view|browser)[^"]*(?:online|web|browser)[^"]*)"',
            r'href="(https?://[^"]*(?:web|browser)[^"]*(?:version|view)[^"]*)"',
            r'href="(https?://(?:view|online|newsletter)[^"]*\.[a-z]+/[^"]*)"',
            r'href="(https?://[^"]*(?:campaign-archive|mailchi\.mp)[^"]*)"',
            r'href="(https?://tracking\.tldrnewsletter\.com[^"]*)"',
            r'href="(https?://.*tldrnewsletter\.com[^"]*)"',
            r'href="(https?://[^"]*(?:a\.tldr)[^"]*)"'
        ]
        
        logger.debug(f"Searching for View Online link in HTML content of length {len(html_content)}")
        for pattern in patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                # Clean up URL if needed
                url = matches[0]
                url = url.replace('&amp;', '&')
                logger.info(f"Found 'View Online' link: {url}")
                return url
        
        # Log a sample of the HTML content for debugging
        sample_length = min(500, len(html_content))
        logger.debug(f"No 'View Online' link found. HTML sample: {html_content[:sample_length]}...")
        return None
    
    def scrape_newsletter_content(self, url: str) -> Tuple[Optional[List[Dict]], Optional[List[str]], str]:
        """
        Scrape content from a newsletter web version.
        Returns a tuple of (sections, links, url)
        """
        try:
            logger.info(f"Scraping content from: {url}")
            
            # Store the original URL as the default return value
            final_url = url
            
            # Use the configured timeout from settings
            timeout = config.SETTINGS["scraping_timeout"]
            
            response = requests.get(url, headers=self.headers, timeout=timeout)
            response.raise_for_status()
            
            logger.debug(f"Response received: {len(response.text)} bytes, status {response.status_code}")
            
            # Update final URL in case of redirects
            if response.url != url:
                final_url = response.url
                logger.debug(f"URL redirected to: {final_url}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Log the page title for reference
            title = soup.find('title')
            if title:
                logger.info(f"Page title: {title.text.strip()}")
            
            # Handle redirects
            if soup.find('meta', attrs={'http-equiv': 'refresh'}):
                meta_refresh = soup.find('meta', attrs={'http-equiv': 'refresh'})
                content = meta_refresh.get('content', '')
                if 'url=' in content.lower():
                    redirect_url = content.split('url=')[1].strip()
                    logger.info(f"Following redirect to: {redirect_url}")
                    return self.scrape_newsletter_content(redirect_url)
            
            # Extract all links first
            links = []
            for a_tag in soup.find_all('a', href=True):
                link = a_tag.get('href', '')
                if link and link.startswith('http') and link not in links:
                    links.append(link)
            
            logger.debug(f"Found {len(links)} links on the page")
            
            # Log some basic page structure info
            logger.debug(f"Page structure: {len(soup.find_all('div'))} divs, {len(soup.find_all('p'))} paragraphs, " 
                       f"{len(soup.find_all(['h1', 'h2', 'h3', 'h4']))} headings")
            
            # TLDR newsletter specific handling
            logger.info("Attempting TLDR-specific extraction method")
            sections = self._extract_tldr_newsletter(soup)
            if sections:
                logger.info(f"Successfully extracted content using TLDR-specific method: {len(sections)} sections")
                self._log_extracted_content(sections)
                logger.debug(f"Returning final URL: {final_url}")
                return sections, links, final_url
            
            # Generic newsletter handling
            logger.info("Attempting generic newsletter extraction method")
            sections = self._extract_generic_newsletter(soup)
            if sections:
                logger.info(f"Successfully extracted content using generic method: {len(sections)} sections")
                self._log_extracted_content(sections)
                logger.debug(f"Returning final URL: {final_url}")
                return sections, links, final_url
            
            # Fall back to basic content extraction
            logger.warning(f"Using basic content extraction for {url}")
            sections = self._extract_basic_content(soup)
            if sections:
                logger.info(f"Basic extraction yielded {len(sections)} sections")
                self._log_extracted_content(sections)
            else:
                logger.error("Basic extraction failed to find any content")
            
            logger.debug(f"Returning final URL: {final_url}")
            return sections, links, final_url
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}", exc_info=True)
            # Even on error, return the original URL
            logger.debug(f"Returning original URL due to error: {url}")
            return None, None, url
    
    def _log_extracted_content(self, sections: List[Dict]):
        """Log extracted content summary for debugging."""
        try:
            total_paragraphs = 0
            section_names = []
            
            for section in sections:
                section_names.append(section.get("name", "Unnamed section"))
                total_paragraphs += len(section.get("content", []))
                
                # Log first few words of each content section to verify extraction
                for i, content in enumerate(section.get("content", [])[:3]):  # Log up to 3 content items per section
                    # Content might be a dictionary if we've extracted article URLs
                    if isinstance(content, dict):
                        preview = content.get("text", "")[:50] + "..." if len(content.get("text", "")) > 50 else content.get("text", "")
                        logger.debug(f"Section '{section.get('name', 'Unnamed')}' item {i+1}: {preview}")
                    else:
                        preview = content[:50] + "..." if len(content) > 50 else content
                        logger.debug(f"Section '{section.get('name', 'Unnamed')}' item {i+1}: {preview}")
                
            logger.info(f"Extracted content summary: {len(sections)} sections, {total_paragraphs} paragraphs")
            logger.info(f"Section names: {', '.join(section_names)}")
        except Exception as e:
            logger.error(f"Error logging content: {str(e)}")
    
    def _extract_tldr_newsletter(self, soup: BeautifulSoup) -> Optional[List[Dict]]:
        """Extract content specifically from TLDR newsletters."""
        # Check if this is likely a TLDR newsletter
        is_tldr = False
        if soup.find('title') and 'TLDR' in soup.find('title').text:
            is_tldr = True
            logger.info("Detected TLDR newsletter format based on title")
        
        # Also check for TLDR in other key places
        if not is_tldr:
            tldr_elements = soup.find_all(string=lambda text: text and 'TLDR' in text)
            if tldr_elements:
                is_tldr = True
                logger.info(f"Detected TLDR newsletter format based on content (found {len(tldr_elements)} TLDR mentions)")
        
        if is_tldr:
            logger.debug("Starting TLDR-specific content extraction")
            sections = []
            
            # TLDR newsletters have a specific table-based structure
            # First, try to find section header emojis which are typically in spans with font-size: 36px
            section_icons = soup.find_all('span', style=lambda s: s and 'font-size: 36px' in s)
            logger.debug(f"Found {len(section_icons)} section icons/emojis")
            
            section_headers = []
            for icon in section_icons:
                # Find the next h1 after the icon
                next_header = icon.find_next(['h1', 'h2'])
                if next_header:
                    section_headers.append(next_header)
                    logger.debug(f"Found section header with icon: {next_header.text.strip()}")
            
            if section_headers:
                logger.info(f"Found {len(section_headers)} TLDR section headers with icons")
                
                # Process each section and its content
                for i, header in enumerate(section_headers):
                    section_name = header.text.strip()
                    logger.debug(f"Processing section: {section_name}")
                    
                    # Collect all content tables until the next section header
                    next_header = section_headers[i+1] if i+1 < len(section_headers) else None
                    
                    # First, try to get the direct parent table that contains everything
                    parent_table = header
                    while parent_table and parent_table.name != 'table':
                        parent_table = parent_table.parent
                    
                    if not parent_table:
                        logger.debug(f"Could not find parent table for section: {section_name}")
                        continue
                    
                    # Now find the content tables - typically tables with class text-block
                    # TLDR newsletters often have content in <table><tbody><tr><td class="container"><div class="text-block">
                    content_tables = []
                    
                    # First find all potential tables that might contain content
                    if next_header:
                        # Get tables between this header and next header
                        current = header
                        while current and current != next_header:
                            # Look for tables with text-block divs inside
                            if current.name == 'table':
                                for text_block in current.find_all('div', class_='text-block'):
                                    # Only add if contains substantial content (avoid headers/ads)
                                    if len(text_block.text.strip()) > 50:
                                        content_tables.append(text_block)
                            current = current.find_next(['table', 'h1', 'h2'])
                    else:
                        # For the last section, get all remaining relevant tables
                        current = header.find_next('table')
                        while current:
                            for text_block in current.find_all('div', class_='text-block'):
                                if len(text_block.text.strip()) > 50:
                                    content_tables.append(text_block)
                            current = current.find_next('table')
                    
                    logger.debug(f"Found {len(content_tables)} content blocks for section: {section_name}")
                    
                    # Now extract the content from each table
                    section_content = []
                    
                    for content_table in content_tables:
                        # Look for article items which typically have a title in <strong> and a description
                        articles = []
                        
                        # First check for "a" tags with strong elements (typical article format)
                        for link in content_table.find_all('a'):
                            strong = link.find('strong')
                            article_url = link.get('href', '')
                            if strong:
                                article_title = strong.text.strip()
                                
                                # Find the description - typically in a span after the strong
                                description = ""
                                
                                # Look for the span with the font-family containing "Helvetica"
                                # This is a common pattern in TLDR newsletters for descriptions
                                desc_span = content_table.find('span', style=lambda s: s and 'font-family' in s and 'Helvetica' in s)
                                if desc_span:
                                    description = desc_span.text.strip()
                                
                                # If we found both title and description, add as an article
                                if article_title and description:
                                    # Format the title and description more nicely
                                    # Convert "Title (X minute read)" to "Title [X minute read]"
                                    formatted_title = article_title
                                    if '(' in article_title and ')' in article_title and 'read' in article_title:
                                        title_parts = article_title.split('(')
                                        main_title = title_parts[0].strip()
                                        read_time = title_parts[1].strip().rstrip(')')
                                        formatted_title = f"{main_title} [{read_time}]"
                                    
                                    # Clean up whitespace in the description
                                    formatted_desc = re.sub(r'\s+', ' ', description).strip()
                                    
                                    # Format as a proper article with title and description
                                    article_text = f"**{formatted_title}**\n\n{formatted_desc}"
                                    
                                    # Instead of just adding the text, create a dict with text and url
                                    if article_url and article_url.startswith('http'):
                                        articles.append({
                                            "text": article_text,
                                            "url": article_url,
                                            "title": formatted_title
                                        })
                                        logger.debug(f"Found article with URL: {formatted_title[:50]}... -> {article_url}")
                                    else:
                                        articles.append({
                                            "text": article_text,
                                            "url": None,
                                            "title": formatted_title
                                        })
                                        logger.debug(f"Found article without URL: {formatted_title[:50]}...")
                        
                        # If we didn't find articles with the above method, try another approach
                        if not articles:
                            # Try to extract standalone paragraphs and spans with substantial text
                            for elem in content_table.find_all(['p', 'span']):
                                text = elem.text.strip()
                                if text and len(text) > 50:  # Only include substantial text
                                    # Check if element is inside or near a link
                                    parent_a = elem.find_parent('a')
                                    if parent_a and parent_a.get('href', '').startswith('http'):
                                        section_content.append({
                                            "text": text,
                                            "url": parent_a.get('href', ''),
                                            "title": text[:50] + "..." if len(text) > 50 else text
                                        })
                                        logger.debug(f"Added content with URL: {text[:50]}...")
                                    else:
                                        section_content.append({
                                            "text": text,
                                            "url": None,
                                            "title": None
                                        })
                                        logger.debug(f"Added content without URL: {text[:50]}...")
                        else:
                            # Add all the articles we found
                            section_content.extend(articles)
                    
                    # Add section if it has content
                    if section_content:
                        sections.append({
                            "name": section_name,
                            "content": section_content
                        })
                        logger.info(f"Added section '{section_name}' with {len(section_content)} content items")
                
                # If we have sections, return them
                if sections:
                    return sections
            
            # If we couldn't extract by the section headers method, try direct table cell extraction
            # This is for cases where the icons/headers aren't properly detected
            if not sections:
                logger.info("Trying direct table cell extraction for TLDR newsletter")
                
                # Find all tables with a container class
                all_tables = soup.find_all('table')
                logger.debug(f"Found {len(all_tables)} tables in total")
                
                # TLDR newsletters typically have their articles in tables with cells that have the "container" class
                article_cells = soup.find_all('td', class_='container')
                logger.debug(f"Found {len(article_cells)} container cells that might contain articles")
                
                # Group content by common patterns
                categorized_content = {}
                
                for cell in article_cells:
                    # Skip cells that are too small to be actual content
                    if len(cell.text.strip()) < 100:
                        continue
                    
                    # Check if this cell has a "text-block" div which typically contains article content
                    text_block = cell.find('div', class_='text-block')
                    if not text_block:
                        continue
                    
                    # Try to find a heading or section name above this cell
                    section_name = "Newsletter Content"
                    
                    # Look backwards for the nearest heading
                    prev_elem = cell.find_previous(['h1', 'h2', 'h3'])
                    if prev_elem:
                        section_name = prev_elem.text.strip()
                    
                    # Check for specific section identifiers
                    if re.search(r'Vulnerab|Attack', text_block.text, re.IGNORECASE):
                        section_name = "Attacks & Vulnerabilities"
                    elif re.search(r'Strateg|Tactic', text_block.text, re.IGNORECASE):
                        section_name = "Strategies & Tactics"
                    elif re.search(r'Launch|Tool', text_block.text, re.IGNORECASE):
                        section_name = "Launches & Tools"
                    elif re.search(r'Quick|Link', text_block.text, re.IGNORECASE):
                        section_name = "Quick Links"
                    elif re.search(r'Misc', text_block.text, re.IGNORECASE):
                        section_name = "Miscellaneous"
                    
                    # Now extract the article content from the text block
                    content_items = []
                    
                    # First look for specific article patterns: links with strong titles and description spans
                    articles_found = False
                    
                    # Pattern: <a href="..."><strong>Title (X min read)</strong></a><br><span>Description</span>
                    for link in text_block.find_all('a'):
                        strong = link.find('strong')
                        if strong and '(' in strong.text and ')' in strong.text:  # Pattern like "Title (X min read)"
                            article_title = strong.text.strip()
                            
                            # Find description - look for the span with Helvetica font
                            span_elem = text_block.find('span', style=lambda s: s and 'font-family' in s and 'Helvetica' in s)
                            if span_elem:
                                description = span_elem.text.strip()
                                if description and len(description) > 30:
                                    # Format the title and description nicely
                                    formatted_title = article_title
                                    if '(' in article_title and ')' in article_title and 'read' in article_title:
                                        title_parts = article_title.split('(')
                                        main_title = title_parts[0].strip()
                                        read_time = title_parts[1].strip().rstrip(')')
                                        formatted_title = f"{main_title} [{read_time}]"
                                    
                                    # Clean up whitespace in the description
                                    formatted_desc = re.sub(r'\s+', ' ', description).strip()
                                    
                                    # Format as a proper article
                                    article_text = f"**{formatted_title}**\n\n{formatted_desc}"
                                    content_items.append(article_text)
                                    articles_found = True
                                    logger.debug(f"Extracted article: {formatted_title[:50]}...")
                    
                    # If we didn't find articles, try to extract paragraphs directly
                    if not articles_found:
                        for p in text_block.find_all(['p', 'span']):
                            if p.parent.name != 'a':  # Skip spans inside links
                                text = p.text.strip()
                                if text and len(text) > 50:
                                    content_items.append(text)
                                    logger.debug(f"Extracted paragraph: {text[:50]}...")
                    
                    # Add content to the appropriate section
                    if content_items:
                        if section_name not in categorized_content:
                            categorized_content[section_name] = []
                        categorized_content[section_name].extend(content_items)
                
                # Convert categorized content to sections
                for name, content in categorized_content.items():
                    if content:
                        sections.append({
                            "name": name, 
                            "content": content
                        })
                        logger.info(f"Created section '{name}' with {len(content)} items via cell extraction")
                
                if sections:
                    return sections
            
            # If all else fails, try to extract structured content directly from text blocks
            if not sections:
                logger.info("Trying text block direct extraction")
                
                # Find all text-block divs
                text_blocks = soup.find_all('div', class_='text-block')
                logger.debug(f"Found {len(text_blocks)} text blocks")
                
                # Analyze each text block to see if it contains an article
                articles = []
                
                for block in text_blocks:
                    # Skip blocks that are too small to be actual content
                    if len(block.text.strip()) < 100:
                        continue
                    
                    # Articles typically have:
                    # 1. A link with a strong tag containing the title
                    # 2. A span with the description
                    
                    strong_links = block.select('a strong')
                    for strong in strong_links:
                        title = strong.text.strip()
                        # Look for nearby text that could be the description
                        parent = strong.parent.parent  # Get the parent of the 'a' tag
                        # Clone the block to avoid modifying original
                        clone = BeautifulSoup(str(parent), 'html.parser')
                        # Remove the strong/link elements
                        for s in clone.find_all('strong'):
                            s.extract()
                        for a in clone.find_all('a'):
                            a.extract()
                        # Get remaining text as description
                        desc = clone.text.strip()
                        
                        if title and desc and len(desc) > 30:
                            # Format the title and description nicely
                            formatted_title = title
                            if '(' in title and ')' in title and 'read' in title:
                                title_parts = title.split('(')
                                main_title = title_parts[0].strip()
                                read_time = title_parts[1].strip().rstrip(')')
                                formatted_title = f"{main_title} [{read_time}]"
                            
                            # Clean up whitespace in the description
                            formatted_desc = re.sub(r'\s+', ' ', desc).strip()
                            
                            # Format as a proper article
                            article_text = f"**{formatted_title}**\n\n{formatted_desc}"
                            articles.append(article_text)
                            logger.debug(f"Extracted article from text block: {formatted_title[:50]}...")
                
                if articles:
                    sections.append({
                        "name": "Newsletter Content",
                        "content": articles
                    })
                    logger.info(f"Created general section with {len(articles)} articles from text blocks")
                    return sections
        
        return None
    
    def _extract_generic_newsletter(self, soup: BeautifulSoup) -> Optional[List[Dict]]:
        """Extract content from a generic newsletter format."""
        logger.debug("Starting generic newsletter extraction")
        sections = []
        
        # Try to find the main content container
        content_selectors = [
            'main', 'article', 
            'div.container', 'div.content', 'div.main', 
            'div#content', 'div#main', 'div#newsletter',
            'div.newsletter', 'div.email', 'div.body'
        ]
        
        main_content = None
        for selector in content_selectors:
            logger.debug(f"Trying selector: {selector}")
            tag, *classes = selector.split('.')
            if '#' in tag:
                tag, id_val = tag.split('#')
                main_content = soup.find(tag, id=id_val)
            elif classes:
                main_content = soup.find(tag, class_=classes[0])
            else:
                main_content = soup.find(tag)
                
            if main_content:
                logger.info(f"Found main content using selector: {selector}")
                break
        
        # If still not found, try a heuristic approach
        if not main_content:
            logger.info("Using heuristic approach to find main content")
            # Find the div with the most text content that's not too shallow
            candidates = soup.find_all(['div', 'section'], recursive=True)
            logger.debug(f"Found {len(candidates)} potential content containers")
            
            if candidates:
                # Filter candidates to those with enough content but not the whole page
                min_length = 200
                max_length = len(soup.text) * 0.9
                
                content_candidates = [c for c in candidates if 
                                     len(c.text) > min_length and 
                                     len(c.text) < max_length and
                                     len(list(c.find_all(['h1', 'h2', 'h3', 'p'], recursive=True))) > 3]
                
                logger.debug(f"Filtered to {len(content_candidates)} candidates with appropriate content volume")
                
                if content_candidates:
                    main_content = max(content_candidates, key=lambda x: len(x.text))
                    logger.info(f"Selected main content container with {len(main_content.text)} characters")
        
        if main_content:
            logger.debug(f"Main content type: {main_content.name}, class: {main_content.get('class')}, id: {main_content.get('id')}")
            
            # Log headings found
            all_headings = main_content.find_all(['h1', 'h2', 'h3', 'h4'])
            logger.debug(f"Found {len(all_headings)} headings in main content")
            for h in all_headings[:5]:  # Log first 5 headings
                logger.debug(f"Heading ({h.name}): {h.text.strip()}")
            
            # First try to extract structured content using headers
            headings = main_content.find_all(['h1', 'h2', 'h3', 'h4'])
            
            if headings:
                logger.info(f"Extracting content using {len(headings)} headings")
                current_section = {"name": "Introduction", "content": []}
                current_heading = None
                
                # Gather text before the first heading
                intro_elements = []
                for element in main_content.children:
                    if element.name in ['h1', 'h2', 'h3', 'h4']:
                        break
                    if element.name == 'p':
                        text = element.text.strip()
                        if text:
                            intro_elements.append(text)
                            logger.debug(f"Intro paragraph: {text[:50]}...")
                
                if intro_elements:
                    current_section["content"] = intro_elements
                    sections.append(current_section)
                    logger.debug(f"Added introduction section with {len(intro_elements)} paragraphs")
                
                # Process each heading and its content
                for heading in headings:
                    # Start a new section
                    current_section = {
                        "name": heading.text.strip(),
                        "content": []
                    }
                    logger.debug(f"Processing section: {current_section['name']}")
                    
                    # Get content until next heading
                    current_element = heading.next_sibling
                    while current_element and not (hasattr(current_element, 'name') and 
                                                 current_element.name in ['h1', 'h2', 'h3', 'h4']):
                        if hasattr(current_element, 'name'):
                            if current_element.name == 'p':
                                text = current_element.text.strip()
                                if text:
                                    current_section["content"].append(text)
                                    logger.debug(f"Added paragraph: {text[:50]}...")
                            elif current_element.name == 'ul':
                                for li in current_element.find_all('li'):
                                    text = li.text.strip()
                                    if text:
                                        current_section["content"].append(f"• {text}")
                                        logger.debug(f"Added list item: {text[:50]}...")
                        
                        current_element = current_element.next_sibling
                    
                    # Only add sections with content
                    if current_section["content"]:
                        sections.append(current_section)
                        logger.debug(f"Added section '{current_section['name']}' with {len(current_section['content'])} items")
            
            # If no structured content found, fall back to flat extraction
            if not sections:
                logger.info("No structured content found, using flat extraction")
                all_paragraphs = []
                for p in main_content.find_all(['p', 'div'], recursive=True):
                    if p.name == 'div' and p.find(['p', 'div']):
                        continue  # Skip divs with nested paragraphs
                    
                    text = p.text.strip()
                    if text and len(text) > 20:  # Only include substantial paragraphs
                        all_paragraphs.append(text)
                        logger.debug(f"Added text: {text[:50]}...")
                
                # If we have content, create a single section
                if all_paragraphs:
                    sections.append({
                        "name": "Newsletter Content",
                        "content": all_paragraphs
                    })
                    logger.info(f"Created single section with {len(all_paragraphs)} paragraphs")
        else:
            logger.warning("Failed to find main content container")
        
        return sections if sections else None
    
    def _extract_basic_content(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract basic content when other methods fail."""
        logger.debug("Starting basic content extraction")
        
        # Extract title
        title = ""
        if soup.find('title'):
            title = soup.find('title').text.strip()
            logger.debug(f"Page title: {title}")
        
        # Extract all paragraphs
        paragraphs = []
        for p in soup.find_all(['p', 'div.paragraph']):
            text = p.text.strip()
            if text and len(text) > 20:  # Only include substantial paragraphs
                paragraphs.append(text)
                logger.debug(f"Found paragraph: {text[:50]}...")
        
        logger.info(f"Found {len(paragraphs)} paragraphs in basic extraction")
        
        # If no paragraphs found, try getting text from divs
        if not paragraphs:
            logger.info("No paragraphs found, trying divs")
            for div in soup.find_all('div'):
                # Skip divs that contain other divs to avoid duplication
                if div.find('div'):
                    continue
                    
                text = div.text.strip()
                if text and len(text) > 20:
                    paragraphs.append(text)
                    logger.debug(f"Found div text: {text[:50]}...")
        
        # Try table cells as a last resort
        if not paragraphs:
            logger.info("No paragraphs or divs found, trying table cells")
            for td in soup.find_all('td'):
                # Skip cells with nested structure
                if td.find(['div', 'p', 'td']):
                    continue
                    
                text = td.text.strip()
                if text and len(text) > 20:
                    paragraphs.append(text)
                    logger.debug(f"Found table cell text: {text[:50]}...")
        
        # Create a basic section structure
        sections = [{
            "name": title or "Newsletter Content",
            "content": paragraphs
        }]
        
        logger.info(f"Created basic section with {len(paragraphs)} paragraphs")
        
        return sections 