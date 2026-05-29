import os
import json
import re
import subprocess
from pathlib import Path
from datetime import datetime
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
URL_LOG = os.path.expanduser("~/Documents/zoom_youtube_log.txt")

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
ZOOM_FOLDER_RE = re.compile(
    r'(?P<date>\d{4}-\d{2}-\d{2})\s(?P<time>\d{2}\.\d{2}\.\d{2})\s?(?P<title>.*)'
)

def notify(title, message):
    subprocess.run(['osascript', '-e',
        f'display dialog "{message}" with title "{title}" buttons {{"OK"}} default button "OK"'])

def ask_text(title, prompt):
    script = f'display dialog "{prompt}" with title "{title}" default answer "" buttons {{"キャンセル", "OK"}} default button "OK"'
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    if result.returncode != 0:
        return None
    for part in result.stdout.split(','):
        if 'text returned:' in part:
            return part.replace('text returned:', '').strip()
    return None

def make_label(file_path):
    folder = Path(file_path).parent.name
    m = ZOOM_FOLDER_RE.match(folder)
    if m:
        date = m.group('date')
        title = m.group('title').strip()
        return f"{date} {title}" if title else date
    return folder

def load_uploaded_log():
    if os.path.exists(UPLOADED_LOG):
        with open(UPLOADED_LOG, 'r') as f:
            return set(json.load(f))
    return set()

def save_uploaded_log(uploaded):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(UPLOADED_LOG, 'w') as f:
        json.dump(list(uploaded), f)

def folder_to_video_title(folder_name):
    m = ZOOM_FOLDER_RE.match(folder_name)
    if m:
        date = m.group('date')
        t = m.group('time').replace('.', ':')
        title_part = m.group('title').strip()
        base = f"Zoom録画 {date} {t}"
        return f"{base} {title_part}" if title_part else base
    return f"Zoom録画 {folder_name}"

def find_new_mp4s(uploaded):
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
            try:
                creds.refresh(Request())
            except Exception:
                notify("再認証が必要です", "Googleの認証が切れました。\nOKを押すとブラウザでログイン画面が開きます。")
                os.remove(TOKEN_FILE)
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                notify("エラー", "credentials.json が見つかりません。")
                return None
            notify("初回ログイン", "OKを押すとブラウザでGoogleログイン画面が開きます。")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())
    return build('youtube', 'v3', credentials=creds)

def upload_file(youtube, file_path, title):
    body = {
        'snippet': {'title': title, 'description': 'Zoom録画の自動アーカイブ', 'categoryId': '22'},
        'status': {'privacyStatus': 'unlisted', 'selfDeclaredMadeForKids': False},
    }
    media = MediaFileUpload(file_path, mimetype='video/mp4', resumable=True)
    request = youtube.videos().insert(part='snippet,status', body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
    return response.get('id')

def save_url_log(title, url):
    with open(URL_LOG, 'a') as f:
        date = datetime.now().strftime('%Y-%m-%d %H:%M')
        f.write(f"{date}  {title}\n{url}\n\n")

def main():
    subprocess.Popen(['osascript', '-e', 'display dialog "起動しました" giving up after 2 with title "Zoom録画アップロード"'])

    youtube = get_youtube_service()
    if not youtube:
        return

    uploaded = load_uploaded_log()
    new_files = find_new_mp4s(uploaded)

    if not new_files:
        notify("Zoom録画アップロード", "新しいZoom録画はありません。")
        return

    lines = [f"{i+1}. {make_label(f)}" for i, f in enumerate(new_files)]
    list_text = "\n".join(lines)
    prompt = (
        f"新しい録画が{len(new_files)}件あります。\n\n"
        f"{list_text}\n\n"
        f"アップロード: 番号を入力（例: 1,3）または「全部」\n"
        f"スキップ（今後表示しない）: 番号の前に s（例: s1,s2）"
    )

    answer = ask_text("Zoom録画アップロード", prompt)
    if answer is None:
        return

    upload_targets = []
    skip_targets = []

    if answer.strip() == "全部":
        upload_targets = new_files
    else:
        for token in answer.split(','):
            token = token.strip()
            if token.startswith('s'):
                try:
                    idx = int(token[1:]) - 1
                    if 0 <= idx < len(new_files):
                        skip_targets.append(new_files[idx])
                except ValueError:
                    pass
            else:
                try:
                    idx = int(token) - 1
                    if 0 <= idx < len(new_files):
                        upload_targets.append(new_files[idx])
                except ValueError:
                    pass

    for f in skip_targets:
        uploaded.add(f)
    if skip_targets:
        save_uploaded_log(uploaded)

    if not upload_targets:
        if skip_targets:
            notify("Zoom録画アップロード", f"{len(skip_targets)}件をスキップ登録しました。")
        return

    urls = []
    for i, file_path in enumerate(upload_targets):
        title = folder_to_video_title(Path(file_path).parent.name)
        notify("アップロード中...", f"({i+1}/{len(upload_targets)})\n{title}\n\nしばらくお待ちください...")
        try:
            video_id = upload_file(youtube, file_path, title)
            uploaded.add(file_path)
            save_uploaded_log(uploaded)
            url = f"https://youtu.be/{video_id}"
            urls.append(url)
            save_url_log(title, url)
        except Exception as e:
            notify("エラー", f"アップロード失敗:\n{os.path.basename(file_path)}")

    result = f"{len(urls)}件のアップロードが完了しました！\n\n" + "\n".join(urls)
    notify("完了！", result)

if __name__ == '__main__':
    main()
