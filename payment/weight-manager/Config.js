const CONFIG = {
    // スプレッドシートの設定
    SHEET_NAME: 'Data',

    // Gemini API の設定
    GEMINI: {
        API_KEY_PROPERTY: 'GEMINI_API_KEY', // ScriptProperties のキー名
        // 2025年2月現在の最新（v2.0）を指定。v1エンドポイントで動作実績あり。
        MODEL: 'gemini-2.0-flash',
        // ユーザー環境に合わせて v1 に設定
        URL: 'https://generativelanguage.googleapis.com/v1/models/'
    },

    // プロンプトテンプレート
    PROMPT: `
以下の体重データ（日付: 体重 (メモ)）をもとに、この人の体重の傾向を分析し、
健康管理のアドバイスを150文字以内で、優しく励ますような口調で教えてください。

データ:
{{DATA}}
`
};
