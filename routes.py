import os
from flask import request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from functools import wraps
from models import db, User, Category, Product, CartItem, Order, OrderItem
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ====================== UTILS ======================
def get_current_user():
    identity = get_jwt_identity()
    if not identity:
        return None
    return User.query.get(int(identity))  # identity is user ID string

def login_required(f):
    @wraps(f)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"message": "Login required"}), 401
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user or user.role != "admin":
            return jsonify({"message": "Admin access required"}), 403
        return f(*args, **kwargs)
    return wrapper

# ====================== ROUTES ======================
def init_routes(app):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    # --- Serve images ---
    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # --- AUTH ---
    @app.route('/register', methods=['POST'])
    def register():
        data = request.get_json()
        role = data.get('role', 'customer')
        user = User(username=data['username'], email=data['email'], role=role)
        user.set_password(data['password'])
        db.session.add(user)
        db.session.commit()
        return jsonify({'message': 'Registered successfully', 'role': user.role})

    @app.route('/login', methods=['POST'])
    def login():
        data = request.get_json()
        user = User.query.filter_by(username=data['username']).first()
        if user and user.check_password(data['password']):
            token = create_access_token(identity=str(user.id))  # ID as string
            return jsonify({'message': 'Login success', 'token': token})
        return jsonify({'message': 'Invalid credentials'}), 401

    # --- CATEGORY ---
    @app.route('/categories', methods=['POST'])
    @admin_required
    def create_category():
        data = request.get_json()
        cat = Category(name=data['name'])
        db.session.add(cat)
        db.session.commit()
        return jsonify({'message': 'Category created'})

    @app.route('/categories', methods=['GET'])
    def list_categories():
        cats = Category.query.all()
        return jsonify([{'id': c.id, 'name': c.name} for c in cats])

    # --- PRODUCTS ---
    @app.route('/products', methods=['POST'])
    @admin_required
    def create_product():
        if 'image' not in request.files:
            return jsonify({'message': 'No image uploaded'}), 400

        file = request.files['image']
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        product = Product(
            title=request.form['title'],
            description=request.form['description'],
            price=float(request.form['price']),
            qty=int(request.form['qty']),
            image=filename,
            category_id=int(request.form['category_id'])
        )
        db.session.add(product)
        db.session.commit()
        return jsonify({'message': 'Product added', 'id': product.id})

    @app.route('/products', methods=['GET'])
    @login_required
    def list_products():
        products = Product.query.all()
        return jsonify([
            {
                'id': p.id,
                'title': p.title,
                'description': p.description,
                'price': p.price,
                'qty': p.qty,
                'image_url': request.host_url + 'uploads/' + p.image if p.image else None,
                'category_id': p.category_id
            } for p in products
        ])

    @app.route('/products/category/<int:cat_id>', methods=['GET'])
    @login_required
    def products_by_category(cat_id):
        products = Product.query.filter_by(category_id=cat_id).all()
        return jsonify([{'id': p.id, 'title': p.title, 'price': p.price} for p in products])

    # --- CART ---
    @app.route('/cart', methods=['POST'])
    @login_required
    def add_to_cart():
        user = get_current_user()
        data = request.get_json()
        item = CartItem(user_id=user.id, product_id=data['product_id'], quantity=data['quantity'])
        db.session.add(item)
        db.session.commit()
        return jsonify({'message': 'Added to cart'})

    @app.route('/cart', methods=['GET'])
    @login_required
    def view_cart():
        user = get_current_user()
        items = CartItem.query.filter_by(user_id=user.id).all()
        return jsonify([{'product_id': i.product_id, 'qty': i.quantity} for i in items])

    # --- CHECKOUT ---
    @app.route('/checkout', methods=['POST'])
    @login_required
    def checkout():
        user = get_current_user()
        cart_items = CartItem.query.filter_by(user_id=user.id).all()
        if not cart_items:
            return jsonify({'message': 'Cart is empty'}), 400

        total = 0
        order = Order(user_id=user.id, total_price=0)
        db.session.add(order)
        db.session.flush()

        for item in cart_items:
            product = Product.query.get(item.product_id)
            if product.qty < item.quantity:
                return jsonify({'message': f'Not enough stock for {product.title}'}), 400

            product.qty -= item.quantity
            total += product.price * item.quantity

            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=item.quantity,
                price=product.price
            )
            db.session.add(order_item)
            db.session.delete(item)

        order.total_price = total
        db.session.commit()
        return jsonify({'message': 'Order placed', 'order_id': order.id})

    # --- TRACK ORDER ---
    @app.route('/orders/my', methods=['GET'])
    @login_required
    def my_orders():
        user = get_current_user()
        orders = Order.query.filter_by(user_id=user.id).all()
        return jsonify([{'id': o.id, 'total': o.total_price, 'status': o.status} for o in orders])

    # --- ADMIN ORDER MANAGEMENT ---
    @app.route('/admin/orders', methods=['GET'])
    @admin_required
    def all_orders():
        orders = Order.query.all()
        return jsonify([{'id': o.id, 'user_id': o.user_id, 'total': o.total_price, 'status': o.status} for o in orders])