-- 数据库迁移：添加分镜图相关字段
-- 执行时间: 2025-07-13

USE video_agent;

-- 为 recreation_scenes 表添加新字段
ALTER TABLE `recreation_scenes` 
ADD COLUMN `shot_type` VARCHAR(100) NULL COMMENT '镜头类型' AFTER `duration`,
ADD COLUMN `plot` TEXT NULL COMMENT '情节描述' AFTER `description`,
ADD COLUMN `dialogue` TEXT NULL COMMENT '台词' AFTER `plot`;

-- 提示：如果需要回滚，可以使用以下语句：
-- ALTER TABLE `recreation_scenes` DROP COLUMN `shot_type`, DROP COLUMN `plot`, DROP COLUMN `dialogue`;
