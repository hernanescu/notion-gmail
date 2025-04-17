"""
LLM Service for categorizing newsletter content.
"""
import os
import logging
from typing import Dict, Tuple, List
import json
import openai

import config

logger = logging.getLogger("gmail_notion_manager.llm")

class LLMService:
    """Service for interacting with LLMs to categorize content."""
    
    def __init__(self):
        """Initialize the LLM service."""
        # Ensure API key is set
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            logger.warning("OPENAI_API_KEY environment variable not set")
        
        self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        logger.info(f"Initialized LLM service using model: {self.model}")
    
    def categorize_content(self, subject: str, content: str) -> Tuple[str, float, Dict[str, float], str]:
        """
        Use LLM to categorize newsletter content based on predefined categories.
        Returns tuple of (category, confidence_score, all_scores, explanation)
        """
        try:
            # Prepare prompt for categorization
            prompt = self._prepare_categorization_prompt(subject, content)
            
            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that categorizes newsletter content."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,  # Low temperature for more deterministic outputs
                max_tokens=400
            )
            
            # Extract category and confidence from response
            response_text = response.choices[0].message.content.strip()
            
            # Log the full response for debugging
            logger.debug(f"LLM raw response: {response_text}")
            
            # Parse the response to extract category, scores, and explanation
            category, confidence, all_scores, explanation = self._parse_categorization_response(response_text)
            
            # Log detailed information about the decision
            self._log_categorization_decision(category, confidence, all_scores, explanation)
            
            return category, confidence, all_scores, explanation
            
        except Exception as e:
            logger.error(f"Error in LLM categorization: {str(e)}")
            return "Sin categoría", 0.0, {}, "Error in LLM processing"
    
    def _prepare_categorization_prompt(self, subject: str, content: str) -> str:
        """
        Prepare prompt for the LLM to categorize content.
        """
        # Create a string with all categories and their keywords
        categories_text = ""
        for category, keywords in config.CATEGORIES.items():
            categories_text += f"\n- {category}: {', '.join(keywords)}"
        
        # Limit content length to avoid token limits
        max_content_length = 2000  # Adjust based on your token limits
        truncated_content = content[:max_content_length]
        if len(content) > max_content_length:
            truncated_content += "... [content truncated]"
        
        # Create the full prompt
        prompt = f"""Categorize the following newsletter content into one of the predefined categories.

CATEGORIES:
{categories_text}

NEWSLETTER:
Title: {subject}

Content:
{truncated_content}

For each category, provide a relevance score between 0 and 1, where 1 means highly relevant.
Then select the most appropriate category and provide your confidence score.
Also provide a brief explanation (1-2 sentences) of why you chose this category.

Output format:
Category scores:
<category1>: <score>
<category2>: <score>
...

Selected category: <most_relevant_category>
Confidence: <confidence_score>
Explanation: <brief explanation of why this category was chosen>
"""
        return prompt
    
    def _parse_categorization_response(self, response_text: str) -> Tuple[str, float, Dict[str, float], str]:
        """
        Parse the LLM response to extract category, scores, and explanation.
        Returns tuple of (category, confidence_score, all_scores, explanation)
        """
        all_scores = {}
        category = "Sin categoría"
        confidence = 0.0
        explanation = ""
        
        try:
            # Extract category scores
            if "Category scores:" in response_text:
                scores_section = response_text.split("Category scores:")[1].split("Selected category:")[0].strip()
                score_lines = scores_section.split("\n")
                
                for line in score_lines:
                    if ":" in line:
                        cat, score_str = line.split(":", 1)
                        cat = cat.strip()
                        try:
                            score = float(score_str.strip())
                            all_scores[cat] = score
                        except ValueError:
                            logger.warning(f"Could not parse score from: {line}")
            
            # Extract selected category
            if "Selected category:" in response_text:
                category_section = response_text.split("Selected category:")[1]
                if "\n" in category_section:
                    category_line = category_section.split("\n")[0].strip()
                else:
                    category_line = category_section.strip()
                category = category_line
            
            # Extract confidence
            if "Confidence:" in response_text:
                confidence_section = response_text.split("Confidence:")[1]
                if "\n" in confidence_section:
                    confidence_line = confidence_section.split("\n")[0].strip()
                else:
                    confidence_line = confidence_section.strip()
                try:
                    confidence = float(confidence_line)
                except ValueError:
                    logger.warning(f"Could not parse confidence from: {confidence_line}")
            
            # Extract explanation
            if "Explanation:" in response_text:
                explanation_section = response_text.split("Explanation:")[1].strip()
                explanation = explanation_section
            
            # If no category was found or confidence is too low, use "Sin categoría"
            if not category or confidence < config.SETTINGS.get("categorization_threshold", 0.5):
                category = "Sin categoría"
                confidence = 0.0
                explanation = "Confidence too low or category not determined"
            
            return category, confidence, all_scores, explanation
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            return "Sin categoría", 0.0, {}, f"Error: {str(e)}"
    
    def _log_categorization_decision(self, category: str, confidence: float, all_scores: Dict[str, float], explanation: str) -> None:
        """
        Log detailed information about the categorization decision.
        """
        # Create a sorted list of categories by score
        sorted_scores = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Format the scores for logging
        scores_formatted = "\n".join([f"  - {cat}: {score:.4f}" for cat, score in sorted_scores])
        
        # Log the decision details
        logger.info(f"LLM Categorization Decision:")
        logger.info(f"  Selected: {category} (confidence: {confidence:.4f})")
        logger.info(f"  Explanation: {explanation}")
        logger.info(f"  All category scores:\n{scores_formatted}")
        
        # Log the score difference between top categories if there are at least 2 categories
        if len(sorted_scores) >= 2:
            top_score_diff = sorted_scores[0][1] - sorted_scores[1][1]
            logger.info(f"  Score difference between top 2 categories: {top_score_diff:.4f}")
        
        # Create a structured log record for potential analysis
        decision_log = {
            "timestamp": None,  # Will be added by logging framework
            "selected_category": category,
            "confidence": confidence,
            "explanation": explanation,
            "all_scores": dict(sorted_scores),
            "model": self.model
        }
        
        # Log as JSON for potential parsing by analysis tools
        logger.debug(f"LLM decision details: {json.dumps(decision_log)}") 