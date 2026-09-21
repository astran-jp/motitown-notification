---
name: notification-en
description: モチタウンお知らせの英語版を作る(ワークフローの第2.5段階。HTML作成(notification-page) → 英語版(このスキル) → SQL作成・公開(notification-sql))。{N}/index.html から文言を抜いて {N}/en.json に英訳を書き、en/{N}/index.html と英語バナー、英語一覧 en/index.html を生成する。旧お知らせ(Notification/{N})の英語化にも使う。「英語版を作って」「22を英語に」「英語一覧を更新して」等で使用。
---

# お知らせ英語版の作成

日本語の `{N}/index.html` が完成した後に行う(通常は `/notification-page` の 7 節から続けて実行され、ユーザーが別に呼ぶ必要はない。旧お知らせの英語化や英語版だけの直しでは単独で使う)。英語版は同じ番号で `en/{N}/`(旧お知らせは `en/Notification/{N}/`)に置き、公開 URL は `https://motitown-notification.astran.jp/en/{N}/`、一覧は `https://motitown-notification.astran.jp/en/`。アプリは表示言語が英語のユーザーに、配信された `https://motitown.com/notification/{N}` を `/en/{N}` に読み替えてこの内容を開く(配信 SQL は言語で出し分けない)。

```
原稿作成 → HTML作成 (/notification-page) → 英語版 (このスキル) → SQL作成・公開 (/notification-sql)
```

翻訳は毎回このスキルの中で Claude が行う(外部 API・モデルは使わない)。`{N}/en.json` が訳の記録で、日本語 HTML を直しても extract をやり直せば既訳は残る。

## 1. 文言の抽出

```sh
python3 scripts/en/extract.py {N}            # 旧お知らせは Notification/{N}
```

`{N}/en.json` ができる。`title`(`<title>`)、`list_title`(一覧カードの文言。一覧に載っていれば)、`banner`(draft.md の banner。ヘッダー画像の文字)、`segments`(本文ブロックと alt 等)の `en` が空で入る。

## 2. 翻訳(en.json の en を埋める)

- **用語**: 固有名詞は仕様裁定スプレッドシート「固有名詞」タブ(`1TYZUbeBgbGzD-YZHPXdkJklLu_0Z6I0zO03QJ1wzXUU`)と、兄弟 clone `../app-localization/locales/en-US/glossary.tsv` に従う(Motitown / Motitan / Motispi / Motibear / キャラクター名 / 機能名)。アプリの画面名・ボタン名は英語版アプリの文言に合わせる
- **書き手**: 日本語と同じ人格(開発者 神谷 創)。冒頭「モチタン・モチスピを開発している神谷です。」→ `Hi, this is Kamiya, the developer of Motitan and Motispi.`、署名「開発者 神谷創」→ `Sou Kamiya, Developer`。モチベアが語る旧お知らせはモチベアの声のまま(`It's Motibear!`)
- **文体**: 直訳しない。英語ユーザーが読んで自然な告知文にする(意図第一。文の分割・結合は可)。`※` の注記は `* ` で始める。バージョン表記・日時・数値はそのまま
- **タグ**: `ja` に含まれる `<br>` `<strong>` `<a …>` は `en` でも同じ位置・同じ個数で残す(`<br>` は英語で改行が不自然なら位置を変えてよいが個数は保つ)
- **title**: `【アプリ名】タイトル｜モチタウン` → `Title | Motitown`(アプリ名の角括弧は付けない)
- **list_title**: 一覧カードは 2 行に収まる短さ(目安 45 字以内、文頭だけ大文字)
- **banner**: ヘッダー画像の文字。1〜3 語(例 `Pinch to Zoom`)。長いと自動で縮むが 900px を超えない語数にする
- 訳し終えたら未訳 0 を確認する: `python3 scripts/en/extract.py {N}`(再実行しても既訳は消えない)

## 3. 英語バナー(header-bg.png がある場合)

`{N}/assets/header-bg.png`(文字なし背景)があれば、英語タイトルを合成して `en/{N}/header.png` を作る。build.py は `en/{N}/` に同名ファイルがあると日本語版の `assets/header.png` の代わりにそれを使う。

```sh
mkdir -p en/{N}
python3 .claude/skills/notification-page/scripts/banner-title.py {N}/assets/header-bg.png "Pinch to Zoom" en/{N}/header.png   # Pillow が要る(無ければ pip install pillow)
python3 -c "from PIL import Image; im=Image.open('en/{N}/header.png').convert('RGB'); im=im.resize((900,int(im.height*900/im.width)),Image.LANCZOS); im.save('en/assets/notice-{N}.webp',quality=75)"   # 一覧サムネイル
```

