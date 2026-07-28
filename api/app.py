from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "super_secret_key"
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Products Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_no TEXT,
            description TEXT,
            price REAL,
            image TEXT,
            sizes TEXT DEFAULT 'S, M, L',
            status TEXT DEFAULT 'Available'
        )
    ''')
    
    # Orders Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            phone TEXT,
            address TEXT,
            article_no TEXT,
            size TEXT,
            qty INTEGER,
            total_price REAL,
            status TEXT DEFAULT 'Pending',
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Announcements Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM announcements")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO announcements (message) VALUES (?)", 
                       ("✨ Flat 20% OFF on New Lawn Collection! | Free Delivery on Orders Above PKR 5000 🚚 ✨",))
    
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    
    cursor.execute("SELECT message FROM announcements ORDER BY id DESC LIMIT 1")
    announcement_row = cursor.fetchone()
    announcement = announcement_row[0] if announcement_row else "Welcome to Elegance Store!"
    
    conn.close()
    return render_template('index.html', products=products, announcement=announcement)

@app.route('/buy/<int:product_id>', methods=['POST'])
def buy(product_id):
    name = request.form['name']
    phone = request.form['phone']
    address = request.form['address']
    size = request.form['size']
    qty = int(request.form['qty'])
    
    delivery_charges = 200
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT article_no, price FROM products WHERE id = ?", (product_id,))
    prod = cursor.fetchone()
    
    if prod:
        total_price = (prod[1] * qty) + delivery_charges
        cursor.execute('''
            INSERT INTO orders (customer_name, phone, address, article_no, size, qty, total_price, status) 
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending')
        ''', (name, phone, address, prod[0], size, qty, total_price))
        conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        # Direct quotes (' ') me username aur password dein
        if request.form['username'] == 'dastaneposaak' and request.form['password'] == 'dastaneposaak123':
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error="Invalid Credentials")
            
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

# API Endpoint - Fast Background Data Fetching (Every 10 seconds)
@app.route('/admin/api/stats')
def admin_api_stats():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM orders ORDER BY id DESC")
    orders = cursor.fetchall()
    
    cursor.execute("SELECT SUM(total_price) FROM orders WHERE status = 'Delivered'")
    total_sales_row = cursor.fetchone()
    total_sales = total_sales_row[0] if total_sales_row and total_sales_row[0] else 0.0

    total_orders_count = len(orders)
    delivered_orders_count = sum(1 for o in orders if o[8] == 'Delivered')
    pending_orders_count = sum(1 for o in orders if o[8] == 'Pending')
    cancelled_orders_count = sum(1 for o in orders if o[8] == 'Cancelled')
    
    # Orders JSON structure for table update
    orders_list = []
    for o in orders:
        orders_list.append({
            'id': o[0],
            'name': o[1],
            'phone': o[2],
            'address': o[3],
            'article_no': o[4],
            'size': o[5],
            'qty': o[6],
            'total_price': o[7],
            'status': o[8]
        })
        
    conn.close()
    
    return jsonify({
        'total_sales': total_sales,
        'total_orders_count': total_orders_count,
        'delivered_orders_count': delivered_orders_count,
        'pending_orders_count': pending_orders_count,
        'cancelled_orders_count': cancelled_orders_count,
        'orders': orders_list
    })

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    
    cursor.execute("SELECT * FROM orders ORDER BY id DESC")
    orders = cursor.fetchall()
    
    cursor.execute("SELECT message FROM announcements ORDER BY id DESC LIMIT 1")
    ann_row = cursor.fetchone()
    announcement = ann_row[0] if ann_row else ""
    
    cursor.execute("SELECT SUM(total_price) FROM orders WHERE status = 'Delivered'")
    total_sales_row = cursor.fetchone()
    total_sales = total_sales_row[0] if total_sales_row and total_sales_row[0] else 0.0

    total_orders_count = len(orders)
    delivered_orders_count = sum(1 for o in orders if o[8] == 'Delivered')
    pending_orders_count = sum(1 for o in orders if o[8] == 'Pending')
    cancelled_orders_count = sum(1 for o in orders if o[8] == 'Cancelled')
    
    conn.close()
    
    return render_template(
        'admin_dashboard.html', 
        products=products, 
        orders=orders, 
        announcement=announcement,
        total_sales=total_sales,
        total_orders_count=total_orders_count,
        delivered_orders_count=delivered_orders_count,
        pending_orders_count=pending_orders_count,
        cancelled_orders_count=cancelled_orders_count
    )

@app.route('/admin/add_product', methods=['POST'])
def add_product():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
        
    article_no = request.form['article_no']
    description = request.form['description']
    price = request.form['price']
    sizes = request.form.get('sizes', 'Small, Medium, Large')
    file = request.files['image']
    
    if file:
        filename = file.filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO products (article_no, description, price, image, sizes) VALUES (?, ?, ?, ?, ?)",
                       (article_no, description, price, filename, sizes))
        conn.commit()
        conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update_announcement', methods=['POST'])
def update_announcement():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
        
    msg = request.form['announcement']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO announcements (message) VALUES (?)", (msg,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update_order_status/<int:order_id>/<string:new_status>')
def update_order_status(order_id, new_status):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
        
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/toggle_stock/<int:product_id>')
def toggle_stock(product_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
        
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM products WHERE id = ?", (product_id,))
    status = cursor.fetchone()[0]
    new_status = 'Out of Stock' if status == 'Available' else 'Available'
    cursor.execute("UPDATE products SET status = ? WHERE id = ?", (new_status, product_id))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_product/<int:product_id>')
def delete_product(product_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
        
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)