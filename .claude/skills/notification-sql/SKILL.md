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

## 2. sql/deployed/{N}.sql の作成

直近の `sql/deployed/` のファイルをベースに、URL の番号だけを変えて作成する。全員配信のパターン:

- `SET @url = 'https://motitown-notification.astran.jp/{N}' COLLATE utf8mb4_unicode_ci;`
- 「削除されていない(`deleted_at IS NULL`)」かつ「BOTでない(`is_bot = FALSE`)」かつ「直近3ヶ月以内にログイン」のユーザーへ
- `app` = `'motispi'` と `'motitan'` のそれぞれに `notices` へ INSERT(タイトルは `'お知らせ'`)

`apps` が片方だけなら、その `app` の INSERT だけにする。対象を絞る場合も WHERE 句の基本3条件は維持し、条件を追加する形にする。

## 3. push(公開)

ユーザーが完成を確認してから:

1. `git add {N}/ sql/deployed/{N}.sql` — `.DS_Store` は追加しない。`{N}/brief.md` `{N}/draft.md` も一緒に入れる(原稿の履歴として残す)
2. コミットメッセージは過去の慣例に合わせ「`add {N}`」
3. `git push origin main` — GitHub Actions が回り公開される(初回pushのユーザーは無視される設定あり)
4. 公開URL `https://motitown-notification.astran.jp/{N}/` を報告する。SQL の実行は配信担当が行うので、`sql/deployed/{N}.sql` のパスも併せて伝える

## 4. デプロイ完了を待つ

GitHub Pages のデプロイには数十秒〜数分かかる。公開URLに新しい title が載るまでポーリングする(最大15分):

```sh
.claude/skills/notification-sql/scripts/wait-deploy.sh {N}
```

`deployed:` が出たら次へ。タイムアウトしたら GitHub Actions / Pages の状態をユーザーに報告して止まる(Slack には投稿しない)。

## 5. Slack に確認依頼を投稿する(デプロイ確認の直後、間を置かずに)

宛先と文面は `slack.json` に固定してある(チャンネル `#02-develop` = `C04APK82UCD`、メンション3名)。`slack_send_message` で次の文面をそのまま投稿する(`{url}` を公開URLに置換。文言は変えない):

```
<@U037PTX0Q9Z> <@U057R6NQPC2> <@U037PUGC9SN> 神谷です。お知らせを作成しました。ご確認ください。https://motitown-notification.astran.jp/{N}/
```

投稿結果の `ts`(親メッセージのタイムスタンプ)とチャンネルIDを `{N}/review.json` に保存する(返信の追跡に使う):

```json
{ "channel": "C04APK82UCD", "ts": "1757400000.123456", "url": "https://motitown-notification.astran.jp/{N}/", "posted_at": "2026-09-09T15:00:00+09:00", "replies_seen": [] }
```

`review.json` は `git add` して次の push に含める。投稿後、ユーザーには投稿へのリンクと「返信が来たら `/notification-review` で反映する」ことを伝える。
