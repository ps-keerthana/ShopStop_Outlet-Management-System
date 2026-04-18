-- ================================================================
--  CS 432 Assignment 4 – Sharding Setup for ShopStop
--  Group: Nexus
--  Database: Nexus (same name on all 3 shards)
--
--  SHARD KEY: MemberID (hash-based, 3 shards)
--    shard_id = CONV(SUBSTR(MD5(MemberID), 1, 8), 16, 10) % 3
--    (In Python: int(hashlib.md5(member_id.encode()).hexdigest()[:8], 16) % 3)
--
--  Shard 0 → Port 3307
--  Shard 1 → Port 3308
--  Shard 2 → Port 3309
--
--  HOW TO RUN:
--    Connect to EACH shard and run this file:
--      mysql -h 10.0.116.184 -P 3307 -u Nexus -p Nexus < shard_setup.sql
--      mysql -h 10.0.116.184 -P 3308 -u Nexus -p Nexus < shard_setup.sql
--      mysql -h 10.0.116.184 -P 3309 -u Nexus -p Nexus < shard_setup.sql
-- ================================================================

USE Nexus;

-- ----------------------------------------------------------------
-- Drop existing shard tables (clean slate)
-- ----------------------------------------------------------------
DROP TABLE IF EXISTS SaleItem;
DROP TABLE IF EXISTS Sale;
DROP TABLE IF EXISTS Member;
DROP TABLE IF EXISTS ShardMeta;

-- ----------------------------------------------------------------
-- ShardMeta: records which shard this node is (self-documenting)
-- ----------------------------------------------------------------
CREATE TABLE ShardMeta (
    shard_id   INT PRIMARY KEY,
    port       INT NOT NULL,
    description VARCHAR(100)
);

-- NOTE: Run the matching INSERT below only on the right shard
-- On shard at port 3307: INSERT INTO ShardMeta VALUES (0, 3307, 'Shard 0 – MemberIDs hashing to 0');
-- On shard at port 3308: INSERT INTO ShardMeta VALUES (1, 3308, 'Shard 1 – MemberIDs hashing to 1');
-- On shard at port 3309: INSERT INTO ShardMeta VALUES (2, 3309, 'Shard 2 – MemberIDs hashing to 2');

-- ----------------------------------------------------------------
-- Member table (sharded by MemberID hash)
-- ----------------------------------------------------------------
CREATE TABLE Member (
    MemberID        VARCHAR(10)  PRIMARY KEY,
    Name            VARCHAR(100) NOT NULL,
    Age             INT          NOT NULL CHECK (Age >= 18),
    Email           VARCHAR(100) NOT NULL UNIQUE,
    ContactNumber   VARCHAR(15)  NOT NULL,
    Address         VARCHAR(255) NOT NULL,
    MembershipType  ENUM('Silver','Gold','Platinum') NOT NULL DEFAULT 'Silver',
    RegistrationDate DATE        NOT NULL,
    LoyaltyPoints   INT          DEFAULT 0 CHECK (LoyaltyPoints >= 0),
    shard_id        INT          NOT NULL  -- which shard this row belongs to
);

CREATE INDEX idx_member_type    ON Member(MembershipType);
CREATE INDEX idx_member_regdate ON Member(RegistrationDate);

-- ----------------------------------------------------------------
-- Sale table (co-located with Member – same shard as the member)
-- ----------------------------------------------------------------
CREATE TABLE Sale (
    SaleID          VARCHAR(10)  PRIMARY KEY,
    MemberID        VARCHAR(10),
    EmployeeID      VARCHAR(10)  NOT NULL,
    SaleDate        DATETIME     NOT NULL,
    TotalAmount     DECIMAL(10,2) NOT NULL CHECK (TotalAmount >= 0),
    DiscountAmount  DECIMAL(10,2) DEFAULT 0 CHECK (DiscountAmount >= 0),
    FinalAmount     DECIMAL(10,2) NOT NULL CHECK (FinalAmount >= 0),
    PaymentMethod   ENUM('Cash','Card','UPI','Wallet') NOT NULL,
    OrderType       ENUM('In-Store','Online') NOT NULL DEFAULT 'In-Store',
    shard_id        INT          NOT NULL,
    INDEX idx_sale_member  (MemberID),
    INDEX idx_sale_date    (SaleDate),
    INDEX idx_sale_empid   (EmployeeID)
);

-- ----------------------------------------------------------------
-- SaleItem table (co-located – same shard as its Sale)
-- ----------------------------------------------------------------
CREATE TABLE SaleItem (
    SaleItemID  VARCHAR(10)   PRIMARY KEY,
    SaleID      VARCHAR(10)   NOT NULL,
    ProductID   VARCHAR(10)   NOT NULL,
    Quantity    INT           NOT NULL CHECK (Quantity > 0),
    UnitPrice   DECIMAL(10,2) NOT NULL CHECK (UnitPrice > 0),
    Subtotal    DECIMAL(10,2) NOT NULL CHECK (Subtotal > 0),
    shard_id    INT           NOT NULL,
    INDEX idx_saleitem_sale    (SaleID),
    INDEX idx_saleitem_product (ProductID)
);

SELECT CONCAT('Shard tables created in database Nexus on port: ',
              @@port) AS Status;
