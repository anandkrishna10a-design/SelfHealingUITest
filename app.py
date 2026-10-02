from flask import Flask, jsonify, send_from_directory
import sqlite3

app = Flask(__name__)

DATABASE = "smartkart.db"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_database_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


# =========================================================
# HOME / LOGIN PAGE
# =========================================================

@app.route("/")
def home():
    return send_from_directory("demo_app", "index.html")


@app.route("/index.html")
def index_page():
    return send_from_directory("demo_app", "index.html")


# =========================================================
# PRODUCTS PAGE
# =========================================================

@app.route("/products.html")
def products_page():
    return send_from_directory("demo_app", "products.html")


# =========================================================
# CART PAGE
# =========================================================

@app.route("/cart.html")
def cart_page():
    return send_from_directory("demo_app", "cart.html")


@app.route("/cart")
def cart_page_short():
    return send_from_directory("demo_app", "cart.html")


# =========================================================
# PRODUCT IMAGES
# =========================================================

@app.route("/images/<path:filename>")
def product_images(filename):
    return send_from_directory(
        "demo_app/images",
        filename
    )


# =========================================================
# PRODUCTS API
# =========================================================

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

        product_list.append({

            "id": product["id"],

            "name": product["name"],

            "category": product["category"],

            "price": product["price"],

            "description": product["description"],

            "image": product["image"],

            "stock": product["stock"]

        })


    return jsonify(product_list)


# =========================================================
# START FLASK SERVER
# =========================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=8080,
        debug=True
    )