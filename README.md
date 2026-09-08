# お知らせ作成の流れ

1. figmaでデザインを行う
2. claudeでhrml化を行う
3. git pushでactionが回り、公開される
 - 公開urlは https://motitown-notification.astran.jp/xx/
 - git actionには、初回pushするユーザーは無視される設定がある

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
