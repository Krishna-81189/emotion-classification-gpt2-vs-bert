import os
import io
import sys
import yaml
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

# ----------------------------- #
# Logging setup
# ----------------------------- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# ----------------------------- #
# Load dataset config
# ----------------------------- #
CONFIG_PATH = "config/dataset_config.yaml"
SERVICE_ACCOUNT_KEY = "drive-service-key.json"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

def load_config():
    if not os.path.exists(CONFIG_PATH):
        logging.error(f"Missing config file: {CONFIG_PATH}")
        sys.exit(1)

    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)

    if "drive_file_id" not in config or "output_path" not in config:
        logging.error("Invalid config file — must contain 'drive_file_id' and 'output_path'.")
        sys.exit(1)

    return config["drive_file_id"], config["output_path"]

# ----------------------------- #
# Auth and download
# ----------------------------- #
def main():
    logging.info("🚀 Starting dataset download...")

    drive_file_id, output_path = load_config()

    if not os.path.exists(SERVICE_ACCOUNT_KEY):
        logging.error(f"Missing service account key: {SERVICE_ACCOUNT_KEY}")
        sys.exit(1)

    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_KEY, scopes=SCOPES
        )
        service = build("drive", "v3", credentials=creds)
    except Exception as e:
        logging.error(f"Failed to authenticate with service account: {e}")
        sys.exit(1)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        request = service.files().get_media(fileId=drive_file_id)
        fh = io.FileIO(output_path, "wb")
        downloader = MediaIoBaseDownload(fh, request)
        done = False

        logging.info(f"⬇️  Downloading file (ID: {drive_file_id})...")
        while not done:
            status, done = downloader.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                logging.info(f"   Progress: {progress}%")

        logging.info(f"✅ Download complete. File saved to: {output_path}")

    except HttpError as e:
        if e.resp.status == 403:
            logging.error("❌ Permission denied. Ensure the file is shared with your service account.")
        elif e.resp.status == 404:
            logging.error("❌ File not found. Check the file ID in your config.")
        else:
            logging.error(f"HTTP Error: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error during download: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
