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

### 2. Environment Configuration
Create your `.env` file from the provided `.env.example`:
```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```
Edit `.env` and set your MySQL server credentials (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`).

### 3. Database Setup (MySQL / MariaDB)
1. Start your MySQL service (e.g., via **XAMPP Control Panel** or native `mysqld`).
2. Run the initialization utility:
```bash
python init_db.py
```
This automatically runs `schema.sql`, creates the `civic_connects` database, sets up foreign key constraints, and seeds default municipal departments, users, and realistic sample complaints.

> **Zero-Config Fallback:** If MySQL is not running on your machine, Civic Connects automatically uses its localized SQLite fallback database (`civic_connects.db`) with full schema synchronization so you can evaluate the entire application immediately without setup friction.

### 4. Launch the Application
Start the Flask development server:
```bash
python app.py
```
Open your browser and navigate to:
👉 **`http://127.0.0.1:5000`**

---

## 🔑 Initial Administrator Credentials

| Portal Role | Email | Password | Access / Clearance |
| :--- | :--- | :--- | :--- |
| **Municipal Authority (Admin)** | `admin@gmail.com` | `admin@1234` | Full triage, dispatch, remarks, metrics |

*Note: Resident citizens register their own accounts directly via the **Create Account** button on the Citizen Portal.*
*Administrative access is restricted to pre-provisioned accounts; public/self-registration for Administrator accounts is disabled.*

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

## ☁️ Deployment Guide: Render + TiDB Cloud + Cloudinary

### 1. Database Setup: TiDB Cloud (Serverless)
1. Sign up / Log in to [TiDB Cloud](https://tidbcloud.com/).
2. Create a free **Serverless Cluster**.
3. In the cluster dashboard, under **Security**, ensure IP Access allows incoming traffic from `0.0.0.0/0` (Render's dynamic IPs).
4. Click **Connect** and select **Connect with MySQL CLI / Driver**.
5. Note down your credentials:
   - `Host` (e.g. `gateway01.us-east-1.prod.aws.tidbcloud.com`)
   - `Port` (`4000`)
   - `User` (e.g. `<cluster_prefix>.root`)
   - `Password`
   - `Database Name` (`civic_connects` or your default database)

### 2. Ephemeral Storage: Cloudinary
1. Sign up / Log in to [Cloudinary](https://cloudinary.com/).
2. In the dashboard, copy:
   - `Cloud Name`
   - `API Key`
   - `API Secret`

### 3. Deploy on Render
1. Create a new **Web Service** on [Render](https://render.com/) connected to your GitHub repository.
2. Select runtime: **Python 3**.
3. Configure commands:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
4. Add the following **Environment Variables** in the Render Dashboard:
   - `FLASK_ENV`: `production`
   - `SECRET_KEY`: `<generate-a-strong-secret-key>`
   - `DB_MODE`: `tidb`
   - `DB_HOST`: `<your-tidb-cloud-host>`
   - `DB_PORT`: `4000`
   - `DB_USER`: `<your-tidb-user>`
   - `DB_PASSWORD`: `<your-tidb-password>`
   - `DB_NAME`: `civic_connects`
   - `CLOUDINARY_CLOUD_NAME`: `<your-cloudinary-cloud-name>`
   - `CLOUDINARY_API_KEY`: `<your-cloudinary-api-key>`
   - `CLOUDINARY_API_SECRET`: `<your-cloudinary-api-secret>`
5. Initialize the database schema and baseline departments by running the following in the Render Shell:
   ```bash
   python init_db.py
   ```

---

## 🧪 Automated Test Suite
Run the test suites to verify all endpoints, database safety, authentication, and deployment readiness:
```bash
python -m unittest discover -s tests -p "test_*.py"
```
All tests execute in sandbox with 100% pass rate.
