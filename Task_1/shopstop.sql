-- CS 432 Assignment 1: Database Implementation(Module A)
-- ShopStop - Outlet Management System


DROP DATABASE IF EXISTS ShopStop;
CREATE DATABASE ShopStop;
USE ShopStop;

-- Member Table
CREATE TABLE Member (
    MemberID VARCHAR(10) PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    Image VARCHAR(255),
    Age INT NOT NULL CHECK (Age >= 18),
    Email VARCHAR(100) NOT NULL UNIQUE,
    ContactNumber VARCHAR(15) NOT NULL,
    Address VARCHAR(255) NOT NULL,
    MembershipType ENUM('Silver', 'Gold', 'Platinum') NOT NULL DEFAULT 'Silver',
    RegistrationDate DATE NOT NULL,
    LoyaltyPoints INT DEFAULT 0 CHECK (LoyaltyPoints >= 0)
);

-- Employee Table
CREATE TABLE Employee (
    EmployeeID VARCHAR(10) PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    Email VARCHAR(100) NOT NULL UNIQUE,
    ContactNumber VARCHAR(15) NOT NULL,
    Position VARCHAR(50) NOT NULL,
    Salary DECIMAL(10,2) NOT NULL CHECK (Salary > 0),
    HireDate DATE NOT NULL,
    ShiftTiming VARCHAR(20) NOT NULL,
    ManagerID VARCHAR(10),
    FOREIGN KEY (ManagerID) REFERENCES Employee(EmployeeID) ON DELETE SET NULL
);

-- Supplier Table
CREATE TABLE Supplier (
    SupplierID VARCHAR(10) PRIMARY KEY,
    SupplierName VARCHAR(100) NOT NULL,
    ContactPerson VARCHAR(100) NOT NULL,
    Email VARCHAR(100) NOT NULL UNIQUE,
    PhoneNumber VARCHAR(15) NOT NULL,
    Address VARCHAR(255) NOT NULL,
    City VARCHAR(50) NOT NULL,
    SupplyCategory VARCHAR(50) NOT NULL,
    Rating DECIMAL(3,2) CHECK (Rating >= 0 AND Rating <= 5)
);

-- Category Table
CREATE TABLE Category (
    CategoryID VARCHAR(10) PRIMARY KEY,
    CategoryName VARCHAR(100) NOT NULL UNIQUE,
    Description TEXT,
    ParentCategoryID VARCHAR(10),
    FOREIGN KEY (ParentCategoryID) REFERENCES Category(CategoryID) ON DELETE SET NULL
);

-- Product Table
CREATE TABLE Product (
    ProductID VARCHAR(10) PRIMARY KEY,
    ProductName VARCHAR(150) NOT NULL,
    CategoryID VARCHAR(10) NOT NULL,
    SupplierID VARCHAR(10) NOT NULL,
    Price DECIMAL(10,2) NOT NULL CHECK (Price > 0),
    StockQuantity INT NOT NULL CHECK (StockQuantity >= 0),
    ReorderLevel INT NOT NULL CHECK (ReorderLevel >= 0),
    ExpiryDate DATE,
    ManufactureDate DATE NOT NULL,
    Barcode VARCHAR(50) UNIQUE,
    FOREIGN KEY (CategoryID) REFERENCES Category(CategoryID) ON DELETE RESTRICT,
    FOREIGN KEY (SupplierID) REFERENCES Supplier(SupplierID) ON DELETE RESTRICT,
    CONSTRAINT chk_manufacture_expiry CHECK (ExpiryDate IS NULL OR ExpiryDate > ManufactureDate)
);

-- Sale Table
CREATE TABLE Sale (
    SaleID VARCHAR(10) PRIMARY KEY,
    MemberID VARCHAR(10),
    EmployeeID VARCHAR(10) NOT NULL,
    SaleDate DATETIME NOT NULL,
    TotalAmount DECIMAL(10,2) NOT NULL CHECK (TotalAmount >= 0),
    DiscountAmount DECIMAL(10,2) DEFAULT 0 CHECK (DiscountAmount >= 0),
    FinalAmount DECIMAL(10,2) NOT NULL CHECK (FinalAmount >= 0),
    PaymentMethod ENUM('Cash', 'Card', 'UPI', 'Wallet') NOT NULL,
    FOREIGN KEY (MemberID) REFERENCES Member(MemberID) ON DELETE SET NULL,
    FOREIGN KEY (EmployeeID) REFERENCES Employee(EmployeeID) ON DELETE RESTRICT,
    CONSTRAINT chk_final_amount CHECK (FinalAmount = TotalAmount - DiscountAmount)
);

-- SaleItem Table
CREATE TABLE SaleItem (
    SaleItemID VARCHAR(10) PRIMARY KEY,
    SaleID VARCHAR(10) NOT NULL,
    ProductID VARCHAR(10) NOT NULL,
    Quantity INT NOT NULL CHECK (Quantity > 0),
    UnitPrice DECIMAL(10,2) NOT NULL CHECK (UnitPrice > 0),
    Subtotal DECIMAL(10,2) NOT NULL CHECK (Subtotal > 0),
    FOREIGN KEY (SaleID) REFERENCES Sale(SaleID) ON DELETE CASCADE,
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID) ON DELETE RESTRICT,
    CONSTRAINT chk_subtotal CHECK (Subtotal = Quantity * UnitPrice)
);

