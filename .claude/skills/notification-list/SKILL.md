---
name: notification-list
description: お知らせ一覧(リポジトリ直下の index.html、モチタウン右上のメールボックスから開く一覧)に、公開済みのお知らせ {N} のカードを追加して push する(ワークフローの第5段階。公開(notification-sql)とは別のタイミングで行う)。「お知らせ一覧に追加して」「一覧を更新して」「21を一覧に載せて」等で使用。
---

# お知らせ一覧の更新

お知らせ本体の公開(`/notification-sql`)とは**別のタイミング**で行う工程。本体を公開しただけでは一覧には載らない。ユーザーが「一覧に追加して」と言ったときだけ実行する(自動では行わない)。

```
原稿作成 → HTML作成 → SQL作成・公開・確認依頼 → 返信の反映 → 一覧の更新 (このスキル)
```

## 一覧の構造(要点)

- `index.html` は旧 STUDIO サイトの静的移植。`<script>` は無く、見た目は `<style>` 内の `[data-s-<UUID>]` セレクタで決まる
- 本文は縦並びコンテナ 1 つの中に、カード `<a class="sd appear" data-s-…>` が新しい順に並ぶ。カードは「サムネイル `<img>` + 日時 `<p>` + タイトル `<p>`」
- 番号付きお知らせのカードは、UUID を除いて CSS が同一。新しいカードは既存カードを複製して同じ `data-s-` 属性を使う(CSS を増やさない)
- サムネイルは `assets/` に幅 900px・品質 75 の WebP。新規は `assets/notice-{N}.webp`
- 先頭 2 件は `loading="lazy"` なし、3 件目以降は付ける

## 手順

1. **前提確認**: `{N}/` が公開済み(`https://motitown-notification.astran.jp/{N}/` が 200)で、`{N}/draft.md` の `date` が確定していること(TBD 不可)
2. **一覧用タイトル**: `{N}/draft.md` の frontmatter `list_title`(無ければ `title`)。一覧では 1〜2 行に収まる短い文言が良いので、`title` が長い場合は `list_title` を追加してユーザーに確認する(「／」で改行)
3. **追加**:
   ```sh
   python3 .claude/skills/notification-list/scripts/add-to-list.py {N} --dry-run   # 差し込む HTML を確認
   python3 .claude/skills/notification-list/scripts/add-to-list.py {N}
   ```
   すでに載っていれば何もしない。日時は `2026/09/10 12:00` の形に正規化される
4. **表示確認**: 先頭部分をヘッドレス Chrome で描画して Read で見る(カードが先頭にあり、サムネイル・日時・タイトルが正しい)。スクリーンショットをユーザーに送る
   ```sh
   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu --hide-scrollbars --window-size=500,1100 --screenshot=<scratchpad>/list-top.png "file:///.../index.html"
   ```
5. **push の前に差分を見せる**: `git diff -U0 index.html` の変更行(追加カード 1 行と lazy の付け替え)と `assets/notice-{N}.webp` の追加を返信に貼り、確認をとる
6. **push**: `git add index.html assets/notice-{N}.webp {N}/draft.md`(list_title を足した場合)→ コミット「`{N}: お知らせ一覧に追加`」→ `git push origin main` → 公開 URL `https://motitown-notification.astran.jp/` に載ったことを curl で確認して報告
