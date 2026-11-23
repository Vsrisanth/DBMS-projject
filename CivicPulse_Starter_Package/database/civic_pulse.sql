-- =====================================================================
-- Civic Connects - Complete MySQL Database Schema & Seed Data
-- Database Engine: MySQL / MariaDB (InnoDB, UTF-8)
-- =====================================================================

CREATE DATABASE IF NOT EXISTS `civic_connects`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `civic_connects`;

-- ---------------------------------------------------------------------
-- Table: users
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `users` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(120) NOT NULL,
  `email` VARCHAR(150) NOT NULL UNIQUE,
  `phone` VARCHAR(25) NOT NULL,
  `address` TEXT NULL,
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
  `image_url` VARCHAR(255) NULL,
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
-- SEED DATA
-- Passwords:
--   Admin:   Admin@123
--   Citizen: Citizen@123
-- ---------------------------------------------------------------------
INSERT IGNORE INTO `departments` (`id`, `name`, `contact_email`, `description`) VALUES
(1, 'Roads & Highways Department', 'roads@civicconnects.gov', 'Potholes, asphalt resurfacing, road debris, and sidewalk maintenance'),
(2, 'City Electricity & Power Board', 'electricity@civicconnects.gov', 'Power outages, transformer sparks, open junction boxes, and grid safety'),
(3, 'Water Supply & Sewerage Board', 'water@civicconnects.gov', 'Pipeline bursts, water contamination, low pressure, and sewage leakage'),
(4, 'Solid Waste & Sanitation', 'sanitation@civicconnects.gov', 'Garbage dumping, overflowing dumpsters, and commercial waste clearance'),
(5, 'Urban Drainage & Flood Control', 'drainage@civicconnects.gov', 'Stormwater drainage blockages, canal siltation, and flood mitigation'),
(6, 'Street Lighting & Signals', 'lighting@civicconnects.gov', 'Non-functional streetlights, timer issues, and traffic signal repairs'),
(7, 'Public Works & Parks', 'publicworks@civicconnects.gov', 'Public parks, playground equipment, hazardous tree branches, and civic structures');

INSERT IGNORE INTO `users` (`id`, `name`, `email`, `phone`, `address`, `password_hash`, `role`, `created_at`) VALUES
(1, 'Civic Admin Officer', 'admin@civicconnects.gov', '+1 (555) 019-2834', 'City Hall, 100 Civic Center Plaza, Suite 400', 'scrypt:32768:8:1$S3B1DkkE7rxNNIaJ$d2eecf4feba92e277fd45941f3c4e805243a92583d6e9d0df66379081d4834c49f8863398b9ff357e1de740a94f5bd69abfcb413d0fdded8dbe9cf66f3f24da5', 'admin', NOW() - INTERVAL 30 DAY),
(2, 'Jane Citizen', 'citizen@example.com', '+1 (555) 014-9821', '742 Evergreen Terrace, Sector 4, Civic Heights', 'scrypt:32768:8:1$GoZFt4MYPvRKauzK$0d8b0f02cacdfc935d61d4bdd4d6786400e72d745c998321a0d0512296cb3dd7cc9458dfe1ae2097d8e9113f8fb74ad1b6d66326a75c159d43be8fc54fa434cc', 'citizen', NOW() - INTERVAL 20 DAY),
(3, 'Marcus Vance', 'marcus.vance@example.com', '+1 (555) 018-4412', '108 Pine Crest Ave, Ward 12', 'scrypt:32768:8:1$GoZFt4MYPvRKauzK$0d8b0f02cacdfc935d61d4bdd4d6786400e72d745c998321a0d0512296cb3dd7cc9458dfe1ae2097d8e9113f8fb74ad1b6d66326a75c159d43be8fc54fa434cc', 'citizen', NOW() - INTERVAL 15 DAY);

