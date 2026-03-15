import os
import time
import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Configuration
WATCH_DIRECTORY = os.path.expanduser("~/Documents/Zoom")
# ID of the Google Drive folder where you want to upload files
# You can find this in the URL of your Drive folder: drive.google.com/drive/folders/<FOLDER_ID>
DRIVE_FOLDER_ID = "Please_Replace_With_Your_Folder_ID" 

SCOPES = ['https://www.googleapis.com/auth/drive.file']

class ZoomHandler(FileSystemEventHandler):
    def __init__(self, service):
        self.service = service
        self.processing_dirs = set()

    def on_created(self, event):
        if event.is_directory:
            print(f"New recording session detected: {event.src_path}")
            # We don't upload the folder itself immediately, we wait for files.
            # Zoom creates a folder, then writes .zoom files, then converts to mp4.
            # We need a strategy to wait for completion.
            
            # Simple strategy: Watch for MP4 files within this new directory.
            # Since on_created triggers for files too, we'll handle files below.
            return

        filename = os.path.basename(event.src_path)
        if filename.lower().endswith(".mp4") or filename.lower().endswith(".m4a"):
            print(f"New media file detected: {event.src_path}")
            self.upload_file(event.src_path)

    def upload_file(self, file_path):
        """Uploads a file to Google Drive."""
        file_name = os.path.basename(file_path)
        
        # Optional: Wait a bit to ensure file write is complete (Zoom logic can be tricky)
        # A more robust check determines if file size is stable.
        self.wait_for_file_settle(file_path)

        print(f"Uploading {file_name}...")
        
        file_metadata = {
            'name': file_name,
            'parents': [DRIVE_FOLDER_ID]
        }
        media = MediaFileUpload(file_path, resumable=True)
        
        try:
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            print(f"File ID: {file.get('id')} uploaded.")
        except Exception as e:
            print(f"An error occurred during upload: {e}")

    def wait_for_file_settle(self, file_path, timeout=60):
        """Waits until the file size stops changing."""
        last_size = -1
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                current_size = os.path.getsize(file_path)
                if current_size == last_size and current_size > 0:
                    return
                last_size = current_size
                time.sleep(2)
            except OSError:
                time.sleep(1)
        print(f"Warning: File {file_path} might not be fully written.")

def get_drive_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        print("Credentials not valid or found. Please run setup_auth.py first.")
        return None

    return build('drive', 'v3', credentials=creds)

def main():
    if not os.path.exists(WATCH_DIRECTORY):
        print(f"Directory {WATCH_DIRECTORY} does not exist. Creating it for testing...")
        os.makedirs(WATCH_DIRECTORY)

    if DRIVE_FOLDER_ID == "Please_Replace_With_Your_Folder_ID":
        print("WARNING: You haven't set the DRIVE_FOLDER_ID in the script.")
        print("Please edit zoom_uploader.py and set the target Google Drive Folder ID.")

    service = get_drive_service()
    if not service:
        return

    event_handler = ZoomHandler(service)
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIRECTORY, recursive=True)
    observer.start()
    print(f"Monitoring {WATCH_DIRECTORY} for new Zoom recordings...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == '__main__':
    main()