`en/{N}/header.png` を Read で確認する(文字がキャラクターに重なっていない、切れていない)。

`header-bg.png` が無い(日本語の文字を焼き込んだ)バナーは、**元画像を入力にして日本語の文字だけを消す編集**を Codex にさせ、空いた位置に英語タイトルを載せる。新規生成にすると元の絵と別物になるので使わない:

```sh
codex exec -s workspace-write -i {N}/assets/header.png - <<'PROMPT'
添付画像から日本語の文字(縁取り・影・文字の背景の帯も)だけを消し、消した部分は周囲の絵柄で自然に埋めてください。キャラクター・構図・配色・画角は元画像と完全に同じに保ち、新しい要素や文字を足さないでください。元画像と同じ寸法の PNG で en/{N}/assets/header-bg.png に保存してください。
PROMPT
```

1 枚 1.5 分ほど。複数枚は並列に走らせてよい。Codex が「model requires a newer version」で止まるときは `codex update`。英語タイトルは文字があった位置に合成する(`banner-title.py` は上端固定なので、位置指定が要るときは同じスタイルで描く。中央寄せ・オレンジ #FF940F・白縁・水色ハロー)。旧お知らせ(`Notification/{N}`)のヘッダーはファイル名が `01-xxxx.webp` なので出力名を合わせる。同じヘッダーを共用する記事(11 と 12、旧 1/4/5、旧 113/127)は同じファイルをコピーして置く。

## 3.5 画像の中の日本語

英語版は日本語版の画像をそのまま参照するので、画像に日本語が写っていればそのまま英語ページに出る。新しいお知らせでは以下を守る:

- ヘッダー画像は 3. で英語タイトルを合成する(`header-bg.png` を必ず残す)
- アプリのスクリーンショットは英語表示のアプリで撮り直し、`en/{N}/` に日本語版と同じファイル名で置く(build.py が自動でそちらを使う)。英語ビルドが無い場合はユーザーに相談する(画像対応仕様に起票するか、その画像を外すか)
- 図解・スタンプ・見出し入りイラストなど、アプリ画面のスクショ以外で日本語の文字がある画像は、3. と同じ「文字だけ消す編集 → 英語を描く」で英語版を作り `en/{N}/` に同名で置く(build.py が自動でそちらを使う)
- `en/{N}/index.html` を生成したら、参照している画像を Read で全部見て、日本語が残っていないことを確認する(HTML の文字は build.py が数えるが、画像の中は数えない)

## 4. ページ生成と一覧の再生成

```sh
python3 scripts/en/build.py {N}         # en/{N}/index.html。残った日本語 0 文字でないと失敗
python3 scripts/en/build_list.py        # en/index.html。英語版のあるお知らせだけを載せる
```

画像・CSS は日本語版のディレクトリを参照する(コピーしない)。build.py が「en.json に無いブロック」で失敗したら日本語 HTML が変わっているので 1. からやり直す。

## 5. 表示確認

`/notification-page` 5 節と同じ方法で `en/{N}/index.html` と `en/index.html` の先頭を描画して見る。英語は日本語より長いので、見出しの折り返しと一覧カードのタイトルが 2 行に収まっているかを見る。

## 6. コミット・公開

- `git add {N}/en.json en/{N}/ en/assets/notice-{N}.webp en/index.html`(`.DS_Store` は入れない)
- 新しいお知らせは `/notification-sql` の push に同乗させる(コミット「`add {N}`」に含める)。旧お知らせの英語化はコミット「`{N}: 英語版を追加`」で単独 push してよい
- 公開後 `https://motitown-notification.astran.jp/en/{N}/` と `https://motitown-notification.astran.jp/en/` を curl で確認する

## 英語一覧に載らないもの

- 英語版を作っていないお知らせ(build_list.py が自動で除外する)
- 画像だけの旧お知らせ(`Notification/` のうち本文が画像 1 枚のもの約 30 件)。文字が画像に焼き込まれているため翻訳できない。英語化するなら画像対応仕様(デザイン)として別途起票する

## 画像で作られた説明ページ(information/ recommend/ など)の英語化

STUDIO から移植した説明ページ(`information/about-bp` など)は本文が画像に焼き込まれている。
英語版は画像の日本語部分を背景色で塗り、同じ位置に英語を描いて作る(`scripts/en/overlay.py`)。

```sh
python3 scripts/en/overlay.py --grid information/about-bp/assets/01-xxxx.webp /tmp/grid.png   # 100px 目盛り付き画像。Read で見て座標を読む
# {dir}/en.images.json を書く(形式は overlay.py の docstring。information/about-bp/en.images.json が実例)
python3 scripts/en/overlay.py information/about-bp        # en/{dir}/<画像名> に英語版画像を書く
python3 scripts/en/extract.py information/about-bp        # en.json(title と og:title だけ)を作って英訳を書く
python3 scripts/en/build.py information/about-bp          # en/{dir}/index.html(英語版画像を自動で参照)
```

- 文字色は `{"darkest": [x0,y0,x1,y1]}` で元画像の日本語の文字から拾う。塗りは `"fill": "auto"`(範囲の四辺の中央値)が基本。
  グラデーションや絵に重なる文字は塗りが目立つので、範囲を文字ぎりぎりに絞るか、単色の帯・パネルの内側だけ塗る
- 見出しの蛍光マーカー(帯)は `fill` に `{"sample": [x,y]}` で帯の色を拾って塗り直してから文字を載せる(about-bp の 1 枚目参照)
- 英語は日本語より長いので `fit` で自動縮小されるが、縮みすぎる(元の 8 割未満)ときは文を短くする。段落は `box` を広げる
- 画面名・機能名は `MOTITAN_APP=<motitan_app の path> python3 scripts/en/glossary.py 記憶度` で英語版アプリの文言に合わせる(記憶度 = Mastery、市民リーグ = Citizen League など)
- 生成後は en/{dir}/ の画像を Read で全部見て、塗り残し・はみ出し・日本語の残りが無いことを確認する
- 英語版を作らないページは `build_list.py` が `en/{dir}/index.html` に日本語ページへの転送を置く(アプリは英語表示のとき全ページを `/en/` 付きで開く)

## 画像内の日本語の走査(OCR)

英語ページが参照している画像に日本語が残っていないかは、目視ではなく OCR で機械的に確かめる。

```sh
python3 scripts/en/scan_images.py                 # en/ 配下の全英語ページ(転送スタブ以外)の画像を走査。残りがあれば exit 1
python3 scripts/en/scan_images.py <画像> [...]     # 1 枚の全文字と座標を出す(overlay の rect を取るのに使う)
```

macOS の Vision を使う(`scripts/en/ocr.swift` を初回に `~/.cache/motitown-notification/ocr` へコンパイル。swiftc が要る)。

- **アイコンの誤読に注意**: `く`=「<」/ `八））`・`小）`=スピーカー / `三の`・`三う`=ハンバーガーメニュー / `玄`=翻訳アイコン。
  これらは日本語ではないので直さない。逆に OCR は装飾文字・極小文字を取りこぼすので、最後は必ず目で見る
- 走査は**英語ページが実際に参照している画像だけ**を見る。日本語版の画像がそのまま参照されている(パスが `en/` で始まらない)なら、
  その画像は英語版が未作成ということ
- アルファ付き PNG/WebP を overlay にかけると透明部分が黒くなるので、白背景に合成した `{dir}/en-src/<名前>` を作り、
  そのキーで `en.images.json` に書く(出力は `en/{dir}/<名前>` に落ちる)

## 文字だけの画像はテキストに戻す

画像が「無地の背景に文字だけ」(表・Q&A・規約文など)なら、塗り替えるより HTML に戻した方が読みやすく、翻訳も後から直せる。

`{dir}/en.replace.json` に `{"assets/<画像>": "<h3>…</h3><p>…</p>"}` を書くと、`build.py` がその `<img>` を
`<div class="en-text">…</div>` に差し替える(値を空文字にすると画像を消すだけ。複数タイルを 1 枚目にまとめる時に使う)。
使えるタグ: h2 h3 p ul ol li table tr th td strong br、`class="note"`(注記)、`class="panel"`(青いパネル)、`ul class="cols"`(2 段組)。
**キャラ・スクショ・デザインされたレイアウトのある画像には使わない**(塗り替える)。使ったら `en.images.json` の該当キーと
`en/{dir}/<画像>` を消す。実例: `information/gacha-drop/*/en.replace.json`(排出率の表 5 ページ)

### overlay で描けないもの(傾いた文字など)

`overlay.py` は水平の文字しか描けない。傾いた文字・縁取り・グラデーションの上の文字は、出力を Pillow で後処理する
`{dir}/en.post.py` を置く(`overlay.py` が最後に自動実行する)。実例: `information/widget/1/en.post.py`(傾いたウィジェットカード)。
元画像の文字を消した下地を先に作る場合は `{dir}/en-src/<名前>` に置き、`en.images.json` のキーもそれにする
(実例: `Notification/70/en-src/`, `Notification/61/en-src/`)。
