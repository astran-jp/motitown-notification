// motitown.com/notification/* を、この Worker に同梱した静的アセット（このリポジトリの内容）から配信する。
// お知らせのページはルート基準のリンク（/favicon.png・/Notification/127/ など）で作られているので、
// HTML とリダイレクト先を /notification/ 配下に書き換えて返す。
//
// 以前は GitHub Pages（motitown-notification.astran.jp）を中継していた。旧ホストの絶対 URL は
// 移行期間中も HTML に残り得るので、書き換え対象に含めたままにしている。

const PREFIX = '/notification';
const PUBLIC_ORIGIN = 'https://motitown.com';

// motitown.com 自身のページを指すルート基準のパス。お知らせの一部（18・19）は /news/ のページを
// 元に作られていて、これらは motitown.com のページを読むので書き換えない
const SITE_SECTIONS = new Set(['news', 'motitan', 'motispi', 'assets', 'styles', 'recruit', 'account', 'vocabulary', 'notification', 'cdn-cgi']);

const LEGACY_ORIGIN_RE = /^https?:\/\/motitown-notification\.astran\.jp(?=[/?#]|$)/i;

function rewriteUrl(value) {
  if (!value) return value;
  const trimmed = value.trim();
  if (LEGACY_ORIGIN_RE.test(trimmed)) {
    return trimmed.replace(LEGACY_ORIGIN_RE, PUBLIC_ORIGIN + PREFIX);
  }
  if (trimmed.startsWith('/') && !trimmed.startsWith('//')) {
    const first = trimmed.slice(1).split(/[/?#]/, 1)[0];
    if (SITE_SECTIONS.has(first)) return value;
    return PREFIX + trimmed;
  }
  return value;
}

// <meta http-equiv="refresh" content="0; url=/Notification/78/">
function rewriteRefresh(content) {
  return content.replace(/(url\s*=\s*)([^;]+)$/i, (_, head, url) => head + rewriteUrl(url));
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

class AttributeRewriter {
  constructor(attributes) {
    this.attributes = attributes;
  }
  element(element) {
    for (const name of this.attributes) {
      const value = element.getAttribute(name);
      if (value === null) continue;
      const next = name === 'srcset' ? rewriteSrcset(value) : rewriteUrl(value);
      if (next !== value) element.setAttribute(name, next);
    }
  }
}

class MetaRewriter {
  element(element) {
    const equiv = (element.getAttribute('http-equiv') || '').toLowerCase();
    const content = element.getAttribute('content');
    if (content === null) return;
    if (equiv === 'refresh') {
      element.setAttribute('content', rewriteRefresh(content));
    } else if (LEGACY_ORIGIN_RE.test(content.trim())) {
      element.setAttribute('content', rewriteUrl(content));
    }
  }
}

// <script>location.replace('/');</script>（/Alert/ の転送）
class ScriptRewriter {
  constructor() {
    this.buffer = '';
  }
  text(chunk) {
    this.buffer += chunk.text;
    if (!chunk.lastInTextNode) {
      chunk.remove();
      return;
    }
    const rewritten = this.buffer.replace(
      /(location(?:\.href)?\s*=\s*|location\.(?:replace|assign)\(\s*)(['"])([^'"]*)\2/g,
      (_, head, quote, url) => head + quote + rewriteUrl(url) + quote,
    );
    this.buffer = '';
    chunk.replace(rewritten, { html: true });
  }
}

function rewriteHtml(response) {
  return new HTMLRewriter()
    .on('a, link, area', new AttributeRewriter(['href']))
    .on('img, script, iframe, source, video, audio, track, embed', new AttributeRewriter(['src', 'srcset', 'poster']))
    .on('form', new AttributeRewriter(['action']))
    .on('meta', new MetaRewriter())
    .on('script', new ScriptRewriter())
    .transform(response);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === PREFIX) {
      return Response.redirect(`${url.origin}${PREFIX}/${url.search}`, 301);
    }
    if (!url.pathname.startsWith(PREFIX + '/')) {
      return fetch(request);
    }
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      return new Response('Method Not Allowed', { status: 405, headers: { Allow: 'GET, HEAD' } });
    }

    // アセットはリポジトリのルート基準（/Notification/1/ など）で置かれているので /notification を外して引く
    const assetUrl = new URL(url);
    assetUrl.pathname = url.pathname.slice(PREFIX.length);
    const asset = await env.ASSETS.fetch(new Request(assetUrl, request));

    const responseHeaders = new Headers(asset.headers);
    const location = responseHeaders.get('location');
    if (location) {
      // 末尾スラッシュ補完などのリダイレクト先を /notification/ 配下に戻す
      const absolute = new URL(location, assetUrl);
      if (absolute.origin === assetUrl.origin) {
        responseHeaders.set('location', PREFIX + absolute.pathname + absolute.search + absolute.hash);
      }
    }
    // 末尾スラッシュ補完はアセット配信が 307 で返すが、GitHub Pages 時代と同じ恒久リダイレクト（301）に揃える
    const status = asset.status === 307 && location ? 301 : asset.status;

    const contentType = responseHeaders.get('content-type') || '';
    const response = new Response(asset.body, { status, statusText: status === asset.status ? asset.statusText : 'Moved Permanently', headers: responseHeaders });
    if (request.method === 'GET' && asset.status === 200 && contentType.includes('text/html')) {
      response.headers.delete('content-length');
      response.headers.delete('etag');
      return rewriteHtml(response);
    }
    return response;
  },
};
