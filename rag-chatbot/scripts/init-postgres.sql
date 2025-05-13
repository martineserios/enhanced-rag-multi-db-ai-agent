-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create a sample products table
CREATE TABLE IF NOT EXISTS products (
    product_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    category VARCHAR(100),
    in_stock BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create a sample customers table
CREATE TABLE IF NOT EXISTS customers (
    customer_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    address TEXT,
    signup_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create a sample orders table
CREATE TABLE IF NOT EXISTS orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id),
    product_id INTEGER REFERENCES products(product_id),
    quantity INTEGER NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample products
INSERT INTO products (name, description, price, category) VALUES
    ('Laptop Pro', 'High-performance laptop with 16GB RAM and 1TB SSD', 1299.99, 'Electronics'),
    ('Smartphone X', 'Latest smartphone with 5G capability', 899.99, 'Electronics'),
    ('Wireless Headphones', 'Noise-cancelling wireless headphones', 199.99, 'Audio'),
    ('Smart Watch', 'Fitness tracker and smartwatch', 249.99, 'Wearables'),
    ('Coffee Maker', 'Programmable coffee maker with thermal carafe', 89.99, 'Kitchen');

-- Insert sample customers
INSERT INTO customers (name, email, address) VALUES
    ('John Doe', 'john.doe@example.com', '123 Main St, Anytown, USA'),
    ('Jane Smith', 'jane.smith@example.com', '456 Oak Ave, Somewhere, USA'),
    ('Robert Johnson', 'robert.johnson@example.com', '789 Pine Rd, Nowhere, USA'),
    ('Emily Davis', 'emily.davis@example.com', '321 Maple Dr, Anywhere, USA'),
    ('Michael Wilson', 'michael.wilson@example.com', '654 Birch Ln, Everywhere, USA');

-- Insert sample orders
INSERT INTO orders (customer_id, product_id, quantity, price) VALUES
    (1, 1, 1, 1299.99),
    (1, 3, 1, 199.99),
    (2, 2, 1, 899.99),
    (3, 5, 2, 179.98),
    (4, 4, 1, 249.99),
    (5, 1, 1, 1299.99),
    (2, 3, 1, 199.99),
    (3, 2, 1, 899.99),
    (4, 5, 1, 89.99),
    (5, 4, 2, 499.98);
