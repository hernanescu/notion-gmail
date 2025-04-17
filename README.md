# Gmail to Notion Newsletter Importer

A tool to automatically import newsletter emails into Notion with structured formatting and categorization.

## Features

- Monitors specified email addresses in Gmail
- Automatically categorizes content using either:
  - Keyword-based matching (default)
  - LLM-powered categorization (optional)
- Creates well-formatted Notion pages for each newsletter
- Preserves newsletter structure with proper formatting
- Extracts and organizes links from newsletters
- Extracts article URLs and links them to titles
- Generates concise summaries using LLM (when enabled)
- Avoids duplicate processing with persistent tracking

## Setup

### Prerequisites

- Python 3.6+
- Google account with Gmail
- Notion account and API token
- Google Cloud Project with Gmail API enabled
- OpenAI API key (optional, for LLM features)

### Installation

1. Clone this repository:
   ```
   git clone <repository-url>
   cd notion_gmail
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Set up Google Cloud Project and enable Gmail API:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Gmail API for the project
   - Create OAuth 2.0 credentials and download as `credentials.json`
   - Place the `credentials.json` file in the project root

4. Set up Notion:
   - Create a Notion integration at https://www.notion.so/my-integrations
   - Create a database to store newsletters
   - Share your database with the integration
   - Copy the database ID from the URL

5. Create a `.env` file with your configuration:
   ```
   # Required settings
   NOTION_TOKEN=your_notion_api_token
   NOTION_DATABASE_ID=your_notion_database_id
   
   # Optional LLM settings
   USE_LLM_CATEGORIZATION=false  # Set to true to enable LLM features
   OPENAI_API_KEY=your_openai_api_key  # Required if USE_LLM_CATEGORIZATION=true
   OPENAI_MODEL=gpt-3.5-turbo  # Or another OpenAI model
   OPENAI_REQUESTS_PER_MINUTE=20  # Rate limit for API calls
   ```

6. Configure monitored email addresses and categories in `config.py`

## Usage

Run the script to process new emails:

```
python main.py
```

The script will:
1. Authenticate with Gmail (first run will require browser authorization)
2. Scan for new newsletters from configured senders
3. Process and categorize the content
4. Extract original source URLs when available
5. Generate summaries (if LLM is enabled)
6. Create Notion pages with structured formatting
7. Track processed emails to avoid duplicates

## Configuration

Edit `config.py` to customize:

- `MONITORED_SENDERS`: List of email addresses to track
- `CATEGORIES`: Keyword-based categorization
- `NOTION_DATABASE_PROPERTIES`: Database field mapping
- `SETTINGS`: Runtime settings like check interval and LLM configuration
- `LLM_CONFIG`: Advanced LLM prompt configuration (if using LLM features)

## Advanced Features

### LLM-Based Categorization

When `USE_LLM_CATEGORIZATION` is enabled, the system will:
1. Use an LLM to analyze newsletter content
2. Determine the most appropriate category
3. Provide an explanation for the categorization
4. Generate a concise summary for the Description field

### Article URL Extraction

The system automatically extracts URLs associated with article titles in newsletters, making them directly accessible from the Notion database.

## License

MIT License 