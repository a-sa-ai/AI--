import os
import json
import time
import re
import subprocess
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

WATCH_DIRECTORY = os.path.expanduser("~/Documents/Zoom")
CONFIG_DIR = os.path.expanduser("~/.zoom_youtube")
UPLOADED_LOG = os.path.join(CONFIG_DIR, "uploaded.json")
TOKEN_FILE = os.path.join(CONFIG_DIR, "token_youtube.json")
CREDENTIALS_FILE = os.path.join(CONFIG_DIR, "credentials.json")

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

ZOOM_FOLDER_RE = re.compile(
    r'(?P<date>\d{4}-\d{2}-\d{2})\s(?P<time>\d{2}\.\d{2}\.\d{2})\s?(?P<title>.*)'
)


def notify(title, message):
    subprocess.run([
        'osascript', '-e',
        f'display dialog "{message}" with title "{title}" buttons {{"OK"}} default button "OK"'
    ])


def load_uploaded_log() -> set:
    if os.path.exists(UPLOADED_LOG):
        with open(UPLOADED_LOG, 'r') as f:
            return set(json.load(f))
    return set()


def save_uploaded_log(uploaded: set):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(UPLOADED_LOG, 'w') as f:
        json.dump(list(uploaded), f)


def folder_to_video_title(folder_name: str) -> str:
    m = ZOOM_FOLDER_RE.match(folder_name)
    if m:
        date = m.group('date')
        t = m.group('time').replace('.', ':')
        title_part = m.group('title').strip()
        base = f"Zoom録画 {date} {t}"
        return f"{base} {title_part}" if title_part else base
    return f"Zoom録画 {folder_name}"


def find_new_mp4s(uploaded: set) -> list:
    new_files = []
    for root, dirs, files in os.walk(WATCH_DIRECTORY):
        for f in files:
            if f.lower().endswith('.mp4'):
                full_path = os.path.join(root, f)
                if full_path not in uploaded:
                    new_files.append(full_path)
    return sorted(new_files)


def get_youtube_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                notify("エラー", "credentials.json が見つかりません。\\n~/.zoom_youtube/ に置いてください。")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())

    return build('youtube', 'v3', credentials=creds)


def upload_file(youtube, file_path, title):
    body = {
        'snippet': {
            'title': title,
            'description': f'Zoom録画の自動アーカイブ\nファイル: {os.path.basename(file_path)}',
            'categoryId': '22',
        },
        'status': {
            'privacyStatus': 'unlisted',
            'selfDeclaredMadeForKids': False,
        },
    }
    media = MediaFileUpload(file_path, mimetype='video/mp4', resumable=True)
    request = youtube.videos().insert(part='snippet,status', body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()

    return response.get('id')


def main():
    youtube = get_youtube_service()
    if not youtube:
        return

    uploaded = load_uploaded_log()
    new_files = find_new_mp4s(uploaded)

    if not new_files:
        notify("Zoom録画アップロード", "新しいZoom録画はありません。")
        return

    notify("Zoom録画アップロード", f"{len(new_files)}件の新しい録画をアップロードします。\\nOKを押すと開始します。")

    urls = []
    for i, file_path in enumerate(new_files):
        title = folder_to_video_title(Path(file_path).parent.name)
        print(f"({i+1}/{len(new_files)}) {title}")
        try:
            video_id = upload_file(youtube, file_path, title)
            uploaded.add(file_path)
            save_uploaded_log(uploaded)
            urls.append(f"https://youtu.be/{video_id}")
        except Exception as e:
            notify("エラー", f"アップロード失敗:\\n{os.path.basename(file_path)}")

    result = f"{len(urls)}件のアップロードが完了しました！\\n\\n" + "\\n".join(urls)
    notify("完了！", result)


if __name__ == '__main__':
    main()
