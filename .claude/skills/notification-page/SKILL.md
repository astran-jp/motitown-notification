---
name: notification-page
description: モチタウンお知らせのHTMLページを作る(ワークフローの第2段階。原稿作成(notification-draft) → HTML作成 → SQL作成(notification-sql))。{N}/draft.md の原稿を文言ソースとし、デザイン画像があればレイアウトの参考にして {N}/index.html を作成、アセット画像をリネーム・配置し、表示確認までを行う。「お知らせページを作って」「原稿をHTMLにして」等で使用。
---

# お知らせページ(HTML)作成

お知らせ配信ワークフローの第2段階。全体の流れは README.md も参照。

```
原稿作成 (/notification-draft)  →  HTML作成 (このスキル)  →  SQL作成・公開 (/notification-sql)
```

## 1. お知らせ番号と原稿の確認

原稿は `{N}/draft.md`(/notification-draft の成果物)。{N} は draft.md の frontmatter `number`。
draft.md が無い場合(旧来どおりデザイン画像だけ渡された場合)は、番号を「数字ディレクトリの最大値 +1」で決め、デザイン画像の文言を原稿として扱う。

```sh
ls | grep -E '^[0-9]+$' | sort -n | tail -1
```

公開URLは `https://motitown-notification.astran.jp/{N}` になる。

文言の優先順位は **draft.md > デザイン画像**。両者で文言が違う場合はユーザーに確認し、原則として draft.md に合わせる(デザイン側を直してもらう)。

## 2. HTML作成 ({N}/index.html)

直近の番号のindex.htmlを読み、共通の作りを踏襲する:

- **常にレスポンシブ実装にする**: 固定px幅のレイアウトを作らず、`max-width` + 流動単位(`clamp()` / `%` / `vw`)でどの画面幅でも破綻なくスケールさせる。320px幅で横はみ出しゼロが最低ライン(検証は下記5節)。デザイン画像への忠実はモバイル表示を基準とし、ワイド画面では中央寄せ+余白で自然に見えること
- `.wrap`: max-width:430px の流動1カラム(固定px幅にしない)。フォントは Noto Sans JP(Google Fonts)
- 配色: ネイビー `#0D4962`(本文・見出し)、日付グレー `#7C878A`
- ヘッダーは `.banner` 画像(全幅・比率維持・下方向シャドウ)。画像未配置でも崩れないようフォールバック背景を敷く
- 本文は `.content{padding:14px 22px 40px}`。`.title` / `.date` / `.lead` / `.note` のスタイルを再利用
- `<title>` は「【アプリ名】タイトル｜モチタウン」形式。`og:title` / `og:type` も設定

draft.md からの転記ルール:

- 文言は一字一句そのまま。frontmatter の `title` → `h1.title` / `<title>`、`date` → `.date`、本文の `#` 見出し以下 → `.content`
- `## 見出し` → `h2.section`、段落 → `p.lead`、`※` で始まる行 → `p.note`、`A > B > C` 形式の操作手順は `>` を `&gt;` にして1行で表示
- 冒頭の「モチタン・モチスピを開発している神谷です。」と末尾の署名「開発者 神谷創」は本文の一部として残す(署名は右寄せの `p.sign` 等で控えめに)
- 改行位置(`<br>`)はデザイン画像があればそれに合わせ、無ければ 430px 幅で自然に折り返す位置に置く
- アプリのUIモック(設定画面など)は、スクリーンショット素材が支給されるなら `<img>`、なければCSSで再現(過去例: 13はCSS再現、14〜15は画像)

## 3. ヘッダーバナーの作成(Codex で背景 → スクリプトでタイトル合成)

バナーは「絵は Codex の画像生成、文字はスクリプトで固定スタイル」の2段で作る。文字を生成モデルに任せるとフォントが毎回変わるため、タイトルは必ず `scripts/banner-title.py` で載せる。

