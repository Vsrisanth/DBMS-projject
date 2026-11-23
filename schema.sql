-- =====================================================================
-- Civic Connects - Complete MySQL / TiDB Database Schema & Seed Data
-- Database Engine: MySQL / TiDB Cloud (InnoDB, UTF-8)
-- NOTE: Strictly NON-DESTRUCTIVE schema definition.
--       All DROP TABLE and destructive operations are prohibited.
-- =====================================================================

-- ---------------------------------------------------------------------
-- Table: users
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `users` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(120) NOT NULL,
  `email` VARCHAR(150) NOT NULL UNIQUE,
  `phone` VARCHAR(25) NOT NULL,
  `address` TEXT NULL,
  `avatar_url` VARCHAR(500) NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `role` ENUM('citizen', 'admin') NOT NULL DEFAULT 'citizen',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_users_email` (`email`),
  INDEX `idx_users_role` (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Table: departments
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `departments` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(120) NOT NULL UNIQUE,
  `contact_email` VARCHAR(150) NULL,
  `description` VARCHAR(255) NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Table: complaints
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `complaints` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `ticket_number` VARCHAR(30) NOT NULL UNIQUE,
  `user_id` INT NOT NULL,
  `category` VARCHAR(80) NOT NULL,
  `title` VARCHAR(200) NOT NULL DEFAULT '',
  `description` TEXT NOT NULL,
  `location` TEXT NOT NULL,
  `latitude` DECIMAL(10, 8) NULL,
  `longitude` DECIMAL(11, 8) NULL,
  `image_url` VARCHAR(500) NULL,
  `department_id` INT NULL,
  `status` ENUM('pending', 'in_progress', 'resolved', 'rejected') NOT NULL DEFAULT 'pending',
  `admin_remarks` TEXT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_complaints_ticket` (`ticket_number`),
  INDEX `idx_complaints_status` (`status`),
  INDEX `idx_complaints_category` (`category`),
  INDEX `idx_complaints_user_id` (`user_id`),
  INDEX `idx_complaints_dept` (`department_id`),
  INDEX `idx_complaints_created` (`created_at`),
  CONSTRAINT `fk_complaints_user`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_complaints_department`
    FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Table: complaint_logs (Audit Trail for Status Changes & Notes)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `complaint_logs` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `complaint_id` INT NOT NULL,
  `admin_id` INT NULL,
  `previous_status` VARCHAR(30) NULL,
  `new_status` VARCHAR(30) NOT NULL,
  `notes` TEXT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_logs_complaint`
    FOREIGN KEY (`complaint_id`) REFERENCES `complaints` (`id`)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_logs_admin`
    FOREIGN KEY (`admin_id`) REFERENCES `users` (`id`)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Table: feedbacks (Anonymous Citizen Feedback & Bug Reporting)
-- Strict Anonymity Requirement: No user_id, user_name, email, or IP address stored.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `feedbacks` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `feedback_type` VARCHAR(50) NOT NULL,
  `subject` VARCHAR(200) NOT NULL,
  `message` TEXT NOT NULL,
  `severity` VARCHAR(20) NOT NULL DEFAULT 'medium',
  `status` VARCHAR(20) NOT NULL DEFAULT 'unread',
  `admin_notes` TEXT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_feedback_status` (`status`),
  INDEX `idx_feedback_type` (`feedback_type`),
  INDEX `idx_feedback_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Table: contact_messages (Citizen & Visitor Inquiries via Landing Form)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `contact_messages` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(120) NOT NULL,
  `email` VARCHAR(150) NOT NULL,
  `subject` VARCHAR(200) NOT NULL DEFAULT 'General Inquiry',
  `message` TEXT NOT NULL,
  `status` VARCHAR(20) NOT NULL DEFAULT 'unread',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_contact_status` (`status`),
  INDEX `idx_contact_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- PRODUCTION CORE SEED DATA
-- Passwords:
--   Admin: Admin@123
-- =====================================================================

-- 1. Insert Core Municipal Departments (Ignored if already exists)
INSERT IGNORE INTO `departments` (`id`, `name`, `contact_email`, `description`) VALUES
(1, 'Roads & Highways Department', 'roads@civicconnects.gov', 'Potholes, asphalt resurfacing, road debris, and sidewalk maintenance'),
(2, 'City Electricity & Power Board', 'electricity@civicconnects.gov', 'Power outages, transformer sparks, open junction boxes, and grid safety'),
(3, 'Water Supply & Sewerage Board', 'water@civicconnects.gov', 'Pipeline bursts, water contamination, low pressure, and sewage leakage'),
(4, 'Solid Waste & Sanitation', 'sanitation@civicconnects.gov', 'Garbage dumping, overflowing dumpsters, and commercial waste clearance'),
(5, 'Urban Drainage & Flood Control', 'drainage@civicconnects.gov', 'Stormwater drainage blockages, canal siltation, and flood mitigation'),
(6, 'Street Lighting & Signals', 'lighting@civicconnects.gov', 'Non-functional streetlights, timer issues, and traffic signal repairs'),
(7, 'Public Works & Parks', 'publicworks@civicconnects.gov', 'Public parks, playground equipment, hazardous tree branches, and civic structures');

-- 2. Insert Default Municipal Administrator Account (Ignored if already exists)
-- Email: admin@gmail.com
-- Password: admin@1234 (hashed with Werkzeug security scrypt)
-- Phone: 9876543210 (Standard 10-digit Indian format)
INSERT IGNORE INTO `users` (`id`, `name`, `email`, `phone`, `address`, `password_hash`, `role`, `created_at`) VALUES
(1, 'Civic Admin Officer', 'admin@gmail.com', '9876543210', 'City Hall, 100 Civic Center Plaza, Suite 400', 'scrypt:32768:8:1$lgxu3UT0wzPHsVjr$dae478c4baedc2e91f8907c262d56556cd6802c24bd3db3d6bee372cd0eb463f4c535b615447fc1383f4793a0b2dc58b874a8a3dc1802bf7a343470191f2ab3a', 'admin', NOW());