-- PurchaseOrder Table
CREATE TABLE PurchaseOrder (
    OrderID VARCHAR(10) PRIMARY KEY,
    SupplierID VARCHAR(10) NOT NULL,
    EmployeeID VARCHAR(10) NOT NULL,
    OrderDate DATE NOT NULL,
    ExpectedDeliveryDate DATE NOT NULL,
    ActualDeliveryDate DATE,
    TotalAmount DECIMAL(10,2) NOT NULL CHECK (TotalAmount > 0),
    OrderStatus ENUM('Pending', 'Confirmed', 'Delivered', 'Cancelled') NOT NULL DEFAULT 'Pending',
    FOREIGN KEY (SupplierID) REFERENCES Supplier(SupplierID) ON DELETE RESTRICT,
    FOREIGN KEY (EmployeeID) REFERENCES Employee(EmployeeID) ON DELETE RESTRICT,
    CONSTRAINT chk_delivery_dates CHECK (ExpectedDeliveryDate >= OrderDate),
    CONSTRAINT chk_actual_delivery CHECK (ActualDeliveryDate IS NULL OR ActualDeliveryDate >= OrderDate)
);

-- OrderItem Table
CREATE TABLE OrderItem (
    OrderItemID VARCHAR(10) PRIMARY KEY,
    OrderID VARCHAR(10) NOT NULL,
    ProductID VARCHAR(10) NOT NULL,
    QuantityOrdered INT NOT NULL CHECK (QuantityOrdered > 0),
    UnitCost DECIMAL(10,2) NOT NULL CHECK (UnitCost > 0),
    Subtotal DECIMAL(10,2) NOT NULL CHECK (Subtotal > 0),
    FOREIGN KEY (OrderID) REFERENCES PurchaseOrder(OrderID) ON DELETE CASCADE,
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID) ON DELETE RESTRICT,
    CONSTRAINT chk_order_subtotal CHECK (Subtotal = QuantityOrdered * UnitCost)
);

-- Inventory Table
CREATE TABLE Inventory (
    InventoryID VARCHAR(10) PRIMARY KEY,
    ProductID VARCHAR(10) NOT NULL,
    LastRestockDate DATE NOT NULL,
    LastRestockQuantity INT NOT NULL CHECK (LastRestockQuantity > 0),
    CurrentStock INT NOT NULL CHECK (CurrentStock >= 0),
    Location VARCHAR(50) NOT NULL,
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID) ON DELETE CASCADE
);

-- Promotion Table
CREATE TABLE Promotion (
    PromotionID VARCHAR(10) PRIMARY KEY,
    PromotionName VARCHAR(100) NOT NULL,
    Description TEXT NOT NULL,
    StartDate DATE NOT NULL,
    EndDate DATE NOT NULL,
    DiscountPercentage DECIMAL(5,2) NOT NULL CHECK (DiscountPercentage > 0 AND DiscountPercentage <= 100),
    IsActive BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT chk_promo_dates CHECK (EndDate >= StartDate)
);

-- ProductPromotion Table
CREATE TABLE ProductPromotion (
    ProductPromotionID VARCHAR(10) PRIMARY KEY,
    ProductID VARCHAR(10) NOT NULL,
    PromotionID VARCHAR(10) NOT NULL,
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID) ON DELETE CASCADE,
    FOREIGN KEY (PromotionID) REFERENCES Promotion(PromotionID) ON DELETE CASCADE,
    UNIQUE(ProductID, PromotionID)
);


-- Sample data insertion:

INSERT INTO Member VALUES
('MEM001', 'Rajesh Kumar', '/images/members/rajesh.jpg', 35, 'rajesh.kumar@email.com', '9876543210', '123 MG Road, Gandhinagar', 'Gold', '2024-01-15', 2500),
('MEM002', 'Priya Sharma', '/images/members/priya.jpg', 28, 'priya.sharma@email.com', '9876543211', '456 Sector 21, Gandhinagar', 'Silver', '2024-02-20', 1200),
('MEM003', 'Amit Patel', '/images/members/amit.jpg', 42, 'amit.patel@email.com', '9876543212', '789 Infocity, Gandhinagar', 'Platinum', '2023-12-10', 5000),
('MEM004', 'Sneha Desai', '/images/members/sneha.jpg', 31, 'sneha.desai@email.com', '9876543213', '321 Kudasan, Gandhinagar', 'Gold', '2024-01-25', 3200),
('MEM005', 'Vikram Singh', '/images/members/vikram.jpg', 38, 'vikram.singh@email.com', '9876543214', '654 Sector 11, Gandhinagar', 'Silver', '2024-03-05', 800),
('MEM006', 'Anita Mehta', '/images/members/anita.jpg', 45, 'anita.mehta@email.com', '9876543215', '987 Raysan, Gandhinagar', 'Platinum', '2023-11-20', 6500),
('MEM007', 'Rohit Joshi', '/images/members/rohit.jpg', 29, 'rohit.joshi@email.com', '9876543216', '147 Sector 15, Gandhinagar', 'Silver', '2024-02-28', 950),
('MEM008', 'Kavita Rao', '/images/members/kavita.jpg', 36, 'kavita.rao@email.com', '9876543217', '258 Koba, Gandhinagar', 'Gold', '2024-01-18', 2800),
('MEM009', 'Suresh Nair', '/images/members/suresh.jpg', 50, 'suresh.nair@email.com', '9876543218', '369 Sector 25, Gandhinagar', 'Platinum', '2023-10-15', 7200),
('MEM010', 'Meera Iyer', '/images/members/meera.jpg', 33, 'meera.iyer@email.com', '9876543219', '741 Sector 7, Gandhinagar', 'Silver', '2024-03-10', 650),
('MEM011', 'Deepak Gupta', '/images/members/deepak.jpg', 27, 'deepak.gupta@email.com', '9876543220', '852 Sector 18, Gandhinagar', 'Gold', '2024-02-15', 2100),
('MEM012', 'Pooja Shah', '/images/members/pooja.jpg', 40, 'pooja.shah@email.com', '9876543221', '963 Sector 22, Gandhinagar', 'Silver', '2024-03-01', 1100),
('MEM013', 'Manish Verma', '/images/members/manish.jpg', 34, 'manish.verma@email.com', '9876543222', '159 Sector 13, Gandhinagar', 'Platinum', '2023-12-05', 5500),
('MEM014', 'Neha Kapoor', '/images/members/neha.jpg', 26, 'neha.kapoor@email.com', '9876543223', '357 Sector 19, Gandhinagar', 'Silver', '2024-03-15', 720),
('MEM015', 'Arun Kumar', '/images/members/arun.jpg', 44, 'arun.kumar@email.com', '9876543224', '468 Sector 24, Gandhinagar', 'Gold', '2024-01-20', 3000),
('MEM016', 'Divya Pillai', '/images/members/divya.jpg', 30, 'divya.pillai@email.com', '9876543225', '579 Sector 16, Gandhinagar', 'Silver', '2024-02-25', 890),
('MEM017', 'Sanjay Reddy', '/images/members/sanjay.jpg', 48, 'sanjay.reddy@email.com', '9876543226', '681 Sector 20, Gandhinagar', 'Platinum', '2023-11-10', 6800),
('MEM018', 'Rekha Devi', '/images/members/rekha.jpg', 37, 'rekha.devi@email.com', '9876543227', '792 Sector 23, Gandhinagar', 'Gold', '2024-01-30', 2600),
('MEM019', 'Karan Malhotra', '/images/members/karan.jpg', 32, 'karan.malhotra@email.com', '9876543228', '803 Sector 12, Gandhinagar', 'Silver', '2024-03-08', 1050),
('MEM020', 'Sunita Bose', '/images/members/sunita.jpg', 41, 'sunita.bose@email.com', '9876543229', '914 Sector 17, Gandhinagar', 'Gold', '2024-02-10', 2900);

