---
name: notification-blog
description: 開発者ブログ(https://motitown.com/blog/<slug>/)の記事をお知らせとして配信する。日本語・英語のお知らせ一覧にブログへのカード(サムネイル付き)を追加し、配信SQL(sql/deployed/blog-<slug>.sql)を作って push し、依頼スレッドに配信報告を返す。お知らせページ自体は作らない。「ブログをお知らせ配信して」「技術ブログを配信」「release-12-2-0 を配信」等で使用。
---

# 開発者ブログのお知らせ配信

リリースのたびに、リリーススレッド(Slack `#02-develop`)で「開発者ブログ配信したので、お知らせ配信お願いします」と依頼が来る(崔さんから)。ブログ記事はモチタウン本体のサイトにあり、このリポジトリではページを作らない。やるのは**一覧のカード・配信SQL・報告**の3つだけ。

実績: `release-12-1-0`(2026-10-15)、`release-12-2-0`(2026-10-23)

## 0. 前提

- `git pull --ff-only`(チームが main に直接 push する)
- 入力: ブログ URL(slug は `release-12-2-0` の部分)

## 1. 記事を読む

```sh
curl -sS -A 'MotitownOpsCheck/1.0' https://motitown.com/blog/<slug>/ -o <scratchpad>/blog.html   # 素の curl は WAF が弾く
```

- `<title>`、`<time datetime>`(公開日時)、目次(h2)を拾う
- 記事中の画像は `https://motitown.com/blog/assets/<slug>-*.webp`(cover / og / 各節の図)。全部落として Read で見る

## 2. カードのタイトルと日時(ユーザーに確認)

- 日本語: `<版> アップデート内容／<目玉機能を短く>`(「／」で改行)。例: `12.2.0 アップデート内容／動画学習・大辞典からの単語登録ほか`
- 英語: `v<版> Update<br/><…>`。用語はアプリの英語表記に合わせる(`~/git/motitan_app/Assets/Localization/motitan-localization-table_en.asset` を grep。例: 大辞典 = `MotiTan Dictionary`)。造語しない。`&` は `&amp;`
- 日時: ユーザーに確認する(配信する時刻。12.1.0 は 11:30、12.2.0 は記事 15:39 公開で 17:00)

## 3. サムネイル(900x270)

**記事の cover と同じ構図**で作る: 左に大きな見出し文字、右に cover の絵(モチベアと目玉機能の絵の塊)。12.2.0 で採用(`assets/blog-release-12-2-0.webp`)。

- 記事と見た目が離れた画像(節の図解など)は使わない。目玉機能が一目で分かる cover の絵を使う
- キャラはモチベアを主役に(顔が見える)。木・空などの風景で面積を埋めない
- 文字は大きく。1行目は強調(数字など)をオレンジのグラデーション、残りを紺、白縁と薄い影(cover の見出しと同じ配色)
- 元画像の文字(見出し・バッジ「12.2.0」・吹き出しの文字等)は残さない。先に Codex で文字だけ消した版を作る(新規生成・構図の組み替えはしない):
  ```sh
  codex exec --skip-git-repo-check -m gpt-6-astra -c model_reasoning_effort=high -s workspace-write -C <scratchpad> -i <scratchpad>/cover.png - <<'PROMPT'
  添付画像から、日本語の文字(縁取り・影・文字の背景の帯や吹き出し・バッジも)と「12.2.0」などの見出し文字をすべて消し、消した部分は周囲の絵柄で自然に埋めてください。キャラクター・構図・配色・画角は元画像と同じに保ち、新しい要素や文字を足さないでください。元画像と同じ寸法の PNG で ./cover-bg.png に保存してください。
  PROMPT
  ```
- 合成(右の絵は cover-bg の (x0,y0)-(x1,y1) を高さいっぱいに置く。--l1 の「|」の前がオレンジ):
  ```sh
  S=.claude/skills/notification-blog/scripts/blog-banner.py
  python3 $S cover-bg.png 740 10 1733 640 assets/blog-<slug>.webp --l1 "4,784本|の動画学習" --l2 "大辞典からの単語登録" --sub ほか --preview <scratchpad>/ja.png
  python3 $S cover-bg.png 740 10 1733 640 en/assets/blog-<slug>.webp --l1 "4,784| Videos" --l2 "MotiTan Dictionary" --sub "and more" --preview <scratchpad>/en.png
  ```
  (数値は 12.2.0 の実例。cover の絵の塊を囲む範囲を記事ごとに決める)
- プレビューを Read で見て、ユーザーに見せて確認をとる

### うまくいかなかったやり方(12.2.0 で差し戻し)

- 節の図解を切り抜く → 記事と見た目が違う
- cover を横長に切るだけ → 要素が小さい、または左が空・木だけでスカスカ
- Codex で 2000x600 に構図を組み替える → 風景が増える、絵が縦につぶれる。画像生成で構図を変えない
- 文字を小さく下寄せ → 読めない

## 4. 一覧に追加

```sh
python3 .claude/skills/notification-blog/scripts/add-blog-card.py <slug> --title "<日本語タイトル(／で改行)>" --date "2026/10/23 15:40"
```

英語一覧は `scripts/en/build_list.py` の `EXTERNAL` に `"https://motitown.com/blog/<slug>/": "<英語タイトル>"` を**先頭に**足して(過去分は残す)再生成する:

```sh
python3 scripts/en/build_list.py
git status --short en/   # en/index.html 以外が変わっていたら、それはブログと無関係(転送ページ雛形の差分など)なので git checkout -- で戻し、ユーザーに一言伝える
```

確認: `git diff` で `index.html` / `en/index.html` の変化が「新カード1枚 + 3件目への loading="lazy"」だけであること。ヘッドレス Chrome で両一覧の先頭を描画して Read で見る(`notification-list` の 4. と同じコマンド)。

## 5. 配信SQL

```sh
sed 's/<前回slug>/<slug>/' sql/deployed/blog-<前回slug>.sql > sql/deployed/blog-<slug>.sql
```

URL がブログなのでアプリの `/en/` 読み替えは効かない(英語ユーザーにも同じ記事が開く)。対象は既定でモチタン・モチスピ両方の全員(直近3ヶ月ログイン)。

## 6. push

1. 差分を見せて確認をとる(`git diff --stat` と、追加カード・EXTERNAL・SQL の中身、サムネイル2枚)
2. `git add index.html en/index.html assets/blog-<slug>.webp en/assets/blog-<slug>.webp scripts/en/build_list.py sql/deployed/blog-<slug>.sql`
3. コミット「`<版> ブログ記事: お知らせ一覧(日・英)にカードを追加、配信SQLを作成`」→ `git push origin main`
4. デプロイ後、`curl -sS -A 'MotitownOpsCheck/1.0' https://motitown.com/notification/ | grep <slug>` と `/notification/en/` で載ったことを確認

## 7. 配信と報告

- SQL の実行は配信担当(ユーザー)。`sql/deployed/blog-<slug>.sql` のパスを伝える
- 配信後、ユーザーがアプリの WebView で記事の見た目を確認したら、依頼メッセージのスレッドに返信する(前回はユーザー本人名義):
  ```
  開発者ブログをお知らせに配信しました。WebView経由の見た目は問題なしです。
  ```
  送るのはユーザーの確認がとれてから(`slack_send_message` に依頼メッセージの `thread_ts`)
