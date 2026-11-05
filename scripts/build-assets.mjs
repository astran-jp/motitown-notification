#!/usr/bin/env node
// リポジトリの内容を Cloudflare Worker の静的アセットとして配信できる形に組み立てる。
//   出力: dist/notification/<リポジトリと同じパス>
// お知らせのページはルート基準のリンク（/favicon.png・/Notification/127/ など）で作られているので、
// HTML の URL と転送先を /notification/ 配下に書き換えて置く。Worker のスクリプトは使わず、
// アセットだけを配信する（アセットへのリクエストは Worker の起動回数に数えられず無料・無制限）。
//
// 使い方: node scripts/build-assets.mjs   （出力先を変えるなら第 1 引数）

import { promises as fs } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT = path.resolve(process.argv[2] || path.join(ROOT, 'dist'));
const PREFIX = '/notification';

// motitown.com 自身のページを指すルート基準のパス。お知らせの一部（18・19）は /news/ のページを
// 元に作られていて、これらは motitown.com のページを読むので書き換えない
const SITE_SECTIONS = new Set(['news', 'motitan', 'motispi', 'assets', 'styles', 'recruit', 'account', 'vocabulary', 'notification', 'cdn-cgi']);

// 配信しないもの（原稿・翻訳データ・スクリプト・SQL・フォントなど）
const SKIP_DIRS = new Set(['.git', '.github', '.claude', 'node_modules', '.wrangler', 'worker', 'scripts', 'sql', 'dist', 'en-src']);
const SKIP_FILES = new Set(['.git', '.gitignore', '.assetsignore', '.DS_Store', 'CNAME', 'wrangler.toml', 'package.json', 'package-lock.json']);
const SKIP_EXT = new Set(['.md', '.json', '.py', '.pyc', '.sh', '.swift', '.sql', '.ttf', '.txt', '.toml', '.mjs']);

// 法務文書の英語本文 document/legal-privacy/<slug>/en.html は en/document/legal-privacy/<slug>/index.html を作る原稿で、
// 本文だけ（文字コードの指定も見た目も無い）なのでそのまま配信すると文字化けした下書きに見える（2026-11-03 QA 指摘）。
// 原稿は配信せず、同じ URL に英語版の正式ページへの転送ページを置く（既に共有されたリンクも正しいページに着く）
const LEGAL_EN_SOURCE = /^document\/legal-privacy\/(.+)\/en\.html$/;

