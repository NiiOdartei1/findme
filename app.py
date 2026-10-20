from flask import Flask, abort, g, jsonify, render_template, request, redirect, url_for, session, flash
from models import db, Admin, Product, User, Order, OrderItem, Category, Review
from datetime import datetime, timezone
from decimal import Decimal
from functools import wraps
import hashlib
import hmac
import os
import secrets
from urllib.parse import urlsplit

import click
import requests
from flask_migrate import Migrate

IS_VERCEL = os.environ.get('VERCEL') == '1'
IS_HOSTED = IS_VERCEL
SECRET_KEY = os.environ.get('SECRET_KEY')

def get_database_url():
    database_url = os.environ.get('DATABASE_URL')

    # Local development can use SQLite; hosted deployments require a persistent database URL.
    if not database_url:
        if IS_HOSTED:
            raise RuntimeError('DATABASE_URL is required in hosted environments. Configure a PostgreSQL connection string before deploying.')
        return 'sqlite:///findme.db'

    if IS_VERCEL and database_url.startswith('sqlite:'):
        raise RuntimeError('Vercel requires a persistent PostgreSQL DATABASE_URL; SQLite storage is not persistent.')

    if database_url.startswith('postgres://'):
        return database_url.replace('postgres://', 'postgresql://', 1)
    return database_url


if IS_HOSTED and not SECRET_KEY:
    raise RuntimeError('SECRET_KEY is required in hosted environments. Set it in the project environment variables.')

app = Flask(
    __name__,
    static_folder=None if IS_VERCEL else os.path.join(os.path.dirname(__file__), 'public', 'static'),
    static_url_path=None if IS_VERCEL else '/static',
)
app.config['SQLALCHEMY_DATABASE_URI'] = get_database_url()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_SECURE'] = IS_HOSTED
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.secret_key = SECRET_KEY or 'dev-secret-key-change-me'

def format_currency(value):
    return f"GH₵ {float(value):,.2f}"


app.jinja_env.globals['currency'] = format_currency
app.jinja_env.filters['currency'] = format_currency
db.init_app(app)
migrate = Migrate(app, db)


@app.before_request
def load_current_user_and_validate_csrf():
    user_id = session.get('user_id')
    g.current_user = db.session.get(User, user_id) if user_id else None
    if user_id and g.current_user is None:
        session.pop('user_id', None)

    if request.method == 'POST' and request.endpoint != 'paystack_webhook':
        expected_token = session.get('_csrf_token')
        submitted_token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
        if not expected_token or not submitted_token or not hmac.compare_digest(expected_token, submitted_token):
            abort(400, description='Invalid or missing CSRF token.')


@app.context_processor
def inject_security_context():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_urlsafe(32)
    return {'csrf_token': session['_csrf_token'], 'current_user': g.get('current_user')}


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.current_user is None:
            flash('Please sign in to continue.', 'info')
            return redirect(url_for('login', next=request.full_path.rstrip('?')))
        return view(*args, **kwargs)
    return wrapped_view


def safe_redirect_target(target):
    if not target:
        return None
    if not target.startswith('/') or target.startswith('//') or '\\' in target:
        return None
    redirect_url = urlsplit(target)
    if redirect_url.scheme or redirect_url.netloc:
        return None
    return redirect_url.path + (f'?{redirect_url.query}' if redirect_url.query else '')


