"""
Content processor module for categorizing and processing email content.
"""
import logging
import os
from typing import Dict, Tuple, List, Optional

import config
from src.llm_service import LLMService

logger = logging.getLogger("gmail_notion_manager.processor")

class ContentProcessor:
    """Handles content classification and processing."""
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        Initialize the content processor.
        
        Args:
            llm_service: Optional LLMService instance. If None, will create a new one if USE_LLM_CATEGORIZATION is enabled.
        """
        # Check if LLM categorization is enabled
        self.use_llm = os.getenv("USE_LLM_CATEGORIZATION", "false").lower() == "true"
        
        # Use provided LLM service or create a new one if needed
        if self.use_llm:
            self.llm_service = llm_service if llm_service else LLMService()
            logger.info("Content processor initialized with LLM categorization")
        else:
            self.llm_service = None
            logger.info("Content processor initialized with keyword-based categorization")
    
    def categorize_content(self, subject: str, content: str) -> Tuple[str, float, Dict[str, float]]:
        """
        Categorize content based on LLM or keywords with confidence score.
        
        Args:
            subject: The newsletter subject line
            content: The newsletter content
            
        Returns:
            A tuple of (category, confidence_score, all_scores)
        """
        # Try LLM categorization if enabled
        if self.use_llm and self.llm_service:
            try:
                category, confidence, all_scores, explanation = self.llm_service.categorize_content(subject, content)
                
                # If LLM categorization was successful, return the results
                if category != "Sin categoría" and confidence > 0:
                    logger.info(f"LLM categorization: {category} (confidence: {confidence:.2f})")
                    # Store explanation in the scores dict with special key
                    all_scores["__explanation__"] = explanation
                    return category, confidence, all_scores
                
                # If LLM failed, fall back to keyword-based approach
                logger.info("LLM categorization failed, falling back to keyword-based approach")
            except Exception as e:
                logger.error(f"Error in LLM categorization, falling back to keyword-based: {type(e).__name__} - {str(e)}")
        
        # Keyword-based categorization (original implementation)
        return self._keyword_categorize(subject, content)
    
    def _keyword_categorize(self, subject: str, content: str) -> Tuple[str, float, Dict[str, float]]:
        """
        Categorize content based on keyword matching.
        
        Args:
            subject: The newsletter subject line
            content: The newsletter content
            
        Returns:
            A tuple of (category, confidence_score, all_scores)
        """
        text = (subject + " " + content).lower()
        
        # Track keyword matches for each category
        category_scores = {}
        category_matched_keywords = {}
        
        for category, keywords in config.CATEGORIES.items():
            score = 0
            matched_keywords = []
            
            for keyword in keywords:
                keyword_lower = keyword.lower()
                # Count occurrences of keyword in text
                count = text.count(keyword_lower)
                if count > 0:
                    score += count
                    matched_keywords.append(keyword)
            
            # Normalize score by number of keywords
            if keywords:  # Avoid division by zero
                normalized_score = score / len(keywords)
                category_scores[category] = normalized_score
                category_matched_keywords[category] = matched_keywords
            else:
                category_scores[category] = 0
                category_matched_keywords[category] = []
        
        # Get category with highest score
        if category_scores:
            best_category = max(category_scores.items(), key=lambda x: x[1])
            
            # If confidence is too low, mark as uncategorized
            if best_category[1] < config.SETTINGS["categorization_threshold"]:
                return "Sin categoría", 0.0, category_scores
                
            # For keyword-based approach, provide an explanation of keywords matched
            if category_matched_keywords[best_category[0]]:
                matched_kws = ", ".join(category_matched_keywords[best_category[0]])
                explanation = f"Matched keywords: {matched_kws}"
                category_scores["__explanation__"] = explanation
                logger.info(f"Keyword categorization: {best_category[0]} (confidence: {best_category[1]:.2f})")
                logger.info(f"  {explanation}")
                
            return best_category[0], best_category[1], category_scores
        
        return "Sin categoría", 0.0, {}
    
    def get_matched_keywords(self, text: str, category: str) -> List[str]:
        """
        Get the list of keywords from a category that match in the text.
        
        Args:
            text: The text to search for keywords
            category: The category whose keywords to check
            
        Returns:
            A list of matching keywords
        """
        if category not in config.CATEGORIES:
            return []
            
        text_lower = text.lower()
        matched = []
        
        for keyword in config.CATEGORIES[category]:
            if keyword.lower() in text_lower:
                matched.append(keyword)
                
        return matched 