import requests
import sqlite3
import time

BASE_URL = "http://127.0.0.1:5000"

def print_response(title, r):
    print(f"\n[{title}]")
    print("Status Code:", r.status_code)
    if r.status_code != 200 and r.status_code != 201:
        print("❌ خطا! سرور پاسخ غیرمنتظره داد:")
        print("Response Text:", r.text)
        return False
    try:
        print("Response JSON:", r.json())
        return True
    except Exception as e:
        print("❌ خطا در خواندن JSON! متن خام پاسخ:", r.text)
        return False

# ساخت یک ایمیل یکتا با استفاده از زمان فعلی
# اینطوری هر بار که اجرا می‌کنی، ایمیل جدیدیه و خطای تکراری نمیده
unique_email = f"moein_{int(time.time())}@test.com"

print("=" * 50)
print(f"STARTING FULL TEST (with email: {unique_email})")
print("=" * 50)

# 1. Register
r = requests.post(f"{BASE_URL}/api/register", json={
    "name": "Moein",
    "email": unique_email,
    "password": "123456"
})
if not print_response("1. Register user", r): exit()

# 2. Make admin (از همون ایمیل یکتا استفاده می‌کنیم)
print("\n[2] Make user admin")
conn = sqlite3.connect('shop.db')
conn.execute(f"UPDATE users SET is_admin = 1 WHERE email = '{unique_email}'")
conn.commit()
conn.close()
print("Done!")

# 3. Login
r = requests.post(f"{BASE_URL}/api/login", json={
    "email": unique_email,
    "password": "123456"
})
if not print_response("3. Login", r): exit()
token = r.json().get('token')
headers = {"Authorization": token}

# 4. Add category
r = requests.post(f"{BASE_URL}/api/categories", json={
    "name": "Mobile",
    "description": "Smartphones"
}, headers=headers)
print_response("4. Add category", r)

# 5. Add product
r = requests.post(f"{BASE_URL}/api/products", json={
    "name": "Samsung S24",
    "description": "Flagship phone",
    "price": 3000,
    "stock": 10,
    "category_id": 1
}, headers=headers)
print_response("5. Add product", r)

# 6. Get products
r = requests.get(f"{BASE_URL}/api/products")
print_response("6. Get all products", r)

# 7. Add to cart
r = requests.post(f"{BASE_URL}/api/cart", json={
    "product_id": 1,
    "quantity": 2
}, headers=headers)
print_response("7. Add to cart", r)

# 8. Get cart
r = requests.get(f"{BASE_URL}/api/cart", headers=headers)
print_response("8. Get cart", r)

# 9. Create order
r = requests.post(f"{BASE_URL}/api/orders", headers=headers)
print_response("9. Create order", r)

# 10. Get my orders
r = requests.get(f"{BASE_URL}/api/orders", headers=headers)
print_response("10. Get my orders", r)

print("\n" + "=" * 50)
print("TEST FINISHED")
print("=" * 50)