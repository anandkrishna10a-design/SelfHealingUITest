from flask import Flask, jsonify, send_from_directory, request
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)

DATABASE = "smartkart.db"


def get_database_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


# ---------------------------------------------------------
# USER TABLE SETUP
# ---------------------------------------------------------

def initialize_users_table():
    connection = get_database_connection()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
        """
    )

    # Keep the existing demo account working
    existing_user = connection.execute(
        "SELECT id FROM users WHERE username = ?",
        ("testacc",)
    ).fetchone()

    if existing_user is None:
        connection.execute(
            """
            INSERT INTO users (username, password_hash)
            VALUES (?, ?)
            """,
            (
                "testacc",
                generate_password_hash("vs12345")
            )
        )

    connection.commit()
    connection.close()


initialize_users_table()


# ---------------------------------------------------------
# PAGE ROUTES
# ---------------------------------------------------------

@app.route("/")
def home():
    return send_from_directory("demo_app", "index.html")


@app.route("/index.html")
def index_page():
    return send_from_directory("demo_app", "index.html")


@app.route("/signup.html")
def signup_page():
    return send_from_directory("demo_app", "signup.html")


@app.route("/products.html")
def products_page():
    return send_from_directory("demo_app", "products.html")


@app.route("/cart.html")
def cart_page():
    return send_from_directory("demo_app", "cart.html")


@app.route("/cart")
def cart_page_short():
    return send_from_directory("demo_app", "cart.html")


# ---------------------------------------------------------
# IMAGE ROUTE
# ---------------------------------------------------------

@app.route("/images/<path:filename>")
def product_images(filename):
    return send_from_directory("demo_app/images", filename)


# ---------------------------------------------------------
# PRODUCTS API
# ---------------------------------------------------------

@app.route("/api/products")
def get_products():

    connection = get_database_connection()

    products = connection.execute(
        """
        SELECT
            id,
            name,
            category,
            price,
            description,
            image,
            stock
        FROM products
        ORDER BY id
        """
    ).fetchall()

    connection.close()

    product_list = []

    for product in products:
        product_list.append(
            {
                "id": product["id"],
                "name": product["name"],
                "category": product["category"],
                "price": product["price"],
                "description": product["description"],
                "image": product["image"],
                "stock": product["stock"]
            }
        )

    return jsonify(product_list)


# ---------------------------------------------------------
# SIGN UP API
# ---------------------------------------------------------

@app.route("/api/signup", methods=["POST"])
def signup():

    data = request.get_json()

    if not data:
        return jsonify(
            {
                "success": False,
                "message": "Invalid request"
            }
        ), 400

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    # Username/password required
    if not username or not password:
        return jsonify(
            {
                "success": False,
                "message": "Username and password are required"
            }
        ), 400

    # Username validation
    if len(username) < 3:
        return jsonify(
            {
                "success": False,
                "message": "Username must be at least 3 characters"
            }
        ), 400

    # Password validation
    if len(password) < 6:
        return jsonify(
            {
                "success": False,
                "message": "Password must be at least 6 characters"
            }
        ), 400

    connection = get_database_connection()

    # Check whether username already exists
    existing_user = connection.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    if existing_user:
        connection.close()

        return jsonify(
            {
                "success": False,
                "message": "Username already exists"
            }
        ), 409

    # Store a secure password hash instead of plain password
    password_hash = generate_password_hash(password)

    connection.execute(
        """
        INSERT INTO users (username, password_hash)
        VALUES (?, ?)
        """,
        (username, password_hash)
    )

    connection.commit()
    connection.close()

    return jsonify(
        {
            "success": True,
            "message": "Account created successfully"
        }
    ), 201


# ---------------------------------------------------------
# LOGIN API
# ---------------------------------------------------------

@app.route("/api/login", methods=["POST"])
def login():

    data = request.get_json()

    if not data:
        return jsonify(
            {
                "success": False,
                "message": "Invalid request"
            }
        ), 400

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    connection = get_database_connection()

    user = connection.execute(
        """
        SELECT
            id,
            username,
            password_hash
        FROM users
        WHERE username = ?
        """,
        (username,)
    ).fetchone()

    connection.close()

    # Verify password against stored hash
    if user and check_password_hash(
        user["password_hash"],
        password
    ):
        return jsonify(
            {
                "success": True,
                "username": user["username"]
            }
        )

    return jsonify(
        {
            "success": False,
            "message": "Invalid username or password"
        }
    ), 401


# ---------------------------------------------------------
# START FLASK SERVER
# ---------------------------------------------------------

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=8080,
        debug=True
    )