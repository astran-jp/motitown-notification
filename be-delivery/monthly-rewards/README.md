# 月間ミッション報酬のお知らせ

アプリ内 WebView で開く「今月の報酬一覧」のページ。

偶数月・奇数月とも同じ作り（2026年10月分から偶数月も HTML 化。それまでの偶数月は旧 STUDIO ページの 1 枚画像だった）。

- 自前の HTML/CSS。モチタン限定 / モチスピ限定の 2 ブロックを **1 ページに持ち**、
  起動アプリのブロックが上に来るように表示順とゾーン背景だけを入れ替える
- `even-months/index.html` と `odd-months/index.html` は中身（キャラ名・説明文・画像）以外は同一。
  レイアウトを直すときは `shared/style.css` を直せば両方に効く

## URL

```
https://motitown-notification.astran.jp/be-delivery/monthly-rewards/even-months/?app=motitan
https://motitown-notification.astran.jp/be-delivery/monthly-rewards/odd-months/?app=motispi
```

- `even-months` / `odd-months` … 偶数月 / 奇数月。BE が当月に応じて出し分ける（従来どおり）
- `app` … `motitan` / `motispi`。**このパラメータのブロックが上に来る**。
  未指定・不正値はモチタン扱い（`<html data-app="motitan">` が初期値）

## ディレクトリ

```
be-delivery/monthly-rewards/
├── shared/          … 両ページ共通。レイアウト修正はここだけで完結する
│   ├── style.css
│   ├── glow.svg / sparkle.svg / calendar.svg / gold-leaf.svg / silver-leaf.svg
├── even-months/     … 偶数月
│   ├── index.html   … 偶数月の中身（キャラ名・説明文）
│   └── images/      … 偶数月のキャラ画像 6 枚
├── odd-months/      … 奇数月
│   ├── index.html   … 奇数月の中身（キャラ名・説明文）
│   └── images/      … 奇数月のキャラ画像 6 枚
└── en/{even,odd}-months/ … 英語版への転送スタブと、英語版ページが参照する画像（日本語版のコピー）
```

`even-months` と `odd-months` は画像も含めて独立している。`shared/style.css` は両方に効く。

## 毎月の更新手順（even / odd の 2 枚ローテ）

公開中の月と同じパリティのディレクトリは触らないこと。BE が 1 日に参照先を切り替えるので、
それまではいつ push しても表示は変わらない。

### 翌月の準備（偶数月なら `even-months/`、奇数月なら `odd-months/`）

1. `{parity}-months/images/` の 6 枚をその月のキャラ画像に差し替える（ファイル名は変えない）
2. `{parity}-months/index.html` のキャラ名・説明文・`alt`・先頭コメントの「現在の内容」を書き換える
3. ローカルで両アプリ分を確認（下記）してから push する

キャラと文言は BE のマスタが正。`character_way_of_gettings.way_of_getting` が
`monthly-mission-{YYYYMM}` / `mission-calendar-effort-1-{YYYYMM}` /
`mission-calendar-excellence-1-{YYYYMM}`（モチスピは `motispi-` 始まり）の行を引き、
`characters` の `name` / `profile` をそのまま使う。
画像は Unity 側 `Assets/AddressableAssets/CharacterImage/{model_id}.png`（512×512・透過）を下表のサイズに縮小する。
DB を引けないときは motitan-api の `manual_migration/japan/0015-characters.sql`（name / profile / model_id）と
`0019-character_way_of_gettings.sql`（`way_of_getting` → character id）が同じ内容の正本。

### 画像の仕様

| ファイル | 表示サイズ | 用意するサイズ |
|---|---|---|
| `{app}-monthly.png` | 172px | 344 × 344 |
| `{app}-effort.png`（努力賞・カード左にはみ出す） | 160px | 320 × 320 |
| `{app}-excellent.png`（優秀賞・カード右端で切れる） | 172px | 344 × 344 |

いずれも背景透過 PNG。`{app}` は `motitan` / `motispi`。

## ローカル確認

```sh
cd be-delivery/monthly-rewards
python3 -m http.server 8931
# http://localhost:8931/odd-months/index.html?app=motitan
# http://localhost:8931/odd-months/index.html?app=motispi
# http://localhost:8931/even-months/index.html?app=motitan
# http://localhost:8931/even-months/index.html?app=motispi
```

幅 358px（アプリ内 WebView 相当）で確認する。両方の `app` を必ず見る。
英語版も見るときはリポジトリ直下で `python3 -m http.server 8931` を起動し、
`http://localhost:8931/en/be-delivery/monthly-rewards/{parity}-months/index.html?app=…` を開く（相対パスがリポ直下基準のため）。

## アプリ / BE 側の前提

- BE の `domain/notice/monthly_reward.go` が偶数月 / 奇数月の URL を出し分ける。
  STUDIO からの移行にあたり、この定数を上記 URL に差し替える必要がある
- `?app=` はアプリ（またはリクエストヘッダを見て BE）が付与する。付いていなくても
  モチタンの順序で表示されるだけで、ページは壊れない

## 英語版（en/）

`/en/be-delivery/monthly-rewards/{even,odd}-months/` が英語版ページ（`be-delivery/monthly-rewards/en/{even,odd}-months/index.html` はそこへの転送スタブ）。
`shared/style.css` は日本語版と共通、画像は `be-delivery/monthly-rewards/en/{parity}-months/images/` に日本語版のコピーを置く。

毎月の更新: 日本語版の index.html を更新したら、英語版の index.html も同じキャラで更新する。
キャラ名・説明文の英訳は motitan-api の `character_translations`（native=en）を使う
（正本は app-localization `locales/en-US/drafts/character-translations-*.tsv`）。
固定ラベルの英訳: モチタン限定=Motitan Exclusive／モチスピ限定=Motispi Exclusive／月間ミッション=Monthly Mission／
カレンダーミッション=Calendar Mission／努力賞=Achiever Award／優秀賞=Excellence Award。

（2026年10月分から偶数月も奇数月と同じ HTML 構成になったため、IMG-27 の画像対応は不要になった。）

