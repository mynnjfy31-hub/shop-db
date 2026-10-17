from flask import Flask, request, jsonify
import sqlite3
import hashlib
import jwt
import datetime
from functools import wraps

app = Flask(__name__)
SECRET_KEY = "moein_shop_secret_key"

# ===== اتصال به دیتابیس =====
def get_db():
    conn = sqlite3.connect('shop.db')
    conn.row_factory = sqlite3.Row
    return conn

# ===== هش کردن رمز =====
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ===== ساخت دیتابیس =====
def create_db():
    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()

    # جدول کاربران
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    ''')

    # جدول دسته‌بندی
    cur.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT
        )
    ''')

    # جدول محصولات
    cur.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price INTEGER NOT NULL,
            stock INTEGER DEFAULT 0,
            category_id INTEGER,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    ''')

    # جدول سبد خرید
    cur.execute('''
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    ''')

    # جدول سفارشات
    cur.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total_price INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # جدول آیتم‌های سفارش
    cur.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price INTEGER NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    ''')

    conn.commit()
    conn.close()
    print("دیتابیس shop.db با ۶ جدول ساخته شد!")

# ===== ساخت توکن =====
def create_token(user_id, is_admin=0):
    payload = {
        'user_id': user_id,
        'is_admin': is_admin,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

# ===== دکوراتور احراز هویت =====
def token_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "توکن ارسال نشده"}), 401
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            request.user_id = payload['user_id']
            request.is_admin = payload['is_admin']
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "توکن منقضی شده"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "توکن نامعتبر است"}), 401
        return func(*args, **kwargs)
    return wrapper

# ===== ثبت‌نام =====
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    print("DEBUG - Data received by server:", data)
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not name or not email or not password:
        return jsonify({"error": "نام، ایمیل و رمز الزامی است"}), 400

    hashed = hash_password(password)
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)',
                    (name, email, hashed))
        db.commit()
        user_id = cur.lastrowid
        db.close()
        return jsonify({"id": user_id, "message": "ثبت‌نام موفق!"}), 201
    except sqlite3.IntegrityError:
        db.close()
        return jsonify({"error": "این ایمیل قبلاً ثبت شده است"}), 400

# ===== ورود =====
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "ایمیل و رمز الزامی است"}), 400

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    db.close()

    if user and user['password'] == hash_password(password):
        token = create_token(user['id'], user['is_admin'])
        return jsonify({
            "message": "خوش آمدی!",
            "token": token,
            "user_id": user['id'],
            "name": user['name'],
            "is_admin": user['is_admin']
        }), 200

    return jsonify({"error": "ایمیل یا رمز اشتباه است"}), 401

# ===== پروفایل =====
@app.route('/api/profile', methods=['GET'])
@token_required
def profile():
    db = get_db()
    user = db.execute('SELECT id, name, email, is_admin FROM users WHERE id = ?',
                      (request.user_id,)).fetchone()
    db.close()
    if user:
        return jsonify(dict(user))
    return jsonify({"error": "کاربر پیدا نشد"}), 404
# ===== GET: لیست همه محصولات =====
@app.route('/api/products', methods=['GET'])
def get_products():
    db = get_db()
    products = db.execute('SELECT * FROM products').fetchall()
    db.close()
    return jsonify([dict(p) for p in products])

# ===== GET: یک محصول با شناسه =====
@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    db = get_db()
    product = db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    db.close()
    if product:
        return jsonify(dict(product))
    return jsonify({"error": "محصول پیدا نشد"}), 404

# ===== GET: جستجوی محصولات =====
@app.route('/api/products/search', methods=['GET'])
def search_products():
    query = request.args.get('q', '')
    if not query:
        return jsonify({"error": "عبارت جستجو الزامی است"}), 400

    db = get_db()
    products = db.execute(
        'SELECT * FROM products WHERE name LIKE ?',
        (f'%{query}%',)
    ).fetchall()
    db.close()

    if products:
        return jsonify([dict(p) for p in products])
    return jsonify({"message": "محصولی پیدا نشد"}), 404

# ===== GET: محصولات یک دسته =====
@app.route('/api/products/category/<int:category_id>', methods=['GET'])
def get_products_by_category(category_id):
    db = get_db()
    products = db.execute('SELECT * FROM products WHERE category_id = ?', (category_id,)).fetchall()
    db.close()
    return jsonify([dict(p) for p in products])

