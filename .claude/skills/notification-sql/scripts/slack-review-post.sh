#!/usr/bin/env bash
# Slack App(Bot token)でお知らせの確認依頼を #02-develop に投稿する。
# 認証情報はリポジトリ直下の .env から読む(値は一切表示しない)。
#
# usage: slack-review-post.sh <N> [--dry-run]
# .env に必要な変数(どれか): SLACK_BOT_TOKEN または SLACK_TOKEN(xoxb-...)。
#   任意: SLACK_CHANNEL_ID(既定は slack.json の channel.id)
# 出力: 投稿の permalink と ts。{N}/review.json を更新する(channel / ts / url / posted_at / replies_seen)。
set -euo pipefail
N="${1:?usage: slack-review-post.sh <N> [--dry-run]}"
DRY="${2:-}"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REPO_DIR="$(cd "$SKILL_DIR/../../.." && pwd)"
ENV_FILE="$REPO_DIR/.env"
[ -f "$ENV_FILE" ] || { echo ".env がありません: $ENV_FILE" >&2; exit 2; }
set -a; # shellcheck disable=SC1090
source "$ENV_FILE"; set +a
TOKEN="${SLACK_BOT_TOKEN:-${SLACK_TOKEN:-}}"
[ -n "$TOKEN" ] || { echo ".env に SLACK_BOT_TOKEN(または SLACK_TOKEN)がありません" >&2; exit 2; }

CHANNEL="${SLACK_CHANNEL_ID:-$(python3 -c "import json;print(json.load(open('$SKILL_DIR/slack.json'))['channel']['id'])")}"
MENTIONS="$(python3 -c "import json;print(' '.join('<@%s>'%r['id'] for r in json.load(open('$SKILL_DIR/slack.json'))['reviewers']))")"
URL_JA="https://motitown.com/notification/$N/"
URL_EN="https://motitown.com/notification/en/$N/"
TEXT="$MENTIONS 神谷です。お知らせを作成しました。ご確認ください。
日本語版: $URL_JA
英語版: $URL_EN"

if [ "$DRY" = "--dry-run" ]; then echo "channel=$CHANNEL"; echo "$TEXT"; exit 0; fi

# JSON はブレース展開を避けるため python で組み立てる(環境変数経由)
PAYLOAD="$(SLACK_CH="$CHANNEL" SLACK_TEXT="$TEXT" python3 -c 'import json,os;print(json.dumps(dict(channel=os.environ["SLACK_CH"],text=os.environ["SLACK_TEXT"],unfurl_links=False)))')"
RESP="$(curl -s -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json; charset=utf-8' \
  --data "$PAYLOAD")"
OK="$(printf '%s' "$RESP" | python3 -c "import sys,json;j=json.load(sys.stdin);print('ok' if j.get('ok') else 'error:'+str(j.get('error')))")"
if [ "$OK" = "error:not_in_channel" ]; then
  # Bot がチャンネル未参加なら参加してから再送(公開チャンネルのみ。channels:join スコープが要る)
  JOIN="$(curl -s -X POST https://slack.com/api/conversations.join -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data "$(SLACK_CH="$CHANNEL" python3 -c 'import json,os;print(json.dumps(dict(channel=os.environ["SLACK_CH"])))')" | python3 -c "import sys,json;j=json.load(sys.stdin);print('ok' if j.get('ok') else 'error:'+str(j.get('error')))")"
  [ "$JOIN" = ok ] || { echo "Slack API join $JOIN(Bot を #02-develop に招待してください)" >&2; exit 3; }
  RESP="$(curl -s -X POST https://slack.com/api/chat.postMessage -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json; charset=utf-8' --data "$PAYLOAD")"
  OK="$(printf '%s' "$RESP" | python3 -c "import sys,json;j=json.load(sys.stdin);print('ok' if j.get('ok') else 'error:'+str(j.get('error')))")"
fi
[ "$OK" = ok ] || { echo "Slack API $OK" >&2; exit 3; }
TS="$(printf '%s' "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin)['ts'])")"
CH="$(printf '%s' "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin)['channel'])")"
LINK="$(curl -s -G https://slack.com/api/chat.getPermalink -H "Authorization: Bearer $TOKEN" --data-urlencode "channel=$CH" --data-urlencode "message_ts=$TS" | python3 -c "import sys,json;print(json.load(sys.stdin).get('permalink',''))")"

python3 - "$REPO_DIR/$N/review.json" "$CH" "$TS" "$URL_JA" "$LINK" <<'PY'
import json,sys,datetime,os
p,ch,ts,url,link=sys.argv[1:]
j=json.load(open(p,encoding='utf-8')) if os.path.exists(p) else {}
j.update({"channel":ch,"ts":ts,"url":url,"message_link":link,"posted_at":datetime.datetime.now().astimezone().isoformat(timespec='seconds'),"posted_by":"slack-app"})
j.setdefault("replies_seen",[])
json.dump(j,open(p,'w',encoding='utf-8'),ensure_ascii=False,indent=2); open(p,'a').write('\n')
PY
echo "posted: ts=$TS channel=$CH"; echo "$LINK"
