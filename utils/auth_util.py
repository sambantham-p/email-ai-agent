import logging
import os
from pathlib import Path
from utils.config_util import load_config
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import glob
import shutil

auth_logger = logging.getLogger("Auth")
config = load_config()


def get_credential():
    auth_logger.info("Fetching credentials from downloads folder if exists")
    project_dir = Path(__file__).resolve().parent.parent
    target_path = project_dir / "credentials.json"

    # Search Downloads for client_secret JSON
    download_dir = Path.home() / "Downloads"
    pattern = str(download_dir / "client_secret*.json")
    found_files = glob.glob(pattern)

    if not found_files:
        raise FileNotFoundError(
            "Could not find the client_secret.json file in the user's Downloads folder. "
            "Please download it from the Google Cloud Console."
        )

    # Get the latest downloaded file
    latest = max(found_files, key=os.path.getmtime)

    # Copy it into the project folder
    shutil.copy(latest, target_path)
    auth_logger.info("Copied %s to credentials.json", latest)


def initialize_authentication():
    credentials_file = config['auth']['credentials_filename']
    if not os.path.exists(credentials_file):
        try:
            auth_logger.info(f"File {credentials_file} does not exist")
            auth_logger.info("Fetching credentials from downloads folder if exists")
            get_credential()
        except FileNotFoundError as fife:
            auth_logger.error("client_secret JSON NOT FOUND in downloads.")
            auth_logger.error(fife)
            auth_logger.error("Please download your OAuth client JSON from Google Cloud Console.")
            return
        except Exception as e:
            auth_logger.error("Unexpected error during credential import.")
            auth_logger.exception(e)
            return


def initialize_gmail_authentication():
    creds = None
    auth_logger.info("Starting gmail authentication.")
    credentials_file = config['auth']['credentials_filename']
    token_file = config['auth']['token_filename']
    scopes = config['auth']['scopes']
    # Load existing saved credentials
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, scopes)

    # Token missing or invalid/expired
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Token expired but can be refreshed
            auth_logger.info("Refreshing expired token...")
            creds.refresh(Request())
        else:
            # Full OAuth login required
            auth_logger.info("Starting new OAuth flow. Browser window will open.")
            if not os.path.exists(credentials_file):
                raise FileNotFoundError(f"OAuth client secrets file not found at: {credentials_file}")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, scopes)
            creds = flow.run_local_server(port=0)

        # Save new or refreshed credentials
        with open(token_file, "w") as token:
            token.write(creds.to_json())
            auth_logger.info("Token saved/updated in %s", token_file)

    service = build("gmail", "v1", credentials=creds)
    auth_logger.info("Completed gmail authentication.")
    return service

