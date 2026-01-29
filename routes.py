from flask import jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from functools import wraps
from models import db, User, Category, Product, CartItem, Order, OrderItem

# 🔐 Admin decorator
def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = User.query.get(int(get_jwt_identity()))
        if not user or user.role != 'admin':
            return jsonify({'message': 'Admin only'}), 403
        return fn(*args, **kwargs)
    return wrapper


def init_routes(app):

    # ---------------- AUTH ----------------

    @app.route('/create-admin', methods=['POST'])
    def create_admin():
        from models import db, User  # ensure models are imported

        data = request.get_json()

        if User.query.filter_by(username=data['username']).first():
            return jsonify({'message': 'Username already exists'}), 400

        admin = User(
            username=data['username'],
            email=data['email'],
            role='admin'  # 👈 gives admin privileges
        )
        admin.set_password(data['password'])

        db.session.add(admin)
        db.session.commit()

        return jsonify({'message': 'Admin user created successfully'})

    @app.route('/register', methods=['POST'])
    def register():
        data = request.get_json()
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'message': 'Username exists'}), 400

        user = User(username=data['username'], email=data['email'], role='customer')
        user.set_password(data['password'])
        db.session.add(user)
        db.session.commit()
        return jsonify({'message': 'Registered successfully'}), 201

    @app.route('/login', methods=['POST'])
    def login():
        data = request.get_json()
        user = User.query.filter_by(username=data['username']).first()
        if user and user.check_password(data['password']):
            token = create_access_token(identity=str(user.id))
            return jsonify({'token': token})
        return jsonify({'message': 'Invalid credentials'}), 401

    # ---------------- PRODUCTS ----------------
    @app.route('/products', methods=['GET'])
    def get_products():
        products = Product.query.all()
        return jsonify([{
            'id': p.id,
            'title': p.title,
            'description': p.description,
            'price': p.price,
            'image': p.image,
            'category': p.category.name
        } for p in products])

    # ---------------- CART ----------------
    @app.route('/cart', methods=['GET'])
    @jwt_required()
    def get_cart():
        user_id = int(get_jwt_identity())
        items = CartItem.query.filter_by(user_id=user_id).all()
        return jsonify([{
            'product': i.product.title,
            'quantity': i.quantity,
            'price': i.product.price
        } for i in items])

    @app.route('/cart', methods=['POST'])
    @jwt_required()
    def add_to_cart():
        user_id = int(get_jwt_identity())
        data = request.get_json()  # expects {"product_id": 1, "quantity": 2}

        # check if item already exists for this user
        item = CartItem.query.filter_by(user_id=user_id, product_id=data['product_id']).first()
        if item:
            item.quantity += data.get('quantity', 1)  # increase quantity if already exists
        else:
            item = CartItem(
                user_id=user_id,
                product_id=data['product_id'],
                quantity=data.get('quantity', 1)
            )
            db.session.add(item)

        db.session.commit()
        return jsonify({'message': 'Cart updated'})

    @app.route('/cart/<int:item_id>', methods=['PUT'])
    @jwt_required()
    def update_cart_item(item_id):
        user_id = int(get_jwt_identity())
        item = CartItem.query.filter_by(id=item_id, user_id=user_id).first()
        if not item:
            return jsonify({'message': 'Item not found'}), 404

        data = request.get_json()
        item.quantity = data.get('quantity', item.quantity)
        db.session.commit()
        return jsonify({'message': 'Cart item updated'})

    @app.route('/cart/<int:item_id>', methods=['DELETE'])
    @jwt_required()
    def delete_cart_item(item_id):
        user_id = int(get_jwt_identity())
        item = CartItem.query.filter_by(id=item_id, user_id=user_id).first()
        if not item:
            return jsonify({'message': 'Item not found'}), 404

        db.session.delete(item)
        db.session.commit()
        return jsonify({'message': 'Cart item deleted'})

    # ---------------- CHECKOUT ----------------
    @app.route('/checkout', methods=['POST'])
    @jwt_required()
    def checkout():
        user_id = get_jwt_identity()
        cart_items = CartItem.query.filter_by(user_id=user_id).all()

        if not cart_items:
            return jsonify({'message': 'Cart empty'}), 400

        total = sum(i.quantity * i.product.price for i in cart_items)

        order = Order(user_id=user_id, total_price=total)
        db.session.add(order)
        db.session.flush()  # get order.id

        for item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.product.price
            )
            db.session.add(order_item)
            db.session.delete(item)

        db.session.commit()
        return jsonify({'message': 'Order placed', 'order_id': order.id})

    # ---------------- ORDER TRACK ----------------
    @app.route('/orders/<int:order_id>', methods=['GET'])
    @jwt_required()
    def track_order(order_id):
        user_id = get_jwt_identity()
        order = Order.query.filter_by(id=order_id, user_id=user_id).first()
        if not order:
            return jsonify({'message': 'Order not found'}), 404

        return jsonify({
            'id': order.id,
            'total': order.total_price,
            'status': order.status,
            'created_at': order.created_at
        })

    # ---------------- ADMIN: CATEGORY ----------------
    @app.route('/admin/categories', methods=['POST'])
    @jwt_required()
    @admin_required
    def create_category():
        data = request.get_json()
        category = Category(name=data['name'])
        db.session.add(category)
        db.session.commit()
        return jsonify({'message': 'Category created'})

    # ---------------- ADMIN: PRODUCT ----------------
    @app.route('/admin/products', methods=['POST'])
    @jwt_required()
    @admin_required
    def create_product():
        data = request.get_json()
        product = Product(
            title=data['title'],
            description=data['description'],
            price=data['price'],
            image=data.get('image'),
            category_id=data['category_id']
        )
        db.session.add(product)
        db.session.commit()
        return jsonify({'message': 'Product created'})

    # ---------------- ADMIN: ORDERS ----------------
    @app.route('/admin/orders', methods=['GET'])
    @jwt_required()
    @admin_required
    def get_orders():
        orders = Order.query.all()
        return jsonify([{
            'id': o.id,
            'user_id': o.user_id,
            'total': o.total_price,
            'status': o.status
        } for o in orders])

    @app.route('/admin/orders/<int:order_id>', methods=['PUT'])
    @jwt_required()
    @admin_required
    def update_order(order_id):
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'message': 'Order not found'}), 404
        data = request.get_json()
        order.status = data['status']
        db.session.commit()
        return jsonify({'message': 'Order updated'})