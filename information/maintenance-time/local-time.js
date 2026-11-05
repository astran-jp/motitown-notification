// メンテナンス時間（schedule.js の MAINTENANCE_TIME）を、ページを開いた端末の現地時刻にして
// [data-maintenance-time] の要素に表示する。<html lang="en"> のページは英語、それ以外は日本語で出す。
//   英語:   Wed, Nov 11, 9:00 PM – 10:00 PM PST / Wed, Nov 11, 11:00 PM – Thu, Nov 12, 1:00 AM PST
//   日本語: 11/12(木) 14:00〜15:00（日本時間の端末は何も付けない）/ 11/11(水) 23:00〜11/12(木) 01:00（PST）
// タイムゾーンの略称は Intl.DateTimeFormat('en-US', {timeZoneName: 'short'}) の値。
// 変換できない環境では HTML に書かれた日本時間の表示がそのまま残る。
// scripts/build-assets.mjs はこのファイルの fallback() で、JS が動かない端末向けの日本時間の表示を HTML に書き込む。
(function (root) {
  function partsOf(date, locale, options, required) {
    var out = {};
    new Intl.DateTimeFormat(locale, options).formatToParts(date).forEach(function (p) {
      out[p.type] = p.value;
    });
    required.forEach(function (key) {
      if (!out[key]) throw new Error('missing ' + key);
    });
    return out;
  }

  function zoneName(date, timeZone) {
    return partsOf(date, 'en-US', { timeZone: timeZone, timeZoneName: 'short' }, ['timeZoneName']).timeZoneName;
  }

  function offsetMinutes(date, timeZone) {
    var p = partsOf(date, 'en-US', {
      timeZone: timeZone, hour12: false,
      year: 'numeric', month: 'numeric', day: 'numeric', hour: 'numeric', minute: 'numeric', second: 'numeric',
    }, ['year', 'month', 'day', 'hour', 'minute', 'second']);
    var wall = Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour % 24, +p.minute, +p.second);
    return Math.round((wall - Math.floor(date.getTime() / 1000) * 1000) / 60000);
  }

  function isJapanTime(date, timeZone) {
    var zone = timeZone || new Intl.DateTimeFormat().resolvedOptions().timeZone;
    return (zone === 'Asia/Tokyo' || zone === 'Japan') && offsetMinutes(date, timeZone) === 540;
  }

  function pad2(value) {
    var n = +value % 24;
    return (n < 10 ? '0' : '') + n;
  }

  function sameDay(a, b) {
    return a.year === b.year && a.month === b.month && a.day === b.day;
  }

  function formatEn(start, end, timeZone, label) {
    var options = {
      timeZone: timeZone, hour12: true,
      year: 'numeric', weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
    };
    var keys = ['year', 'weekday', 'month', 'day', 'hour', 'minute', 'dayPeriod'];
    var s = partsOf(start, 'en-US', options, keys);
    var e = partsOf(end, 'en-US', options, keys);
    var day = function (p) { return p.weekday + ', ' + p.month + ' ' + p.day + ', '; };
    var time = function (p) { return p.hour + ':' + p.minute + ' ' + p.dayPeriod; };
    var zone = label !== undefined ? label : zoneName(start, timeZone);
    return day(s) + time(s) + ' – ' + (sameDay(s, e) ? '' : day(e)) + time(e) + ' ' + zone;
  }

  function formatJa(start, end, timeZone, label) {
    var options = {
      timeZone: timeZone, hour12: false,
      year: 'numeric', weekday: 'short', month: 'numeric', day: 'numeric', hour: 'numeric', minute: '2-digit',
    };
    var keys = ['year', 'weekday', 'month', 'day', 'hour', 'minute'];
    var s = partsOf(start, 'ja-JP', options, keys);
    var e = partsOf(end, 'ja-JP', options, keys);
    var day = function (p) { return p.month + '/' + p.day + '(' + p.weekday + ') '; };
    var time = function (p) { return pad2(p.hour) + ':' + p.minute; };
    var zone = label !== undefined ? label : (isJapanTime(start, timeZone) ? '' : zoneName(start, timeZone));
    return day(s) + time(s) + '〜' + (sameDay(s, e) ? '' : day(e)) + time(e) + (zone ? '（' + zone + '）' : '');
  }

  // timeZone を省くと端末のタイムゾーン。label を渡すとタイムゾーンの表示をその文字列にする
  function format(lang, startIso, endIso, timeZone, label) {
    var start = new Date(startIso);
    var end = new Date(endIso);
    if (isNaN(start.getTime()) || isNaN(end.getTime())) throw new Error('invalid MAINTENANCE_TIME');
    return lang === 'en' ? formatEn(start, end, timeZone, label) : formatJa(start, end, timeZone, label);
  }

  // 組み立て時に使う。時差の付いていない値は端末ごとに解釈が変わるので失敗させる
  function fallback(lang, schedule) {
    [schedule.start, schedule.end].forEach(function (value) {
      if (!/([+-]\d\d:\d\d|Z)$/.test(value)) throw new Error('MAINTENANCE_TIME needs +09:00: ' + value);
    });
    return format(lang, schedule.start, schedule.end, 'Asia/Tokyo', lang === 'en' ? 'JST' : '日本時間');
  }

  root.MaintenanceTime = { format: format, fallback: fallback };

  var doc = root.document;
  var schedule = root.MAINTENANCE_TIME;
  if (!doc || !schedule) return;
  var el = doc.querySelector('[data-maintenance-time]');
  if (!el) return;
  var lang = (doc.documentElement.lang || '').slice(0, 2).toLowerCase() === 'en' ? 'en' : 'ja';
  try {
    el.textContent = format(lang, schedule.start, schedule.end);
  } catch (e) {
    // HTML に書かれた日本時間の表示を残す
  }
})(this);
