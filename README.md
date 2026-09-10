# お知らせ作成の流れ

1. 原稿作成 — `/notification-draft`
   - 伝えたい内容のメモを `{N}/brief.md` にまとめ、開発者・神谷創の人格を読み込ませた Gemini に `{N}/draft.md`(Markdown)を書かせる。Claude がレビュー
2. デザイン — figma でバナー等を作る(`draft.md` の `banner` を元に)
3. HTML作成 — `/notification-page`
   - `{N}/draft.md` を文言ソースに `{N}/index.html` を作り、アセットを配置して表示確認
4. SQL作成・公開・確認依頼 — `/notification-sql`
   - `sql/deployed/{N}.sql` を作り、git push で公開(GitHub Pages)
   - 公開urlは https://motitown-notification.astran.jp/xx/
   - git actionには、初回pushするユーザーは無視される設定がある
   - デプロイ完了を待って、Slack `#02-develop` に確認依頼を投稿(宛先・文面は `.claude/skills/notification-sql/slack.json`)
5. 返信の反映 — `/notification-review`
   - Slack スレッドの返信を読んで原稿・HTMLを修正し、再公開してスレッドに報告
6. お知らせ一覧の更新 — `/notification-list`(公開とは別タイミングで、指示されたときに実行)
   - 直下の `index.html`(一覧)の先頭にカードを追加し、`assets/notice-{N}.webp` を置いて push

スキルは `.claude/skills/` 配下。原稿の書き手の人格は `.claude/skills/notification-draft/persona.md`(Notion の履歴書の要約)。
Gemini CLI(`npm i -g @google/gemini-cli`)と認証(`GEMINI_API_KEY` または `gemini` での Google ログイン)が必要。

# 旧 STUDIO サイト (motitan-notification.astran.jp) からの移植ページ

アプリから参照していた STUDIO 製ページを、同じパスのまま静的 HTML として移植したもの。
アプリ側は `https://motitan-notification.astran.jp/...` を `https://motitown-notification.astran.jp/...` に差し替えるだけで移行できる。

| パス | 内容 |
|---|---|
| `/` | お知らせ一覧 (モチタウン右上のメールボックスから開く) |
| `/Notification/{N}/` | 旧お知らせ本文 (一覧からリンク) |
| `/information/...` | 市民リーグ・使い方ガイド・BP・ガチャ排出率などの説明 |
| `/document/legal-privacy/...`, `/document/license/` | 利用規約・プライバシーポリシー・各種法定表示・ライセンス |
| `/event/x_campaign/...` | X キャンペーン |
| `/recommend/{motitan,motispi}/` | 相互アプリ紹介 (クロスプロモ広告の遷移先) |

各ページの作り:

- `index.html` は STUDIO が描画していた DOM と、そのページに実際に当たっていた CSS ルールだけを抜き出したもの。
  `data-s-*` 属性が STUDIO 由来のスタイルのキーなので消さないこと
- 画像は `assets/` に WebP で置いてある。幅 900px 上限・品質 75 で再圧縮し、
  縦 2600px を超える 1 枚絵は 2000px ごとのタイルに分割している (先頭から順に表示され、真っ白な時間が減る)
- フォント (Noto Sans JP / Lato / Material Icons) は Google Fonts、Font Awesome は cdnjs から読む
- 折りたたみ (`button[aria-controls]`) は各ページ末尾の小さなスクリプトで `_isClose` を付け外ししている
- X のポスト埋め込みは `blockquote.twitter-tweet` + `widgets.js`
