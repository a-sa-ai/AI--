function doGet() {
    const template = HtmlService.createTemplateFromFile('index');
    template.sheetUrl = CONFIG.SPREADSHEET_URL;
    template.folderUrl = CONFIG.FOLDER_URL;

    // API Key is available in CONFIG.GEMINI_API_KEY for server-side use

    return template.evaluate()
        .addMetaTag('viewport', 'width=device-width, initial-scale=1')
        .setTitle('Video Manager');
}

/**
 * Saves YouTube video info to Spreadsheet
 * @param {string} url - YouTube video URL
 * @param {string} type - '耳学' or 'メモ'
 * @return {Object} result - {success: boolean, message: string, title: string}
 */
function saveVideoToSheet(url, type) {
    try {
        const videoId = getVideoId(url);
        if (!videoId) {
            throw new Error('YouTubeのURLが無効です');
        }

        const title = getVideoTitle(videoId);

        // Replace with your actual Spreadsheet ID if not bound to the container
        // If bound, use SpreadsheetApp.getActiveSpreadsheet()
        // const ss = SpreadsheetApp.openById('YOUR_SPREADSHEET_ID');
        const ss = SpreadsheetApp.getActiveSpreadsheet();
        const sheet = ss.getSheetByName('シート1') || ss.insertSheet('シート1');

        // Append headers if empty
        if (sheet.getLastRow() === 0) {
            sheet.appendRow(['タイトル', 'URL', '種別', '日付', 'ステータス']);
        }

        // Status is '未完了' by default
        sheet.appendRow([title, url, type, new Date(), '未完了']);

        return {
            success: true,
            message: `「${title}」を保存しました`,
            title: title
        };

    } catch (e) {
        return {
            success: false,
            message: 'エラー: ' + e.message
        };
    }
}

/**
 * Get active videos (Status != '完了')
 * Returns up to 20 recent active items, reversed (newest first)
 */
function getRecentVideos() {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = ss.getSheetByName('シート1');

    if (!sheet || sheet.getLastRow() <= 1) {
        return [];
    }

    const lastRow = sheet.getLastRow();
    // Fetch all data to filter in memory (efficient enough for small personal sheets)
    // For very large sheets, we might want to limit the range, but filtering is needed.
    // Let's grab the last 100 rows to find active ones.
    const numRows = Math.min(lastRow - 1, 100);
    const startRow = Math.max(2, lastRow - numRows + 1);

    const data = sheet.getRange(startRow, 1, numRows, 5).getValues(); // Columns A to E

    // Filter for items that are not '完了'
    const activeItems = data.filter(row => row[4] !== '完了');

    // Return last 20 active items, newest first
    const recentItems = activeItems.slice(-20).reverse();

    return recentItems.map(row => ({
        title: row[0],
        url: row[1],
        type: row[2],
        date: Utilities.formatDate(new Date(row[3]), Session.getScriptTimeZone(), 'MM/dd HH:mm')
    }));
}

/**
 * Mark a video as Done
 * @param {string} url - The URL of the video to complete
 */
function markVideoAsDone(url) {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = ss.getSheetByName('シート1');

    if (!sheet) return { success: false, message: 'シートが見つかりません' };

    const lastRow = sheet.getLastRow();
    if (lastRow <= 1) return { success: false, message: 'データがありません' };

    // Search from bottom up to find the most recent entry for this URL that is not done
    // We read the URL column (B) and Status column (E)
    // Getting range in batches is better, but let's read columns B and E for the last 100 rows
    const numRows = Math.min(lastRow - 1, 100);
    const startRow = Math.max(2, lastRow - numRows + 1);
    const urls = sheet.getRange(startRow, 2, numRows, 1).getValues(); // Col B
    const statuses = sheet.getRange(startRow, 5, numRows, 1).getValues(); // Col E

    let foundRow = -1;

    // Loop backwards through the fetched data
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
 * Extract Video ID from URL
 */
function getVideoId(url) {
    if (!url) return null;
    const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
    const match = url.match(regExp);
    return (match && match[2].length === 11) ? match[2] : null;
}

/**
 * Get Video Title using YouTube Advanced Service
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
 * Get Spreadsheet URL
 */
function getSpreadsheetUrl() {
    return SpreadsheetApp.getActiveSpreadsheet().getUrl();
}
