# E-Commerce API

A complete RESTful API for an online shop built with Flask and SQLite.

## Features

- **User Authentication:** Register, Login, and JWT-based authorization.
- **Role Management:** Admin and normal user roles (only admins can add/edit products and categories).
- **Product Management:** Full CRUD for products with categories, stock tracking, and search.
- **Shopping Cart:** Add, update, and remove items from the cart.
- **Order Processing:** Checkout system that verifies stock, calculates total price, and creates orders.
- **Order Cancellation:** Users can cancel pending orders (stock is automatically restored).

## Tech Stack

- **Python 3**
- **Flask** (Web framework)
- **SQLite** (Database)
- **PyJWT** (Authentication)
- **Hashlib** (Password hashing)

## API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/register` | Register a new user |
| POST | `/api/login` | Login and get JWT token |
| GET | `/api/profile` | Get current user profile (Protected) |

### Products & Categories
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/products` | Get all products |
| GET | `/api/products/<id>` | Get a single product |
| GET | `/api/products/search?q=` | Search products by name |
| POST | `/api/products` | Add a new product (Admin only) |
| PUT | `/api/products/<id>` | Update a product (Admin only) |
| DELETE | `/api/products/<id>` | Delete a product (Admin only) |
| GET | `/api/categories` | Get all categories |
| POST | `/api/categories` | Add a new category (Admin only) |

### Cart & Orders
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/cart` | View current user's cart |
| POST | `/api/cart` | Add product to cart |
| PUT | `/api/cart/<id>` | Update cart item quantity |
| DELETE | `/api/cart/<id>` | Remove item from cart |
| DELETE | `/api/cart/clear` | Clear the entire cart |
| POST | `/api/orders` | Create an order from cart |
| GET | `/api/orders` | Get user's orders |
| GET | `/api/orders/<id>` | Get details of a specific order |
| PUT | `/api/orders/<id>/cancel` | Cancel a pending order |

## How to Run

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   