INSERT INTO Employee VALUES
('EMP001', 'Mahesh Yadav', 'mahesh.yadav@shopstop.com', '9123456780', 'Store Manager', 65000.00, '2020-01-10', 'Morning', NULL),
('EMP002', 'Lakshmi Nair', 'lakshmi.nair@shopstop.com', '9123456781', 'Assistant Manager', 50000.00, '2020-06-15', 'Morning', 'EMP001'),
('EMP003', 'Ravi Shankar', 'ravi.shankar@shopstop.com', '9123456782', 'Cashier', 25000.00, '2021-03-20', 'Morning', 'EMP002'),
('EMP004', 'Geeta Reddy', 'geeta.reddy@shopstop.com', '9123456783', 'Cashier', 25000.00, '2021-04-10', 'Evening', 'EMP002'),
('EMP005', 'Prakash Jain', 'prakash.jain@shopstop.com', '9123456784', 'Stock Manager', 45000.00, '2020-08-25', 'Morning', 'EMP001'),
('EMP006', 'Seema Gupta', 'seema.gupta@shopstop.com', '9123456785', 'Sales Associate', 22000.00, '2022-01-15', 'Morning', 'EMP002'),
('EMP007', 'Ajay Kumar', 'ajay.kumar@shopstop.com', '9123456786', 'Sales Associate', 22000.00, '2022-02-20', 'Evening', 'EMP002'),
('EMP008', 'Nisha Patel', 'nisha.patel@shopstop.com', '9123456787', 'Inventory Clerk', 28000.00, '2021-07-10', 'Morning', 'EMP005'),
('EMP009', 'Vinod Mehta', 'vinod.mehta@shopstop.com', '9123456788', 'Security Officer', 30000.00, '2020-11-05', 'Night', 'EMP001'),
('EMP010', 'Radha Krishna', 'radha.krishna@shopstop.com', '9123456789', 'Cashier', 25000.00, '2021-09-15', 'Evening', 'EMP002'),
('EMP011', 'Sunil Sharma', 'sunil.sharma@shopstop.com', '9123456790', 'Sales Associate', 22000.00, '2022-03-10', 'Morning', 'EMP002'),
('EMP012', 'Asha Devi', 'asha.devi@shopstop.com', '9123456791', 'HR Executive', 40000.00, '2020-05-20', 'Morning', 'EMP001'),
('EMP013', 'Ramesh Tiwari', 'ramesh.tiwari@shopstop.com', '9123456792', 'Accountant', 42000.00, '2020-09-01', 'Morning', 'EMP001'),
('EMP014', 'Kamla Singh', 'kamla.singh@shopstop.com', '9123456793', 'Maintenance Staff', 20000.00, '2021-11-20', 'Morning', 'EMP001'),
('EMP015', 'Bharat Mishra', 'bharat.mishra@shopstop.com', '9123456794', 'Delivery Executive', 26000.00, '2022-01-05', 'Morning', 'EMP005');

