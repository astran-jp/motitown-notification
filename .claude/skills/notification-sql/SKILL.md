---
name: notification-sql
description: モチタウンお知らせの配信用SQLを作成し、pushして公開し、デプロイ完了後に Slack #02-develop へ確認依頼を投稿する(ワークフローの第3段階。原稿作成(notification-draft) → HTML作成(notification-page) → SQL作成・公開・確認依頼)。{N}/index.html が完成した後に使う。「配信用SQLを作って」「公開して」「pushして」「Slackに確認依頼を出して」等で使用。返信の反映は notification-review。
---

# 配信用SQL作成・公開・確認依頼

お知らせ配信ワークフローの第3段階。前提: `{N}/index.html` が完成し、ユーザーが表示を確認済み。

```
原稿作成 (/notification-draft)  →  HTML作成 (/notification-page)  →  SQL作成・公開・確認依頼 (このスキル)  →  返信の反映 (/notification-review)
```

## 1. 配信対象の確認

`{N}/draft.md` の frontmatter `apps` を既定値としてユーザーに確認する。draft.md が無い場合の既定は「モチタン・モチスピ両方の全員に配信」。

## 1.5 英語版の確認

`en/{N}/index.html` があり、中に `<!-- fallback: redirect to ja -->` が無いことを確認する。無ければ公開前に `/notification-en` の手順で英語版を作る(アプリが英語表示のユーザーに `/en/{N}` を開くため、英語版なしで配信すると日本語ページへの転送になる)。

## 2. sql/deployed/{N}.sql の作成

直近の `sql/deployed/` のファイルをベースに作成する。`sql/deployed/22.sql` 以前は `@url` のホストが `motitown-notification.astran.jp` なので、番号だけでなくホストも下の形に直す。全員配信のパターン:

- `SET @url = 'https://motitown.com/notification/{N}' COLLATE utf8mb4_unicode_ci;` — 配信する URL は `motitown.com/notification/` 配下にする。アプリが表示言語に合わせて `/en/{N}` へ読み替えるのはこの URL だけで、`motitown-notification.astran.jp` のまま配信すると英語表示のユーザーにも日本語ページが開く(ページの公開先と下の確認用 URL は `motitown-notification.astran.jp` のままでよい。`motitown.com/notification/` はそこを同じパスで中継している)
- 「削除されていない(`deleted_at IS NULL`)」かつ「BOTでない(`is_bot = FALSE`)」かつ「直近3ヶ月以内にログイン」のユーザーへ
- `app` = `'motispi'` と `'motitan'` のそれぞれに `notices` へ INSERT(タイトルは `'お知らせ'`)
- 英語ユーザー向けの出し分けは SQL ではやらない。アプリ(v12 以降)が表示時に URL を `/en/{N}` に読み替え、番号のお知らせのタイトルをアプリ内の訳語に差し替える(仕様裁定 P-17)。BE は URL を書き換えないので、`@url` を上の形で入れておくことがそのまま英語表示の条件になる。配信前に `/notification-en` で英語版を作っておく(英語版が無いお知らせには `build_list.py` が日本語ページへの転送を置くので 404 にはならない)

`apps` が片方だけなら、その `app` の INSERT だけにする。対象を絞る場合も WHERE 句の基本3条件は維持し、条件を追加する形にする。

## 3. push(公開)

ユーザーが完成を確認してから:

0. **push の前に差分を見せる**: `git add` 後に `git diff --cached -- {N}/ sql/deployed/{N}.sql` の変更行(HTML の CSS 等は要約でよい)を返信に貼り、意図した変更だけであることを確認してから push する。修正の再公開(日時変更など)でも同じ
1. `git add {N}/ sql/deployed/{N}.sql en/{N}/ en/index.html en/assets/notice-{N}.webp` — `.DS_Store` は追加しない。`{N}/brief.md` `{N}/draft.md` `{N}/en.json` も一緒に入れる(原稿と訳の履歴として残す)
2. コミットメッセージは過去の慣例に合わせ「`add {N}`」
3. `git push origin main` — GitHub Actions が回り公開される(初回pushのユーザーは無視される設定あり)
4. 公開URL `https://motitown.com/notification/{N}/`(2026-09-24 からユーザー向けはこのドメイン。`motitown-notification.astran.jp` を同じパスで中継)を報告する。SQL の実行は配信担当が行うので、`sql/deployed/{N}.sql` のパスも併せて伝える

## 4. デプロイ完了を待つ

GitHub Pages のデプロイには数十秒〜数分かかる。公開URLに新しい title が載るまでポーリングする(最大15分。ポーリングは中継元の `motitown-notification.astran.jp` に対して行う。`motitown.com` は curl を Cloudflare が弾くため):

```sh
.claude/skills/notification-sql/scripts/wait-deploy.sh {N}
```

`deployed:` が出たら次へ。タイムアウトしたら GitHub Actions / Pages の状態をユーザーに報告して止まる(Slack には投稿しない)。

## 5. Slack に確認依頼を投稿する(デプロイ確認の直後、間を置かずに)

投稿は **Slack App(Bot)** から行う(2026-09-24 から。以前の MCP 経由=ユーザー本人名義の投稿は使わない)。認証情報はリポジトリ直下の `.env`(`SLACK_BOT_TOKEN`)にあり、スクリプトが読む。**`.env` の中身を Read/cat で見ない**(値を会話に出さない。設定でも Read が拒否される)。

```sh
.claude/skills/notification-sql/scripts/slack-review-post.sh {N} --dry-run   # 文面と宛先の確認(トークンは表示しない)
.claude/skills/notification-sql/scripts/slack-review-post.sh {N}             # 投稿。{N}/review.json を更新する
```

宛先は `slack.json`(チャンネル `#02-develop` = `C04APK82UCD`、メンション3名)。文面は固定:

```
<@U037PTX0Q9Z> <@U057R6NQPC2> <@U037PUGC9SN> 神谷です。お知らせを作成しました。ご確認ください。
日本語版: https://motitown.com/notification/{N}/
英語版: https://motitown.com/notification/en/{N}/
```

スクリプトが `{N}/review.json`(channel / ts / url / message_link / posted_at / replies_seen)を書くので、`git add` して次の push に含める。投稿後、ユーザーには permalink と「返信が来たら `/notification-review` で反映する」ことを伝える。スクリプトが `.env` を読めずに止まったら、ユーザーに `! .claude/skills/notification-sql/scripts/slack-review-post.sh {N}` を実行してもらう。

## 6. お知らせ一覧には載せない(別タイミング)

一覧(`index.html`)への追加は `/notification-list` で、ユーザーが指示したときに別途行う。このスキルでは `index.html` に触らない。報告の最後に「一覧への追加は別途 `/notification-list` で」と一言添える。
