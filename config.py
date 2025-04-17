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
    "Source": "url",                      # Link to original email
    "Web Source": "url",                  # Link to web version
    "Category": "select",                 # Category of content
    "Date": "date",                       # Date received
    "Description": "rich_text"            # Email body preview
}

# Configuration settings
SETTINGS = {
    "check_interval_minutes": 30,         # How often to check for new emails
    "max_emails_per_run": 10,             # Maximum emails to process per run
    "history_days": 7,                    # How many days back to check for emails
    "batch_save_count": 5,                # Save processed IDs after this many emails
    "categorization_threshold": 0.1,      # Minimum confidence to assign a category
    "use_web_scraping": True,             # Whether to try web scraping first
    "scraping_timeout": 10                # Timeout for web scraping requests in seconds
} 