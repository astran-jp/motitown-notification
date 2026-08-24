# 月間ミッション報酬のお知らせ

アプリ内 WebView で開く「今月の報酬一覧」のページ。

偶数月と奇数月で作りが違う。

- **奇数月** … 自前の HTML/CSS。モチタン限定 / モチスピ限定の 2 ブロックを **1 ページに持ち**、
  起動アプリのブロックが上に来るように表示順とゾーン背景だけを入れ替える
- **偶数月** … 旧 STUDIO ページ（`motitan-notification.astran.jp`）の丸ごとコピー。
  向こうは中身が 1 枚画像なので、この HTML も画像を 1 枚置くだけ

## URL

```
https://motitown-notification.astran.jp/be-delivery/monthly-rewards/even-months/?app=motitan
https://motitown-notification.astran.jp/be-delivery/monthly-rewards/odd-months/?app=motispi
```

- `even-months` / `odd-months` … 偶数月 / 奇数月。BE が当月に応じて出し分ける（従来どおり）
- `app` … `motitan` / `motispi`。**このパラメータのブロックが上に来る**。
  未指定・不正値はモチタン扱い（`<html data-app="motitan">` が初期値）。
  偶数月は 1 枚画像なので付いていても無視される

## ディレクトリ

```
be-delivery/monthly-rewards/
├── shared/          … 奇数月ページ用。レイアウト修正はここだけで完結する
│   ├── style.css
│   ├── glow.svg / sparkle.svg / calendar.svg / gold-leaf.svg / silver-leaf.svg
├── even-months/     … 旧 STUDIO ページのコピー
│   ├── index.html   … 画像を 1 枚置くだけ。shared/ は使わない
│   └── images/page.webp
└── odd-months/      … 自前 HTML
    ├── index.html   … 奇数月の中身（キャラ名・説明文）
    └── images/      … 奇数月のキャラ画像 6 枚
```

`even-months` と `odd-months` は画像も含めて独立している。ただし `shared/style.css` は
奇数月ページ専用なので、ここを触っても偶数月ページには影響しない。

## 毎月の更新手順（even / odd の 2 枚ローテ）

公開中の月と同じパリティのディレクトリは触らないこと。BE が 1 日に参照先を切り替えるので、
それまではいつ push しても表示は変わらない。

### 奇数月の準備

1. `odd-months/images/` の 6 枚をその月のキャラ画像に差し替える（ファイル名は変えない）
2. `odd-months/index.html` のキャラ名・説明文・`alt` を書き換える
3. ローカルで両アプリ分を確認（下記）してから push する

キャラと文言は BE のマスタが正。`character_way_of_gettings.way_of_getting` が
`monthly-mission-{YYYYMM}` / `mission-calendar-effort-1-{YYYYMM}` /
`mission-calendar-excellence-1-{YYYYMM}`（モチスピは `motispi-` 始まり）の行を引き、
`characters` の `name` / `profile` をそのまま使う。
画像は Unity 側 `Assets/AddressableAssets/CharacterImage/{model_id}.png`。

### 偶数月の準備

`even-months/images/page.webp` を新しい書き出しに差し替えるだけ。
HTML は幅 100%・比率維持で 1 枚表示しているので、縦横比が変わっても崩れない。

### 画像の仕様（奇数月）

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
# http://localhost:8931/even-months/index.html
```

幅 358px（アプリ内 WebView 相当）で確認する。奇数月は両方の `app` を必ず見る。

## アプリ / BE 側の前提

- BE の `domain/notice/monthly_reward.go` が偶数月 / 奇数月の URL を出し分ける。
  STUDIO からの移行にあたり、この定数を上記 URL に差し替える必要がある
- `?app=` はアプリ（またはリクエストヘッダを見て BE）が付与する。付いていなくても
  モチタンの順序で表示されるだけで、ページは壊れない
