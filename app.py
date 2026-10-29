
import os
import math
import sqlite3
from pathlib import Path

from flask import Flask, request, redirect, url_for, render_template_string

app = Flask(__name__)

VERSION = "v2"

# Works on Windows and in Docker.
DEFAULT_DB = Path(__file__).resolve().parent / "sales.db"
DB_PATH = Path(os.getenv("DB_PATH", str(DEFAULT_DB))).resolve()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_db():
    connection = sqlite3.connect(str(DB_PATH), timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                price REAL NOT NULL CHECK(price > 0)
            )
        """)


initialize_db()


HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Sales System - V2</title>

    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f1f4f9;
            margin: 0;
            padding: 25px;
            color: #243047;
        }

        main {
            max-width: 900px;
            margin: 30px auto;
            padding: 28px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 3px 15px rgba(0, 0, 0, 0.07);
        }

        h1, h2 {
            color: #243b64;
        }

        .version {
            color: #64748b;
        }

        input, button {
            box-sizing: border-box;
            width: 100%;
            padding: 12px;
            margin: 8px 0;
        }

        input {
            border: 1px solid #cbd5e1;
            border-radius: 5px;
        }

        button {
            background: #243b64;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }

        button:hover {
            background: #172a4a;
        }

        .message {
            background: #e6f6e9;
            color: #176534;
            padding: 12px;
            border-radius: 6px;
        }

        .table-wrapper {
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 18px;
        }

        th, td {
            border: 1px solid #dce1e8;
            padding: 12px;
            text-align: left;
        }

        th {
            background: #e8effb;
        }

        .empty {
            text-align: center;
            color: #64748b;
        }
    </style>
</head>

<body>
<main>
    <h1>Sales System</h1>
    <p>Registration Number: 24MIS0356</p>
    <p class="version">Version 2 — View Sales</p>

    <h2>Add Sale - Record Sale</h2>

    {% if saved %}
        <p class="message">Sale recorded successfully!</p>
    {% endif %}

    <form method="post" action="{{ url_for('add_sale') }}">
        <input
            type="text"
            name="product"
            placeholder="Product Name"
            maxlength="100"
            required
        >

        <input
            type="number"
            name="quantity"
            placeholder="Quantity"
            min="1"
            step="1"
            required
        >

        <input
            type="number"
            name="price"
            placeholder="Price per Unit (₹)"
            min="0.01"
            step="0.01"
            required
        >

        <button type="submit">Record Sale</button>
    </form>

    <h2>View Sales</h2>
    <p>All recorded sales are listed below.</p>

    <div class="table-wrapper">
        <table>
            <thead>
                <tr>
                    <th>Sale ID</th>
                    <th>Product</th>
                    <th>Quantity</th>
                    <th>Unit Price</th>
                    <th>Sale Amount</th>
                </tr>
            </thead>

            <tbody>
                {% for sale in sales %}
                <tr>
                    <td>{{ sale['id'] }}</td>
                    <td>{{ sale['product'] }}</td>
                    <td>{{ sale['quantity'] }}</td>
                    <td>₹{{ "%.2f"|format(sale['price']) }}</td>
                    <td>
                        ₹{{ "%.2f"|format(
                            sale['quantity'] * sale['price']
                        ) }}
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="5" class="empty">
                        No sales recorded yet.
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</main>
</body>
</html>
"""


@app.get("/")
def index():
    with get_db() as db:
        sales = db.execute(
            """
            SELECT id, product, quantity, price
            FROM sales
            ORDER BY id DESC
            """
        ).fetchall()

    return render_template_string(
        HTML_PAGE,
        sales=sales,
        saved=request.args.get("saved") == "1"
    )


@app.post("/add")
def add_sale():
    product = request.form.get("product", "").strip()

    try:
        quantity = int(request.form.get("quantity", ""))
        price = float(request.form.get("price", ""))

        if (
            not product
            or len(product) > 100
            or quantity <= 0
            or quantity > 1_000_000
            or not math.isfinite(price)
            or price <= 0
            or price > 1_000_000_000
            or not math.isfinite(quantity * price)
        ):
            raise ValueError

    except (ValueError, TypeError, OverflowError):
        return (
            "Invalid details. Enter a product, positive "
            "whole-number quantity and valid price.",
            400
        )

    try:
        with get_db() as db:
            db.execute(
                """
                INSERT INTO sales (product, quantity, price)
                VALUES (?, ?, ?)
                """,
                (product, quantity, price)
            )
    except sqlite3.Error:
        app.logger.exception("Failed to record sale")
        return "Unable to record sale.", 500

    return redirect(url_for("index", saved="1"))


@app.get("/health")
def health():
    try:
        with get_db() as db:
            db.execute("SELECT 1").fetchone()

        return {"status": "healthy", "version": VERSION}, 200

    except sqlite3.Error:
        return {"status": "unhealthy"}, 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=False
    )
