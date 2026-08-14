-- URLの設定 (以下全てで参照される)
SET @url = 'https://motitown-notification.astran.jp/17' COLLATE utf8mb4_unicode_ci;
-- モチタンの全ユーザーに配信
-- (「削除されていない」かつ「BOTでない」かつ「直近3ヶ月以内にログインしたことがある」)
INSERT INTO `notices` (`user_id`, `title`, `url`, `app`, `created_at`, `updated_at`)
SELECT `id`, 'お知らせ', @url, 'motitan', NOW(), NOW()
FROM `users`
WHERE `deleted_at` IS NULL AND `is_bot` = FALSE
AND `last_logged_in_at` > DATE_SUB(NOW(), INTERVAL 3 MONTH);
