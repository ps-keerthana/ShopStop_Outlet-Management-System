-- ================================================================
--  CS 432 Assignment 2 - Module B
--  ShopStop: Core System Tables + SQL Indexes
--
--  HOW TO RUN:
--    Step 1: Open MySQL Command Line Client
--    Step 2: Type your password
--    Step 3: Run:  source C:/path/to/shopstop.sql
--    Step 4: Run:  source C:/path/to/schema_moduleB.sql
-- ================================================================

USE ShopStop;

UPDATE Promotion 
SET StartDate = '2026-03-01', EndDate = '2026-12-31' 
WHERE IsActive = TRUE;


-- Core Table 1: User login credentials (separate from business tables)
DROP TABLE IF EXISTS GroupMapping;
DROP TABLE IF EXISTS UserCredentials;

CREATE TABLE UserCredentials (
    UserID       INT AUTO_INCREMENT PRIMARY KEY,
    MemberID     VARCHAR(10) DEFAULT NULL,
    EmployeeID   VARCHAR(10) DEFAULT NULL,
    Username     VARCHAR(50)  NOT NULL UNIQUE,
    PasswordHash VARCHAR(255) NOT NULL,
    Role         ENUM('admin','user') NOT NULL DEFAULT 'user',
    CreatedAt    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (MemberID)   REFERENCES Member(MemberID)     ON DELETE CASCADE,
    FOREIGN KEY (EmployeeID) REFERENCES Employee(EmployeeID) ON DELETE CASCADE
);

-- Core Table 2: Group membership for portfolio feature
CREATE TABLE GroupMapping (
    MappingID  INT AUTO_INCREMENT PRIMARY KEY,
    MemberID   VARCHAR(10) NOT NULL,
    GroupName  VARCHAR(100) NOT NULL,
    JoinedAt   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (MemberID) REFERENCES Member(MemberID) ON DELETE CASCADE,
    UNIQUE KEY uq_member_group (MemberID, GroupName)
);

-- Seed login users (passwords set by /init-passwords route)
INSERT IGNORE INTO UserCredentials (MemberID, EmployeeID, Username, PasswordHash, Role) VALUES
    (NULL,     'EMP001',  'admin',  'PLACEHOLDER', 'admin'),
    ('MEM001',  NULL,     'rajesh', 'PLACEHOLDER', 'user'),
    ('MEM002',  NULL,     'priya',  'PLACEHOLDER', 'user'),
    ('MEM003',  NULL,     'amit',   'PLACEHOLDER', 'user'),
    ('MEM004',  NULL,     'sneha',  'PLACEHOLDER', 'user'),
    ('MEM005',  NULL,     'vikram', 'PLACEHOLDER', 'user');

-- Seed group memberships
INSERT IGNORE INTO GroupMapping (MemberID, GroupName) VALUES
    ('MEM001', 'Group 15'),
    ('MEM002', 'Group 15'),
    ('MEM003', 'Group 15'),
    ('MEM004', 'Group 15'),
    ('MEM005', 'Group 15');

-- ================================================================
-- SQL INDEXES (SubTask 4)
-- Each index targets WHERE/JOIN/ORDER BY in our API queries
-- ================================================================

CREATE INDEX idx_product_category  ON Product(CategoryID);
CREATE INDEX idx_product_supplier  ON Product(SupplierID);
CREATE INDEX idx_sale_date         ON Sale(SaleDate);
CREATE INDEX idx_sale_member       ON Sale(MemberID);
CREATE INDEX idx_saleitem_sale     ON SaleItem(SaleID);
CREATE INDEX idx_saleitem_product  ON SaleItem(ProductID);
CREATE INDEX idx_inventory_product ON Inventory(ProductID);
CREATE INDEX idx_order_status      ON PurchaseOrder(OrderStatus);
CREATE INDEX idx_order_supplier    ON PurchaseOrder(SupplierID);
CREATE INDEX idx_member_type       ON Member(MembershipType);
CREATE INDEX idx_pp_product        ON ProductPromotion(ProductID);
CREATE INDEX idx_pp_promotion      ON ProductPromotion(PromotionID);

SELECT 'Schema_moduleB.sql loaded successfully!' AS Status;
