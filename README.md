# legacy-redirect

`motitown-notification.astran.jp`（GitHub Pages）を転送専用にするためのブランチ。お知らせの公開先は `https://motitown.com/notification/`（main → Cloudflare Workers 静的アセット）。

- 各 `index.html` は同じパスの `https://motitown.com/notification/...` へクエリ・ハッシュを引き継いで転送する（noindex）
- 一覧に無いパスは `404.html` が同じパスへ転送する
- v12.0.0 未満のアプリが規約・ガチャ排出率などをこのドメインで開くため、旧アプリが十分減るまで残す
- 新しいお知らせはここに足さなくてよい（404.html が転送する）
