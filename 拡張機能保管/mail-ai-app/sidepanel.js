const btnDraft = document.getElementById('btn-draft');
const btnFix = document.getElementById('btn-fix');
const btnChat = document.getElementById('btn-chat');
const btnCopy = document.getElementById('btn-copy');
const inputArea = document.getElementById('input');
const chatInput = document.getElementById('chat-input');
const resultDiv = document.getElementById('result');
const toneSelect = document.getElementById('tone-select');

// ★ここにあなたのAPIキーを貼り付けてください
const apiKey = "AIzaSyBjWdHvs2IVV1Qkenu-Qh5hbPSWel0iuWQ";

// デバッグ用: 現在の拡張機能IDをログに出力
console.log("Current Extension ID:", chrome.runtime.id);

let conversationHistory = [];

async function callGemini(newPrompt, isChat = false) {
  resultDiv.innerHTML = '<span style="color:#8ebf86">AIが考え中...</span>';
  if (!isChat) conversationHistory = [];
  conversationHistory.push({ role: "user", parts: [{ text: newPrompt }] });

  try {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contents: conversationHistory })
    });

    const data = await response.json();

    if (!response.ok || !data.candidates || data.candidates.length === 0) {
      const msg = data.error?.message || "APIからの応答が不正です";
      if (msg.includes("API key not valid") || msg.includes("blocked")) {
        throw new Error("APIキーの設定エラー(リファラー制限など)の可能性があります。\n詳細: " + msg);
      }
      throw new Error(msg);
    }

    const aiText = data.candidates[0].content.parts[0].text;
    conversationHistory.push({ role: "model", parts: [{ text: aiText }] });
    resultDiv.innerText = aiText;
    chatInput.value = "";
  } catch (error) {
    resultDiv.innerText = "エラー: " + error.message;
  }
}

// コピー機能の処理
btnCopy.addEventListener('click', () => {
  const text = resultDiv.innerText;
  if (!text || text === "ここに結果が表示されます") return;

  navigator.clipboard.writeText(text).then(() => {
    const originalText = btnCopy.innerText;
    btnCopy.innerText = "✅ 完了！";
    btnCopy.style.backgroundColor = "#dff0d8";
    setTimeout(() => {
      btnCopy.innerText = originalText;
      btnCopy.style.backgroundColor = "#eee";
    }, 2000);
  });
});

btnDraft.addEventListener('click', () => {
  if (!inputArea.value) {
    resultDiv.innerText = "⚠️ 入力欄に何か書いてからボタンを押してください";
    return;
  }
  callGemini(`以下のメモを元に、【${toneSelect.value}】トーンでビジネスメールを作成してください：\n${inputArea.value}`, false);
});

btnFix.addEventListener('click', () => {
  if (!inputArea.value) {
    resultDiv.innerText = "⚠️ 添削したい文章を入力してください";
    return;
  }
  callGemini(`以下の文章を、【${toneSelect.value}】トーンで添削してください：\n${inputArea.value}`, false);
});

btnChat.addEventListener('click', () => {
  if (!chatInput.value) return;
  callGemini(chatInput.value, true);
});