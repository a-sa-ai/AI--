// 拡張機能のアイコンをクリックしたときに、サイドパネルを開くように設定します
chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch((error) => console.error(error));