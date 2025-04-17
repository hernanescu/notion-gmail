"""
Data storage module for handling persistent data.
"""
import os
import json
import logging
from typing import Set

logger = logging.getLogger("gmail_notion_manager.storage")

class DataStorage:
    """Handles persistent storage operations."""
    
    def __init__(self, filename="processed_ids.json"):
        """Initialize the data storage with the target filename."""
        self.filename = filename
        
    def load_processed_ids(self) -> Set[str]:
        """Load previously processed email IDs from persistent storage."""
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r') as f:
                    return set(json.load(f))
            return set()
        except Exception as e:
            logger.error(f"Error loading processed IDs: {str(e)}")
            return set()
    
    def save_processed_ids(self, processed_ids: Set[str], max_items: int = 1000):
        """Save processed email IDs to persistent storage."""
        try:
            # Keep only the last 1000 processed IDs to avoid file growth
            ids_to_save = list(processed_ids)[-max_items:] if len(processed_ids) > max_items else list(processed_ids)
            with open(self.filename, 'w') as f:
                json.dump(ids_to_save, f)
            logger.debug(f"Saved {len(ids_to_save)} processed IDs to {self.filename}")
        except Exception as e:
            logger.error(f"Error saving processed IDs: {str(e)}")
            
    def append_processed_id(self, processed_ids: Set[str], new_id: str, save: bool = True):
        """Add a new ID to the processed set and optionally save."""
        processed_ids.add(new_id)
        if save:
            self.save_processed_ids(processed_ids) 