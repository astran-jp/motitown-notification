---
name: notification-draft
description: モチタウンお知らせの「原稿」を作る(ワークフローの第1段階。原稿作成 → HTML作成(notification-page) → SQL作成(notification-sql))。伝えたい内容のメモを受け取り、開発者・神谷創の人格を読み込ませた Gemini に Markdown 原稿を書かせ、レビューして {N}/draft.md に保存する。「お知らせの原稿を作って」「お知らせの文章を書いて」「次のお知らせのドラフト」等で使用。
---

# お知らせ原稿作成

お知らせ配信ワークフローの第1段階。ここでは **HTML を書かない**。成果物は `{N}/draft.md`(Markdown)のみ。

```
原稿作成 (このスキル)  →  HTML作成 (/notification-page)  →  SQL作成・公開 (/notification-sql)
```

書き手は開発者・神谷創(persona.md)。実際の文章生成は Gemini に任せ、Claude はブリーフ整理・ディスパッチ・レビューを担当する。

## 1. お知らせ番号の決定

リポジトリ直下の数字ディレクトリの最大値 +1 を {N} とする。`{N}/` を作成する。

```sh
ls | grep -E '^[0-9]+$' | sort -n | tail -1
```

## 2. ブリーフの作成 ({N}/brief.md)

ユーザーから受け取った内容(口頭メモ、Slack の文面、リリースノート等)を、事実だけの箇条書きにして `{N}/brief.md` に保存する。ここが Gemini に渡す唯一の事実ソースになるので、以下を漏れなく含める:

- 何が変わったか / 何が起きているか(機能追加、不具合、メンテ等)
- 対象アプリ(モチタン / モチスピ / 両方)と配信予定日時(不明なら `TBD`)
- 操作手順(画面名はアプリの表記どおり。例: `マイページ > 設定 > 学習設定`)
- 数値・日付・固有名詞(コース名、先生の名前 等)
- 商標注記が必要なら、その文言(過去の `*/index.html` の `p.note` から一字一句コピー)
- 伝えたい「体験」(なぜ作ったか)があれば一言。無ければ Gemini に創作させない旨を書く

ブリーフに無い事実は Gemini に書かせない。足りない情報はユーザーに聞くか `TBD` と明記する。

**対象アプリはチケットの記載を鵜呑みにしない。** Notion のタスク名や本文は起票時の言葉(例: 「モチタン自動再生の…」)のままで、実装が両アプリ共通でもそう書かれていることがある(21 で実際に起きた)。機能ごとに、実装が `Assets/Motitan/Scripts/Common/` 配下か、`AppMode` による分岐があるか、PR 本文に「単語詳細／フレーズ詳細」のような両アプリの記述があるかを確認し、ブリーフには確認結果に基づく対象アプリを書く。判断できなければユーザーに聞く。

```sh
grep -rn 'AppMode' /Users/hal/git/motitan_app/Assets/Motitan/Scripts/Common/<機能のファイル>.cs   # 分岐が無ければ共通
```

**用語はアプリの表記に忠実に。** Notion のタスクや開発資料には内部名(「Book画面」「WordBook」など)が混ざっている。ブリーフに書く前に `glossary.txt`(公式UI用語集)で表記を確かめ、無ければ `app-terms.generated.txt`(アプリのソースから抽出した全UI文字列)を grep して実在する表記を探す。見つかった正しい表記は `glossary.txt` に出典付きで追記する。どこにも無い名前は使わず、ユーザーに聞く。

```sh
grep -n '自動再生' .claude/skills/notification-draft/app-terms.generated.txt
python3 .claude/skills/notification-draft/scripts/lint.py --terms-only {N}/brief.md   # ブリーフの用語検査
```

`app-terms.generated.txt` が古い(アプリに新機能が入った)ときは `scripts/build-app-terms.sh` で `../motitan_app` から再生成する。

## 3. Gemini にディスパッチ

```sh
.claude/skills/notification-draft/scripts/dispatch.sh {N} {N}/brief.md {N}/draft.md
```

- モデルは `GEMINI_MODEL` 環境変数で変更できる(既定 `gemini-3.8-flash`)。モデルIDが通らない場合は `gemini` を対話起動して利用可能なモデル名を確認し、既定値を `scripts/dispatch.sh` で更新する
- 認証は `~/.zsh_secret` の `GEMINI_API_KEY`(スクリプトが自動で読む)。未認証エラー(code 41)が出たらそのファイルを確認してもらう
- プロンプトは `prompt-template.md` に `persona.md` + `writing-guide.md` + 禁句/禁止表現 + 過去の `*/draft.md`(最大2件) + ブリーフを埋め込んで組み立てる
- 実行前にブリーフの用語検査が走り、未定義用語があれば止まる(exit 6)
- 書き出し後に `scripts/lint.py`(機械検査)と `scripts/term-judge.sh`(Gemini による用語判定)が自動で走る。違反があれば違反内容を添えて Gemini に書き直させる(最大3回)。それでも残れば exit 5 で違反一覧を出す(draft.md は最後の出力のまま残る)

