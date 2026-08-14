-- URLの設定 (以下全てで参照される)
SET @url = 'https://motitown-notification.astran.jp/16' COLLATE utf8mb4_unicode_ci;
-- すべてのユーザーに配信
-- (「削除されていない」かつ「BOTでない」かつ「直近3ヶ月以内にログインしたことがある」)
INSERT INTO `notices` (`user_id`, `title`, `url`, `app`, `created_at`, `updated_at`)
SELECT `id`, 'お知らせ', @url, 'motispi', NOW(), NOW()
FROM `users`
WHERE `deleted_at` IS NULL AND `is_bot` = FALSE
AND `last_logged_in_at` > DATE_SUB(NOW(), INTERVAL 3 MONTH);


INSERT INTO `notices` (`user_id`, `title`, `url`, `app`, `created_at`, `updated_at`)
SELECT `id`, 'お知らせ', @url, 'motitan', NOW(), NOW()
FROM `users`
WHERE `deleted_at` IS NULL AND `is_bot` = FALSE
AND `last_logged_in_at` > DATE_SUB(NOW(), INTERVAL 3 MONTH);
