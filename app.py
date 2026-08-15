from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, Admin, Product, User, Order, OrderItem, Category, Review
from datetime import datetime
import os

app = Flask(__name__)

def get_database_url():
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        if database_url.startswith('postgres://'):
            return database_url.replace('postgres://', 'postgresql://', 1)
        return database_url
    return 'sqlite:///findme.db'


app.config['SQLALCHEMY_DATABASE_URI'] = get_database_url()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')

def format_currency(value):
    return f"GH₵ {float(value):,.2f}"


app.jinja_env.globals['currency'] = format_currency
app.jinja_env.filters['currency'] = format_currency
db.init_app(app)


# Create tables and seed initial data
def init_db():
    with app.app_context():
        db.create_all()
        
        # Check if data already exists
        if Product.query.first() is None:
            # Create default category
            essentials = Category(name='Essentials', description='Essential everyday items')
            accessories = Category(name='Accessories', description='Premium accessories')
            bottoms = Category(name='Bottoms', description='Tailored bottoms')
            outerwear = Category(name='Outerwear', description='Lightweight outerwear')
            footwear = Category(name='Footwear', description='Premium footwear')
            db.session.add_all([essentials, accessories, bottoms, outerwear, footwear])
            db.session.commit()
            
            # Seed products
            products_data = [
                {
                    'name': 'The Signature Hoodie',
                    'category_id': essentials.id,
                    'price': 129,
                    'old_price': 169,
                    'rating': 4.9,
                    'reviews_count': 186,
                    'image': 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=900&q=80',
                    'gallery': [
                        'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=900&q=80',
                        'https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?auto=format&fit=crop&w=900&q=80',
                        'https://images.unsplash.com/photo-1483985988355-763728e1935b?auto=format&fit=crop&w=900&q=80',
                    ],
                    'colors': ['Sand', 'Black', 'Stone'],
                    'sizes': ['S', 'M', 'L', 'XL'],
                    'stock': 50,
                    'featured': True,
                    'description': 'A heavyweight hoodie designed for everyday polishing. Soft-touch cotton fleece with a premium drape and refined finishing.',
                },
                {
                    'name': 'Luna Leather Tote',
                    'category_id': accessories.id,
                    'price': 214,
                    'old_price': 279,
                    'rating': 4.8,
                    'reviews_count': 94,
                    'image': 'https://images.unsplash.com/photo-1594223274512-ad4803739b7c?auto=format&fit=crop&w=900&q=80',
                    'gallery': [
                        'https://images.unsplash.com/photo-1594223274512-ad4803739b7c?auto=format&fit=crop&w=900&q=80',
                        'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=80',
                        'https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?auto=format&fit=crop&w=900&q=80',
                    ],
                    'colors': ['Espresso', 'Cognac'],
                    'sizes': ['One Size'],
                    'stock': 35,
                    'featured': True,
                    'description': 'Structured yet soft, this signature tote carries daily essentials with elevated polish and timeless elegance.',
                },
                {
                    'name': 'Noir Cargo Trouser',
                    'category_id': bottoms.id,
                    'price': 188,
                    'old_price': 240,
                    'rating': 4.7,
                    'reviews_count': 132,
                    'image': 'https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=900&q=80',
                    'gallery': [
                        'https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=900&q=80',
                        'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=900&q=80',
                        'https://images.unsplash.com/photo-1496747611176-843222e1e57c?auto=format&fit=crop&w=900&q=80',
                    ],
                    'colors': ['Black', 'Slate'],
                    'sizes': ['28', '30', '32', '34'],
                    'stock': 42,
                    'featured': True,
                    'description': 'Utility-inspired tailoring with a clean silhouette, providing structure without sacrificing movement.',
                },
                {
                    'name': 'Aster Linen Shirt',
                    'category_id': outerwear.id,
                    'price': 158,
                    'old_price': 205,
                    'rating': 4.9,
                    'reviews_count': 241,
                    'image': 'https://images.unsplash.com/photo-1483985988355-763728e1935b?auto=format&fit=crop&w=900&q=80',
                    'gallery': [
                        'https://images.unsplash.com/photo-1483985988355-763728e1935b?auto=format&fit=crop&w=900&q=80',
                        'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?auto=format&fit=crop&w=900&q=80',
                        'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=900&q=80',
                    ],
                    'colors': ['Ivory', 'Sky', 'Black'],
                    'sizes': ['S', 'M', 'L'],
                    'stock': 28,
                    'featured': False,
                    'description': 'Breathable linen with crisp lines and a refined finish that works from daytime layering to evening styling.',
                },
                {
                    'name': 'Veloura Knit Set',
                    'category_id': essentials.id,
                    'price': 248,
                    'old_price': 310,
                    'rating': 5.0,
                    'reviews_count': 58,
                    'image': 'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?auto=format&fit=crop&w=900&q=80',
                    'gallery': [
                        'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?auto=format&fit=crop&w=900&q=80',
                        'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=900&q=80',
                        'https://images.unsplash.com/photo-1496747611176-843222e1e57c?auto=format&fit=crop&w=900&q=80',
                    ],
                    'colors': ['Cream', 'Taupe'],
                    'sizes': ['XS', 'S', 'M', 'L'],
                    'stock': 31,
                    'featured': True,
                    'description': 'A soft knit pairing that offers all-day comfort with elevated tailoring and a polished finish.',
                },
                {
                    'name': 'Crest Running Sneaker',
                    'category_id': footwear.id,
                    'price': 172,
                    'old_price': 220,
                    'rating': 4.8,
                    'reviews_count': 120,
                    'image': 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=80',
                    'gallery': [
                        'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=80',
                        'https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?auto=format&fit=crop&w=900&q=80',
                        'https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?auto=format&fit=crop&w=900&q=80',
                    ],
                    'colors': ['White', 'Onyx'],
                    'sizes': ['6', '7', '8', '9', '10'],
                    'stock': 45,
                    'featured': False,
                    'description': 'A refined street sneaker blending comfort technology with premium details and clean modern lines.',
                },
            ]
            
            for prod_data in products_data:
                product = Product(**prod_data)
                db.session.add(product)
            
            db.session.commit()
            
            # Create default admin
            if Admin.query.first() is None:
                admin = Admin(name='Admin', email='admin@findme.shop')
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()