## 3a. 機械検査(lint)

```sh
python3 .claude/skills/notification-draft/scripts/lint.py {N}/draft.md
```

検査内容: 禁句(`banned-words.txt`)、禁止表現(`banned-patterns.txt`: 質問・感想募集・モチベア口調)、**未定義用語**(カタカナ語・英字語・「」内の語・操作手順の各段・「〜機能/画面/モード」の複合語が `glossary.txt` / `app-terms.generated.txt` / `common-words.txt` のどれにも無い)、frontmatter 必須項目、冒頭「モチタン・モチスピを開発している神谷です。」、署名「開発者 神谷創」、「！」1つまで。TBD は警告。

機械検査で拾えない造語(「フレーズ対戦機能」のような日本語の複合語)は `scripts/term-judge.sh {N}/draft.md` が Gemini に用語集と突き合わせさせて検出する。

未定義用語の違反が出たときの対応: (a) アプリに実在する表記なら `glossary.txt` に出典付きで追加、(b) 一般語の誤検出なら `common-words.txt` に追加、(c) 造語なら原稿を用語集の語で言い換える。
禁句・禁止表現を増やしたいときは、それぞれのファイルに1行足すだけでよい(プロンプトにも自動で入る)。
Claude が手で直したあとも、必ずもう一度 lint を通してから確認に出す。

## 4. レビュー(Claude が行う)

出力された `{N}/draft.md` を読み、次を点検する。直しは Claude が直接編集してよいが、文体を崩さないよう最小限にする。大きく外れている場合はブリーフを補強して再ディスパッチする。

- **事実**: ブリーフに無い日付・数値・機能・対応予定が混ざっていないか。機能の効果・使い心地の描写(「〜してくれます」)がブリーフ由来でなければ削る。`TBD` が残っていればユーザーに確認して埋める
- **分量**: こだわりの一文が1つ以下か、励まし・呼びかけが無いか。ブリーフに対して長すぎれば削る(目安 200〜450字)
- **形式**: writing-guide.md の frontmatter(number / title / date / apps / author / banner)が揃っているか。`number` が {N} と一致するか
- **人格**: 「モチタン・モチスピを開発している神谷です。」で始まり「開発者 神谷創」で終わるか。です・ます調か。モチベア口調(「〜だよ！」)や作品世界の住人としての名乗りが無いか。「！」が一つ以下か
- **本題の明瞭さ**: 何が変わったか・どう使うかが、こだわりの話に埋もれていないか
- **表記**: 操作手順の区切りが `A > B > C`、画面名がブリーフどおりか。商標注記が一字一句同じか
- **lint**: 上の点検で編集したら `lint.py` を再実行して OK を確認する

## 5. ユーザー確認

`{N}/draft.md` の本文をそのまま返信に貼って確認をとる。修正要望は draft.md に反映する(人格・形式の点検を再度通す)。

確定したら次の段階を案内する: 「/notification-page で HTML 化」。バナーは frontmatter の `banner` を元に作る(notification-page の 3 節)。`list_title` は後で `/notification-list` が一覧のカードに使う。

## ファイル

- `persona.md` — 神谷創の人格(Notion の履歴書の要約。Notion 側が更新されたら同期する)
- `writing-guide.md` — 原稿の形式・文体・禁止事項
- `banned-words.txt` / `banned-patterns.txt` — 禁句(部分一致)と禁止表現(正規表現)。ユーザーが自由に追記する
- `glossary.txt` — 公式UI用語集(機能名・画面名・ボタン名の正しい表記。出典メモ付き)。プロンプトにも入る
- `app-terms.generated.txt` — `../motitan_app` の C# 文字列リテラル・Unity ローカライズ表・prefab テキストから抽出した全UI文字列(自動生成。`scripts/build-app-terms.sh`)
- `common-words.txt` — 用語検査で許可する一般語(アプリ、スマホ 等)
- `scripts/lint.py` — 原稿の機械検査(禁句・質問募集・未定義用語・形式・署名)
- `scripts/term-judge.sh` — Gemini による用語判定(造語の検出)
- `prompt-template.md` — Gemini に渡すプロンプトの骨組み
- `scripts/dispatch.sh` — プロンプト組み立て → `gemini -p` 実行 → draft.md 書き出し
