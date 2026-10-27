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

# note 投稿キャンペーン (`/event/note_campaign/`)

MT-6124。ホームのイベントバナーから、アプリがヘッダーなしの全画面 WebView で開くページ
(`URLManager.LinkNoteCampaign()`、`PopupWebViewFullScreen` の `hideHeader`)。デザインの正本は
Figma「モチタンUI」の `20260930_noteキャンペーン_…_完成版` セクション (node `88901:149780`)。

| パス | 内容 |
|---|---|
| `/event/note_campaign/` | イベント詳細 (KV・限定キャラ 5 体・やること・事例・注意事項・下部固定の CTA)。キャラをタップするとキャラ詳細ポップ |
| `/event/note_campaign/report/` | 投稿の報告フォーム (入力 → 完了、エラー文言 10 種) |
| `/en/event/note_campaign/…` | 英語版は無し。日本語ページへの転送スタブ (クエリを引き継ぐ) |

- アプリはログイン済みの通信で motitan-api からトークンを受け取り、`?token=<トークン>` を付けて開く。
  どちらのページも読んだ後に sessionStorage (`note_campaign_token`) に控えて、アドレスからクエリを消す。
  イベント詳細 → 報告フォームへは sessionStorage で引き継ぐ (使えない時だけリンクのクエリで渡す)。
  トークンはリンク先・解析・ログ・画面に出さない
- トークンが無い時 (アプリ外から開いた、アプリがトークンを取れなかった): イベント詳細は普通に読める。
  報告フォームは入力・送信ができない状態になり、アプリのバナーから開き直す案内を出す
- アプリとの橋渡しは `Unity.call()`: 左上の戻る = `swipeBack` (WebView を閉じる)、note へのリンク = `openURL:<url>`
  (note アプリ / ブラウザで外部に開く。アプリ側が受けるまではアプリ内では何も起きない)。アプリ外では通常のリンク
- 報告フォームは motitan-api (`https://motitan-api.astran.dev`、別オリジン) を直接呼ぶ。
  motitown.com の `/contact/api.php` は使わない (CSRF トークン・受付番号も無い)。
  リクエストはどちらも `{token, url}`、`Content-Type` は `application/json` ちょうど (`; charset=…` を付けない):
  - `POST /note-campaign/checks` — URL を貼って入力が 0.4 秒止まった時の判定。`{ok:true}` か `{ok:false, reason}`
  - `POST /note-campaign/reports` — 送信時。判定を通ればその場で限定キャラを 1 体付与する。
    `{ok:true, num_reports}` か `{ok:false, reason, num_reports}`。完了画面の「報告済み n/5」は `num_reports` が取れた時だけ出す
  - 判定 NG は HTTP 200 + `reason`。ページ側は `not_note` / `reported` / `not_public` / `official` / `too_short` /
    `no_tag` / `daily_limit_reached` / `limit_reached` / `completed` / `invalid_token` の 10 種の文言に対応する
  - MT-6312 の条件は、1アカウント内で **note 記事の投稿日が重複しないこと**。
    報告を受理した日で制限するものではなく、投稿日が異なる記事は同じ日にまとめて報告できる。
    `checks` / `reports` が `{ok:false, reason:"daily_limit_reached"}` を返すと「同じ投稿日の記事は1記事までが対象です」と表示する。
    API の reason 名は維持し、`limit_reached` は従来どおり累計 5 記事の上限を表す。
    この変更は説明・表示文言のみ。マージ済みの motitan-api PR #4100 は報告受理日で判定するため、
    投稿日の重複を判定するバックエンド修正を別途行う必要がある
  - HTTP が 200 以外・通信失敗・応答が読めない・知らない `reason` は、固定の「時間をおいてもう一度お試しください」を出す。
    サーバーのエラー本文 (`{message}`) は画面に出さない
- API の URL は本番だけ (報告フォームの定数 `API`)。環境の切り替えは無い。dev / stg のアプリが発行したトークンは
  本番 API では `invalid_token` になるので、アプリ → ページ → API の通し確認は、本番に API を出した後、
  本番向けのアプリでしかできない。それまでは、ローカルで静的サーバーを立て、定数 `API` を手元の模擬サーバーに向けて確かめる
- 登場とスクロール出現のアニメーションは Figma の「🎬 MI仕様」カードの数値どおり。「視差を減らす」ではフェードのみ
- 画像は Figma の画像フィルをそのまま WebP にしたもの (`event/note_campaign/assets/`)

# 法務文書 (`/document/legal-privacy/…`) の正本

利用規約・プライバシーポリシー・特定商取引法・資金決済法・Apple/Google 連携・Astran プライバシーポリシー・Astran 外部送信ポリシー・ライセンスの**正本はこのリポジトリの HTML**（2026-09-30 裁定、2026-10-01 に会社全体の 2 本も移植して Notion 管理を終了）。Notion「外部公開ページ」は写しであり、編集しても公開されない。

