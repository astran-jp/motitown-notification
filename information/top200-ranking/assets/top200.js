// トップ200の解説（日本語・英語で共通）
// - ?app=motispi でモチスピの言い方、?lang=zh などで学習言語の闘力の名前と旗に変える
// - #bp24h などのアンカー（または ?k=bp24h）でその種類のカードから見せ、一度だけ光らせる
// - アプリの中（window.Unity）では、最後のボタンで Web ビューを閉じる（swipeBack）
(function () {
  var root = document.documentElement;
  root.classList.add('js');
  var params = new URLSearchParams(location.search);
  var isEn = (root.lang || '').indexOf('en') === 0;

  // アプリの見分け
  if (params.get('app') === 'motispi') root.classList.add('spi');

  // 学習言語ごとの闘力の名前と旗
  var names = isEn
    ? { en: 'English Power', zh: 'Chinese Power', ko: 'Korean Power', es: 'Spanish Power', fr: 'French Power', de: 'German Power', ja: 'Japanese Power' }
    : { en: '英闘力', zh: '中闘力', ko: '韓闘力', es: '西闘力', fr: '仏闘力', de: '独闘力', ja: '日闘力' };
  var lang = (params.get('lang') || 'en').toLowerCase().split(/[-_]/)[0];
  if (!names[lang]) lang = 'en';
  document.querySelectorAll('[data-power]').forEach(function (el) { el.textContent = names[lang]; });
  document.querySelectorAll('img[data-flag]').forEach(function (img) {
    img.src = img.getAttribute('data-flag').replace('{lang}', lang);
  });
  document.querySelectorAll('.langs [data-lang]').forEach(function (el) {
    el.classList.toggle('is-mine', el.getAttribute('data-lang') === lang);
  });

  // スクロールで出てくる
  var items = document.querySelectorAll('.rv');
  function showAll() { items.forEach(function (el) { el.classList.add('is-in'); }); }
  var io = null;
  if ('IntersectionObserver' in window) {
    io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add('is-in'); io.unobserve(e.target); }
      });
    }, { rootMargin: '0px 0px -6% 0px', threshold: 0.06 });
    items.forEach(function (el) { io.observe(el); });
  } else {
    showAll();
  }

  // 「200」を数え上げる
  var count = document.querySelector('[data-count]');
  if (count && window.requestAnimationFrame) {
    var to = +count.getAttribute('data-count'), t0 = null;
    count.textContent = '0';
    var step = function (t) {
      if (!t0) t0 = t;
      var p = Math.min(1, (t - t0) / 1100);
      count.textContent = Math.round(to * (1 - Math.pow(1 - p, 3)));
      if (p < 1) requestAnimationFrame(step);
    };
    setTimeout(function () { requestAnimationFrame(step); }, 250);
  }

  // 3 つの力のメーター: まず今の力 → いちばん苦手な力が伸びると、全体がぐんと上がる
  var meter = document.querySelector('.meter');
  if (meter) {
    var spi = root.classList.contains('spi');
    var start = spi ? { vocab: 26, game: 60, talk: 82 } : { vocab: 80, game: 66, talk: 22 };
    var weak = spi ? 'vocab' : 'talk';
    var totalFill = meter.querySelector('.meter__fill');
    var timers = [];
    var play = function () {
      timers.forEach(clearTimeout); timers = [];
      meter.classList.remove('is-up');
      meter.querySelectorAll('.part').forEach(function (p) {
        var k = p.getAttribute('data-part');
        p.classList.toggle('is-weak', k === weak);
        p.querySelector('i').style.width = '0';
      });
      totalFill.style.width = '0';
      timers.push(setTimeout(function () {
        meter.querySelectorAll('.part').forEach(function (p) {
          p.querySelector('i').style.width = start[p.getAttribute('data-part')] + '%';
        });
        totalFill.style.width = '38%';
      }, 120));
      timers.push(setTimeout(function () {
        meter.querySelector('.part[data-part="' + weak + '"] i').style.width = '74%';
        totalFill.style.width = '82%';
        meter.classList.add('is-up');
      }, 1900));
    };
    var started = false;
    if ('IntersectionObserver' in window) {
      var mo = new IntersectionObserver(function (es) {
        if (es[0].isIntersecting && !started) { started = true; play(); mo.disconnect(); }
      }, { threshold: 0.4 });
      mo.observe(meter);
    } else { play(); }
    var again = meter.querySelector('.meter__replay');
    if (again) again.addEventListener('click', play);
  }

  // 吸い付くナビ: ヒーローを過ぎたら出す・いま見ているカードを白くする
  var snav = document.querySelector('.snav');
  var hero = document.querySelector('.hero');
  if (snav && hero && 'IntersectionObserver' in window) {
    new IntersectionObserver(function (es) {
      snav.classList.toggle('is-on', !es[0].isIntersecting);
    }, { threshold: 0, rootMargin: '-60px 0px 0px 0px' }).observe(hero);
    var links = {};
    snav.querySelectorAll('a').forEach(function (a) { links[a.getAttribute('href').slice(1)] = a; });
    var cur = null;
    var so = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (!e.isIntersecting) return;
        var a = links[e.target.id];
        if (!a || a === cur) return;
        if (cur) cur.classList.remove('is-cur');
        cur = a; a.classList.add('is-cur');
        var row = a.parentNode;
        row.scrollTo ? row.scrollTo({ left: a.offsetLeft - 12, behavior: 'smooth' }) : (row.scrollLeft = a.offsetLeft - 12);
      });
    }, { rootMargin: '-45% 0px -50% 0px' });
    Object.keys(links).forEach(function (id) { var el = document.getElementById(id); if (el) so.observe(el); });
  }

  // アンカー（#power-talk などの部門つきも受ける）
  var partIndex = { 'power-vocab': 1, 'power-game': 2, 'power-talk': 3 };
  function openTarget(key, jump) {
    if (!key) return;
    var id = key;
    if (partIndex[key] != null) {
      id = 'power';
      document.querySelectorAll('.parts-demo span').forEach(function (s, i) { s.classList.toggle('is-on', i === partIndex[key]); });
    }
    var el = document.getElementById(id);
    if (!el) return;
    el.querySelectorAll('.rv').forEach(function (r) { r.classList.add('is-in'); });
    if (el.classList.contains('rv')) el.classList.add('is-in');
    if (jump) {
      var html = document.documentElement, prev = html.style.scrollBehavior;
      html.style.scrollBehavior = 'auto';
      el.scrollIntoView({ block: 'start' });
      html.style.scrollBehavior = prev;
    }
    var glow = el.matches('.rk, .dropdown__item, .privacy') ? el : el.querySelector('.rk');
    if (glow) { glow.classList.remove('is-target'); void glow.offsetWidth; glow.classList.add('is-target'); }
  }
  var first = params.get('k') || decodeURIComponent(location.hash.slice(1));
  if (first) {
    openTarget(first, true);
    window.addEventListener('load', function () { openTarget(first, true); });
  }
  window.addEventListener('hashchange', function () { openTarget(decodeURIComponent(location.hash.slice(1)), false); });

  // アプリの中で開いているときだけ「ランキングへもどる」を出す
  function inApp() { return !!(window.Unity && window.Unity.call); }
  function applyAppMode() {
    var app = inApp();
    document.querySelectorAll('[data-close-app]').forEach(function (el) { el.hidden = !app; });
  }
  document.querySelectorAll('[data-close-app]').forEach(function (btn) {
    btn.addEventListener('click', function () { if (inApp()) window.Unity.call('swipeBack'); });
  });
  applyAppMode();
  window.addEventListener('load', function () { applyAppMode(); setTimeout(applyAppMode, 600); });
})();