@app.context_processor
def inject_cart_data():
    cart = session.get('cart', {})
    item_count = sum(cart.values())
    subtotal = 0
    for product_id, quantity in cart.items():
        product = Product.query.get(int(product_id))
        if product:
            subtotal += product.price * quantity
    return {'cart_count': item_count, 'cart_subtotal': subtotal}


# ========================== Storefront Routes ==========================

@app.route('/')
def index():
    featured_products = Product.query.filter_by(featured=True).all()
    return render_template('index.html', products=featured_products)


@app.route('/shop')
def shop():
    category_id = request.args.get('category', type=int)
    products = Product.query.all()
    
    if category_id:
        products = Product.query.filter_by(category_id=category_id).all()
    
    categories = Category.query.all()
    return render_template('shop.html', products=products, categories=categories, selected_category=category_id)


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    related = Product.query.filter(Product.id != product_id).limit(3).all()
    return render_template('product.html', product=product, related=related)


@app.route('/add-to-cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    cart = session.get('cart', {})
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    session['cart'] = cart
    return redirect(request.referrer or url_for('shop'))


@app.route('/cart', methods=['GET', 'POST'])
def cart():
    if request.method == 'POST':
        action = request.form.get('action')
        product_id = request.form.get('product_id')
        cart = session.get('cart', {})

        if action == 'update':
            quantity = int(request.form.get('quantity', 1))
            if quantity <= 0:
                cart.pop(str(product_id), None)
            else:
                cart[str(product_id)] = quantity
        elif action == 'remove':
            cart.pop(str(product_id), None)

        session['cart'] = cart
        return redirect(url_for('cart'))

    cart_items = []
    total = 0
    for product_id, quantity in session.get('cart', {}).items():
        product = Product.query.get(int(product_id))
        if not product:
            continue
        item_total = product.price * quantity
        total += item_total
        cart_items.append({
            'product': product,
            'quantity': quantity,
            'item_total': item_total,
        })

    shipping = 0 if total >= 250 else 18
    grand_total = total + shipping
    return render_template('cart.html', cart_items=cart_items, shipping=shipping, total=total, grand_total=grand_total)


@app.route('/checkout')
def checkout():
    cart = session.get('cart', {})
    if not cart:
        return redirect(url_for('shop'))

    cart_items = []
    total = 0
    for product_id, quantity in cart.items():
        product = Product.query.get(int(product_id))
        if product:
            item_total = product.price * quantity
            total += item_total
            cart_items.append({'product': product, 'quantity': quantity, 'item_total': item_total})

    shipping = 0 if total >= 250 else 18
    grand_total = total + shipping
    return render_template('checkout.html', cart_items=cart_items, total=total, shipping=shipping, grand_total=grand_total)


@app.route('/account')
def account():
    orders = Order.query.limit(3).all()
    return render_template('account.html', orders=orders)


@app.route('/order-success')
def order_success():
    products = Product.query.limit(3).all()
    return render_template('order-success.html', products=products)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/login')
def login():
    return render_template('login.html', mode='login')


@app.route('/register')
def register():
    return render_template('login.html', mode='register')


# ========================== Admin Routes ==========================

@app.route('/admin')
def admin():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    total_products = Product.query.count()
    total_orders = Order.query.count()
    total_revenue = db.session.query(db.func.sum(Order.total)).scalar() or 0
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html', 
                          total_products=total_products,
                          total_orders=total_orders,
                          total_revenue=total_revenue,
                          recent_orders=recent_orders)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        admin = Admin.query.filter_by(email=email).first()
        if admin and admin.check_password(password):
            session['admin_id'] = admin.id
            return redirect(url_for('admin'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    flash('You have been logged out', 'success')
    return redirect(url_for('admin_login'))


@app.route('/admin/products')
def admin_products():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    products = Product.query.all()
    return render_template('admin/products.html', products=products)


@app.route('/admin/products/add', methods=['GET', 'POST'])
def admin_add_product():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    categories = Category.query.all()
    
    if request.method == 'POST':
        try:
            product = Product(
                name=request.form.get('name'),
                description=request.form.get('description'),
                price=float(request.form.get('price')),
                old_price=float(request.form.get('old_price')) if request.form.get('old_price') else None,
                image=request.form.get('image'),
                gallery=[request.form.get('image')],
                category_id=int(request.form.get('category_id')),
                colors=request.form.get('colors', '').split(','),
                sizes=request.form.get('sizes', '').split(','),
                stock=int(request.form.get('stock')),
                featured=request.form.get('featured') == 'on',
                rating=float(request.form.get('rating', 5.0))
            )
            db.session.add(product)
            db.session.commit()
            flash('Product added successfully', 'success')
            return redirect(url_for('admin_products'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding product: {str(e)}', 'error')
    
    return render_template('admin/add_product.html', categories=categories)


@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
def admin_edit_product(product_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    product = Product.query.get_or_404(product_id)
    categories = Category.query.all()
    
    if request.method == 'POST':
        try:
            product.name = request.form.get('name')
            product.description = request.form.get('description')
            product.price = float(request.form.get('price'))
            product.old_price = float(request.form.get('old_price')) if request.form.get('old_price') else None
            product.image = request.form.get('image')
            product.category_id = int(request.form.get('category_id'))
            product.colors = request.form.get('colors', '').split(',')
            product.sizes = request.form.get('sizes', '').split(',')
            product.stock = int(request.form.get('stock'))
            product.featured = request.form.get('featured') == 'on'
            product.rating = float(request.form.get('rating', 5.0))
            
            db.session.commit()
            flash('Product updated successfully', 'success')
            return redirect(url_for('admin_products'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating product: {str(e)}', 'error')
    
    return render_template('admin/edit_product.html', product=product, categories=categories)


@app.route('/admin/products/delete/<int:product_id>', methods=['POST'])
def admin_delete_product(product_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    product = Product.query.get_or_404(product_id)
    try:
        db.session.delete(product)
        db.session.commit()
        flash('Product deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting product: {str(e)}', 'error')
    
    return redirect(url_for('admin_products'))


@app.route('/admin/orders')
def admin_orders():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)


@app.route('/admin/orders/<int:order_id>')
def admin_order_detail(order_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    order = Order.query.get_or_404(order_id)
    return render_template('admin/order_detail.html', order=order)


@app.route('/admin/orders/<int:order_id>/status', methods=['POST'])
def admin_update_order_status(order_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    order = Order.query.get_or_404(order_id)
    status = request.form.get('status')
    
    if status in ['Pending', 'Processing', 'Shipped', 'Delivered']:
        order.status = status
        db.session.commit()
        flash('Order status updated', 'success')
    
    return redirect(url_for('admin_order_detail', order_id=order_id))


@app.route('/admin/categories')
def admin_categories():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    categories = Category.query.all()
    return render_template('admin/categories.html', categories=categories)


@app.route('/admin/categories/add', methods=['GET', 'POST'])
def admin_add_category():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        try:
            category = Category(
                name=request.form.get('name'),
                description=request.form.get('description')
            )
            db.session.add(category)
            db.session.commit()
            flash('Category added successfully', 'success')
            return redirect(url_for('admin_categories'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding category: {str(e)}', 'error')
    
    return render_template('admin/add_category.html')


if __name__ == '__main__':
    init_db()
    # Production: Railway sets PORT env var; development uses 5000
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