def paystack_request(method, endpoint, **kwargs):
    secret_key = os.environ.get('PAYSTACK_SECRET_KEY')
    if not secret_key:
        raise RuntimeError('PAYSTACK_SECRET_KEY is not configured.')

    try:
        response = requests.request(
            method,
            f'https://api.paystack.co/{endpoint}',
            headers={'Authorization': f'Bearer {secret_key}', 'Content-Type': 'application/json'},
            timeout=(5, 20),
            **kwargs,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as error:
        app.logger.exception('Paystack request failed.')
        raise RuntimeError('Payment provider is temporarily unavailable. Please try again.') from error

    if not payload.get('status'):
        raise RuntimeError('Payment provider could not process the request.')
    return payload.get('data') or {}


def verify_paystack_payment(order):
    data = paystack_request('GET', f'transaction/verify/{order.payment_reference}')
    expected_amount = int((Decimal(str(order.total)) * 100).quantize(Decimal('1')))
    if (
        data.get('status') != 'success'
        or data.get('reference') != order.payment_reference
        or data.get('amount') != expected_amount
        or data.get('currency') != 'GHS'
        or (data.get('customer') or {}).get('email', '').casefold() != order.email.casefold()
    ):
        return False
    return True


def mark_order_paid(order):
    locked_order = db.session.execute(
        db.select(Order).where(Order.id == order.id).with_for_update()
    ).scalar_one()
    if locked_order.payment_status == 'paid':
        return locked_order

    products = {
        product.id: product
        for product in db.session.execute(
            db.select(Product)
            .join(OrderItem, OrderItem.product_id == Product.id)
            .where(OrderItem.order_id == locked_order.id)
            .with_for_update()
        ).scalars().unique()
    }
    has_stock = all(
        item.product_id in products and products[item.product_id].stock >= item.quantity
        for item in locked_order.items
    )

    locked_order.payment_status = 'paid'
    if has_stock:
        for item in locked_order.items:
            products[item.product_id].stock -= item.quantity
    else:
        locked_order.status = 'On hold'

    db.session.commit()
    return locked_order


def init_db():
    with app.app_context():
        db.create_all()

        if Product.query.first() is None:
            def get_or_create_category(name, description):
                category = Category.query.filter_by(name=name).first()
                if category is None:
                    category = Category(name=name, description=description)
                    db.session.add(category)
                return category

            essentials = get_or_create_category('Essentials', 'Essential everyday items')
            accessories = get_or_create_category('Accessories', 'Premium accessories')
            bottoms = get_or_create_category('Bottoms', 'Tailored bottoms')
            outerwear = get_or_create_category('Outerwear', 'Lightweight outerwear')
            footwear = get_or_create_category('Footwear', 'Premium footwear')
            db.session.commit()

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
            db.session.add_all(Product(**product_data) for product_data in products_data)
            db.session.commit()

        if Admin.query.first() is None:
            admin_email = os.environ.get('ADMIN_EMAIL')
            admin_password = os.environ.get('ADMIN_PASSWORD')
            if IS_HOSTED and (not admin_email or not admin_password):
                raise RuntimeError('ADMIN_EMAIL and ADMIN_PASSWORD are required to create the initial hosted admin account.')

            admin = Admin(
                name=os.environ.get('ADMIN_NAME', 'Admin'),
                email=admin_email or 'admin@findme.shop',
            )
            admin.set_password(admin_password or 'admin123')
            db.session.add(admin)
            db.session.commit()


@app.cli.command('create-admin')
def create_admin_command():
    """Create the initial administrator from environment variables."""
    if Admin.query.first() is not None:
        raise click.ClickException('An administrator already exists; no account was created.')

    admin_email = os.environ.get('ADMIN_EMAIL', '').strip().casefold()
    admin_password = os.environ.get('ADMIN_PASSWORD', '')
    if not admin_email or not admin_password:
        raise click.ClickException('Set ADMIN_EMAIL and ADMIN_PASSWORD before creating the initial administrator.')

    admin = Admin(
        name=os.environ.get('ADMIN_NAME', 'Store Admin').strip() or 'Store Admin',
        email=admin_email,
    )
    admin.set_password(admin_password)
    db.session.add(admin)
    db.session.commit()


@app.cli.command('seed')
def seed_database_command():
    """Create starter catalog data and the initial administrator."""
    init_db()


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
    product = Product.query.get_or_404(product_id)
    cart = session.get('cart', {})
    quantity = cart.get(str(product_id), 0)
    if quantity >= product.stock:
        flash('There is not enough stock available for that quantity.', 'error')
        return redirect(request.referrer or url_for('shop'))
    cart[str(product_id)] = quantity + 1
    session['cart'] = cart
    return redirect(request.referrer or url_for('shop'))


@app.route('/cart', methods=['GET', 'POST'])
def cart():
    if request.method == 'POST':
        action = request.form.get('action')
        product_id = request.form.get('product_id')
        cart = session.get('cart', {})

        if action == 'update':
            try:
                quantity = int(request.form.get('quantity', 1))
                product_id = int(product_id)
            except (TypeError, ValueError):
                flash('Enter a valid quantity.', 'error')
                return redirect(url_for('cart'))

            product = db.session.get(Product, product_id)
            if quantity <= 0:
                cart.pop(str(product_id), None)
            elif product is None:
                cart.pop(str(product_id), None)
                flash('That product is no longer available.', 'error')
            elif quantity > product.stock:
                flash(f'Only {product.stock} units of {product.name} are available.', 'error')
            else:
                cart[str(product_id)] = quantity
        elif action == 'remove':
            cart.pop(str(product_id), None)
        else:
            flash('Choose a valid cart action.', 'error')

        session['cart'] = cart
        return redirect(url_for('cart'))

    cart_items = []
    total = 0
    for product_id, quantity in session.get('cart', {}).items():
        try:
            product = Product.query.get(int(product_id))
            quantity = int(quantity)
        except (TypeError, ValueError):
            continue
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
@login_required
def checkout():
    cart_items, total = get_checkout_items()
    if not cart_items:
        return redirect(url_for('shop'))

    shipping = 0 if total >= 250 else 18
    grand_total = total + shipping
    return render_template(
        'checkout.html',
        cart_items=cart_items,
        total=total,
        shipping=shipping,
        grand_total=grand_total,
        paystack_enabled=bool(os.environ.get('PAYSTACK_SECRET_KEY')),
    )


@app.route('/account')
@login_required
def account():
    orders = Order.query.filter_by(user_id=g.current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('account.html', orders=orders, user=g.current_user)


@app.route('/order-success')
def order_success():
    return redirect(url_for('account'))


@app.route('/order-success/<int:order_id>')
@login_required
def order_success_detail(order_id):
    order = Order.query.filter_by(id=order_id, user_id=g.current_user.id).first_or_404()
    if order.payment_status != 'paid':
        flash('That order has not been paid yet.', 'error')
        return redirect(url_for('account'))
    products = Product.query.filter(Product.id.notin_([item.product_id for item in order.items])).limit(3).all()
    return render_template('order-success.html', order=order, products=products)


def get_checkout_items():
    cart_items = []
    total = 0
    cart = session.get('cart', {})
    if not isinstance(cart, dict):
        session['cart'] = {}
        return cart_items, total

    for product_id, raw_quantity in cart.items():
        try:
            product_id = int(product_id)
            quantity = int(raw_quantity)
        except (TypeError, ValueError):
            continue
        product = db.session.get(Product, product_id)
        if product is None or quantity <= 0:
            continue
        if quantity > product.stock:
            flash(f'Only {product.stock} units of {product.name} are available.', 'error')
            return [], 0
        item_total = product.price * quantity
        total += item_total
        cart_items.append({'product': product, 'quantity': quantity, 'item_total': item_total})
    return cart_items, total


@app.route('/checkout/pay', methods=['POST'])
@login_required
def checkout_pay():
    cart_items, subtotal = get_checkout_items()
    if not cart_items:
        flash('Your cart is empty or one of its items is no longer available.', 'error')
        return redirect(url_for('cart'))

    shipping = 0 if subtotal >= 250 else 18
    total = subtotal + shipping
    shipping_address = request.form.get('shipping_address', '').strip()
    phone = request.form.get('phone', '').strip()
    if not shipping_address:
        flash('Enter a shipping address to continue.', 'error')
        return redirect(url_for('checkout'))
    if len(shipping_address) > 1000 or len(phone) > 20:
        flash('Check the length of your shipping details and try again.', 'error')
        return redirect(url_for('checkout'))

    reference = secrets.token_hex(20)
    try:
        payment = paystack_request(
            'POST',
            'transaction/initialize',
            json={
                'email': g.current_user.email,
                'amount': int((Decimal(str(total)) * 100).quantize(Decimal('1'))),
                'currency': 'GHS',
                'reference': reference,
                'callback_url': url_for('paystack_callback', _external=True),
                'metadata': {'user_id': g.current_user.id},
            },
        )
    except RuntimeError as error:
        flash(str(error), 'error')
        return redirect(url_for('checkout'))

    authorization_url = payment.get('authorization_url')
    provider_reference = payment.get('reference')
    if not authorization_url or provider_reference != reference:
        app.logger.error('Paystack returned an invalid transaction initialization response.')
        flash('Payment provider returned an invalid response. Please try again.', 'error')
        return redirect(url_for('checkout'))

    order = Order(
        order_number=f"FINDME-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(4).upper()}",
        user_id=g.current_user.id,
        status='Pending',
        payment_status='pending',
        payment_reference=reference,
        total=total,
        subtotal=subtotal,
        shipping_cost=shipping,
        shipping_address=shipping_address,
        email=g.current_user.email,
    )
    g.current_user.phone = phone or g.current_user.phone
    g.current_user.shipping_address = shipping_address
    for item in cart_items:
        order.items.append(OrderItem(
            product_id=item['product'].id,
            quantity=item['quantity'],
            price=item['product'].price,
        ))

    try:
        db.session.add(order)
        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception('Could not persist Paystack order.')
        flash('We could not save your order. Please try checkout again.', 'error')
        return redirect(url_for('checkout'))

    return redirect(authorization_url)


@app.route('/payments/paystack/callback')
@login_required
def paystack_callback():
    reference = request.args.get('reference', '')
    if not reference or len(reference) > 100:
        flash('The payment reference is missing or invalid.', 'error')
        return redirect(url_for('account'))

    order = Order.query.filter_by(payment_reference=reference, user_id=g.current_user.id).first()
    if order is None:
        flash('We could not find an order for that payment.', 'error')
        return redirect(url_for('account'))
    if order.payment_status == 'paid':
        session.pop('cart', None)
        return redirect(url_for('order_success_detail', order_id=order.id))

    try:
        payment_succeeded = verify_paystack_payment(order)
    except RuntimeError as error:
        flash(str(error), 'error')
        return redirect(url_for('account'))

    if not payment_succeeded:
        order.payment_status = 'failed'
        db.session.commit()
        flash('Payment was not completed. Your order has not been paid.', 'error')
        return redirect(url_for('account'))

    order = mark_order_paid(order)
    session.pop('cart', None)
    if order.status == 'On hold':
        flash('Payment succeeded, but an item is no longer in stock. Contact support to resolve your order.', 'error')
        return redirect(url_for('account'))
    return redirect(url_for('order_success_detail', order_id=order.id))


@app.route('/payments/paystack/webhook', methods=['POST'])
def paystack_webhook():
    secret_key = os.environ.get('PAYSTACK_SECRET_KEY')
    signature = request.headers.get('x-paystack-signature', '')
    if not secret_key:
        app.logger.error('Paystack webhook received without PAYSTACK_SECRET_KEY configured.')
        return jsonify({'error': 'Payment webhook is not configured.'}), 503

    expected_signature = hmac.new(
        secret_key.encode('utf-8'),
        request.get_data(),
        hashlib.sha512,
    ).hexdigest()
    if not hmac.compare_digest(expected_signature, signature):
        abort(400, description='Invalid Paystack signature.')

    try:
        payload = request.get_json()
    except (TypeError, ValueError):
        abort(400, description='Invalid Paystack webhook payload.')
    if not isinstance(payload, dict) or payload.get('event') != 'charge.success':
        return jsonify({'received': True})

    reference = (payload.get('data') or {}).get('reference')
    if not reference or len(reference) > 100:
        abort(400, description='Missing Paystack transaction reference.')

    order = Order.query.filter_by(payment_reference=reference).first()
    if order is None:
        app.logger.warning('Paystack notified an unknown order reference.')
        return jsonify({'received': True})
    if order.payment_status == 'paid':
        return jsonify({'received': True})

    try:
        if verify_paystack_payment(order):
            mark_order_paid(order)
        else:
            app.logger.warning('Paystack webhook verification did not match the order.')
    except RuntimeError:
        return jsonify({'error': 'Could not verify payment yet.'}), 503
    return jsonify({'received': True})


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/login')
def login():
    if g.current_user:
        return redirect(safe_redirect_target(request.args.get('next')) or url_for('account'))
    return render_template('login.html', mode='login', next_url=safe_redirect_target(request.args.get('next')))


@app.route('/login', methods=['POST'])
def customer_login():
    email = request.form.get('email', '').strip().casefold()
    password = request.form.get('password', '')
    user = User.query.filter(db.func.lower(User.email) == email).first()
    if user is None or not user.check_password(password):
        flash('Invalid email or password.', 'error')
        return render_template('login.html', mode='login', next_url=safe_redirect_target(request.form.get('next'))), 401

    cart = session.get('cart', {})
    session.clear()
    session['cart'] = cart
    session['user_id'] = user.id
    flash('You are signed in.', 'success')
    return redirect(safe_redirect_target(request.form.get('next')) or url_for('account'))


@app.route('/register')
def register():
    if g.current_user:
        return redirect(url_for('account'))
    return render_template('login.html', mode='register', next_url=safe_redirect_target(request.args.get('next')))


@app.route('/register', methods=['POST'])
def customer_register():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().casefold()
    password = request.form.get('password', '')
    next_url = safe_redirect_target(request.form.get('next'))

    if not name or len(name) > 120 or not email or len(email) > 120 or '@' not in email:
        flash('Enter a valid name and email address.', 'error')
        return render_template('login.html', mode='register', next_url=next_url), 400
    if len(password) < 10:
        flash('Choose a password with at least 10 characters.', 'error')
        return render_template('login.html', mode='register', next_url=next_url), 400
    if User.query.filter(db.func.lower(User.email) == email).first():
        flash('An account with that email already exists. Please sign in.', 'error')
        return render_template('login.html', mode='register', next_url=next_url), 409

    user = User(name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception('Could not create customer account.')
        flash('We could not create your account. Please try again.', 'error')
        return render_template('login.html', mode='register', next_url=next_url), 500

    session.clear()
    session['user_id'] = user.id
    flash('Your account has been created.', 'success')
    return redirect(next_url or url_for('account'))


@app.route('/logout', methods=['POST'])
def customer_logout():
    session.clear()
    flash('You have been signed out.', 'success')
    return redirect(url_for('index'))


@app.route('/account/profile', methods=['POST'])
@login_required
def update_profile():
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    shipping_address = request.form.get('shipping_address', '').strip()
    if not name or len(name) > 120 or len(phone) > 20 or len(shipping_address) > 1000:
        flash('Check the profile details and try again.', 'error')
        return redirect(url_for('account'))

    g.current_user.name = name
    g.current_user.phone = phone
    g.current_user.shipping_address = shipping_address
    db.session.commit()
    flash('Your profile has been updated.', 'success')
    return redirect(url_for('account'))


# ========================== Admin Routes ==========================

@app.route('/admin')
def admin():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    total_products = Product.query.count()
    total_orders = Order.query.count()
    total_categories = Category.query.count()
    total_customers = User.query.count()
    pending_orders = Order.query.filter_by(status='Pending').count()
    total_revenue = db.session.query(db.func.sum(Order.total)).filter_by(payment_status='paid').scalar() or 0
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html', 
                          total_products=total_products,
                          total_orders=total_orders,
                          total_categories=total_categories,
                          total_customers=total_customers,
                          pending_orders=pending_orders,
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


@app.route('/admin/logout', methods=['POST'])
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
    
    if status in ['Pending', 'On hold', 'Processing', 'Shipped', 'Delivered']:
        try:
            order.status = status
            db.session.commit()
            flash('Order status updated', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating order status: {str(e)}', 'error')
    else:
        flash('Choose a valid order status', 'error')
    
    return redirect(url_for('admin_order_detail', order_id=order_id))


@app.route('/admin/categories')
def admin_categories():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    categories = Category.query.order_by(Category.name.asc()).all()
    return render_template('admin/categories.html', categories=categories)


@app.route('/admin/categories/add', methods=['GET', 'POST'])
def admin_add_category():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            if not name:
                flash('Category name is required', 'error')
                return render_template('admin/add_category.html', category=None)

            category = Category(
                name=name,
                description=request.form.get('description', '').strip()
            )
            db.session.add(category)
            db.session.commit()
            flash('Category added successfully', 'success')
            return redirect(url_for('admin_categories'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding category: {str(e)}', 'error')
    
    return render_template('admin/add_category.html', category=None)


@app.route('/admin/categories/edit/<int:category_id>', methods=['GET', 'POST'])
def admin_edit_category(category_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    category = Category.query.get_or_404(category_id)

    if request.method == 'POST':
        try:
            category.name = request.form.get('name', '').strip()
            category.description = request.form.get('description', '').strip()
            if not category.name:
                flash('Category name is required', 'error')
                return render_template('admin/add_category.html', category=category)

            db.session.commit()
            flash('Category updated successfully', 'success')
            return redirect(url_for('admin_categories'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating category: {str(e)}', 'error')

    return render_template('admin/add_category.html', category=category)


@app.route('/admin/categories/delete/<int:category_id>', methods=['POST'])
def admin_delete_category(category_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    category = Category.query.get_or_404(category_id)
    if category.products:
        flash('This category still has products. Move or remove those products before deleting it.', 'error')
        return redirect(url_for('admin_categories'))

    try:
        db.session.delete(category)
        db.session.commit()
        flash('Category deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting category: {str(e)}', 'error')

    return redirect(url_for('admin_categories'))


if not IS_HOSTED and not os.environ.get('SKIP_DATABASE_INIT'):
    init_db()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG') == '1' or os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
