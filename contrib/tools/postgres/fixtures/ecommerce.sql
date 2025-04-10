-- Create ecommerce database

\c ecommerce;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS ecommerce;

-- Set search path
SET search_path TO ecommerce, public;

-- Create tables
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE categories (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    parent_id INTEGER REFERENCES categories(category_id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    category_id INTEGER REFERENCES categories(category_id),
    image_url VARCHAR(255),
    sku VARCHAR(50) UNIQUE NOT NULL,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE addresses (
    address_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    address_line1 VARCHAR(255) NOT NULL,
    address_line2 VARCHAR(255),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    postal_code VARCHAR(20) NOT NULL,
    country VARCHAR(100) NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    address_id INTEGER REFERENCES addresses(address_id),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    total_amount DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(order_id),
    product_id INTEGER REFERENCES products(product_id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE payments (
    payment_id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(order_id),
    amount DECIMAL(10,2) NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    transaction_id VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE reviews (
    review_id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(product_id),
    user_id INTEGER REFERENCES users(user_id),
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Insert seed data
-- Categories
INSERT INTO categories (name, description) VALUES
('Electronics', 'Electronic devices and accessories'),
('Clothing', 'Apparel and fashion items'),
('Home & Kitchen', 'Home goods and kitchen supplies'),
('Books', 'Books and publications'),
('Sports & Outdoors', 'Sports equipment and outdoor gear');

INSERT INTO categories (name, description, parent_id) VALUES
('Smartphones', 'Mobile phones and accessories', 1),
('Laptops', 'Notebook computers', 1),
('Men''s Clothing', 'Clothing for men', 2),
('Women''s Clothing', 'Clothing for women', 2),
('Cookware', 'Pots, pans, and cooking utensils', 3),
('Fiction', 'Fiction books', 4),
('Non-Fiction', 'Non-fiction books', 4),
('Camping', 'Camping gear and equipment', 5);

-- Users
INSERT INTO users (email, password_hash, first_name, last_name, phone) VALUES
('john.doe@example.com', '$2a$10$xJwVGMNXm4FYkRqbJU9IeeZGSR8xNR5xmrTj8JnJjK5XZZQDoOzYu', 'John', 'Doe', '555-123-4567'),
('jane.smith@example.com', '$2a$10$NnfGMFd9A54MJ7AXCkeFN.NxPkwmECWGrhKcXjQWLPZLBzBRSBFnK', 'Jane', 'Smith', '555-987-6543'),
('mike.wilson@example.com', '$2a$10$RsZUnKmptBUSCpEDEh3VGe9oyMXZ.BeZBJC/yGZJ0fxnvCRXf2D2G', 'Mike', 'Wilson', '555-456-7890'),
('sarah.johnson@example.com', '$2a$10$LHmOkbqZUcMYpIXZqK7ZQeSkEzQsocVFYq7q.AE9NjOg5tpFdwM6a', 'Sarah', 'Johnson', '555-789-0123'),
('david.brown@example.com', '$2a$10$9XmPGv0qKJCHDJxGk2X3UO5eIf4Nm5NzCCVC3aDGvZSYG.EQhp/b.', 'David', 'Brown', '555-321-6547');

-- Addresses
INSERT INTO addresses (user_id, address_line1, city, state, postal_code, country, is_default) VALUES
(1, '123 Main St', 'Seattle', 'WA', '98101', 'USA', true),
(2, '456 Oak Ave', 'Portland', 'OR', '97205', 'USA', true),
(3, '789 Pine Rd', 'San Francisco', 'CA', '94102', 'USA', true),
(4, '321 Maple Dr', 'New York', 'NY', '10001', 'USA', true),
(5, '654 Elm Blvd', 'Chicago', 'IL', '60601', 'USA', true);

-- Products
INSERT INTO products (name, description, price, category_id, sku, stock_quantity) VALUES
('iPhone 13', '128GB smartphone with advanced camera system', 799.99, 6, 'PHONE-IPH13-128', 50),
('Samsung Galaxy S21', '256GB Android smartphone', 699.99, 6, 'PHONE-SAMS21-256', 45),
('MacBook Pro', '13-inch, M1 chip, 8GB RAM, 256GB SSD', 1299.99, 7, 'LAPTOP-MBP-13-M1', 25),
('Dell XPS 15', '15.6-inch, Intel i7, 16GB RAM, 512GB SSD', 1499.99, 7, 'LAPTOP-DXPS-15', 20),
('Men''s Cotton T-Shirt', 'Comfortable cotton t-shirt for everyday wear', 19.99, 8, 'MENS-TSHIRT-M-BLK', 100),
('Women''s Denim Jeans', 'Classic fit denim jeans', 49.99, 9, 'WMNS-JEANS-8-BLU', 80),
('Non-Stick Frying Pan', '12-inch non-stick frying pan', 29.99, 10, 'KITCHEN-PAN-12', 60),
('Harry Potter Complete Set', 'Box set of all 7 Harry Potter books', 79.99, 11, 'BOOK-HP-SET', 40),
('The Art of War', 'Classic book on military strategy', 12.99, 12, 'BOOK-AOFWAR', 75),
('2-Person Tent', 'Waterproof camping tent for 2 people', 89.99, 13, 'CAMP-TENT-2P', 30);

-- Orders
INSERT INTO orders (user_id, address_id, status, total_amount) VALUES
(1, 1, 'completed', 1499.99),
(2, 2, 'completed', 99.98),
(3, 3, 'processing', 929.98),
(4, 4, 'completed', 29.99),
(5, 5, 'pending', 179.97);

-- Order Items
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(1, 3, 1, 1299.99),
(1, 5, 1, 19.99),
(1, 7, 1, 29.99),
(2, 5, 2, 19.99),
(2, 7, 2, 29.99),
(3, 1, 1, 799.99),
(3, 9, 1, 12.99),
(3, 5, 2, 19.99),
(4, 7, 1, 29.99),
(5, 6, 1, 49.99),
(5, 9, 1, 12.99),
(5, 8, 1, 79.99);

-- Payments
INSERT INTO payments (order_id, amount, payment_method, transaction_id, status) VALUES
(1, 1499.99, 'credit_card', 'txn_1234567890', 'completed'),
(2, 99.98, 'paypal', 'txn_0987654321', 'completed'),
(3, 929.98, 'credit_card', 'txn_5678901234', 'pending'),
(4, 29.99, 'credit_card', 'txn_6789012345', 'completed'),
(5, 179.97, 'paypal', 'txn_7890123456', 'pending');

-- Reviews
INSERT INTO reviews (product_id, user_id, rating, comment) VALUES
(1, 2, 5, 'Great phone! The camera quality is excellent.'),
(3, 1, 4, 'Excellent laptop, fast and reliable. Battery life could be better.'),
(5, 3, 5, 'Very comfortable shirt, perfect fit.'),
(7, 2, 3, 'Good pan but food sticks sometimes.'),
(8, 4, 5, 'Perfect collection for any Harry Potter fan!'),
(10, 5, 4, 'Easy to set up and good quality for the price.');

-- Create indexes
CREATE INDEX idx_products_category_id ON products(category_id);
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);
CREATE INDEX idx_reviews_product_id ON reviews(product_id);
CREATE INDEX idx_reviews_user_id ON reviews(user_id);

-- Add more categories
INSERT INTO categories (name, description, parent_id) VALUES
('TVs', 'Television sets and accessories', 1),
('Audio', 'Speakers, headphones, and audio equipment', 1),
('Gaming', 'Video games and consoles', 1),
('Kids Clothing', 'Clothing for children', 2),
('Shoes', 'Footwear for all ages', 2),
('Kitchen Appliances', 'Small and large kitchen appliances', 3),
('Bedding', 'Sheets, pillows, and bedding accessories', 3),
('Mystery', 'Mystery and thriller books', 4),
('Science Fiction', 'Science fiction and fantasy books', 4),
('Fitness', 'Fitness and exercise equipment', 5),
('Water Sports', 'Equipment for water-based activities', 5);

-- Add more users
INSERT INTO users (email, password_hash, first_name, last_name, phone) VALUES
('emily.davis@example.com', '$2a$10$hJKxIY9ld1JnfMpj2L8eguYXQXMbLxaT5YyFUJhZ/iDZbDGTjsQW6', 'Emily', 'Davis', '555-234-5678'),
('alex.rodriguez@example.com', '$2a$10$FJlqpAFKZMzdjVjKY0/D5OqQhGm6Q5eQHRXt4F4UZGnJTMhdqe1c.', 'Alex', 'Rodriguez', '555-345-6789'),
('olivia.moore@example.com', '$2a$10$WMHWyDZHVZPgJU7P0E0OGuGIh9jb4/cNI.EcQ3eZCUf7EqMJuHXGe', 'Olivia', 'Moore', '555-456-7890'),
('william.taylor@example.com', '$2a$10$3qg0jlkvLZCWkZGRvuRPUe.g3Ry7jnc3CCEsHAO9OfK0J8CJZYGta', 'William', 'Taylor', '555-567-8901'),
('sophia.white@example.com', '$2a$10$Xl7.f4Zj.TjY5RHdQ.2p.OTb8hW7cENtEEi9KyLI5MhTvxw0XSyJW', 'Sophia', 'White', '555-678-9012'),
('ethan.harris@example.com', '$2a$10$JYoK5pF8zPwKpZ9SbRUjE.2CJd0qWJJUUr7Q3V9IVuXSFzMGvQ4Ce', 'Ethan', 'Harris', '555-789-0123'),
('ava.martin@example.com', '$2a$10$K3XfnYQSuG06YJ6.q2t3be7DsBl7b3eVKGXFi4h4pDrQQUbxEE4xC', 'Ava', 'Martin', '555-890-1234'),
('noah.thompson@example.com', '$2a$10$T9XgDJMZsU8QTGbQVkGiAetm6NmHD76WLcYgcGlzaQkuLqniZ4W2G', 'Noah', 'Thompson', '555-901-2345'),
('mia.garcia@example.com', '$2a$10$Vz2g5gDuMWvKI94/R9OUZur8wz4Jn78KPT.I3XRWUSd7F7NPJaBoW', 'Mia', 'Garcia', '555-012-3456'),
('james.walker@example.com', '$2a$10$2ZBtgr7H6JnDdpfCYQOvSOWPBh0mU0Qb.jpBJKQvbOSLTW7X44yAO', 'James', 'Walker', '555-123-4567');

-- Add more addresses
INSERT INTO addresses (user_id, address_line1, address_line2, city, state, postal_code, country, is_default) VALUES
(6, '789 Pine Ave', 'Apt 301', 'Boston', 'MA', '02108', 'USA', true),
(7, '456 Elm St', NULL, 'Austin', 'TX', '78701', 'USA', true),
(8, '123 Oak Rd', 'Suite 100', 'Denver', 'CO', '80202', 'USA', true),
(9, '987 Maple Ln', NULL, 'Miami', 'FL', '33101', 'USA', true),
(10, '654 Cherry Blvd', 'Unit 5B', 'Phoenix', 'AZ', '85001', 'USA', true),
(11, '321 Willow Dr', NULL, 'Atlanta', 'GA', '30301', 'USA', true),
(12, '789 Cedar St', 'Apt 202', 'Philadelphia', 'PA', '19101', 'USA', true),
(13, '456 Birch Ave', NULL, 'San Diego', 'CA', '92101', 'USA', true),
(14, '123 Spruce Rd', 'Suite 300', 'Dallas', 'TX', '75201', 'USA', true),
(15, '987 Ash Ln', NULL, 'Detroit', 'MI', '48201', 'USA', true),
(1, '456 Second St', 'Apt 2B', 'Seattle', 'WA', '98102', 'USA', false),
(2, '789 Third Ave', NULL, 'Portland', 'OR', '97206', 'USA', false),
(3, '123 Fourth Rd', 'Unit 3C', 'San Francisco', 'CA', '94103', 'USA', false);

-- Add more products
INSERT INTO products (name, description, price, category_id, sku, stock_quantity) VALUES
('Google Pixel 6', '128GB smartphone with advanced AI features', 699.99, 6, 'PHONE-PXL6-128', 40),
('OnePlus 9', '256GB Android smartphone with Hasselblad camera', 749.99, 6, 'PHONE-OP9-256', 35),
('Lenovo ThinkPad X1', '14-inch, Intel i5, 16GB RAM, 512GB SSD', 1199.99, 7, 'LAPTOP-LTP-X1', 15),
('HP Spectre x360', '13.5-inch, Intel i7, 16GB RAM, 1TB SSD', 1399.99, 7, 'LAPTOP-HP-X360', 18),
('Men''s Running Shoes', 'Lightweight running shoes with cushioned sole', 79.99, 16, 'MENS-SHOES-10-BLK', 50),
('Women''s Winter Jacket', 'Insulated jacket for cold weather', 129.99, 9, 'WMNS-JACKET-M-BLU', 30),
('Kids T-Shirt Set', 'Pack of 5 colorful t-shirts for children', 39.99, 15, 'KIDS-TSHIRT-S-MULTI', 45),
('Digital Air Fryer', '5.5 quart digital air fryer with 6 presets', 89.99, 17, 'KITCHEN-AF-5.5Q', 25),
('Blender Set', 'High-powered blender with multiple attachments', 69.99, 17, 'KITCHEN-BLND-HP', 20),
('Queen Sheet Set', '100% cotton 400-thread count sheet set', 59.99, 18, 'HOME-SHEET-Q-WHT', 40),
('Memory Foam Pillow', 'Ergonomic memory foam pillow for neck support', 49.99, 18, 'HOME-PILLOW-MF', 60),
('The Silent Patient', 'Bestselling psychological thriller novel', 14.99, 19, 'BOOK-SILPAT', 55),
('Gone Girl', 'Popular mystery thriller book', 12.99, 19, 'BOOK-GONGRL', 40),
('Dune', 'Classic science fiction novel', 11.99, 20, 'BOOK-DUNE', 65),
('The Martian', 'Bestselling sci-fi novel about survival on Mars', 13.99, 20, 'BOOK-MRTIAN', 50),
('Yoga Mat', 'Non-slip exercise yoga mat, 6mm thick', 24.99, 21, 'FITNESS-YOGA-MAT', 70),
('Adjustable Dumbbells', 'Set of adjustable dumbbells, 5-25lbs each', 149.99, 21, 'FITNESS-DUMB-ADJ', 20),
('Snorkel Set', 'Mask, snorkel, and fins set for water activities', 34.99, 22, 'WATER-SNRKL-SET', 25),
('Inflatable Paddle Board', 'Stand-up paddle board with pump and paddle', 299.99, 22, 'WATER-PADDLE-BRD', 15),
('55" 4K Smart TV', 'Ultra HD smart television with HDR', 599.99, 14, 'TV-55-4K-SMART', 10),
('Wireless Earbuds', 'Bluetooth earbuds with noise cancellation', 129.99, 15, 'AUDIO-EARBUD-NC', 40),
('PlayStation 5', 'Latest generation gaming console', 499.99, 16, 'GAMING-PS5', 8);

-- Add more orders
INSERT INTO orders (user_id, address_id, status, total_amount) VALUES
(6, 6, 'completed', 779.98),
(7, 7, 'processing', 599.99),
(8, 8, 'completed', 129.99),
(9, 9, 'pending', 229.97),
(10, 10, 'cancelled', 499.99),
(11, 11, 'completed', 184.97),
(12, 12, 'completed', 399.98),
(13, 13, 'processing', 1699.98),
(14, 14, 'pending', 59.98),
(15, 15, 'completed', 299.99),
(1, 16, 'completed', 649.98),
(2, 17, 'processing', 349.98),
(3, 18, 'completed', 1299.97),
(4, 4, 'pending', 299.99),
(5, 5, 'completed', 149.99);

-- Add more order items
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(6, 11, 1, 49.99),
(6, 15, 1, 13.99),
(6, 18, 1, 34.99),
(6, 20, 1, 599.99),
(6, 12, 1, 12.99),
(6, 16, 1, 24.99),
(6, 21, 1, 129.99),
(7, 20, 1, 599.99),
(8, 21, 1, 129.99),
(9, 16, 1, 24.99),
(9, 17, 1, 149.99),
(9, 12, 1, 12.99),
(9, 14, 1, 11.99),
(9, 13, 1, 12.99),
(10, 22, 1, 499.99),
(11, 16, 1, 24.99),
(11, 14, 1, 11.99),
(11, 18, 1, 34.99),
(11, 13, 1, 12.99),
(11, 12, 1, 12.99),
(11, 15, 1, 13.99),
(11, 19, 1, 299.99),
(11, 11, 1, 49.99),
(12, 19, 1, 299.99),
(12, 17, 1, 149.99),
(12, 15, 1, 13.99),
(12, 14, 1, 11.99),
(12, 12, 1, 12.99),
(13, 3, 1, 1299.99),
(13, 4, 1, 1399.99),
(14, 13, 1, 12.99),
(14, 15, 1, 13.99),
(14, 12, 1, 12.99),
(14, 14, 1, 11.99),
(15, 19, 1, 299.99),
(16, 11, 1, 49.99),
(16, 6, 1, 49.99),
(16, 20, 1, 599.99),
(17, 18, 1, 34.99),
(17, 17, 1, 149.99),
(17, 16, 2, 24.99),
(17, 13, 1, 12.99),
(17, 14, 2, 11.99),
(17, 12, 3, 12.99),
(17, 15, 2, 13.99),
(18, 4, 1, 1399.99),
(18, 15, 1, 13.99),
(18, 16, 1, 24.99),
(18, 13, 1, 12.99),
(18, 18, 1, 34.99),
(19, 19, 1, 299.99),
(20, 17, 1, 149.99);

-- Add more payments
INSERT INTO payments (order_id, amount, payment_method, transaction_id, status) VALUES
(6, 779.98, 'credit_card', 'txn_8901234567', 'completed'),
(7, 599.99, 'paypal', 'txn_9012345678', 'processing'),
(8, 129.99, 'credit_card', 'txn_0123456789', 'completed'),
(9, 229.97, 'paypal', 'txn_1234567890', 'pending'),
(10, 499.99, 'credit_card', 'txn_2345678901', 'refunded'),
(11, 184.97, 'credit_card', 'txn_3456789012', 'completed'),
(12, 399.98, 'paypal', 'txn_4567890123', 'completed'),
(13, 1699.98, 'credit_card', 'txn_5678901234', 'processing'),
(14, 59.98, 'credit_card', 'txn_6789012345', 'pending'),
(15, 299.99, 'paypal', 'txn_7890123456', 'completed'),
(16, 649.98, 'credit_card', 'txn_8901234567', 'completed'),
(17, 349.98, 'apple_pay', 'txn_9012345678', 'processing'),
(18, 1299.97, 'credit_card', 'txn_0123456789', 'completed'),
(19, 299.99, 'google_pay', 'txn_1234567890', 'pending'),
(20, 149.99, 'credit_card', 'txn_2345678901', 'completed');

-- Add more reviews
INSERT INTO reviews (product_id, user_id, rating, comment) VALUES
(2, 7, 4, 'Good phone, but battery life could be better.'),
(4, 8, 5, 'Amazing laptop! Fast and reliable for all my needs.'),
(5, 9, 3, 'The shirt is comfortable but runs a bit small.'),
(6, 10, 4, 'Good quality jeans, perfect fit.'),
(7, 11, 5, 'Best pan I''ve ever owned. Nothing sticks to it!'),
(8, 12, 5, 'Beautiful collection, my kids love it.'),
(9, 13, 4, 'Classic book with timeless wisdom.'),
(10, 14, 3, 'Decent tent, but a bit difficult to set up.'),
(11, 15, 4, 'Great for neck support, helped with my back pain.'),
(12, 1, 5, 'Couldn''t put it down! Best thriller I''ve read this year.'),
(13, 2, 4, 'Gripping story with unexpected twists.'),
(14, 3, 5, 'A sci-fi masterpiece. Must read for any fan of the genre.'),
(15, 4, 4, 'Engaging and scientifically interesting.'),
(16, 5, 5, 'Perfect thickness and grip. Great for yoga practice.'),
(17, 6, 4, 'Good adjustable weights, but the locking mechanism is a bit finicky.'),
(18, 7, 3, 'The mask fogs up sometimes, but overall decent quality.'),
(19, 8, 5, 'Sturdy paddle board that''s easy to inflate and pack away.'),
(20, 9, 4, 'Great picture quality. Smart features work well.'),
(21, 10, 5, 'Incredible sound quality and noise cancellation is top-notch.'),
(22, 11, 5, 'Amazing console, worth the wait to get one!'),
(1, 12, 4, 'Camera is excellent but the UI takes some getting used to.'),
(3, 13, 5, 'Perfect for work and personal use. Battery lasts all day.'),
(5, 14, 4, 'Good fabric quality, washes well without shrinking.'),
(7, 15, 5, 'Heats evenly and cleanup is a breeze.'),
(9, 1, 3, 'Interesting read but the translation could be better.'),
(11, 2, 5, 'Most comfortable pillow I''ve ever had.'),
(13, 3, 4, 'Clever plot with great character development.'),
(15, 4, 5, 'Fascinating story that really makes you think.'),
(17, 5, 3, 'Good for beginners but serious lifters might want something more robust.'),
(19, 6, 5, 'Stable and tracks well in the water. Great for beginners and experienced paddlers alike.'),
(21, 7, 4, 'Sound quality is amazing. Battery life could be longer.'),
(2, 8, 4, 'Fast performance and great camera. The UI is intuitive and user-friendly.'),
(4, 9, 5, 'Perfect for work and gaming. No lag even with demanding applications.'),
(6, 10, 4, 'Comfortable and stylish. Looks more expensive than it is.'),
(8, 11, 5, 'My kids are now reading more than ever thanks to this set!'),
(10, 12, 4, 'Lightweight and easy to carry. Waterproofing works well in light rain.'),
(12, 13, 5, 'Couldn''t stop reading! The twist at the end was shocking.'),
(14, 14, 5, 'Classic sci-fi that still holds up today. Beautiful world-building.'),
(16, 15, 4, 'Good thickness and doesn''t slip during use.'),
(18, 1, 3, 'Decent quality but the fins are a bit flimsy.'),
(20, 2, 5, 'Crystal clear picture and the smart features are easy to use.'),
(22, 3, 4, 'Amazing graphics but some games still have loading issues.'),
(1, 4, 5, 'Best phone I''ve ever had. Camera quality is outstanding!'),
(3, 5, 4, 'Fast and reliable. Perfect for work and casual use.'),
(5, 6, 5, 'Comfortable and looks great. Gets many compliments.'),
(7, 7, 4, 'Cooks evenly and cleaning is easy. Good value for money.');

-- Add promotional discounts table
CREATE TABLE promotions (
    promotion_id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    discount_type VARCHAR(20) NOT NULL, -- percentage, fixed_amount
    discount_value DECIMAL(10,2) NOT NULL,
    min_purchase_amount DECIMAL(10,2),
    starts_at TIMESTAMP NOT NULL,
    ends_at TIMESTAMP NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample promotions
INSERT INTO promotions (code, description, discount_type, discount_value, min_purchase_amount, starts_at, ends_at) VALUES
('SUMMER2023', 'Summer sale discount', 'percentage', 15.00, 50.00, '2023-06-01 00:00:00', '2023-08-31 23:59:59'),
('WELCOME10', 'New customer discount', 'percentage', 10.00, 0.00, '2023-01-01 00:00:00', '2023-12-31 23:59:59'),
('FREESHIP', 'Free shipping on orders over $100', 'fixed_amount', 15.00, 100.00, '2023-01-01 00:00:00', '2023-12-31 23:59:59'),
('FLASH25', 'Flash sale 25% off', 'percentage', 25.00, 75.00, '2023-07-15 00:00:00', '2023-07-17 23:59:59'),
('HOLIDAY50', 'Holiday season $50 off', 'fixed_amount', 50.00, 200.00, '2023-11-20 00:00:00', '2023-12-26 23:59:59');

-- Create wishlist table
CREATE TABLE wishlists (
    wishlist_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    product_id INTEGER REFERENCES products(product_id),
    added_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, product_id)
);

-- Add sample wishlist items
INSERT INTO wishlists (user_id, product_id) VALUES
(1, 20),
(1, 21),
(1, 22),
(2, 17),
(2, 19),
(3, 4),
(3, 14),
(3, 15),
(4, 8),
(4, 9),
(5, 11),
(5, 16),
(6, 2),
(6, 22),
(7, 3),
(7, 19),
(8, 6),
(8, 10),
(9, 12),
(9, 13),
(10, 5),
(10, 7);

-- Create product_tags table for better categorization
CREATE TABLE product_tags (
    tag_id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL
);

-- Insert sample tags
INSERT INTO product_tags (name) VALUES
('New Arrival'),
('Best Seller'),
('Limited Edition'),
('Sale'),
('Eco-friendly'),
('Handmade'),
('Imported'),
('Organic'),
('Vegan'),
('Premium');

-- Create product_tag_mapping junction table
CREATE TABLE product_tag_mapping (
    product_id INTEGER REFERENCES products(product_id),
    tag_id INTEGER REFERENCES product_tags(tag_id),
    PRIMARY KEY (product_id, tag_id)
);

-- Add sample product tag mappings
INSERT INTO product_tag_mapping (product_id, tag_id) VALUES
(1, 1), (1, 2),
(2, 4), (2, 7),
(3, 2), (3, 10),
(4, 1), (4, 3),
(5, 2), (5, 8),
(6, 4), (6, 7),
(7, 2), (7, 5),
(8, 3), (8, 6),
(9, 2), (9, 10),
(10, 5), (10, 7),
(11, 1), (11, 9),
(12, 2), (12, 4),
(13, 3), (13, 7),
(14, 2), (14, 10),
(15, 4), (15, 5),
(16, 1), (16, 8),
(17, 2), (17, 10),
(18, 4), (18, 7),
(19, 3), (19, 5),
(20, 1), (20, 2),
(21, 1), (21, 3),
(22, 2), (22, 3);

-- Create shopping_cart table
CREATE TABLE shopping_carts (
    cart_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create cart_items table
CREATE TABLE cart_items (
    cart_item_id SERIAL PRIMARY KEY,
    cart_id INTEGER REFERENCES shopping_carts(cart_id),
    product_id INTEGER REFERENCES products(product_id),
    quantity INTEGER NOT NULL DEFAULT 1,
    added_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample shopping carts
INSERT INTO shopping_carts (user_id) VALUES
(1), (2), (3), (4), (5), (6), (7), (8);

-- Insert sample cart items
INSERT INTO cart_items (cart_id, product_id, quantity) VALUES
(1, 20, 1),
(1, 16, 2),
(2, 12, 1),
(2, 13, 1),
(2, 14, 1),
(3, 22, 1),
(4, 7, 1),
(4, 11, 2),
(5, 19, 1),
(6, 3, 1),
(6, 21, 1),
(7, 5, 3),
(7, 6, 1),
(8, 8, 1),
(8, 9, 1);

-- Additional indexes for performance
CREATE INDEX idx_products_price ON products(price);
CREATE INDEX idx_products_is_active ON products(is_active);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_reviews_rating ON reviews(rating);
CREATE INDEX idx_promotions_code ON promotions(code);
CREATE INDEX idx_promotions_is_active ON promotions(is_active);