function legalEnRedirect(slug) {
  const to = `/en/document/legal-privacy/${slug}/`;
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="robots" content="noindex">
<link rel="canonical" href="${to}">
<meta http-equiv="refresh" content="0; url=${to}">
<title>Redirecting…</title>
</head>
<body><p><a href="${to}">English version</a></p></body>
</html>
`;
}

// メンテナンス時間ページ（日本語・英語）の [data-maintenance-time] の中身を、schedule.js の日本時間で書き込む。
// JS が動かない端末ではこの表示が出て、JS が動けば local-time.js が端末の現地時刻に置き換える
const MAINTENANCE_DIR = path.join(ROOT, 'information', 'maintenance-time');
const MAINTENANCE_ELEMENT = /(<([a-z][a-z0-9]*)\b[^>]*\sdata-maintenance-time\b[^>]*>)[^<]*(<\/\2>)/i;
let maintenanceContext;

async function fillMaintenanceTime(html) {
  if (!MAINTENANCE_ELEMENT.test(html)) return html;
  if (!maintenanceContext) {
    maintenanceContext = vm.createContext({});
    for (const name of ['schedule.js', 'local-time.js']) {
      vm.runInContext(await fs.readFile(path.join(MAINTENANCE_DIR, name), 'utf8'), maintenanceContext, { filename: name });
    }
  }
  const lang = /<html\b[^>]*\slang=["']en/i.test(html) ? 'en' : 'ja';
  const text = maintenanceContext.MaintenanceTime.fallback(lang, maintenanceContext.MAINTENANCE_TIME);
  return html.replace(MAINTENANCE_ELEMENT, (_, open, tag, close) => open + text + close);
}

function rewriteUrl(value) {
  if (!value) return value;
  const trimmed = value.trim();
  if (trimmed.startsWith('/') && !trimmed.startsWith('//')) {
    const first = trimmed.slice(1).split(/[/?#]/, 1)[0];
    if (SITE_SECTIONS.has(first)) return value;
    return PREFIX + trimmed;
  }
  return value;
}

function rewriteSrcset(srcset) {
  return srcset
    .split(',')
    .map((part) => {
      const [url, ...rest] = part.trim().split(/\s+/);
      return [rewriteUrl(url), ...rest].join(' ');
    })
    .join(', ');
}

// <meta http-equiv="refresh" content="0; url=/Notification/78/">
function rewriteRefresh(content) {
  return content.replace(/(url\s*=\s*)([^;]+)$/i, (_, head, url) => head + rewriteUrl(url));
}

const URL_ATTRS = {
  a: ['href'], link: ['href'], area: ['href'],
  img: ['src', 'srcset', 'poster'], script: ['src', 'srcset', 'poster'], iframe: ['src', 'srcset', 'poster'],
  source: ['src', 'srcset', 'poster'], video: ['src', 'srcset', 'poster'], audio: ['src', 'srcset', 'poster'],
  track: ['src', 'srcset', 'poster'], embed: ['src', 'srcset', 'poster'],
  form: ['action'],
};

// 属性値は引用符付きだけを扱う（このサイトの HTML はすべて引用符付き。無い場合は素通しになるので検証で気付ける）
function rewriteTag(tag, name, attrs) {
  const lower = name.toLowerCase();
  if (lower === 'meta') {
    const equiv = (/\shttp-equiv\s*=\s*(["'])(.*?)\1/i.exec(attrs) || [])[2] || '';
    return tag.replace(/(\scontent\s*=\s*)(["'])(.*?)\2/i, (m, head, q, content) => {
      const next = equiv.toLowerCase() === 'refresh' ? rewriteRefresh(content) : content;
      return next === content ? m : head + q + next + q;
    });
  }
  const names = URL_ATTRS[lower];
  if (!names) return tag;
  const re = new RegExp(`(\\s(${names.join('|')})\\s*=\\s*)(["'])(.*?)\\3`, 'gi');
  return tag.replace(re, (m, head, attr, q, value) => {
    const next = attr.toLowerCase() === 'srcset' ? rewriteSrcset(value) : rewriteUrl(value);
    return next === value ? m : head + q + next + q;
  });
}

// <script>location.replace('/');</script>（/Alert/ の転送）
function rewriteScriptText(text) {
  return text.replace(
    /(location(?:\.href)?\s*=\s*|location\.(?:replace|assign)\(\s*)(['"])([^'"]*)\2/g,
    (_, head, quote, url) => head + quote + rewriteUrl(url) + quote,
  );
}

export function rewriteHtml(html) {
  let out = html.replace(/<(a|link|area|img|script|iframe|source|video|audio|track|embed|form|meta)\b([^>]*)>/gi, (tag, name, attrs) => rewriteTag(tag, name, attrs));
  out = out.replace(/(<script\b[^>]*>)([\s\S]*?)(<\/script>)/gi, (_, open, body, close) => open + rewriteScriptText(body) + close);
  return out;
}

async function walk(dir, rel, files) {
  for (const entry of await fs.readdir(dir, { withFileTypes: true })) {
    const relPath = rel ? `${rel}/${entry.name}` : entry.name;
    if (entry.isDirectory()) {
      if (SKIP_DIRS.has(entry.name)) continue;
      await walk(path.join(dir, entry.name), relPath, files);
    } else if (entry.isFile()) {
      if (SKIP_FILES.has(entry.name) || SKIP_EXT.has(path.extname(entry.name).toLowerCase())) continue;
      files.push(relPath);
    }
  }
  return files;
}

async function main() {
  const files = await walk(ROOT, '', []);
  await fs.rm(OUT, { recursive: true, force: true });
  let html = 0;
  for (const rel of files) {
    const dest = path.join(OUT, 'notification', rel);
    await fs.mkdir(path.dirname(dest), { recursive: true });
    const legalEn = LEGAL_EN_SOURCE.exec(rel);
    if (legalEn) {
      await fs.writeFile(dest, rewriteHtml(legalEnRedirect(legalEn[1])));
      html++;
    } else if (rel.toLowerCase().endsWith('.html')) {
      const src = await fs.readFile(path.join(ROOT, rel), 'utf8');
      await fs.writeFile(dest, rewriteHtml(await fillMaintenanceTime(src)));
      html++;
    } else {
      await fs.copyFile(path.join(ROOT, rel), dest);
    }
  }
  console.log(`${files.length} files (${html} html) -> ${path.relative(ROOT, OUT)}/notification/`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((e) => { console.error(e); process.exit(1); });
}