| ファイル | 役割 |
|---|---|
| `document/legal-privacy/<slug>/index.html` | 日本語（正本）。改定はここを直す |
| `document/legal-privacy/<slug>/en.html` | 英語本文（正本）。日本語を直したら同じコミットで追従させる |
| `en/document/legal-privacy/<slug>/index.html` | 生成物。`python3 scripts/en/build_doc.py document/legal-privacy/<slug>` で作り直す。手で編集しない |

| slug | 文書 | アプリから参照 |
|---|---|---|
| `riyokiyaku` / `riyokiyaku/motispi` | 利用規約（モチタン／モチスピ） | ○ |
| `motitan` / `motispi` | プライバシーポリシー（モチタン／モチスピ） | ○ |
| `tokuteisyoho` / `shikinkessaiho` | 特定商取引法・資金決済法に基づく表示 | ○ |
| `data-usage` | Apple/Google 連携により取得する個人情報 | ○ |
| `astran-privacy` / `external-transmission` | Astran プライバシーポリシー・外部送信ポリシー（会社全体。astran.jp のフッターのリンク先） | — |
| `../license` | ライセンス | ○ |

- 変更の出し方: 差分を岡島が承認 → 日本語と英語を同じ PR で直す → マージ後に公開 URL を実機で確認。法務文書フォルダへの直接 push はしない
- モチスピの規約・プラポリの英訳はモチタンの英訳と同じ訳文を土台にし、モチスピ固有の箇所だけ差し替える（改定を 1 回訳せば両方に反映できる）
- 改定したら末尾の【YYYY年M月D日改定】と英語の [Revised …] を両方更新する
- 公開中ページの一覧は `python3 scripts/public_pages.py --html <out.html>` で生成する（分類・英語版の有無・改定日・アプリ参照）

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
Worker のスクリプトは無く、アセットだけを配信するので、リクエストは Worker の起動回数に数えられない
(無料・無制限。Free プランの 1 日 10 万件制限にも当たらない。2026-09-24 に中継 Worker がこの制限に達して 429 になった)。

- main への push で GitHub Actions (`.github/workflows/deploy-cloudflare.yml`) が `node scripts/build-assets.mjs` → `wrangler deploy` を実行する
- `scripts/build-assets.mjs` はリポジトリの内容を `dist/notification/` にコピーし、HTML のルート基準リンク
  (`/favicon.png`・`/Notification/127/` など)・`<meta http-equiv="refresh">`・`location.replace()` の転送先を
  `/notification/` 配下に書き換える (以前の中継 Worker が実行時にやっていた書き換えを、組み立て時に済ませる)。
  motitown.com 自身を指す `/news/` `/motitan/` などは書き換えない。旧ホストの絶対 URL も `motitown.com/notification/` に寄せる
- 原稿 (`*.md`)・翻訳データ (`*.json`)・`scripts/`・`sql/`・`.claude/`・フォントなどは組み立て時に除外する。
  配信されるのは HTML・画像・CSS・favicon だけ。新しい種類のファイルを置いたら `build-assets.mjs` の除外リストを見直す
- 設定は `wrangler.toml`。Worker 名は以前の中継 Worker (`astran-jp/motitown-notification-proxy`) と同じ
  `motitown-notification-proxy` にしてある。同名で deploy すると中継版がその場で置き換わり、ルートを付け替えずに済む
- 必要な Secrets (リポジトリの Settings → Secrets and variables → Actions):
  `CLOUDFLARE_API_TOKEN` (Workers Scripts:Edit と Zone motitown.com の Workers Routes:Edit) と
  `CLOUDFLARE_ACCOUNT_ID` (motitown.com ゾーンがあるアカウント)。未設定のあいだは deploy をスキップして成功終了する
- 手元で確認するときは `npm install` → `npm run dev` → `http://127.0.0.1:8787/notification/`。
  本番の確認は `curl -A 'MotitownOpsCheck/1.0' https://motitown.com/notification/...` (素の curl は WAF が 403 にする)
- motitown.com の WAF カスタムルール・Bot Fight Mode・キャッシュルールは触らない (2026-08 に Googlebot を全ブロックした事故あり)

## 旧ホスト motitown-notification.astran.jp

以前は GitHub Pages (`motitown-notification.astran.jp`) で公開し、中継 Worker で `motitown.com/notification/` に見せていた。
2026-10-07 に静的アセット配信へ切り替え、2026-10-08 に GitHub Pages を削除し、続けてムームードメインの CNAME レコードも削除した。
旧ホストの URL はどこにも転送されないので、ページ・SQL・スクリプトには `https://motitown.com/notification/` を書く。
