// 初心者ガイド（モチタン・モチスピ共通）: 動画の切り替え・スクロールで出てくる動き・アプリへ戻るボタン
(function () {
  document.documentElement.classList.remove('no-js');

  // 動画の切り替え（基本編／効果的に学習する編）
  var video = document.querySelector('.player video');
  var tabs = document.querySelectorAll('.player__tab');
  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      if (tab.getAttribute('aria-selected') === 'true') return;
      tabs.forEach(function (t) { t.setAttribute('aria-selected', t === tab ? 'true' : 'false'); });
      video.pause();
      video.poster = tab.dataset.poster;
      video.src = tab.dataset.src;
      video.load();
    });
  });

  // スクロールで出てくる
  var items = document.querySelectorAll('.rv');
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add('is-in'); io.unobserve(e.target); }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
    items.forEach(function (el) { io.observe(el); });
  } else {
    items.forEach(function (el) { el.classList.add('is-in'); });
  }

  // アプリの中で開いているときだけ「閉じてプレイ」ボタンを出す（PopupWebViewFullScreen が swipeBack で閉じる）
  // アプリとの連絡口（window.Unity）は読み込み後に用意されることがあるので、読み込み完了後にも見直す
  function inApp() { return !!(window.Unity && window.Unity.call); }
  function applyAppMode() {
    var app = inApp();
    document.querySelectorAll('[data-close-app]').forEach(function (el) { el.hidden = !app; });
    document.querySelectorAll('[data-out-app]').forEach(function (el) { el.hidden = app; });
  }
  document.querySelectorAll('[data-close-app]').forEach(function (btn) {
    btn.addEventListener('click', function () { if (inApp()) window.Unity.call('swipeBack'); });
  });
  applyAppMode();
  window.addEventListener('load', function () { applyAppMode(); setTimeout(applyAppMode, 600); });
})();
