# 月間ミッション報酬のお知らせ

アプリ内 WebView で開く「今月の報酬一覧」のページ。
モチタン限定 / モチスピ限定の 2 ブロックを **1 ページに持ち**、起動アプリのブロックが上に来るように
表示順とゾーン背景だけを入れ替える。中身は両アプリで同一なので、文言修正は 1 箇所で済む。

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
├── shared/          … 2 ページ共通。レイアウト修正はここだけで完結する
│   ├── style.css
│   ├── glow.svg / sparkle.svg / calendar.svg / gold-leaf.svg / silver-leaf.svg
├── even-months/
│   ├── index.html   … 偶数月の中身（キャラ名・説明文）
│   └── images/      … 偶数月のキャラ画像
└── odd-months/      … 奇数月。構成は even-months と同じ
```

`even-months` と `odd-months` は画像も含めて独立している。片方を編集しても
もう片方（＝公開中の月）には一切影響しない。

## 毎月の更新手順（even / odd の 2 枚ローテ）

例）9 月（奇数月）が公開中 → 10 月（偶数月）の準備をする場合

1. `even-months/images/` の 6 枚を 10 月のキャラ画像に差し替える（ファイル名は変えない）
2. `even-months/index.html` のキャラ名・説明文・`alt` を 10 月の内容に書き換える
3. ローカルで両アプリ分を確認（下記）してから push する

10/1 に BE が参照先を `even-months` に切り替えるので、9 月中はいつ push しても表示は変わらない。
**公開中の月と同じパリティのディレクトリは絶対に触らないこと。**

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
# http://localhost:8931/even-months/index.html?app=motitan
# http://localhost:8931/even-months/index.html?app=motispi
```

幅 358px（アプリ内 WebView 相当）で、両方の `app` を必ず確認する。

## アプリ / BE 側の前提

- BE の `domain/notice/monthly_reward.go` が偶数月 / 奇数月の URL を出し分ける。
  STUDIO からの移行にあたり、この定数を上記 URL に差し替える必要がある
- `?app=` はアプリ（またはリクエストヘッダを見て BE）が付与する。付いていなくても
  モチタンの順序で表示されるだけで、ページは壊れない