INSERT INTO Supplier VALUES
('SUP001', 'FreshFarms Pvt Ltd', 'Mohan Das', 'mohan@freshfarms.com', '9234567890', '12 Agriculture Hub, Ahmedabad', 'Ahmedabad', 'Fresh Produce', 4.5),
('SUP002', 'DairyBest Corporation', 'Ramesh Patel', 'ramesh@dairybest.com', '9234567891', '45 Dairy Lane, Anand', 'Anand', 'Dairy Products', 4.8),
('SUP003', 'BeveragePro Suppliers', 'Suresh Kumar', 'suresh@beveragepro.com', '9234567892', '78 Industrial Area, Vadodara', 'Vadodara', 'Beverages', 4.2),
('SUP004', 'SnackWorld Distributors', 'Neeta Shah', 'neeta@snackworld.com', '9234567893', '23 Trade Center, Surat', 'Surat', 'Snacks', 4.6),
('SUP005', 'HomeEssentials Ltd', 'Vijay Gupta', 'vijay@homeessentials.com', '9234567894', '67 Market Road, Rajkot', 'Rajkot', 'Household Items', 4.3),
('SUP006', 'BeautyPro Wholesale', 'Anjali Mehta', 'anjali@beautypro.com', '9234567895', '89 Beauty Plaza, Ahmedabad', 'Ahmedabad', 'Personal Care', 4.7),
('SUP007', 'ElectroMart Supplies', 'Rakesh Joshi', 'rakesh@electromart.com', '9234567896', '34 Electronics Hub, Gandhinagar', 'Gandhinagar', 'Electronics', 4.4),
('SUP008', 'GroceryMax Wholesalers', 'Priti Desai', 'priti@grocerymax.com', '9234567897', '56 Wholesale Market, Vadodara', 'Vadodara', 'Groceries', 4.5),
('SUP009', 'OrganicLife Products', 'Deepak Sharma', 'deepak@organiclife.com', '9234567898', '91 Organic Valley, Ahmedabad', 'Ahmedabad', 'Organic Products', 4.9),
('SUP010', 'FrozenFoods Co', 'Meena Iyer', 'meena@frozenfoods.com', '9234567899', '12 Cold Storage Zone, Surat', 'Surat', 'Frozen Items', 4.1),
('SUP011', 'BakerySupplies Plus', 'Anil Kumar', 'anil@bakerysupplies.com', '9234567800', '78 Bakery Street, Rajkot', 'Rajkot', 'Bakery Items', 4.6),
('SUP012', 'PetCare Distributors', 'Sonal Patel', 'sonal@petcare.com', '9234567801', '45 Pet Zone, Gandhinagar', 'Gandhinagar', 'Pet Products', 4.4);

INSERT INTO Category VALUES
('CAT001', 'Food & Beverages', 'All food and beverage products', NULL),
('CAT002', 'Fresh Produce', 'Fresh fruits and vegetables', 'CAT001'),
('CAT003', 'Dairy Products', 'Milk, cheese, yogurt, etc.', 'CAT001'),
('CAT004', 'Beverages', 'Soft drinks, juices, water', 'CAT001'),
('CAT005', 'Personal Care', 'Beauty and hygiene products', NULL),
('CAT006', 'Household Items', 'Cleaning and home essentials', NULL),
('CAT007', 'Electronics', 'Electronic gadgets and appliances', NULL),
('CAT008', 'Snacks', 'Chips, biscuits, chocolates', 'CAT001'),
('CAT009', 'Organic Foods', 'Certified organic products', 'CAT001'),
('CAT010', 'Frozen Foods', 'Frozen items and ice cream', 'CAT001');

INSERT INTO Product VALUES
('PROD001', 'Fresh Bananas (1 Dozen)', 'CAT002', 'SUP001', 60.00, 150, 30, '2026-02-20', '2026-02-10', 'BAN123456789'),
('PROD002', 'Full Cream Milk (1L)', 'CAT003', 'SUP002', 65.00, 200, 50, '2026-02-25', '2026-02-12', 'MLK123456789'),
('PROD003', 'Coca Cola (2L)', 'CAT004', 'SUP003', 90.00, 100, 20, '2027-01-01', '2025-06-15', 'COK123456789'),
('PROD004', 'Lays Classic Chips', 'CAT008', 'SUP004', 20.00, 300, 50, '2026-08-30', '2025-12-01', 'LAY123456789'),
('PROD005', 'Colgate Toothpaste', 'CAT005', 'SUP006', 85.00, 180, 40, '2027-12-31', '2024-06-20', 'COL123456789'),
('PROD006', 'Surf Excel Detergent', 'CAT006', 'SUP005', 250.00, 120, 25, NULL, '2025-11-10', 'SUR123456789'),
('PROD007', 'Fresh Tomatoes (1 Kg)', 'CAT002', 'SUP001', 40.00, 80, 20, '2026-02-18', '2026-02-13', 'TOM123456789'),
('PROD008', 'Greek Yogurt (500g)', 'CAT003', 'SUP002', 120.00, 90, 20, '2026-02-22', '2026-02-10', 'YOG123456789'),
('PROD009', 'Tropicana Orange Juice (1L)', 'CAT004', 'SUP003', 150.00, 70, 15, '2026-03-15', '2026-01-20', 'TRP123456789'),
('PROD010', 'Oreo Biscuits', 'CAT008', 'SUP004', 30.00, 250, 50, '2026-09-30', '2025-10-15', 'ORE123456789'),
('PROD011', 'Dove Soap', 'CAT005', 'SUP006', 45.00, 200, 40, '2028-01-01', '2024-08-10', 'DOV123456789'),
('PROD012', 'Lizol Floor Cleaner', 'CAT006', 'SUP005', 180.00, 95, 20, NULL, '2025-09-25', 'LIZ123456789'),
('PROD013', 'Wireless Mouse', 'CAT007', 'SUP007', 450.00, 50, 10, NULL, '2025-07-15', 'MOU123456789'),
('PROD014', 'Organic Brown Rice (5 Kg)', 'CAT009', 'SUP009', 450.00, 60, 15, NULL, '2025-12-01', 'RIC123456789'),
('PROD015', 'Frozen Peas (1 Kg)', 'CAT010', 'SUP010', 120.00, 110, 25, '2026-12-31', '2025-08-20', 'PEA123456789'),
('PROD016', 'Bread Loaf', 'CAT001', 'SUP011', 35.00, 140, 30, '2026-02-17', '2026-02-14', 'BRE123456789'),
('PROD017', 'Sunflower Oil (1L)', 'CAT001', 'SUP008', 140.00, 85, 20, '2027-06-30', '2025-05-10', 'OIL123456789'),
('PROD018', 'Green Tea Bags', 'CAT004', 'SUP003', 200.00, 75, 15, '2027-03-31', '2025-04-20', 'TEA123456789'),
('PROD019', 'Cadbury Dairy Milk', 'CAT008', 'SUP004', 60.00, 220, 45, '2026-10-31', '2025-11-15', 'CAD123456789'),
('PROD020', 'Hand Sanitizer (500ml)', 'CAT005', 'SUP006', 95.00, 160, 35, '2028-02-28', '2024-09-01', 'SAN123456789'),
('PROD021', 'LED Bulb (9W)', 'CAT007', 'SUP007', 180.00, 100, 20, NULL, '2025-03-15', 'LED123456789'),
('PROD022', 'Dog Food (5 Kg)', 'CAT006', 'SUP012', 850.00, 45, 10, '2027-05-31', '2025-06-01', 'DOG123456789'),
('PROD023', 'Organic Honey (500g)', 'CAT009', 'SUP009', 380.00, 55, 12, '2028-01-31', '2025-02-10', 'HON123456789'),
('PROD024', 'Ice Cream (1L Tub)', 'CAT010', 'SUP010', 250.00, 80, 20, '2026-08-31', '2026-01-15', 'ICE123456789'),
('PROD025', 'Whole Wheat Flour (10 Kg)', 'CAT009', 'SUP009', 450.00, 70, 15, NULL, '2025-11-20', 'FLO123456789');

