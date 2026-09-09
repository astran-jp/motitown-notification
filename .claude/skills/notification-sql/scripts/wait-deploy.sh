#!/usr/bin/env bash
# push 後、公開URL(GitHub Pages)にデプロイされるのを待つ。
# usage: wait-deploy.sh <N> [timeout_sec(既定 900)]
# 判定: HTTP 200 かつ、本文に {N}/draft.md の title(frontmatter)が含まれる(古いキャッシュや 404 ページを弾く)
# exit 0: 公開確認 / 1: タイムアウト / 2: 引数エラー
set -euo pipefail
N="${1:?usage: wait-deploy.sh <N> [timeout_sec]}"
TIMEOUT="${2:-900}"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REPO_DIR="$(cd "$SKILL_DIR/../../.." && pwd)"
URL="https://motitown-notification.astran.jp/$N/"
TITLE="$(sed -n 's/^title:[[:space:]]*//p' "$REPO_DIR/$N/draft.md" 2>/dev/null | head -1)"
[ -n "$TITLE" ] || { echo "title を $N/draft.md から取れません" >&2; exit 2; }
start=$(date +%s)
while :; do
  body="$(curl -s -H 'Cache-Control: no-cache' "$URL?t=$(date +%s)" || true)"
  if printf '%s' "$body" | grep -q -F "$TITLE"; then
    echo "deployed: $URL ($(( $(date +%s) - start ))s)"
    exit 0
  fi
  if [ $(( $(date +%s) - start )) -ge "$TIMEOUT" ]; then
    echo "timeout: $URL にまだ title「$TITLE」が見つかりません(${TIMEOUT}s)" >&2
    exit 1
  fi
  sleep 15
done
