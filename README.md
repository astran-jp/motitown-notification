# お知らせ作成の流れ

1. 原稿作成 — `/notification-draft`
   - 伝えたい内容のメモを `{N}/brief.md` にまとめ、開発者・神谷創の人格を読み込ませた Gemini に `{N}/draft.md`(Markdown)を書かせる。Claude がレビュー
2. デザイン — figma でバナー等を作る(`draft.md` の `banner` を元に)
3. HTML作成 — `/notification-page`
   - `{N}/draft.md` を文言ソースに `{N}/index.html` を作り、アセットを配置して表示確認
   - 続けて英語版も作る(`/notification-page` の中で `/notification-en` の手順を実行): `{N}/en.json` に英訳、`en/{N}/index.html`・英語バナー・英語一覧 `en/index.html` を生成(公開 URL は `/en/{N}/`、一覧は `/en/`)。`/notification-sql` は英語版が無いと公開しない
4. SQL作成・公開・確認依頼 — `/notification-sql`
   - `sql/deployed/{N}.sql` を作り、git push で公開(main への push で Cloudflare Worker に deploy される。下の「公開の仕組み」を参照)
   - 公開urlは https://motitown.com/notification/xx/
   - git actionには、初回pushするユーザーは無視される設定がある
   - デプロイ完了を待って、Slack `#02-develop` に確認依頼を投稿(宛先・文面は `.claude/skills/notification-sql/slack.json`)
5. 返信の反映 — `/notification-review`
   - Slack スレッドの返信を読んで原稿・HTMLを修正し、再公開してスレッドに報告
6. お知らせ一覧の更新 — `/notification-list`(公開とは別タイミングで、指示されたときに実行)
   - 直下の `index.html`(一覧)の先頭にカードを追加し、`assets/notice-{N}.webp` を置いて push

スキルは `.claude/skills/` 配下。英語版の生成スクリプトは `scripts/en/`(extract.py → en.json → build.py / build_list.py)。原稿の書き手の人格は `.claude/skills/notification-draft/persona.md`(Notion の履歴書の要約)。
Gemini CLI(`npm i -g @google/gemini-cli`)と認証(`GEMINI_API_KEY` または `gemini` での Google ログイン)が必要。

# 旧 STUDIO サイト (motitan-notification.astran.jp) からの移植ページ

アプリから参照していた STUDIO 製ページを、同じパスのまま静的 HTML として移植したもの。
アプリ側は `https://motitan-notification.astran.jp/...` を差し替えるだけで移行できる。差し替え先は
`https://motitown.com/notification/...`(Cloudflare Worker がこのリポジトリの内容を同じパスで配信している)。
アプリが表示言語に合わせて `/en/` を付けるのはこのホストの URL だけなので、配信する URL はこちらを使う。

| パス | 内容 |
|---|---|
| `/` | お知らせ一覧 (モチタウン右上のメールボックスから開く) |
| `/Notification/{N}/` | 旧お知らせ本文 (一覧からリンク) |
| `/information/...` | 市民リーグ・使い方ガイド・BP・ガチャ排出率などの説明 |
| `/document/legal-privacy/...`, `/document/license/` | 利用規約・プライバシーポリシー・各種法定表示・ライセンス |
| `/event/x_campaign/...` | X キャンペーン |
| `/recommend/{motitan,motispi}/` | 相互アプリ紹介 (クロスプロモ広告の遷移先) |

各ページの作り:

- 全ページの `<head>` に `<meta charset="utf-8">` の直後で `<meta name="robots" content="noindex">` を置き、検索結果に出さない
  (MT-6141。旧ページが「株式会社Astran / モチタン」として検索に出ていた)。新しいページ・転送スタブ・英語版にも必ず付ける
- `index.html` は STUDIO が描画していた DOM と、そのページに実際に当たっていた CSS ルールだけを抜き出したもの。
  `data-s-*` 属性が STUDIO 由来のスタイルのキーなので消さないこと
- 画像は `assets/` に WebP で置いてある。幅 900px 上限・品質 75 で再圧縮し、
  縦 2600px を超える 1 枚絵は 2000px ごとのタイルに分割している (先頭から順に表示され、真っ白な時間が減る)
- フォント (Noto Sans JP / Lato / Material Icons) は Google Fonts、Font Awesome は cdnjs から読む
- 折りたたみ (`button[aria-controls]`) は各ページ末尾の小さなスクリプトで `_isClose` を付け外ししている
- X のポスト埋め込みは `blockquote.twitter-tweet` + `widgets.js`

# ストアへの案内ページ (`/store/`)

強制アップデートや相互送客でアプリが開く「アプリ一覧」ページ。旧ページは
`astran-jp/store-links` (`motitan-store.astran.jp`) と `astran-jp/motispi-store-links`
(`motispi-store.astran.jp`) の 2 リポジトリに分かれていたので、URL も 1 対 1 で移した。

