import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import config

# The authorization code from your URL
auth_code = "4/0Ab_5qlkMrh6FDJHIjwJqUcdSMUGlnY8F7pQmQE7wWgMBlTe0zYhseGcpYKKZ5G19U3ma8w"  # Replace with your code

# Create a flow instance
flow = InstalledAppFlow.from_client_secrets_file(
    'credentials.json', 
    scopes=config.SCOPES,
    redirect_uri='http://localhost:53177/'
)

# Exchange the authorization code for credentials
flow.fetch_token(code=auth_code)

# Get credentials
creds = flow.credentials

# Save credentials to token.json
with open('token.json', 'w') as token:
    token.write(creds.to_json())

print("Token file created successfully!")