1. 背景(文字なし)を Codex に作らせる。プロンプトの雛形は `scripts/banner-prompt.md`(タイトル文字列と内容を埋める)。Codex 側の `generate-mochitown-banner` スキル(キャラクター・背景素材付き)が使われる。
   ```sh
   sed "s/{{TITLE}}/自動再生の改善と対戦追加/; s/{{N}}/21/" .claude/skills/notification-page/scripts/banner-prompt.md \
     | codex exec -s workspace-write -i 20/assets/header.png -     # 参考に直近のバナーを添付。プロンプトは stdin で渡す(引数渡しだと stdin 待ちで止まる)
   ```
   出力は `{N}/assets/header-bg.png`(1000×380、文字なし、上端 140px の帯に顔や目立つ要素が無いこと)。
2. タイトルを合成する(フォント Noto Sans JP Black、86px、オレンジ #FF940F、白縁 8px、水色ハロー。お知らせ20のバナーを実測した固定値):
   ```sh
   python3 .claude/skills/notification-page/scripts/banner-title.py {N}/assets/header-bg.png "タイトル" {N}/assets/header.png
   ```
   タイトルは draft.md の frontmatter `banner`。1行8文字以内が目安で、長いと自動で縮む。2行にしたいときは「／」で区切る。
3. 出来た `header.png` を Read で確認する: 文字がキャラクターの顔に重なっていない、端で切れていない、誤字がない。重なるなら背景を Codex に直させる(「上端 140px の帯を空だけにして」)か、タイトルを短くする。

`header-bg.png` は再合成用に残しておく(`git add` してよい)。

## 4. アセット画像の配置とリネーム

1. `{N}/assets/` を作成し、HTMLからは意味のある名前(`header.png` 等)で参照しておく
2. 書き出し画像の配置をユーザーに依頼する(Figmaからの書き出しは「Frame 12345.png」等の機械的な名前で来ることが多い)
3. 配置されたら各画像を Read で中身を確認して役割を判別し、意味のある名前にリネーム
4. `file` コマンドで実寸法を確認し、HTMLの `src` と `width`/`height` 属性を実画像に合わせる

## 5. 表示確認

ヘッドレスChromeでレンダリングして目視確認し、スクリーンショットをユーザーに送る:

```sh
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu \
  --window-size=430,3000 --screenshot=<scratchpad>/preview.png \
  "file:///.../{N}/index.html"
```

注意: ヘッドレスChromeはウィンドウ幅を最小500pxに丸めるため、狭幅の検証は320px幅のiframeに読み込んで `document.documentElement.scrollWidth` が320のまま(横はみ出しなし)であることを確認する(`--allow-file-access-from-files` が必要)。

## 6. 美観・可読性チェックと改善

ユーザーにスクリーンショットを送る前に、レンダリング結果を自分の目で批判的に見て、以下を点検・改善する。原稿への忠実(文言)は保ちつつ、読みやすさのための構造追加は原稿・デザイン画像になくても行ってよい。

- **見出し**: 複数トピックを含むお知らせなのに区切りの見出しがないと読みづらい。トピックごとに `h2.section`(左ネイビーバー+薄い水色下線。15/index.html 参照)を入れる。見出し文言はタイトルの各トピックをそのまま使う
- **余白のリズム**: セクション間 > 段落間 > 行間 の階層が保たれているか。画像の前後が詰まって見えないか
- **文字の階層**: タイトル > 見出し > 本文 > 注記(※)のサイズ・太さの序列が一目で分かるか
- **画像**: ぼやけ(表示サイズ > 実寸)、端の見切れ、角丸・枠・影のスタイルが画像間で揃っているか
- **細部**: 横はみ出しなし、フォント適用漏れ(Noto Sans JPになっているか)、リンク・太字の色がネイビー系で統一されているか

改善を入れたら再レンダリングし、そのスクリーンショットをユーザーに送る。このとき原稿・デザイン画像にない追加(見出し等)をした場合は、その旨を一言添えて確認をとる。

## 7. 次の段階へ

ユーザーが表示を確認したら、この段階では push しない。「/notification-sql で配信用SQLを作成し公開」を案内する(push は SQL と一緒に行う)。
