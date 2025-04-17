# Deployment Guide for Gmail to Notion Newsletter Manager

This guide provides instructions for deploying the Gmail to Notion Newsletter Manager in different environments.

## Local Deployment

### Prerequisites
- Python 3.7 or higher
- pip (Python package manager)
- Gmail account with access to the newsletters you want to monitor
- Notion account with a database created for the newsletters

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd gmail-notion-newsletter-manager
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Gmail API**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Gmail API
   - Create OAuth 2.0 credentials (Desktop application)
   - Download the credentials and save as `credentials.json` in the project directory

4. **Set up Notion API**
   - Go to [Notion Integrations](https://www.notion.so/my-integrations)
   - Create a new integration
   - Copy the integration token
   - Create a database in Notion with the following properties:
     - Title (title) - Required
     - Category (select) - Required
     - Source (url) - Required
     - Date (date) - Required
     - Description (rich_text) - Required
     - Content Link (url) - Optional
     - Confidence (number) - Optional
     - Other Categories (rich_text) - Optional
     - Sender (rich_text) - Optional
   - Share your database with the integration
   - Copy the database ID from the URL (the part after the workspace name and before the question mark)

5. **Create environment file**
   Copy the `.env.example` file to `.env` and update with your credentials:
   ```bash
   cp .env.example .env
   ```

   Then edit the `.env` file with your credentials:
   ```
   NOTION_TOKEN=your_notion_integration_token
   NOTION_DATABASE_ID=your_database_id
   LOG_LEVEL=INFO
   ```

6. **Configure monitored senders and categories**
   Edit `config.py` to:
   
   - Add the email addresses you want to monitor to the `MONITORED_SENDERS` list:
     ```python
     MONITORED_SENDERS = [
         "newsletter@example.com",
         "updates@company.com"
     ]
     ```
   
   - Customize the categories and keywords (already configured for AI topics in Spanish):
     ```python
     CATEGORIES = {
         "IA > negocio": ["caso de uso", "decisión estratégica", ...],
         # Other categories...
     }
     ```
   
   - Adjust the settings as needed:
     ```python
     SETTINGS = {
         "check_interval_minutes": 5,          # Time between email checks
         "max_emails_per_run": 50,             # Maximum emails to process in one run
         "categorization_threshold": 0.1,      # Minimum confidence to assign a category
         "description_max_length": 2000,       # Maximum description length
         "batch_save_count": 10,               # Save processed IDs after batch
         "history_days": 7                     # Initial history days to check
     }
     ```

7. **Run the application**
   ```bash
   python main.py
   ```

## Cloud Deployment Options

### Option 1: Google Cloud Run (Recommended)

1. **Create a Dockerfile**
   Use the provided Dockerfile or create one with:
   ```dockerfile
   FROM python:3.9-slim

   WORKDIR /app

   # Install dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   # Copy application code
   COPY . .

   # Create a non-root user
   RUN useradd -m appuser
   USER appuser

   # Run the application
   CMD ["python", "main.py"]
   ```

2. **Build and deploy to Cloud Run**
   ```bash
   # Build the container
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/gmail-notion-manager
   
   # Deploy to Cloud Run
   gcloud run deploy gmail-notion-manager \
     --image gcr.io/YOUR_PROJECT_ID/gmail-notion-manager \
     --platform managed \
     --region us-central1 \
     --set-env-vars="NOTION_TOKEN=your_token,NOTION_DATABASE_ID=your_database_id"
   ```

3. **Set up persistent storage**
   Cloud Run containers are ephemeral, so you'll need to:
   - Create a Google Cloud Storage bucket for persistent data
   - Mount the bucket to your container or modify the code to use GCS directly
   - Update the code to save and load processed_ids.json from the mounted storage

4. **Set up Cloud Scheduler**
   For a truly serverless solution, modify the application to run once and exit, then:
   ```bash
   gcloud scheduler jobs create http gmail-notion-manager-job \
     --schedule="*/5 * * * *" \
     --uri="https://YOUR_CLOUD_RUN_URL/" \
     --http-method=POST \
     --attempt-deadline=4m
   ```

### Option 2: AWS Lambda with EventBridge

1. **Modify the code for Lambda**
   Create a lambda_handler.py with:
   ```python
   import main

   def lambda_handler(event, context):
       manager = main.NewsletterManager()
       manager.process_new_emails()
       return {"statusCode": 200, "body": "Processed emails successfully"}
   ```

2. **Package the application**
   ```bash
   pip install -r requirements.txt -t ./package
   cp *.py ./package/
   cd package
   zip -r ../deployment.zip .
   ```

3. **Create Lambda function**
   - Create a new Lambda function
   - Upload the deployment.zip file
   - Set environment variables for NOTION_TOKEN and NOTION_DATABASE_ID
   - Set the handler to `lambda_handler.lambda_handler`
   - Set up an S3 bucket for persistent storage
   - Grant the Lambda function permissions to access the S3 bucket

4. **Set up EventBridge rule**
   - Create a new rule with a schedule expression of `rate(5 minutes)`
   - Set the target to your Lambda function

### Option 3: Docker on VPS/Dedicated Server

If you prefer to run on your own server:

1. **Set up a server with Docker installed**

2. **Create a docker-compose.yml file**
   ```yaml
   version: '3'
   services:
     gmail-notion-manager:
       build: .
       restart: always
       volumes:
         - ./credentials.json:/app/credentials.json:ro
         - ./token.json:/app/token.json
         - ./processed_ids.json:/app/processed_ids.json
       environment:
         - NOTION_TOKEN=your_token
         - NOTION_DATABASE_ID=your_database_id
   ```

3. **Run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

## Advanced Configuration

### Handling Gmail Authentication in Headless Environments

For servers without a browser, you need to:

1. Run the application locally first to generate the token.json file
2. Copy the token.json file to your server
3. Set up a mechanism to refresh the token when needed

### Customizing the Categorization Logic

The current categorization is based on keyword matching, but you can enhance it by:

1. Implementing ML-based categorization
2. Using NLP libraries for better text analysis
3. Implementing custom rules based on sender, subject patterns, etc.

To modify the categorization logic, edit the `_categorize_content` method in main.py.

### Handling API Rate Limits

Both Gmail and Notion APIs have rate limits. To handle them:

1. Implement exponential backoff for API failures
2. Reduce check frequency
3. Process emails in smaller batches

## Maintenance and Monitoring

### Logging
- The application logs to both console and app.log file
- For cloud deployments, use the respective cloud logging services:
  - Google Cloud Logging
  - AWS CloudWatch
  - Azure Application Insights

### Updating the Application
To update the application:

1. Pull the latest code
2. Install any new dependencies
3. Restart the application or redeploy

### Security Considerations
- Store credentials securely using environment variables or secret management services
- Regularly rotate API tokens
- Implement IP restrictions for API access where possible
- Use least privilege principles for service accounts
- Consider encrypting sensitive data like email content

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify credentials are correct
   - Check token expiration
   - Ensure proper scopes are enabled

2. **Rate Limiting**
   - Check the logs for rate limit errors
   - Increase the interval between checks
   - Reduce batch sizes

3. **Missing Emails**
   - Check Gmail API quotas
   - Verify sender addresses are correct
   - Check for email filtering rules

4. **Notion API Errors**
   - Verify database ID is correct
   - Check database permissions
   - Ensure properties match the expected schema
   - Look for error messages in the logs

5. **Categories Not Working**
   - Check the keywords defined in config.py
   - Lower the categorization threshold
   - Review email content for expected keywords 