"""ONE-TIME helper: run on any computer with a browser to obtain YT_REFRESH_TOKEN.

  pip install google-auth-oauthlib
  python src/get_refresh_token.py client_secret.json

After it prints the token, store it as a GitHub secret. Your PC is not needed again.
Never commit client_secret.json or the token.
"""
import sys
from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_secrets_file(
    sys.argv[1], scopes=["https://www.googleapis.com/auth/youtube.upload"]
)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
print("\nYT_REFRESH_TOKEN =", creds.refresh_token)