INSERT IGNORE INTO `complaints` (`id`, `ticket_number`, `user_id`, `category`, `title`, `description`, `location`, `latitude`, `longitude`, `image_url`, `department_id`, `status`, `admin_remarks`, `created_at`, `updated_at`) VALUES
(1, '#CC-8421', 2, 'Road Damage', 'Severe Potholes and Asphalt Crumbling on Oak Street', 'Multiple deep craters along the westbound lane making vehicular commute hazardous. Two two-wheelers skidded yesterday evening.', 'Corner of Oak Street & 5th Avenue, Ward 4', 37.774929, -122.419416, 'sample_pothole.jpg', 1, 'pending', 'Under preliminary review by civil road inspection team.', NOW() - INTERVAL 3 DAY, NOW() - INTERVAL 2 DAY),
(2, '#CC-9102', 2, 'Water Supply', 'Main Water Line Burst Causing Street Flooding', 'A high-pressure municipal main line ruptured near the subway entrance. Potable water is flooding the street and 30 residential homes have zero water pressure.', 'Block C, Metro Avenue, near Central Park Gate 2', 37.783333, -122.416667, 'sample_waterleak.jpg', 3, 'in_progress', 'Emergency repair crew dispatched on-site. Isolation valve shut off. Pipe replacement underway.', NOW() - INTERVAL 2 DAY, NOW() - INTERVAL 4 HOUR),
(3, '#CC-7341', 2, 'Electricity', 'Overhead High-Voltage Wire Sparking During Rain', 'Frayed electrical cable hanging dangerously close to a pedestrian footpath near the bus shelter. Sparking observed during rainfall.', 'Lane 12, Sunrise Residential Enclave', 37.768900, -122.428500, 'sample_sparking.jpg', 2, 'resolved', 'Emergency lineman team dispatched. Insulators replaced, line tensioned and certified safe by regional electrical inspector.', NOW() - INTERVAL 7 DAY, NOW() - INTERVAL 1 DAY),
(4, '#CC-6523', 3, 'Garbage Management', 'Illegal Waste Dumping and Overflowing Commercial Dumpster', 'A large commercial dump pile has accumulated across 40 feet of roadside. Foul odor and stray dog menace affecting adjacent school campus.', 'Behind Main Market Complex, Sector 9', 37.755000, -122.435000, 'sample_dumping.jpg', 4, 'in_progress', 'Sanitation truck assigned. Bulk clearance scheduled for tomorrow morning 6:00 AM.', NOW() - INTERVAL 4 DAY, NOW() - INTERVAL 12 HOUR),
(5, '#CC-5219', 3, 'Streetlight Failure', 'Dark Stretch - 6 Consecutive LED Streetlights Inactive', 'The entire stretch from 3rd Avenue to 7th Avenue has no streetlights functioning for the past week, leading to safety concerns after dark.', 'Maple Boulevard between 3rd and 7th St', 37.762100, -122.410200, NULL, 6, 'resolved', 'Defective photoelectric controller replaced. All 6 luminaires tested and operational.', NOW() - INTERVAL 10 DAY, NOW() - INTERVAL 5 DAY),
(6, '#CC-4110', 3, 'Drainage', 'Uncovered Deep Drainage Pit on Pedestrian Walkway', 'Storm drain cover is broken and missing. Deep concrete pit poses immediate risk to schoolchildren and evening joggers.', 'Opposite St. Jude Community School, North Gate', 37.790100, -122.405300, NULL, NULL, 'pending', 'Complaint logged and flagged for urgent barrier placement.', NOW() - INTERVAL 1 DAY, NOW() - INTERVAL 1 DAY);

INSERT IGNORE INTO `complaint_logs` (`complaint_id`, `admin_id`, `previous_status`, `new_status`, `notes`, `created_at`) VALUES
(2, 1, 'pending', 'in_progress', 'Assigned to Water Supply & Sewerage Board. Crew on-site.', NOW() - INTERVAL 1 DAY),
(3, 1, 'pending', 'in_progress', 'High priority electrical hazard. Dispatched emergency crew.', NOW() - INTERVAL 6 DAY),
(3, 1, 'in_progress', 'resolved', 'Hazard mitigated. Line secured and re-energized safely.', NOW() - INTERVAL 1 DAY),
(4, 1, 'pending', 'in_progress', 'Forwarded to Sanitation division supervisor for vehicle routing.', NOW() - INTERVAL 2 DAY),
(5, 1, 'pending', 'in_progress', 'Work order issued to Lighting contractor.', NOW() - INTERVAL 8 DAY),
(5, 1, 'in_progress', 'resolved', 'Repairs completed and verified.', NOW() - INTERVAL 5 DAY);
