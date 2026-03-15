document.addEventListener('DOMContentLoaded', function () {
  console.log("Current Extension ID:", chrome.runtime.id);
  const eventList = document.getElementById('calendar-events');
  const dateTitle = document.getElementById('date-title');
  const buttons = {
    '-1': document.getElementById('btn-yesterday'),
    '0': document.getElementById('btn-today'),
    '1': document.getElementById('btn-tomorrow')
  };

  let currentOffset = 0; // 0=今日, -1=昨日, 1=明日

  // 初期表示（今日）
  loadSchedule(0);

  // ボタンクリックイベントの設定
  Object.keys(buttons).forEach(offset => {
    buttons[offset].addEventListener('click', () => {
      // ボタンの見た目を切り替え
      Object.values(buttons).forEach(btn => btn.classList.remove('active'));
      buttons[offset].classList.add('active');

      // タイトルの書き換え
      const titles = { '-1': '昨日の予定', '0': '今日の予定', '1': '明日の予定' };
      dateTitle.innerText = titles[offset];

      loadSchedule(parseInt(offset));
    });
  });

  function loadSchedule(offset) {
    eventList.innerHTML = '読み込み中...';
    chrome.identity.getAuthToken({ interactive: true }, function (token) {
      if (chrome.runtime.lastError) {
        console.error("Auth Error:", chrome.runtime.lastError);
        eventList.innerText = '認証エラー:\n' + chrome.runtime.lastError.message;
        return;
      }
      fetchEvents(token, offset);
    });
  }

  function fetchEvents(token, offset) {
    const targetDate = new Date();
    targetDate.setDate(targetDate.getDate() + offset);

    const minTime = new Date(targetDate.setHours(0, 0, 0, 0)).toISOString();
    const maxTime = new Date(targetDate.setHours(23, 59, 59, 999)).toISOString();

    const url = `https://www.googleapis.com/calendar/v3/calendars/primary/events?timeMin=${minTime}&timeMax=${maxTime}&orderBy=startTime&singleEvents=true`;

    fetch(url, {
      headers: { 'Authorization': 'Bearer ' + token }
    })
      .then(response => response.json())
      .then(data => displayEvents(data.items))
      .catch(error => {
        eventList.innerText = '取得エラーが発生しました。';
      });
  }

  function displayEvents(items) {
    if (!items || items.length === 0) {
      eventList.innerHTML = '<div style="text-align:center; padding:20px; color:#999;">予定はありません。</div>';
      return;
    }

    eventList.innerHTML = '';
    items.forEach(item => {
      const start = item.start.dateTime || item.start.date;
      const timeStr = start.includes('T') ? start.split('T')[1].substring(0, 5) : '終日';

      const div = document.createElement('div');
      div.className = 'event-item';
      div.innerHTML = `<span class="time">${timeStr}</span><span class="summary">${item.summary}</span>`;
      eventList.appendChild(div);
    });
  }
});