INSERT INTO Sale VALUES
('SAL001', 'MEM001', 'EMP003', '2026-02-10 10:30:00', 1500.00, 150.00, 1350.00, 'Card'),
('SAL002', 'MEM002', 'EMP004', '2026-02-10 11:45:00', 890.00, 45.00, 845.00, 'UPI'),
('SAL003', NULL, 'EMP003', '2026-02-10 14:20:00', 350.00, 0.00, 350.00, 'Cash'),
('SAL004', 'MEM003', 'EMP010', '2026-02-11 09:15:00', 2400.00, 360.00, 2040.00, 'Card'),
('SAL005', 'MEM004', 'EMP003', '2026-02-11 16:30:00', 1200.00, 120.00, 1080.00, 'UPI'),
('SAL006', NULL, 'EMP004', '2026-02-11 18:45:00', 420.00, 0.00, 420.00, 'Cash'),
('SAL007', 'MEM005', 'EMP010', '2026-02-12 10:00:00', 680.00, 34.00, 646.00, 'Wallet'),
('SAL008', 'MEM006', 'EMP003', '2026-02-12 12:30:00', 3200.00, 480.00, 2720.00, 'Card'),
('SAL009', 'MEM007', 'EMP004', '2026-02-12 15:15:00', 540.00, 27.00, 513.00, 'UPI'),
('SAL010', NULL, 'EMP010', '2026-02-13 09:45:00', 290.00, 0.00, 290.00, 'Cash'),
('SAL011', 'MEM008', 'EMP003', '2026-02-13 11:20:00', 1850.00, 185.00, 1665.00, 'Card'),
('SAL012', 'MEM009', 'EMP004', '2026-02-13 14:50:00', 2950.00, 442.50, 2507.50, 'Card'),
('SAL013', 'MEM010', 'EMP010', '2026-02-13 17:30:00', 760.00, 38.00, 722.00, 'UPI'),
('SAL014', NULL, 'EMP003', '2026-02-14 10:15:00', 380.00, 0.00, 380.00, 'Cash'),
('SAL015', 'MEM011', 'EMP004', '2026-02-14 12:00:00', 1420.00, 142.00, 1278.00, 'Card'),
('SAL016', 'MEM012', 'EMP010', '2026-02-14 13:45:00', 890.00, 44.50, 845.50, 'UPI'),
('SAL017', 'MEM013', 'EMP003', '2026-02-14 15:30:00', 2680.00, 402.00, 2278.00, 'Card'),
('SAL018', NULL, 'EMP004', '2026-02-14 16:20:00', 520.00, 0.00, 520.00, 'Cash'),
('SAL019', 'MEM014', 'EMP010', '2026-02-14 18:00:00', 640.00, 32.00, 608.00, 'Wallet'),
('SAL020', 'MEM015', 'EMP003', '2026-02-14 19:15:00', 1980.00, 198.00, 1782.00, 'Card');

