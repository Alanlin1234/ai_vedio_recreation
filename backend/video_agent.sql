/*
 Navicat Premium Data Transfer

 Source Server         : localhost_3306
 Source Server Type    : MySQL
 Source Server Version : 80026 (8.0.26)
 Source Host           : localhost:3306
 Source Schema         : video_agent

 Target Server Type    : MySQL
 Target Server Version : 80026 (8.0.26)
 File Encoding         : 65001

 Date: 13/07/2025 09:05:00
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for douyin_authors
-- ----------------------------
DROP TABLE IF EXISTS `douyin_authors`;
CREATE TABLE `douyin_authors`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `nickname` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '昵称',
  `followers_count` int NULL DEFAULT NULL COMMENT '粉丝数',
  `following_count` int NULL DEFAULT NULL COMMENT '关注数',
  `total_favorited` int NULL DEFAULT NULL COMMENT '获赞数',
  `signature` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '个人简介',
  `sec_uid` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT 'sec_uid',
  `uid` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT 'uid',
  `unique_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT 'unique_id',
  `cover_url` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '封面图片链接',
  `avatar_larger_url` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '头像图片链接',
  `share_url` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '分享链接',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uid`(`uid` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 15 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for douyin_videos
-- ----------------------------
DROP TABLE IF EXISTS `douyin_videos`;
CREATE TABLE `douyin_videos`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `duration` int NULL DEFAULT NULL,
  `video_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `video_uri` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `play_count` int NULL DEFAULT NULL,
  `digg_count` int NULL DEFAULT NULL,
  `comment_count` int NULL DEFAULT NULL,
  `share_count` int NULL DEFAULT NULL,
  `collect_count` int NULL DEFAULT NULL,
  `dynamic_cover_url` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `author_nickname` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `author_unique_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `author_uid` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `author_signature` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `author_follower_count` int NULL DEFAULT NULL,
  `author_following_count` int NULL DEFAULT NULL,
  `author_total_favorited` int NULL DEFAULT NULL,
  `video_quality_high` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `video_quality_medium` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `video_quality_low` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `tags` json NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `local_file_path` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '本地存储路径',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `video_id`(`video_id` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 61 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for recreation_logs
-- ----------------------------
DROP TABLE IF EXISTS `recreation_logs`;
CREATE TABLE `recreation_logs`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `recreation_id` int NOT NULL COMMENT '关联video_recreations表',
  `scene_id` int NULL DEFAULT NULL COMMENT '关联recreation_scenes表(可选)',
  `log_level` enum('info','warning','error') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT 'info',
  `step_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '处理步骤名称',
  `message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '日志消息',
  `error_details` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '错误详情',
  `processing_time` float NULL DEFAULT NULL COMMENT '处理耗时(秒)',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `scene_id`(`scene_id` ASC) USING BTREE,
  INDEX `idx_recreation_log`(`recreation_id` ASC, `created_at` ASC) USING BTREE,
  CONSTRAINT `recreation_logs_ibfk_1` FOREIGN KEY (`recreation_id`) REFERENCES `video_recreations` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `recreation_logs_ibfk_2` FOREIGN KEY (`scene_id`) REFERENCES `recreation_scenes` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 38 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for recreation_scenes
-- ----------------------------
DROP TABLE IF EXISTS `recreation_scenes`;
CREATE TABLE `recreation_scenes`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `recreation_id` int NOT NULL COMMENT '关联video_recreations表',
  `scene_index` int NOT NULL COMMENT '场景序号',
  `start_time` float NOT NULL COMMENT '开始时间(秒)',
  `end_time` float NOT NULL COMMENT '结束时间(秒)',
  `duration` float NOT NULL COMMENT '场景时长(秒)',
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '场景描述',
  `video_prompt` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '视频生成提示词',
  `technical_params` json NULL COMMENT '技术参数(分辨率、帧率等)',
  `style_elements` json NULL COMMENT '风格元素',
  `prompt_generation_model` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '提示词生成模型',
  `generated_video_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '单个场景生成的视频文件路径',
  `generation_status` enum('pending','processing','completed','failed') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT 'pending',
  `generation_task_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '外部服务任务ID',
  `generation_service` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '视频生成服务',
  `video_file_size` bigint NULL DEFAULT NULL COMMENT '场景视频文件大小',
  `video_resolution` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '场景视频分辨率',
  `video_fps` int NULL DEFAULT NULL COMMENT '场景视频帧率',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `generation_completed_at` timestamp NULL DEFAULT NULL COMMENT '生成完成时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_recreation_scene`(`recreation_id` ASC, `scene_index` ASC) USING BTREE,
  CONSTRAINT `recreation_scenes_ibfk_1` FOREIGN KEY (`recreation_id`) REFERENCES `video_recreations` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 18 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for video_recreations
-- ----------------------------
DROP TABLE IF EXISTS `video_recreations`;
CREATE TABLE `video_recreations`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `original_video_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '原视频ID',
  `recreation_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '二创项目名称',
  `status` enum('pending','processing','completed','failed') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT 'pending' COMMENT '处理状态',
  `video_understanding` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '视频内容理解结果',
  `understanding_model` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '理解模型名称',
  `understanding_time_cost` float NULL DEFAULT NULL COMMENT '理解耗时(秒)',
  `audio_file_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '音频文件路径',
  `transcription_text` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '转录文本内容',
  `transcription_service` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '转录服务',
  `new_script_content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '新文案内容',
  `script_generation_model` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '文案生成模型',
  `tts_audio_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT 'TTS音频文件路径',
  `tts_service` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT 'TTS服务',
  `tts_voice_model` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '语音模型',
  `tts_audio_duration` float NULL DEFAULT NULL COMMENT 'TTS音频时长(秒)',
  `final_video_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '最终合成视频文件路径',
  `final_video_with_audio_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '音画同步后的最终视频路径',
  `composition_status` enum('pending','processing','completed','failed') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT 'pending' COMMENT '视频合成状态',
  `total_duration` float NULL DEFAULT NULL COMMENT '最终视频总时长(秒)',
  `final_file_size` bigint NULL DEFAULT NULL COMMENT '最终视频文件大小(字节)',
  `video_resolution` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '最终视频分辨率',
  `video_fps` int NULL DEFAULT NULL COMMENT '最终视频帧率',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `completed_at` timestamp NULL DEFAULT NULL COMMENT '完成时间',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 7 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;