# ===== POST: اضافه کردن محصول (فقط ادمین) =====
@app.route('/api/products', methods=['POST'])
@token_required
def add_product():
    if not request.is_admin:
        return jsonify({"error": "فقط ادمین می‌تونه محصول اضافه کنه"}), 403

    data = request.get_json()
    name = data.get('name')
    price = data.get('price')

    if not name or price is None:
        return jsonify({"error": "نام و قیمت الزامی است"}), 400

    db = get_db()
    cur = db.cursor()
    cur.execute('''
        INSERT INTO products (name, description, price, stock, category_id)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        name,
        data.get('description'),
        price,
        data.get('stock', 0),
        data.get('category_id')
    ))
    db.commit()
    product_id = cur.lastrowid
    db.close()
    return jsonify({"id": product_id, "message": "محصول اضافه شد"}), 201

# ===== PUT: ویرایش محصول (فقط ادمین) =====
@app.route('/api/products/<int:product_id>', methods=['PUT'])
@token_required
def update_product(product_id):
    if not request.is_admin:
        return jsonify({"error": "فقط ادمین می‌تونه محصول رو ویرایش کنه"}), 403

    data = request.get_json()
    db = get_db()
    cur = db.cursor()

    existing = cur.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    if not existing:
        db.close()
        return jsonify({"error": "محصول پیدا نشد"}), 404

    if data.get('name'):
        cur.execute('UPDATE products SET name = ? WHERE id = ?', (data['name'], product_id))
    if data.get('description'):
        cur.execute('UPDATE products SET description = ? WHERE id = ?', (data['description'], product_id))
    if data.get('price') is not None:
        cur.execute('UPDATE products SET price = ? WHERE id = ?', (data['price'], product_id))
    if data.get('stock') is not None:
        cur.execute('UPDATE products SET stock = ? WHERE id = ?', (data['stock'], product_id))
    if data.get('category_id'):
        cur.execute('UPDATE products SET category_id = ? WHERE id = ?', (data['category_id'], product_id))

    db.commit()
    db.close()
    return jsonify({"message": f"محصول {product_id} به‌روز شد"}), 200

# ===== DELETE: حذف محصول (فقط ادمین) =====
@app.route('/api/products/<int:product_id>', methods=['DELETE'])
@token_required
def delete_product(product_id):
    if not request.is_admin:
        return jsonify({"error": "فقط ادمین می‌تونه محصول حذف کنه"}), 403

    db = get_db()
    cur = db.cursor()
    existing = cur.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    if not existing:
        db.close()
        return jsonify({"error": "محصول پیدا نشد"}), 404

    cur.execute('DELETE FROM products WHERE id = ?', (product_id,))
    db.commit()
    db.close()
    return jsonify({"message": f"محصول {product_id} حذف شد"}), 200

# ===== GET: لیست همه دسته‌بندی‌ها =====
@app.route('/api/categories', methods=['GET'])
def get_categories():
    db = get_db()
    categories = db.execute('SELECT * FROM categories').fetchall()
    db.close()
    return jsonify([dict(c) for c in categories])

# ===== GET: یک دسته با شناسه =====
@app.route('/api/categories/<int:category_id>', methods=['GET'])
def get_category(category_id):
    db = get_db()
    category = db.execute('SELECT * FROM categories WHERE id = ?', (category_id,)).fetchone()
    db.close()
    if category:
        return jsonify(dict(category))
    return jsonify({"error": "دسته‌بندی پیدا نشد"}), 404

# ===== POST: اضافه کردن دسته‌بندی (فقط ادمین) =====
@app.route('/api/categories', methods=['POST'])
@token_required
def add_category():
    if not request.is_admin:
        return jsonify({"error": "فقط ادمین می‌تونه دسته‌بندی اضافه کنه"}), 403

    data = request.get_json()
    name = data.get('name')

    if not name:
        return jsonify({"error": "نام دسته‌بندی الزامی است"}), 400

    db = get_db()
    cur = db.cursor()
    cur.execute('INSERT INTO categories (name, description) VALUES (?, ?)',
                (name, data.get('description')))
    db.commit()
    category_id = cur.lastrowid
    db.close()
    return jsonify({"id": category_id, "message": "دسته‌بندی اضافه شد"}), 201

# ===== PUT: ویرایش دسته‌بندی (فقط ادمین) =====
@app.route('/api/categories/<int:category_id>', methods=['PUT'])
@token_required
def update_category(category_id):
    if not request.is_admin:
        return jsonify({"error": "فقط ادمین می‌تونه دسته‌بندی رو ویرایش کنه"}), 403

    data = request.get_json()
    db = get_db()
    cur = db.cursor()

    existing = cur.execute('SELECT * FROM categories WHERE id = ?', (category_id,)).fetchone()
    if not existing:
        db.close()
        return jsonify({"error": "دسته‌بندی پیدا نشد"}), 404

    if data.get('name'):
        cur.execute('UPDATE categories SET name = ? WHERE id = ?', (data['name'], category_id))
    if data.get('description'):
        cur.execute('UPDATE categories SET description = ? WHERE id = ?', (data['description'], category_id))

    db.commit()
    db.close()
    return jsonify({"message": f"دسته‌بندی {category_id} به‌روز شد"}), 200

# ===== DELETE: حذف دسته‌بندی (فقط ادمین) =====
@app.route('/api/categories/<int:category_id>', methods=['DELETE'])
@token_required
def delete_category(category_id):
    if not request.is_admin:
        return jsonify({"error": "فقط ادمین می‌تونه دسته‌بندی حذف کنه"}), 403

    db = get_db()
    cur = db.cursor()
    existing = cur.execute('SELECT * FROM categories WHERE id = ?', (category_id,)).fetchone()
    if not existing:
        db.close()
        return jsonify({"error": "دسته‌بندی پیدا نشد"}), 404

    cur.execute('DELETE FROM categories WHERE id = ?', (category_id,))
    db.commit()
    db.close()
    return jsonify({"message": f"دسته‌بندی {category_id} حذف شد"}), 200
# ===== اجرا =====

# ===== GET: مشاهده سبد خرید =====
@app.route('/api/cart', methods=['GET'])
@token_required
def get_cart():
    db = get_db()
    items = db.execute('''
        SELECT cart.id, cart.product_id, cart.quantity,
               products.name, products.price,
               (products.price * cart.quantity) AS total
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id = ?
    ''', (request.user_id,)).fetchall()
    db.close()

    if not items:
        return jsonify({"message": "سبد خرید خالی است", "items": [], "total": 0})

    total_price = sum(item['total'] for item in items)
    return jsonify({
        "items": [dict(i) for i in items],
        "total": total_price
    })

# ===== POST: اضافه کردن محصول به سبد =====
@app.route('/api/cart', methods=['POST'])
@token_required
def add_to_cart():
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)

    if not product_id:
        return jsonify({"error": "product_id الزامی است"}), 400

    if quantity <= 0:
        return jsonify({"error": "تعداد باید بیشتر از صفر باشد"}), 400

    db = get_db()

    product = db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    if not product:
        db.close()
        return jsonify({"error": "محصول پیدا نشد"}), 404

    if product['stock'] < quantity:
        db.close()
        return jsonify({"error": "موجودی کافی نیست"}), 400

    existing = db.execute(
        'SELECT * FROM cart WHERE user_id = ? AND product_id = ?',
        (request.user_id, product_id)
    ).fetchone()

    cur = db.cursor()
    if existing:
        new_quantity = existing['quantity'] + quantity
        cur.execute('UPDATE cart SET quantity = ? WHERE id = ?', (new_quantity, existing['id']))
        db.commit()
        cart_id = existing['id']
        db.close()
        return jsonify({"id": cart_id, "message": "تعداد به‌روز شد"}), 200
    else:
        cur.execute('INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)',
                    (request.user_id, product_id, quantity))
        db.commit()
        cart_id = cur.lastrowid
        db.close()
        return jsonify({"id": cart_id, "message": "به سبد اضافه شد"}), 201

# ===== PUT: تغییر تعداد یک آیتم =====
@app.route('/api/cart/<int:cart_id>', methods=['PUT'])
@token_required
def update_cart_item(cart_id):
    data = request.get_json()
    quantity = data.get('quantity')

    if quantity is None or quantity <= 0:
        return jsonify({"error": "تعداد باید بیشتر از صفر باشد"}), 400

    db = get_db()
    cur = db.cursor()

    item = cur.execute(
        'SELECT * FROM cart WHERE id = ? AND user_id = ?',
        (cart_id, request.user_id)
    ).fetchone()

    if not item:
        db.close()
        return jsonify({"error": "آیتم پیدا نشد"}), 404

    product = db.execute('SELECT * FROM products WHERE id = ?', (item['product_id'],)).fetchone()
    if product['stock'] < quantity:
        db.close()
        return jsonify({"error": "موجودی کافی نیست"}), 400

    cur.execute('UPDATE cart SET quantity = ? WHERE id = ?', (quantity, cart_id))
    db.commit()
    db.close()
    return jsonify({"message": "تعداد به‌روز شد"}), 200

# ===== DELETE: حذف یک آیتم از سبد =====
@app.route('/api/cart/<int:cart_id>', methods=['DELETE'])
@token_required
def delete_cart_item(cart_id):
    db = get_db()
    cur = db.cursor()

    item = cur.execute(
        'SELECT * FROM cart WHERE id = ? AND user_id = ?',
        (cart_id, request.user_id)
    ).fetchone()

    if not item:
        db.close()
        return jsonify({"error": "آیتم پیدا نشد"}), 404

    cur.execute('DELETE FROM cart WHERE id = ?', (cart_id,))
    db.commit()
    db.close()
    return jsonify({"message": "آیتم حذف شد"}), 200

# ===== DELETE: خالی کردن کل سبد =====
@app.route('/api/cart/clear', methods=['DELETE'])
@token_required
def clear_cart():
    db = get_db()
    cur = db.cursor()
    cur.execute('DELETE FROM cart WHERE user_id = ?', (request.user_id,))
    db.commit()
    db.close()
    return jsonify({"message": "سبد خرید خالی شد"}), 200
    
# ===== POST: ثبت سفارش از سبد خرید =====
@app.route('/api/orders', methods=['POST'])
@token_required
def create_order():
    db = get_db()
    cur = db.cursor()

    # ۱. خوندن سبد کاربر
    cart_items = cur.execute('''
        SELECT cart.product_id, cart.quantity, products.price, products.stock, products.name
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id = ?
    ''', (request.user_id,)).fetchall()

    if not cart_items:
        db.close()
        return jsonify({"error": "سبد خرید خالی است"}), 400

    # ۲. چک موجودی همه‌ی محصولات
    for item in cart_items:
        if item['stock'] < item['quantity']:
            db.close()
            return jsonify({"error": f"موجودی {item['name']} کافی نیست"}), 400

    # ۳. محاسبه‌ی قیمت کل
    total_price = sum(item['price'] * item['quantity'] for item in cart_items)

    # ۴. ساخت رکورد سفارش
    cur.execute('INSERT INTO orders (user_id, total_price) VALUES (?, ?)',
                (request.user_id, total_price))
    order_id = cur.lastrowid

    # ۵. ذخیره‌ی آیتم‌ها + کم کردن موجودی
    for item in cart_items:
        cur.execute('''
            INSERT INTO order_items (order_id, product_id, quantity, price)
            VALUES (?, ?, ?, ?)
        ''', (order_id, item['product_id'], item['quantity'], item['price']))

        cur.execute('UPDATE products SET stock = stock - ? WHERE id = ?',
                    (item['quantity'], item['product_id']))

    # ۶. خالی کردن سبد
    cur.execute('DELETE FROM cart WHERE user_id = ?', (request.user_id,))

    db.commit()
    db.close()
    return jsonify({
        "id": order_id,
        "total_price": total_price,
        "message": "سفارش با موفقیت ثبت شد"
    }), 201

# ===== GET: لیست سفارشات کاربر =====
@app.route('/api/orders', methods=['GET'])
@token_required
def get_orders():
    db = get_db()
    orders = db.execute('''
        SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC
    ''', (request.user_id,)).fetchall()
    db.close()
    return jsonify([dict(o) for o in orders])

# ===== GET: یک سفارش با آیتم‌هاش =====
@app.route('/api/orders/<int:order_id>', methods=['GET'])
@token_required
def get_order(order_id):
    db = get_db()

    order = db.execute(
        'SELECT * FROM orders WHERE id = ? AND user_id = ?',
        (order_id, request.user_id)
    ).fetchone()

    if not order:
        db.close()
        return jsonify({"error": "سفارش پیدا نشد"}), 404

    items = db.execute('''
        SELECT order_items.quantity, order_items.price, products.name,
               (order_items.price * order_items.quantity) AS total
        FROM order_items
        JOIN products ON order_items.product_id = products.id
        WHERE order_items.order_id = ?
    ''', (order_id,)).fetchall()

    db.close()
    return jsonify({
        "order": dict(order),
        "items": [dict(i) for i in items]
    })

# ===== PUT: لغو سفارش =====
@app.route('/api/orders/<int:order_id>/cancel', methods=['PUT'])
@token_required
def cancel_order(order_id):
    db = get_db()
    cur = db.cursor()

    order = cur.execute(
        'SELECT * FROM orders WHERE id = ? AND user_id = ?',
        (order_id, request.user_id)
    ).fetchone()

    if not order:
        db.close()
        return jsonify({"error": "سفارش پیدا نشد"}), 404

    if order['status'] == 'cancelled':
        db.close()
        return jsonify({"error": "این سفارش قبلاً لغو شده"}), 400

    if order['status'] == 'paid':
        db.close()
        return jsonify({"error": "سفارش پرداخت‌شده قابل لغو نیست"}), 400

    # برگرداندن موجودی محصولات
    items = cur.execute('SELECT * FROM order_items WHERE order_id = ?', (order_id,)).fetchall()
    for item in items:
        cur.execute('UPDATE products SET stock = stock + ? WHERE id = ?',
                    (item['quantity'], item['product_id']))

    cur.execute("UPDATE orders SET status = 'cancelled' WHERE id = ?", (order_id,))
    db.commit()
    db.close()
    return jsonify({"message": f"سفارش {order_id} لغو شد"}), 200

@app.route('/test', methods=['GET'])
def test():
    return jsonify({"message": "Server is working!", "status": "ok"})
if __name__ == '__main__':
    create_db()
    app.run(host='0.0.0.0', port=5000, debug=True)