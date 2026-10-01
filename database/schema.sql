CREATE DATABASE IF NOT EXISTS jobtrack;
USE jobtrack;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS applications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    company VARCHAR(150) NOT NULL,
    role VARCHAR(150) NOT NULL,
    location VARCHAR(150),
    job_type ENUM('Full Time','Part Time','Internship','Contract','Remote') DEFAULT 'Full Time',
    salary VARCHAR(100),
    application_date DATE NOT NULL,
    job_url VARCHAR(500),
    status ENUM('Applied','Shortlisted','Interview','Selected','Rejected','Withdrawn') DEFAULT 'Applied',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_favorite TINYINT(1) NOT NULL DEFAULT 0,
    follow_up_date DATE NULL,
    follow_up_status VARCHAR(20) NOT NULL DEFAULT 'Pending',
    resume_version VARCHAR(120) NULL,
    recruiter_name VARCHAR(120) NULL,
    recruiter_email VARCHAR(180) NULL,
    recruiter_phone VARCHAR(40) NULL,
    CONSTRAINT fk_app_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_app_user_status (user_id,status),
    INDEX idx_app_user_date (user_id,application_date),
    INDEX idx_app_followup (user_id,follow_up_date,follow_up_status)
);

CREATE TABLE IF NOT EXISTS interviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    application_id INT NOT NULL,
    interview_date DATE NOT NULL,
    interview_time TIME NULL,
    round_name VARCHAR(100),
    mode ENUM('Online','Offline','Phone') DEFAULT 'Online',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_interview_app FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE,
    INDEX idx_interview_app_date (application_id,interview_date)
);

CREATE TABLE IF NOT EXISTS application_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    application_id INT NOT NULL,
    old_status VARCHAR(50),
    new_status VARCHAR(50) NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_history_app_final FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE,
    INDEX idx_history_app_date_final (application_id,changed_at)
);
