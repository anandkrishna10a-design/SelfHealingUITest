import sqlite3


# Connect to the SmartKart database
connection = sqlite3.connect("smartkart.db")

cursor = connection.cursor()


# Create products table if it does not already exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS products (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    name TEXT NOT NULL,

    category TEXT NOT NULL,

    price REAL NOT NULL,

    description TEXT,

    image TEXT,

    stock INTEGER NOT NULL DEFAULT 0

)
""")


# Remove existing products before inserting demo data.
# This prevents duplicate products if init_db.py is run again.
cursor.execute("DELETE FROM products")


# Reset the automatic ID counter
cursor.execute(
    "DELETE FROM sqlite_sequence WHERE name='products'"
)


# SmartKart products
products = [

    (
        "Laptop",
        "Computers",
        50000,
        "Powerful everyday laptop for work, study and entertainment.",
        "images/laptop.jpg",
        10
    ),

    (
        "Headphones",
        "Audio",
        2000,
        "Comfortable wireless headphones with clear and powerful sound.",
        "images/headphones.jpg",
        20
    ),

    (
        "Keyboard",
        "Accessories",
        1500,
        "Full-size keyboard designed for comfortable everyday typing.",
        "images/keyboard.jpg",
        15
    ),

    (
        "Wireless Mouse",
        "Accessories",
        900,
        "Lightweight wireless mouse with smooth and precise tracking.",
        "images/mouse.jpg",
        25
    ),

    (
        "Gaming Monitor",
        "Computers",
        18000,
        "High refresh-rate display for gaming and everyday productivity.",
        "images/monitor.jpg",
        8
    ),

    (
        "Webcam",
        "Accessories",
        2500,
        "Full HD webcam for online meetings and video calls.",
        "images/webcam.jpg",
        12
    ),

    (
        "Bluetooth Speaker",
        "Audio",
        3000,
        "Portable wireless speaker with powerful room-filling audio.",
        "images/speaker.jpg",
        18
    ),

    (
        "SSD 1TB",
        "Storage",
        6500,
        "Fast solid-state storage for computers and laptops.",
        "images/ssd.jpg",
        14
    ),

    (
        "USB Hub",
        "Accessories",
        1200,
        "Multi-port USB hub for connecting several devices.",
        "images/usb-hub.jpg",
        30
    ),

    (
        "External Hard Drive",
        "Storage",
        5000,
        "Portable storage for files, photos, videos and backups.",
        "images/hard-drive.jpg",
        11
    ),

    (
        "Microphone",
        "Audio",
        3500,
        "USB microphone for meetings, streaming and recording.",
        "images/microphone.jpg",
        9
    ),

    (
        "Laptop Stand",
        "Accessories",
        1800,
        "Adjustable laptop stand for comfort and desk organization.",
        "images/laptop-stand.jpg",
        22
    )

]


# Insert products into database
cursor.executemany("""
INSERT INTO products
(
    name,
    category,
    price,
    description,
    image,
    stock
)
VALUES (?, ?, ?, ?, ?, ?)
""", products)


connection.commit()


# Check how many products were inserted
cursor.execute("SELECT COUNT(*) FROM products")

product_count = cursor.fetchone()[0]


connection.close()


print("SmartKart database initialized successfully.")
print(f"{product_count} products added to the database.")