| 公開 URL | 移植元 |
|---|---|
| `https://motitown.com/notification/store/motitan/` | `astran-jp/store-links` |
| `https://motitown.com/notification/store/motispi/` | `astran-jp/motispi-store-links` |
| `https://motitown.com/notification/en/store/{motitan,motispi}/` | 英語版 (MT-6144。アプリは表示言語が英語のとき `/en/` 付きで開く) |

- 移植時点で 2 つの `index.html` はバイト一致（どちらもモチタン・モチスピ両方を並べる）。
  片方だけ直すと差が出るので、内容を変えるときは 2 枚とも直すこと
- `?os=android` / `?os=ios` で表示を切り替える。クエリが無いときは UA で判定し、Android 以外は iOS 表示
- App Store / Google Play への直リンクと、Play のフィーチャーグラフィック・App Store のアイコン
  (iTunes Lookup API) を読むだけで、ルート基準のリンクは持たない
- 英語版は `en/store/{motitan,motispi}/index.html`。日本語版と同じ HTML の文言だけを英語にしたもので、
  App Store のリンクは国コード無し (`apps.apple.com/app/id…`) にしてユーザーのストアフロントで開く。
  日本語版の構造を変えたら英語版 2 枚も同じように直す (計 4 枚が同じ構造)
- 旧リポジトリの `android.html` と `icon.png` はどのページからも参照されていないので移していない

# 公開の仕組み (Cloudflare Workers)

`https://motitown.com/notification/*` は、このリポジトリの内容を静的アセットとして同梱した Cloudflare Worker が配信する。

- main への push で GitHub Actions (`.github/workflows/deploy-cloudflare.yml`) が `wrangler deploy` を実行する。
  リポジトリのルートがそのままアセットになり、`worker/index.js` が `/notification` を外してアセットを引き、
  HTML のルート基準リンク (`/favicon.png`・`/Notification/127/` など) と転送先を `/notification/` 配下に書き換えて返す
- 原稿 (`*.md`)・翻訳データ (`*.json`)・`scripts/`・`sql/`・`.claude/`・フォントなどは `.assetsignore` で配信対象から外している。
  配信されるのは HTML・画像・CSS・favicon だけ。新しい種類のファイルを置いたら `.assetsignore` を見直す
- 設定は `wrangler.toml`。Worker 名は以前の中継 Worker (`astran-jp/motitown-notification-proxy`) と同じ
  `motitown-notification-proxy` にしてある。同名で deploy すると中継版がその場で置き換わり、ルートを付け替えずに済む
- 必要な Secrets (リポジトリの Settings → Secrets and variables → Actions):
  `CLOUDFLARE_API_TOKEN` (Workers Scripts:Edit と Zone motitown.com の Workers Routes:Edit) と
  `CLOUDFLARE_ACCOUNT_ID` (motitown.com ゾーンがあるアカウント)。未設定のあいだは deploy をスキップして成功終了する
- 手元で確認するときは `npm install` → `npx wrangler dev` → `http://127.0.0.1:8787/notification/`。
  本番の確認は `curl -A 'MotitownOpsCheck/1.0' https://motitown.com/notification/...` (素の curl は WAF が 403 にする)
- motitown.com の WAF カスタムルール・Bot Fight Mode・キャッシュルールは触らない (2026-08 に Googlebot を全ブロックした事故あり)

## GitHub Pages (motitown-notification.astran.jp) からの切り替え手順

2026-09-24 時点では GitHub Pages (`motitown-notification.astran.jp`) が公開先で、中継 Worker がそれを `motitown.com/notification/` に見せている。
Worker の静的アセット配信に切り替える手順 (上から順に。1〜3 は本番に影響しない):

1. 上記 Secrets を登録する
2. Actions の「Deploy to Cloudflare Workers」を手動実行 (workflow_dispatch) するか main に push する。
   中継 Worker が同名で置き換わり、この時点から `motitown.com/notification/` はリポジトリの内容を直接返す
3. `motitown.com/notification/`・`/Notification/1/`・`/en/`・`/Alert/`・`/en/store/motitan/` などを確認する
4. 旧ホストを参照している場所を motitown.com に寄せる: 配信済み `notices` 行の URL (SQL の REPLACE)、
   App Store Connect / Google Play Console に登録したプライバシーポリシー等の URL、Slack / Notion の固定リンク
5. 旧アプリ (v12.0.0 未満) は規約・お知らせを旧ホストで開くので、強制アップデートで揃うまでは旧ホストを転送用として残す
6. 残す必要が無くなったら: GitHub Pages のカスタムドメインを外し `CNAME` を削除、ムームードメインの `motitown-notification` CNAME レコードを削除、
   `astran-jp/motitown-notification-proxy` リポジトリをアーカイブ、`worker/index.js` の旧ホスト書き換え (`LEGACY_ORIGIN_RE`) を外す
