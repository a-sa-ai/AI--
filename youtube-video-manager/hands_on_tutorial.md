# 【GASハンズオン】自分だけのYouTube動画管理アプリを作ろう！【スマホ対応】

YouTubeで「後で見よう」と思っていた動画や、勉強になった「耳学」動画、きちんと整理できていますか？
今回は、Google Apps Script (GAS) と Google スプレッドシートを使って、スマホから手軽にYouTube動画を記録・管理できる自分専用の**「My Video Manager」**アプリを作成します。

**完成イメージ:**
- シンプルな検索・入力画面
- スマホで見やすいデザイン
- 「耳学」「メモ」などのタグ付け保存
- 未完了・完了のステータス管理
- **完全自動化**：URLを送るだけでタイトルを自動取得！

プログラミング初心者の方でも、コピペで作成できるように手順を解説していきます！

---

## 準備するもの

1. Google アカウント
2. パソコン（設定用）
3. スマホ（利用用）

---

## 手順1：スプレッドシートの作成

まずはデータを保存するための「データベース」となるスプレッドシートを用意します。

1. [Google スプレッドシート](https://sheets.new) を新規作成します。
2. ファイル名を「YouTube動画管理」など、わかりやすい名前に変更します。
3. シート名が「シート1」になっていることを確認します（デフォルトのままでOK）。
4. 1行目にヘッダーなどは**不要**です（プログラムが自動で作成します）。

---

## 手順2：スクリプトエディタを開く

1. スプレッドシートのメニューバーから **「拡張機能」 > 「Apps Script」** をクリックします。
2. 新しいタブでスクリプトエディタが開きます。
3. プロジェクト名を「Project Video Manager」などに変更しておきましょう。

---

## 手順3：YouTube Data API の有効化

動画のタイトルを自動取得するために、Googleのサービスを追加します。

1. エディタ左側の「サービス」の横にある **「+」** ボタンをクリックします。
2. 一覧から **「YouTube Data API v3」** を探して選択します。
3. **「追加」** をクリックします。
   - ※左側の「サービス」の下に `YouTube` が表示されればOKです。

---

## 手順4：【重要】権限設定ファイルの修正

**ここが一番のポイントです！**
YouTube APIを正しく使うために、設定ファイル（`appsscript.json`）を手動で編集して、「このアプリはYouTubeを使いますよ」と明示的に宣言します。

1. エディタ左側のメニューにある **「歯車アイコン（プロジェクトの設定）」** をクリックします。
2. **「「appsscript.json」マニフェスト ファイルをエディタで表示する」** にチェックを入れます。
3. 左側のファイルリストに戻ると、`appsscript.json` というファイルが現れるのでクリックします。
4. 元の内容をすべて消して、以下のコードを貼り付けてください。

```json
{
  "timeZone": "Asia/Tokyo",
  "dependencies": {
    "enabledAdvancedServices": [{
      "userSymbol": "YouTube",
      "serviceId": "youtube",
      "version": "v3"
    }]
  },
  "exceptionLogging": "STACKDRIVER",
  "runtimeVersion": "V8",
  "oauthScopes": [
    "https://www.googleapis.com/auth/script.external_request",
    "https://www.googleapis.com/auth/spreadsheets", 
    "https://www.googleapis.com/auth/youtube"
  ],
  "webapp": {
    "executeAs": "USER_DEPLOYING",
    "access": "MYSELF"
  }
}
```

5. **「保存（フロッピーアイコン）」** をクリックします。
6. **【重要】ブラウザの更新ボタンを押して、ページを再読み込みしてください！**
   - ※これを忘れると設定が反映されません。必ずリロードしてください。

---

## 手順5：サーバーサイドコード (code.gs) の作成

動画情報の取得やスプレッドシートへの保存を行う「裏方」のプログラムを書きます。

1. エディタにもともと書かれている `function myFunction() {...}` をすべて削除します。
2. 以下のコードをコピーして貼り付けます。

```javascript
function doGet() {
    return HtmlService.createHtmlOutputFromFile('index')
        .addMetaTag('viewport', 'width=device-width, initial-scale=1')
        .setTitle('Video Manager');
}

/**
 * YouTube動画をスプレッドシートに保存
 */
function saveVideoToSheet(url, type) {
    try {
        const videoId = getVideoId(url);
        if (!videoId) {
            throw new Error('YouTubeのURLが無効です');
        }

        const title = getVideoTitle(videoId);
        const ss = SpreadsheetApp.getActiveSpreadsheet();
        const sheet = ss.getSheetByName('シート1') || ss.insertSheet('シート1');

        // ヘッダーがなければ作成
        if (sheet.getLastRow() === 0) {
            sheet.appendRow(['タイトル', 'URL', '種別', '日付', 'ステータス']);
        }

        // ステータスはデフォルトで'未完了'
        sheet.appendRow([title, url, type, new Date(), '未完了']);

        return { success: true, message: `「${title}」を保存しました` };

    } catch (e) {
        return {
            success: false,
            message: 'エラー: ' + e.message
        };
    }
}

/**
 * 最近の未完了動画を取得（最大20件）
 */
function getRecentVideos() {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = ss.getSheetByName('シート1');

    if (!sheet || sheet.getLastRow() <= 1) {
        return [];
    }

    const lastRow = sheet.getLastRow();
    // 直近100件から検索（効率化のため）
    const numRows = Math.min(lastRow - 1, 100);
    const startRow = Math.max(2, lastRow - numRows + 1);

    const data = sheet.getRange(startRow, 1, numRows, 5).getValues(); // A列~E列

    // '完了'以外のアイテムをフィルタ
    const activeItems = data.filter(row => row[4] !== '完了');

    // 新しい順に最大20件返す
    return activeItems.slice(-20).reverse().map(row => ({
        title: row[0],
        url: row[1],
        type: row[2],
        date: Utilities.formatDate(new Date(row[3]), Session.getScriptTimeZone(), 'MM/dd HH:mm')
    }));
}

/**
 * 動画を完了にする
 */
function markVideoAsDone(url) {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = ss.getSheetByName('シート1');

    if (!sheet) return { success: false, message: 'シートが見つかりません' };

    const lastRow = sheet.getLastRow();
    if (lastRow <= 1) return { success: false, message: 'データがありません' };

    // 下から検索して該当URLを見つける
    const numRows = Math.min(lastRow - 1, 100);
    const startRow = Math.max(2, lastRow - numRows + 1);
    const urls = sheet.getRange(startRow, 2, numRows, 1).getValues(); // URL列
    const statuses = sheet.getRange(startRow, 5, numRows, 1).getValues(); // ステータス列

    let foundRow = -1;

    for (let i = urls.length - 1; i >= 0; i--) {
        if (urls[i][0] === url && statuses[i][0] !== '完了') {
            foundRow = startRow + i;
            break;
        }
    }

    if (foundRow !== -1) {
        sheet.getRange(foundRow, 5).setValue('完了');
        return { success: true, message: '完了にしました' };
    }

    return { success: false, message: '対象の動画が見つかりませんでした' };
}

/**
 * URLから動画IDを抽出
 */
function getVideoId(url) {
    if (!url) return null;
    const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
    const match = url.match(regExp);
    return (match && match[2].length === 11) ? match[2] : null;
}

/**
 * YouTube Data APIを使ってタイトルを取得
 */
function getVideoTitle(videoId) {
    try {
        const response = YouTube.Videos.list('snippet', {
            id: videoId
        });

        if (response.items.length === 0) {
            return 'タイトル不明 (動画が見つかりません)';
        }
        return response.items[0].snippet.title;
    } catch (e) {
        console.error('YouTube API Error: ' + e.toString());
        return 'タイトル取得失敗';
    }
}

/**
 * スプレッドシートのURLを取得（おまけ用）
 */
function getSpreadsheetUrl() {
    return SpreadsheetApp.getActiveSpreadsheet().getUrl();
}
```

---

## 手順6：画面デザイン (index.html) の作成

スマホで操作するための画面を作ります。

1. エディタ左上の **「+」** ボタン > **「HTML」** をクリックします。
2. ファイル名を `index` と入力してEnterキーを押します（`.html`は自動でつきます）。
3. 以下のコードをすべてコピーして、もとのコードを上書き貼り付けします。

```html
<!DOCTYPE html>
<html>
<head>
    <base target="_top">
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Video Manager</title>
    <style>
        :root {
            --primary-red: #FF0000;
            --dark-text: #0F0F0F;
            --gray-text: #606060;
            --bg-color: #F9F9F9;
            --card-bg: #FFFFFF;
            --border-color: #E5E5E5;
            --blue-accent: #065FD4;
        }

        body {
            font-family: Roboto, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--dark-text);
            margin: 0;
            padding: 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
        }

        .container {
            width: 100%;
            max-width: 500px;
        }

        /* Header */
        .header {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            margin-bottom: 24px;
            padding-top: 12px;
        }

        .logo-icon {
            width: 32px;
            height: 32px;
            fill: var(--primary-red);
        }

        h1 {
            font-size: 22px;
            margin: 0;
            font-weight: 700;
            letter-spacing: -0.5px;
        }

        /* Input Card */
        .card {
            background: var(--card-bg);
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            padding: 20px;
            margin-bottom: 24px;
        }

        .input-wrapper {
            margin-bottom: 20px;
        }

        input[type="text"] {
            width: 100%;
            padding: 16px;
            font-size: 16px;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            box-sizing: border-box;
            transition: border-color 0.2s;
            outline: none;
            -webkit-appearance: none;
            appearance: none;
            background: #FAFAFA;
            color: var(--dark-text);
        }

        input[type="text"]:focus {
            border-color: var(--blue-accent);
            background: #FFF;
            box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.05);
        }

        .button-group {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }

        button {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 12px 16px;
            font-size: 14px;
            font-weight: 500;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: background-color 0.2s;
            color: var(--dark-text);
            background: #F2F2F2;
            min-height: 80px;
        }

        button:active {
            background: #E5E5E5;
        }

        button svg {
            width: 28px;
            height: 28px;
            fill: currentColor;
        }

        button.btn-ear {
            color: #1E8E3E;
            background: #E6F4EA;
        }

        button.btn-ear:active {
            background: #CEEAD6;
        }

        button.btn-memo {
            color: #1967D2;
            background: #E8F0FE;
        }

        button.btn-memo:active {
            background: #D2E3FC;
        }

        /* History List */
        .history-section {
            width: 100%;
        }

        .section-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 12px;
            padding-left: 4px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .section-title span {
            background: var(--primary-red);
            color: white;
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 700;
        }

        .video-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .video-item {
            display: flex;
            background: var(--card-bg);
            padding: 12px;
            border-radius: 12px;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
            align-items: center;
            gap: 12px;
            transition: transform 0.2s, opacity 0.3s;
        }

        .video-item.removing {
            transform: translateX(100%);
            opacity: 0;
        }

        .video-icon {
            flex-shrink: 0;
            width: 44px;
            height: 44px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            background: #F0F0F0;
        }

        .video-content {
            flex: 1;
            min-width: 0;
            cursor: pointer;
            /* Suggest clickable */
        }

        /* Make the title look like a link */
        .video-title {
            font-size: 14px;
            font-weight: 500;
            line-height: 1.4;
            margin-bottom: 4px;
            color: var(--dark-text);
            display: -webkit-box;
            -webkit-line-clamp: 2;
            line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }

        .video-meta {
            font-size: 12px;
            color: var(--gray-text);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .check-btn {
            flex-shrink: 0;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            border: none;
            background: transparent;
            color: #CCCCCC;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: color 0.2s, background 0.2s;
            min-height: auto;
            /* Override general button style */
            padding: 0;
        }

        .check-btn:active {
            background: #F0F0F0;
        }

        .check-btn svg {
            width: 24px;
            height: 24px;
        }

        .check-btn.checked {
            color: #1E8E3E;
        }

        /* Utilities */
        #status {
            margin-top: 12px;
            font-size: 13px;
            text-align: center;
            display: none;
            min-height: 20px;
        }

        .success {
            color: #1E8E3E;
        }

        .error {
            color: #D93025;
        }

        .spinner {
            display: none;
            width: 24px;
            height: 24px;
            border: 3px solid rgba(0, 0, 0, 0.1);
            border-top-color: var(--primary-red);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }

        @keyframes spin {
            to {
                transform: rotate(360deg);
            }
        }

        .empty-state {
            text-align: center;
            color: var(--gray-text);
            padding: 40px 20px;
            font-size: 14px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
        }

        .empty-state svg {
            width: 48px;
            height: 48px;
            fill: #E5E5E5;
        }
    </style>
</head>

<body>
    <div class="container">
        <div class="header">
            <svg class="logo-icon" viewBox="0 0 24 24">
                <path
                    d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 3.993-8 4.007z" />
            </svg>
            <h1>YouTube Manager</h1>
            <a id="sheet-link" href="#" target="_blank" style="display:none; margin-left: auto;">
                <svg viewBox="0 0 24 24" style="width:24px;height:24px;fill:#0F9D58;">
                    <path
                        d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-2h2v2zm0-4H7v-2h2v2zm0-4H7V7h2v2zm4 8h-2v-2h2v2zm0-4h-2v-2h2v2zm0-4h-2V7h2v2zm4 8h-2v-2h2v2zm0-4h-2v-2h2v2zm0-4h-2V7h2v2z" />
                </svg>
            </a>
        </div>

        <div class="card">
            <div class="input-wrapper">
                <input type="text" id="url" placeholder="YouTubeのURLを入力" autocomplete="off">
            </div>

            <div class="button-group">
                <!-- 耳学 -->
                <button class="btn-ear" onclick="save('耳学')">
                    <svg viewBox="0 0 24 24">
                        <path
                            d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z" />
                    </svg>
                    耳学
                </button>

                <!-- メモ -->
                <button class="btn-memo" onclick="save('メモ')">
                    <svg viewBox="0 0 24 24">
                        <path
                            d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z" />
                    </svg>
                    メモ
                </button>
            </div>

            <div id="status"></div>
            <div id="loader" class="spinner"></div>
        </div>

        <div class="history-section">
            <div class="section-title">
                最近の保存リスト <span>Active</span>
            </div>
            <div id="history-list" class="video-list">
                <div class="empty-state">
                    <div class="spinner" style="display:block"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        window.onload = function () {
            loadHistory();
            loadSheetUrl();
        };

        function loadSheetUrl() {
            google.script.run.withSuccessHandler(url => {
                if (url) {
                    const link = document.getElementById('sheet-link');
                    link.href = url;
                    link.style.display = 'block';
                }
            }).getSpreadsheetUrl();
        }

        function save(type) {
            const urlInput = document.getElementById('url');
            const url = urlInput.value.trim();
            const statusDiv = document.getElementById('status');
            const loader = document.getElementById('loader');

            if (!url) {
                showStatus('URLを入力してください', 'error');
                return;
            }

            setLoading(true);

            google.script.run
                .withSuccessHandler(function (response) {
                    setLoading(false);
                    if (response.success) {
                        showStatus('保存しました', 'success');
                        urlInput.value = '';
                        loadHistory(); // Refresh list
                        setTimeout(() => { statusDiv.style.display = 'none'; }, 2000);
                    } else {
                        showStatus(response.message, 'error');
                    }
                })
                .withFailureHandler(function (error) {
                    setLoading(false);
                    showStatus('エラーが発生しました', 'error');
                })
                .saveVideoToSheet(url, type);

            function setLoading(bool) {
                loader.style.display = bool ? 'block' : 'none';
                statusDiv.style.display = 'none';
            }

            function showStatus(msg, cls) {
                statusDiv.textContent = msg;
                statusDiv.className = cls;
                statusDiv.style.display = 'block';
            }
        }

        function loadHistory() {
            google.script.run
                .withSuccessHandler(renderHistory)
                .withFailureHandler(() => {
                    document.getElementById('history-list').innerHTML = '<div class="empty-state">読み込み失敗</div>';
                })
                .getRecentVideos();
        }

        function renderHistory(videos) {
            const list = document.getElementById('history-list');
            if (!videos || videos.length === 0) {
                list.innerHTML = `
            <div class="empty-state">
              <svg viewBox="0 0 24 24"><path d="M19 5v14H5V5h14m0-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-4.86 8.86l-3 3.87L9 13.14 6 17h12l-3.86-5.14z"/></svg>
              <span>保存された動画はありません</span>
            </div>`;
                return;
            }

            let html = '';
            videos.forEach(v => {
                const isEar = v.type.indexOf('耳') !== -1;
                const iconChar = isEar ? '👂' : '📝';

                html += `
            <div class="video-item" id="item-${encodeId(v.url)}">
              <div class="video-icon">
                ${iconChar}
              </div>
              <div class="video-content" onclick="openVideo('${v.url}')">
                <div class="video-title">${escapeHtml(v.title)}</div>
                <div class="video-meta">
                  <span>${escapeHtml(v.type)}</span> • <span>${v.date}</span>
                </div>
              </div>
              <button class="check-btn" onclick="markDone('${v.url}', this)" title="完了にする">
                <svg viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
              </button>
            </div>
          `;
            });
            list.innerHTML = html;
        }

        function openVideo(url) {
            window.open(url, '_blank');
        }

        function markDone(url, btnElement) {
            // Optimistic UI update
            const item = btnElement.closest('.video-item');
            btnElement.classList.add('checked');

            if (confirm('この動画を完了リストに移動しますか？')) {
                item.classList.add('removing');

                google.script.run
                    .withSuccessHandler(function (res) {
                        if (res.success) {
                            // Actually remove after success logic if needed, but animation handles visual
                            setTimeout(() => item.remove(), 300);

                            // If list empty, show empty state
                            const list = document.getElementById('history-list');
                            if (list.children.length <= 1) { // 1 because we haven't removed it from DOM yet
                                setTimeout(() => {
                                    if (list.children.length === 0) loadHistory();
                                }, 300);
                            }
                        } else {
                            item.classList.remove('removing');
                            alert(res.message);
                        }
                    })
                    .withFailureHandler(function () {
                        item.classList.remove('removing');
                        alert('通信エラー');
                    })
                    .markVideoAsDone(url);
            } else {
                btnElement.classList.remove('checked');
            }
        }

        // Simple unique ID encoder for DOM elements (strip special chars)
        function encodeId(url) {
            return url.replace(/[^a-zA-Z0-9]/g, '');
        }

        function escapeHtml(text) {
            if (!text) return '';
            return text
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }
    </script>
</body>
</html>
```

---

## 手順7：ウェブアプリとしてデプロイ

最後に、このアプリをスマホで使えるように公開します。

1. エディタ右上の **「デプロイ」 > 「新しいデプロイ」** をクリック。
2. 「種類の選択」の歯車アイコンから **「ウェブアプリ」** を選択。
3. 設定項目を入力をします。
   - **説明**: 「My Video Manager v1」など
   - **次のユーザーとして実行**: **「自分」**
   - **アクセスできるユーザー**: **「自分のみ」**（自分専用アプリなので安心！）
4. **「デプロイ」** をクリック。
5. **「アクセスを承認」** を求められたら承認します。
   - ※手順4で設定ファイル書き換えたおかげで、スムーズに承認できるはずです！
   - ※「このアプリはGoogleによって確認されていません」と出た場合は、「詳細」>「(安全ではないページ)に移動」を選択してください。
6. **ウェブアプリのURL** が発行されます。このURLをスマホに送って開いてみましょう！

---

## 完了！

お疲れ様でした！これであなただけの動画管理アプリの完成です。
スマホでURLを開くと、アプリのような画面が表示され、URLをコピペ＆タップするだけでスプレッドシートにどんどん動画が溜まっていきます。

ぜひ活用してみてください！
