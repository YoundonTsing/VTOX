-- init_db.sql

-- 选择要使用的数据库
-- 如果您的数据库名称不是 'vtox_db'，请将下面这行修改为您的实际数据库名称
USE vtox_db;

-- 如果 'users' 表已存在，则先删除它（仅限开发环境）
-- 在生产环境中，通常不会直接删除表，而是使用迁移工具
DROP TABLE IF EXISTS `users`;

-- 创建 'users' 表
CREATE TABLE `users` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `username` VARCHAR(255) NOT NULL UNIQUE,
    `hashed_password` VARCHAR(255) NOT NULL,
    `name` VARCHAR(255) NULL,
    `email` VARCHAR(255) NULL,
    `role` ENUM('admin', 'operator', 'guest') NOT NULL DEFAULT 'operator',
    `status` ENUM('active', 'disabled') NOT NULL DEFAULT 'active',
    `last_login` DATETIME NULL,
    PRIMARY KEY (`id`),
    INDEX `ix_users_id` (`id`),
    INDEX `ix_users_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 注意：
-- 1. `ENGINE=InnoDB` 和 `DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci` 适用于MySQL 8.0+
--    如果您的MySQL版本较旧，可能需要调整 `COLLATE` 部分，例如 `utf8mb4_unicode_ci`。
-- 2. `AUTO_INCREMENT` 确保 `id` 自动递增。
-- 3. `UNIQUE` 确保 `username` 不重复。
-- 4. `INDEX` 为 `id` 和 `username` 列创建索引以提高查询性能。
-- 5. `ENUM` 类型用于限制 `role` 和 `status` 字段的可能值。

-- 插入初始用户数据
-- 注意：下面的密码是已经哈希过的示例值。在实际生产中，你应该使用安全的哈希算法（如 bcrypt）生成密码哈希。
-- 示例中使用的明文密码分别为： admin123, operator123, guest123
INSERT INTO `users` (`username`, `hashed_password`, `name`, `email`, `role`, `status`, `last_login`) VALUES
('admin', '$2b$12$W1XWrvwdIW1tI/T783xdQuFcGjaevjh/yOaIQZx6sB2wog78E0FK6', '系统管理员', 'admin@example.com', 'admin', 'active', NULL),
('operator1', '$2b$12$DbmIZ/a5L51sRDxGDp3pI.UP13D.9/127602IuIq23e..8aK', '操作员张三', 'zhangsan@example.com', 'operator', 'active', NULL),
('guest1', '$2b$12$FGH45/a5L51sRDxGDp3pI.UP13D.9/127602IuIq6789..zxc', '访客李四', 'lisi@example.com', 'guest', 'disabled', NULL);