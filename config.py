# Email configuration
MONITORED_SENDERS = [
    # Add email addresses to monitor
    # Example: "newsletter@example.com"
    "dan@tldrnewsletter.com"
]

# Categories for content classification
CATEGORIES = {
    "IA > negocio": ["caso de uso", "decisión estratégica", "métrica", "impacto", "adopción", "empresa", "negocio", "ROI", "implementación", "transformación digital"],
    "IA > políticas": ["normativa", "regulación", "ética", "debate", "marco regulatorio", "implicancia social", "privacidad", "responsabilidad", "gobernanza"],
    "IA > arquitectura + código": ["buena práctica", "herramienta", "framework", "MLOps", "pipeline", "deployment", "automatización", "infraestructura", "código", "arquitectura"],
    "IA > frontera + R&D": ["investigación", "paper", "modelo", "técnica", "tendencia", "laboratorio", "avance", "innovación", "frontera", "estado del arte"],
    "IA > as a service / product": ["API", "plataforma", "herramienta", "producto", "servicio", "SaaS", "PaaS", "empaquetado", "solución"],
    "Curiosidad de la semana": ["inusual", "hack", "experimento", "lúdico", "creativo", "interesante", "curioso", "divertido", "innovador", "sorprendente"]
}

# Gmail API configuration
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Notion database configuration
NOTION_DATABASE_PROPERTIES = {
    "Name": "title",                     # Newsletter title
    "Source": "url",                     # Link to original email
    "Web Source": "url",                 # Link to web version
    "Category": "select",                # Category of content
    "Date": "date",                      # Date received
    "Description": "rich_text",          # Summary or preview of content
    "Confidence": "number",              # Confidence score of categorization
    "Other Categories": "rich_text",     # Other potential categories
    "Sender": "rich_text",               # Email sender
    "Content Link": "url",               # Primary content link if available
    "Source Type": "select",             # Email or Web Scraped
    "Categorization Method": "select"    # LLM or Keywords
}

# Configuration settings
SETTINGS = {
    # Email processing settings
    "check_interval_minutes": 30,        # How often to check for new emails
    "max_emails_per_run": 100,           # Maximum emails to process per run
    "history_days": 7,                   # How many days back to check for emails
    "batch_save_count": 5,               # Save processed IDs after this many emails
    
    # Content categorization settings
    "categorization_threshold": 0.1,     # Minimum confidence to assign a category
    
    # Web scraping settings
    "use_web_scraping": True,            # Whether to try web scraping first
    "scraping_timeout": 10,              # Timeout for web scraping requests in seconds
    
    # LLM settings (can be overridden by environment variables)
    "llm_enabled": False,                # Whether to use LLM for categorization and summaries (overridable by USE_LLM_CATEGORIZATION)
    "llm_model": "gpt-3.5-turbo",        # Default LLM model to use (overridable by OPENAI_MODEL)
    "llm_requests_per_minute": 20,       # Rate limit for LLM API calls (overridable by OPENAI_REQUESTS_PER_MINUTE)
    "llm_summary_max_words": 100,        # Maximum words for generated summaries
    "llm_retry_attempts": 3              # Number of retry attempts for LLM API calls
}

# LLM prompts and configuration
LLM_CONFIG = {
    # System prompts
    "categorization_system_prompt": "You are a helpful assistant that categorizes newsletter content.",
    "summarization_system_prompt": "You are a helpful assistant that summarizes content concisely and accurately.",
    
    # Temperature settings
    "categorization_temperature": 0.2,   # Low temperature for deterministic categorization
    "summarization_temperature": 0.3,    # Slightly higher for more natural summaries
    
    # Token limits
    "categorization_max_tokens": 400,    # Maximum tokens for categorization response
    "summarization_max_tokens": 150,     # Maximum tokens for summary response
    
    # Content truncation
    "categorization_max_content_length": 2000,  # Characters of content to use for categorization
    "summarization_max_content_length": 3000    # Characters of content to use for summarization
} 