INSERT INTO SaleItem VALUES
('SI001', 'SAL001', 'PROD002', 5, 65.00, 325.00),
('SI002', 'SAL001', 'PROD005', 3, 85.00, 255.00),
('SI003', 'SAL001', 'PROD006', 4, 250.00, 1000.00),
('SI004', 'SAL002', 'PROD001', 3, 60.00, 180.00),
('SI005', 'SAL002', 'PROD004', 8, 20.00, 160.00),
('SI006', 'SAL002', 'PROD010', 5, 30.00, 150.00),
('SI007', 'SAL002', 'PROD019', 4, 60.00, 240.00),
('SI008', 'SAL003', 'PROD003', 2, 90.00, 180.00),
('SI009', 'SAL003', 'PROD016', 5, 35.00, 175.00),
('SI010', 'SAL004', 'PROD013', 2, 450.00, 900.00),
('SI011', 'SAL004', 'PROD014', 1, 450.00, 450.00),
('SI012', 'SAL004', 'PROD023', 2, 380.00, 760.00),
('SI013', 'SAL004', 'PROD006', 1, 250.00, 250.00),
('SI014', 'SAL005', 'PROD008', 4, 120.00, 480.00),
('SI015', 'SAL005', 'PROD009', 3, 150.00, 450.00),
('SI016', 'SAL005', 'PROD018', 1, 200.00, 200.00),
('SI017', 'SAL006', 'PROD011', 4, 45.00, 180.00),
('SI018', 'SAL006', 'PROD020', 2, 95.00, 190.00),
('SI019', 'SAL007', 'PROD007', 5, 40.00, 200.00),
('SI020', 'SAL007', 'PROD015', 4, 120.00, 480.00),
('SI021', 'SAL008', 'PROD022', 2, 850.00, 1700.00),
('SI022', 'SAL008', 'PROD025', 2, 450.00, 900.00),
('SI023', 'SAL008', 'PROD017', 4, 140.00, 560.00),
('SI024', 'SAL009', 'PROD024', 2, 250.00, 500.00),
('SI025', 'SAL010', 'PROD001', 2, 60.00, 120.00),
('SI026', 'SAL010', 'PROD016', 5, 35.00, 175.00),
('SI027', 'SAL011', 'PROD021', 5, 180.00, 900.00),
('SI028', 'SAL011', 'PROD012', 5, 180.00, 900.00),
('SI029', 'SAL012', 'PROD014', 2, 450.00, 900.00),
('SI030', 'SAL012', 'PROD023', 3, 380.00, 1140.00),
('SI031', 'SAL012', 'PROD013', 2, 450.00, 900.00),
('SI032', 'SAL013', 'PROD009', 3, 150.00, 450.00),
('SI033', 'SAL013', 'PROD019', 5, 60.00, 300.00),
('SI034', 'SAL014', 'PROD004', 10, 20.00, 200.00),
('SI035', 'SAL014', 'PROD010', 6, 30.00, 180.00),
('SI036', 'SAL015', 'PROD002', 8, 65.00, 520.00),
('SI037', 'SAL015', 'PROD003', 5, 90.00, 450.00),
('SI038', 'SAL015', 'PROD005', 5, 85.00, 425.00),
('SI039', 'SAL016', 'PROD008', 4, 120.00, 480.00),
('SI040', 'SAL016', 'PROD018', 2, 200.00, 400.00),
('SI041', 'SAL017', 'PROD022', 1, 850.00, 850.00),
('SI042', 'SAL017', 'PROD014', 2, 450.00, 900.00),
('SI043', 'SAL017', 'PROD025', 2, 450.00, 900.00),
('SI044', 'SAL018', 'PROD011', 6, 45.00, 270.00),
('SI045', 'SAL018', 'PROD020', 2, 95.00, 190.00),
('SI046', 'SAL019', 'PROD015', 4, 120.00, 480.00),
('SI047', 'SAL019', 'PROD007', 4, 40.00, 160.00),
('SI048', 'SAL020', 'PROD017', 6, 140.00, 840.00),
('SI049', 'SAL020', 'PROD006', 3, 250.00, 750.00),
('SI050', 'SAL020', 'PROD012', 2, 180.00, 360.00);

INSERT INTO PurchaseOrder VALUES
('ORD001', 'SUP001', 'EMP005', '2026-02-01', '2026-02-08', '2026-02-07', 15000.00, 'Delivered'),
('ORD002', 'SUP002', 'EMP005', '2026-02-02', '2026-02-09', '2026-02-09', 25000.00, 'Delivered'),
('ORD003', 'SUP003', 'EMP005', '2026-02-03', '2026-02-10', '2026-02-10', 18000.00, 'Delivered'),
('ORD004', 'SUP004', 'EMP008', '2026-02-04', '2026-02-11', NULL, 12000.00, 'Confirmed'),
('ORD005', 'SUP005', 'EMP005', '2026-02-05', '2026-02-12', '2026-02-11', 22000.00, 'Delivered'),
('ORD006', 'SUP006', 'EMP008', '2026-02-06', '2026-02-13', NULL, 16000.00, 'Confirmed'),
('ORD007', 'SUP007', 'EMP005', '2026-02-07', '2026-02-14', NULL, 28000.00, 'Pending'),
('ORD008', 'SUP008', 'EMP008', '2026-02-08', '2026-02-15', NULL, 20000.00, 'Confirmed'),
('ORD009', 'SUP009', 'EMP005', '2026-02-09', '2026-02-16', NULL, 32000.00, 'Pending'),
('ORD010', 'SUP010', 'EMP008', '2026-02-10', '2026-02-17', NULL, 14000.00, 'Confirmed'),
('ORD011', 'SUP011', 'EMP005', '2026-02-11', '2026-02-18', NULL, 10000.00, 'Pending'),
('ORD012', 'SUP012', 'EMP008', '2026-02-12', '2026-02-19', NULL, 26000.00, 'Pending'),
('ORD013', 'SUP001', 'EMP005', '2026-02-13', '2026-02-20', NULL, 17000.00, 'Confirmed'),
('ORD014', 'SUP002', 'EMP008', '2026-02-14', '2026-02-21', NULL, 24000.00, 'Pending'),
('ORD015', 'SUP003', 'EMP005', '2026-02-14', '2026-02-21', NULL, 19000.00, 'Pending');

