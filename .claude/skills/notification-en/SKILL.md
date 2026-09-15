---
name: notification-en
description: モチタウンお知らせの英語版を作る(ワークフローの第2.5段階。HTML作成(notification-page) → 英語版(このスキル) → SQL作成・公開(notification-sql))。{N}/index.html から文言を抜いて {N}/en.json に英訳を書き、en/{N}/index.html と英語バナー、英語一覧 en/index.html を生成する。旧お知らせ(Notification/{N})の英語化にも使う。「英語版を作って」「22を英語に」「英語一覧を更新して」等で使用。
---

# お知らせ英語版の作成

日本語の `{N}/index.html` が完成した後に行う。英語版は同じ番号で `en/{N}/`(旧お知らせは `en/Notification/{N}/`)に置き、公開 URL は `https://motitown-notification.astran.jp/en/{N}/`、一覧は `https://motitown-notification.astran.jp/en/`。アプリは表示言語が英語のユーザーにこの URL を開く(配信 SQL は `/notification-sql` が言語で出し分ける)。

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
~/miniforge3/envs/py310_env/bin/python3 .claude/skills/notification-page/scripts/banner-title.py {N}/assets/header-bg.png "Pinch to Zoom" en/{N}/header.png   # Pillow が入っている python
~/miniforge3/envs/py310_env/bin/python3 -c "from PIL import Image; im=Image.open('en/{N}/header.png').convert('RGB'); im=im.resize((900,int(im.height*900/im.width)),Image.LANCZOS); im.save('en/assets/notice-{N}.webp',quality=75)"   # 一覧サムネイル
```

`en/{N}/header.png` を Read で確認する(文字がキャラクターに重なっていない、切れていない)。`header-bg.png` が無い古いお知らせは日本語バナーのまま(画像は差し替えない)。

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
