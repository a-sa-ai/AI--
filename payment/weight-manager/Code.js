function doGet() {
  return HtmlService.createHtmlOutputFromFile('index')
    .setTitle('体重管理アプリ')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

function saveData(date, weight, memo) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(CONFIG.SHEET_NAME);

  if (!sheet) {
    sheet = ss.insertSheet(CONFIG.SHEET_NAME);
    sheet.appendRow(['日付', '体重', 'メモ']);
  }

  sheet.appendRow([date, weight, memo]);
  return "保存しました！";
}

function getData() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(CONFIG.SHEET_NAME);

  if (!sheet) {
    return [];
  }

  const data = sheet.getDataRange().getValues();
  // ヘッダー行を削除
  data.shift();
  return data;
}

function analyzeData() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(CONFIG.SHEET_NAME);

  if (!sheet) {
    return "データがまだありません。";
  }

  // 最新の30件を取得
  const data = sheet.getDataRange().getValues();
  data.shift(); // remove header
  const recentData = data.slice(-30);

  if (recentData.length === 0) {
    return "データが足りません。入力をしてください。";
  }

  // プロンプト作成
  let promptData = recentData.map(row => {
    const d = new Date(row[0]);
    const dateStr = `${d.getMonth() + 1}/${d.getDate()}`;
    return `${dateStr}: ${row[1]}kg (${row[2]})`;
  }).join("\n");

  const prompt = CONFIG.PROMPT.replace('{{DATA}}', promptData);

  // Gemini API呼び出し
  const apiKey = PropertiesService.getScriptProperties().getProperty(CONFIG.GEMINI.API_KEY_PROPERTY);
  if (!apiKey) {
    return "APIキーが設定されていません。スクリプトプロパティに " + CONFIG.GEMINI.API_KEY_PROPERTY + " を設定してください。";
  }

  const url = `${CONFIG.GEMINI.URL}${CONFIG.GEMINI.MODEL}:generateContent?key=${apiKey}`;
  const payload = {
    "contents": [{
      "parts": [{ "text": prompt }]
    }]
  };

  const options = {
    "method": "post",
    "contentType": "application/json",
    "payload": JSON.stringify(payload),
    "muteHttpExceptions": true
  };

  try {
    const response = UrlFetchApp.fetch(url, options);
    const json = JSON.parse(response.getContentText());
    if (json.error) {
      return "エラーが発生しました: " + json.error.message;
    }
    return json.candidates[0].content.parts[0].text;
  } catch (e) {
    return "通信エラーが発生しました: " + e.toString();
  }
}