INSERT INTO OrderItem VALUES
('OI001', 'ORD001', 'PROD001', 200, 45.00, 9000.00),
('OI002', 'ORD001', 'PROD007', 150, 30.00, 4500.00),
('OI003', 'ORD002', 'PROD002', 300, 50.00, 15000.00),
('OI004', 'ORD002', 'PROD008', 100, 90.00, 9000.00),
('OI005', 'ORD003', 'PROD003', 150, 70.00, 10500.00),
('OI006', 'ORD003', 'PROD009', 50, 120.00, 6000.00),
('OI007', 'ORD004', 'PROD004', 400, 15.00, 6000.00),
('OI008', 'ORD004', 'PROD010', 300, 22.00, 6600.00),
('OI009', 'ORD005', 'PROD005', 200, 65.00, 13000.00),
('OI010', 'ORD005', 'PROD011', 250, 35.00, 8750.00),
('OI011', 'ORD006', 'PROD020', 200, 75.00, 15000.00),
('OI012', 'ORD007', 'PROD013', 80, 350.00, 28000.00),
('OI013', 'ORD008', 'PROD017', 100, 110.00, 11000.00),
('OI014', 'ORD008', 'PROD016', 200, 25.00, 5000.00),
('OI015', 'ORD008', 'PROD006', 20, 200.00, 4000.00),
('OI016', 'ORD009', 'PROD014', 80, 350.00, 28000.00),
('OI017', 'ORD009', 'PROD023', 15, 300.00, 4500.00),
('OI018', 'ORD010', 'PROD015', 120, 95.00, 11400.00),
('OI019', 'ORD010', 'PROD024', 50, 200.00, 10000.00),
('OI020', 'ORD011', 'PROD016', 300, 25.00, 7500.00),
('OI021', 'ORD012', 'PROD022', 40, 700.00, 28000.00),
('OI022', 'ORD013', 'PROD001', 180, 45.00, 8100.00),
('OI023', 'ORD013', 'PROD007', 120, 30.00, 3600.00),
('OI024', 'ORD014', 'PROD002', 250, 50.00, 12500.00),
('OI025', 'ORD014', 'PROD008', 90, 90.00, 8100.00),
('OI026', 'ORD015', 'PROD003', 120, 70.00, 8400.00),
('OI027', 'ORD015', 'PROD009', 40, 120.00, 4800.00),
('OI028', 'ORD005', 'PROD012', 8, 140.00, 1120.00),
('OI029', 'ORD006', 'PROD005', 10, 65.00, 650.00),
('OI030', 'ORD001', 'PROD016', 50, 25.00, 1250.00),
('OI031', 'ORD002', 'PROD003', 10, 70.00, 700.00),
('OI032', 'ORD008', 'PROD018', 20, 160.00, 3200.00),
('OI033', 'ORD009', 'PROD025', 20, 350.00, 7000.00),
('OI034', 'ORD010', 'PROD019', 40, 45.00, 1800.00),
('OI035', 'ORD011', 'PROD004', 100, 15.00, 1500.00),
('OI036', 'ORD012', 'PROD006', 15, 200.00, 3000.00),
('OI037', 'ORD013', 'PROD021', 30, 140.00, 4200.00),
('OI038', 'ORD014', 'PROD012', 20, 140.00, 2800.00),
('OI039', 'ORD015', 'PROD004', 200, 15.00, 3000.00),
('OI040', 'ORD015', 'PROD019', 50, 45.00, 2250.00);

INSERT INTO Inventory VALUES
('INV001', 'PROD001', '2026-02-07', 200, 150, 'Aisle-1-A'),
('INV002', 'PROD002', '2026-02-09', 300, 200, 'Fridge-1'),
('INV003', 'PROD003', '2026-02-10', 150, 100, 'Aisle-2-C'),
('INV004', 'PROD004', '2026-02-11', 400, 300, 'Aisle-3-B'),
('INV005', 'PROD005', '2026-02-11', 200, 180, 'Aisle-4-D'),
('INV006', 'PROD006', '2026-02-11', 150, 120, 'Aisle-5-A'),
('INV007', 'PROD007', '2026-02-07', 150, 80, 'Aisle-1-B'),
('INV008', 'PROD008', '2026-02-09', 100, 90, 'Fridge-2'),
('INV009', 'PROD009', '2026-02-10', 80, 70, 'Fridge-3'),
('INV010', 'PROD010', '2026-02-11', 300, 250, 'Aisle-3-C'),
('INV011', 'PROD011', '2026-02-11', 250, 200, 'Aisle-4-A'),
('INV012', 'PROD012', '2026-02-11', 100, 95, 'Aisle-5-C'),
('INV013', 'PROD013', '2026-02-14', 80, 50, 'Electronics-Shelf'),
('INV014', 'PROD014', '2026-02-16', 80, 60, 'Organic-Section-A'),
('INV015', 'PROD015', '2026-02-17', 120, 110, 'Freezer-1'),
('INV016', 'PROD016', '2026-02-08', 300, 140, 'Bakery-Shelf'),
('INV017', 'PROD017', '2026-02-11', 100, 85, 'Aisle-2-D'),
('INV018', 'PROD018', '2026-02-15', 80, 75, 'Aisle-2-B'),
('INV019', 'PROD019', '2026-02-11', 250, 220, 'Aisle-3-D'),
('INV020', 'PROD020', '2026-02-13', 200, 160, 'Aisle-4-B'),
('INV021', 'PROD021', '2026-02-20', 120, 100, 'Electronics-Shelf'),
('INV022', 'PROD022', '2026-02-19', 40, 45, 'Pet-Section'),
('INV023', 'PROD023', '2026-02-16', 35, 55, 'Organic-Section-B'),
('INV024', 'PROD024', '2026-02-17', 100, 80, 'Freezer-2'),
('INV025', 'PROD025', '2026-02-16', 80, 70, 'Organic-Section-C');

