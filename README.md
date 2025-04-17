# Gmail to Notion Newsletter Importer

A tool to automatically import newsletter emails into Notion with structured formatting and categorization.

## Features

- Monitors specified email addresses in Gmail
- Automatically categorizes content based on keywords
- Creates well-formatted Notion pages for each newsletter
- Preserves newsletter structure with proper formatting
- Extracts and organizes links from newsletters
- Avoids duplicate processing with persistent tracking

## Setup

### Prerequisites

- Python 3.6+
- Google account with Gmail
- Notion account and API token
- Google Cloud Project with Gmail API enabled

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
   NOTION_TOKEN=your_notion_api_token
   NOTION_DATABASE_ID=your_notion_database_id
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
4. Create Notion pages with structured formatting
5. Track processed emails to avoid duplicates

## Configuration

Edit `config.py` to customize:

- `MONITORED_SENDERS`: List of email addresses to track
- `CATEGORIES`: Keyword-based categorization
- `NOTION_DATABASE_PROPERTIES`: Database field mapping
- `SETTINGS`: Runtime settings like check interval

## License

MIT License 