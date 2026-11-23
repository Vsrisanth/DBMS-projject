# Civic Connects - Municipal Citizen Grievance Redressal System

An enterprise-grade, full-stack municipal grievance web application built with **Python Flask, Vanilla HTML5/CSS3/JavaScript, and MySQL**.

Designed with clean typography (Plus Jakarta Sans & Inter), a light civic palette, role-based portals (Citizen & Municipal Authority), dynamic 4-step milestone tracking, geolocation tagging, and secure audit trails.

---

## 🏛️ Quick Start Guide

### 1. Requirements & Dependencies
Ensure Python 3.10+ is installed. Install dependencies using:
```bash
pip install -r requirements.txt
```

### 2. Database Setup (MySQL / MariaDB)
1. Start your MySQL service (e.g., via **XAMPP Control Panel** or native `mysqld`).
2. Run the initialization utility:
```bash
python init_db.py
```
This automatically runs `schema.sql`, creates the `civic_connects` database, sets up foreign key constraints, and seeds default municipal departments, users, and realistic sample complaints.

> **Zero-Config Fallback:** If MySQL is not running on your machine, Civic Connects automatically uses its localized SQLite fallback database (`civic_connects.db`) with full schema synchronization so you can evaluate the entire application immediately without setup friction.

### 3. Launch the Application
Start the Flask development server:
```bash
python app.py
```
Open your browser and navigate to:
👉 **`http://127.0.0.1:5000`**

---

## 🔑 Default Credentials (Pre-Seeded)

| Portal Role | Email | Password | Access / Clearance |
| :--- | :--- | :--- | :--- |
| **Municipal Authority (Admin)** | `admin@civicconnects.gov` | `Admin@123` | Full triage, dispatch, remarks, metrics |
| **Resident Citizen** | `citizen@example.com` | `Citizen@123` | File grievances, track status, photo upload |
| **Alternative Citizen** | `marcus.vance@example.com` | `Citizen@123` | Ward 12 resident account |

*Note: For new Authority/Admin registrations, the Municipal Clearance Key is:* **`CIVIC-ADMIN-2026`**

---

## 🚀 Key Features

### 1. Dedicated Dual-Role Authentication
- Dual-pill segmented toggle: **[ Citizen ]** | **[ Admin ]** matching reference specifications.
- Dynamically updates hidden form state, button labels, and clearance fields.
- Password visibility toggle (eye icon).
- Passwords hashed using `werkzeug.security` (`scrypt`).

### 2. Citizen Portal
- **Dashboard Overview:** Live KPI counters (Total, Pending, In Progress, Resolved).
- **Issue Submission (`/report-issue`):** 
  - Municipal category selector.
  - Geolocation capture button ("Detect My Location") via browser GPS API.
  - Drag-and-drop proof image uploader with instant thumbnail preview.
- **Milestone Tracking (`/my-complaints`):**
  - Dynamic 4-step timeline: `Submitted` ➔ `Under Review` ➔ `In Progress` ➔ `Resolved`.
  - Search and filter by status and ticket number.
  - Review official municipal remarks and assigned departments.
- **Citizen Profile (`/citizen/profile`):** Update contact info and change passwords securely.

### 3. Municipal Authority Portal (Admin)
- **Executive Command Center (`/admin/dashboard`):** Real-time analytics, resolution rate KPI, category breakdown progress bars.
- **Complaint Management Table (`/admin/complaints`):** Filter by status, category, department, and search by citizen details.
- **Action / Triage Modal:**
  - Inspect uploaded evidence image with zoom preview.
  - Verify citizen contact info & GPS coordinates.
  - Update status (`pending`, `in_progress`, `resolved`, `rejected`).
  - Assign to designated municipal department.
  - Publish official resolution remarks.
- **Departments & Users Management:** View active workloads per municipal department.

---

## 🗄️ Database Schema Design (`schema.sql`)

- **`users`**: `id`, `name`, `email` (UNIQUE), `phone`, `address`, `password_hash`, `role` (`'citizen'`, `'admin'`), `created_at`.
- **`departments`**: `id`, `name` (UNIQUE), `contact_email`, `description`, `created_at`.
- **`complaints`**: `id`, `ticket_number` (UNIQUE `#CC-XXXX`), `user_id` (FK), `category`, `title`, `description`, `location`, `latitude`, `longitude`, `image_url`, `department_id` (FK), `status` (ENUM), `admin_remarks`, `created_at`, `updated_at`.
- **`complaint_logs`**: `id`, `complaint_id` (FK), `admin_id` (FK), `previous_status`, `new_status`, `notes`, `created_at`.

---

## 🧪 Automated Test Suite
Run the test suite to verify all endpoints, authentication, and file upload flows:
```bash
python -m unittest tests/test_app.py
```
All 10 test suites run in under 2 seconds.