INSERT INTO Promotion VALUES
('PROM001', 'Valentine Special', 'Special discounts for Valentines Day', '2026-02-10', '2026-02-14', 15.00, TRUE),
('PROM002', 'Fresh Produce Sale', 'Discounts on all fresh fruits and vegetables', '2026-02-01', '2026-02-28', 10.00, TRUE),
('PROM003', 'Dairy Delight', 'Special offers on dairy products', '2026-02-05', '2026-02-20', 12.00, TRUE),
('PROM004', 'Electronics Bonanza', 'Heavy discounts on electronics', '2026-02-01', '2026-02-15', 20.00, TRUE),
('PROM005', 'Organic Week', 'Promote healthy living with organic products', '2026-02-08', '2026-02-15', 18.00, TRUE),
('PROM006', 'Household Essentials', 'Save on cleaning and home products', '2026-02-01', '2026-02-28', 8.00, TRUE),
('PROM007', 'Snack Attack', 'Buy more, save more on snacks', '2026-02-10', '2026-02-25', 10.00, TRUE),
('PROM008', 'Beauty Boost', 'Personal care products at reduced prices', '2026-02-05', '2026-02-22', 15.00, TRUE),
('PROM009', 'Beverage Blast', 'Cool offers on beverages', '2026-02-01', '2026-02-28', 12.00, TRUE),
('PROM010', 'Frozen Foods Fest', 'Special prices on frozen items', '2026-02-12', '2026-02-28', 14.00, TRUE);

INSERT INTO ProductPromotion VALUES
('PP001', 'PROD019', 'PROM001'),
('PP002', 'PROD024', 'PROM001'),
('PP003', 'PROD001', 'PROM002'),
('PP004', 'PROD007', 'PROM002'),
('PP005', 'PROD002', 'PROM003'),
('PP006', 'PROD008', 'PROM003'),
('PP007', 'PROD013', 'PROM004'),
('PP008', 'PROD021', 'PROM004'),
('PP009', 'PROD014', 'PROM005'),
('PP010', 'PROD023', 'PROM005'),
('PP011', 'PROD025', 'PROM005'),
('PP012', 'PROD006', 'PROM006'),
('PP013', 'PROD012', 'PROM006'),
('PP014', 'PROD004', 'PROM007'),
('PP015', 'PROD010', 'PROM007'),
('PP016', 'PROD005', 'PROM008'),
('PP017', 'PROD011', 'PROM008'),
('PP018', 'PROD003', 'PROM009'),
('PP019', 'PROD009', 'PROM009'),
('PP020', 'PROD015', 'PROM010');


-- SAMPLE QUERIES TO VERIFY FUNCTIONALITIES

-- Member Management: to view all Gold and Platinum members
SELECT MemberID, Name, Email, MembershipType, LoyaltyPoints 
FROM Member 
WHERE MembershipType IN ('Gold', 'Platinum') 
ORDER BY LoyaltyPoints DESC;

-- Sales Analysis: for daily sales report
SELECT 
    DATE(SaleDate) as SaleDay,
    COUNT(*) as TotalTransactions,
    SUM(TotalAmount) as GrossSales,
    SUM(DiscountAmount) as TotalDiscounts,
    SUM(FinalAmount) as NetSales
FROM Sale
GROUP BY DATE(SaleDate)
ORDER BY SaleDay DESC;

-- Purchase Order Tracking: for pending and confirmed orders
SELECT 
    po.OrderID,
    s.SupplierName,
    po.OrderDate,
    po.ExpectedDeliveryDate,
    po.TotalAmount,
    po.OrderStatus,
    COUNT(oi.OrderItemID) as TotalItems
FROM PurchaseOrder po
JOIN Supplier s ON po.SupplierID = s.SupplierID
JOIN OrderItem oi ON po.OrderID = oi.OrderID
WHERE po.OrderStatus IN ('Pending', 'Confirmed')
GROUP BY po.OrderID
ORDER BY po.ExpectedDeliveryDate;

-- Product Performance - for top selling products
SELECT 
    p.ProductID,
    p.ProductName,
    c.CategoryName,
    COUNT(si.SaleItemID) as TimesSold,
    SUM(si.Quantity) as TotalUnitsSold,
    SUM(si.Subtotal) as TotalRevenue
FROM Product p
JOIN SaleItem si ON p.ProductID = si.ProductID
JOIN Category c ON p.CategoryID = c.CategoryID
GROUP BY p.ProductID
ORDER BY TotalRevenue DESC
LIMIT 10;

-- For active promotions with products
SELECT 
    pr.PromotionName,
    pr.DiscountPercentage,
    pr.StartDate,
    pr.EndDate,
    p.ProductName,
    p.Price,
    ROUND(p.Price * (1 - pr.DiscountPercentage/100), 2) as DiscountedPrice
FROM Promotion pr
JOIN ProductPromotion pp ON pr.PromotionID = pp.PromotionID
JOIN Product p ON pp.ProductID = p.ProductID
WHERE pr.IsActive = TRUE 
AND CURDATE() BETWEEN pr.StartDate AND pr.EndDate
ORDER BY pr.PromotionName;
