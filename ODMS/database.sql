/* ODMS - Microsoft SQL Server database
   Run this script in SQL Server Management Studio (SSMS).
*/
IF DB_ID(N'ODMS') IS NULL
BEGIN
    CREATE DATABASE ODMS;
END
GO
USE ODMS;
GO

IF OBJECT_ID('dbo.Users','U') IS NULL
BEGIN
CREATE TABLE dbo.Users (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL,
    email NVARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(10) NOT NULL,
    age INT NOT NULL CHECK (age BETWEEN 1 AND 100),
    gender NVARCHAR(20) NOT NULL,
    role NVARCHAR(20) NOT NULL CHECK (role IN ('Donor','Recipient')),
    blood_group NVARCHAR(5) NOT NULL,
    city NVARCHAR(100) NOT NULL,
    password_hash NVARCHAR(255) NOT NULL,
    organ NVARCHAR(50) NULL,
    availability NVARCHAR(30) NULL,
    requested_organ NVARCHAR(50) NULL,
    urgency NVARCHAR(30) NULL,
    registered_at DATETIME2 NOT NULL DEFAULT SYSDATETIME()
);
END
GO

IF OBJECT_ID('dbo.Admins','U') IS NULL
BEGIN
CREATE TABLE dbo.Admins (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL,
    email NVARCHAR(255) NOT NULL UNIQUE,
    password_hash NVARCHAR(255) NOT NULL,
    is_active BIT NOT NULL DEFAULT 1,
    created_at DATETIME2 NOT NULL DEFAULT SYSDATETIME()
);
END
GO

IF OBJECT_ID('dbo.OrganRequests','U') IS NULL
BEGIN
CREATE TABLE dbo.OrganRequests (
    id INT IDENTITY(1,1) PRIMARY KEY,
    recipient_id INT NOT NULL,
    organ NVARCHAR(50) NOT NULL,
    urgency NVARCHAR(30) NOT NULL,
    notes NVARCHAR(MAX) NULL,
    status NVARCHAR(50) NOT NULL DEFAULT 'Pending',
    requested_at DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT FK_OrganRequests_Recipient FOREIGN KEY (recipient_id) REFERENCES dbo.Users(id)
);
END
GO

IF OBJECT_ID('dbo.Notifications','U') IS NULL
BEGIN
CREATE TABLE dbo.Notifications (
    id INT IDENTITY(1,1) PRIMARY KEY,
    email NVARCHAR(255) NOT NULL,
    message NVARCHAR(500) NOT NULL,
    notification_type NVARCHAR(30) NOT NULL DEFAULT 'info',
    date_created DATETIME2 NOT NULL DEFAULT SYSDATETIME()
);
END
GO

IF OBJECT_ID('dbo.Activities','U') IS NULL
BEGIN
CREATE TABLE dbo.Activities (
    id INT IDENTITY(1,1) PRIMARY KEY,
    activity_type NVARCHAR(50) NOT NULL,
    name NVARCHAR(100) NOT NULL,
    email NVARCHAR(255) NOT NULL,
    role NVARCHAR(30) NOT NULL,
    details NVARCHAR(500) NULL,
    date_created DATETIME2 NOT NULL DEFAULT SYSDATETIME()
);
END
GO

/* Demo admin account.
   Password: admin123
   The application setup script inserts the correctly hashed value.
*/
GO
