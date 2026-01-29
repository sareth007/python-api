import os
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from models import db, User, Category, Product, CartItem, Order, OrderItem

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_routes(app: Flask):
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # ---------------- STATIC FILE SERVING ----------------
    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


    # ---------------- USER CRUD ----------------
    @app.route('/users', methods=['POST'])
    def create_user():
        data = request.get_json()
        user = User(username=data['username'], email=data['email'], role=data.get('role', 'customer'))
        user.set_password(data['password'])
        db.session.add(user)
        db.session.commit()
        return jsonify({'message': 'User created', 'id': user.id})

    @app.route('/users', methods=['GET'])
    def get_users():
        users = User.query.all()
        return jsonify([{'id': u.id, 'username': u.username, 'email': u.email, 'role': u.role} for u in users])

    @app.route('/users/<int:user_id>', methods=['GET'])
    def get_user(user_id):
        u = User.query.get(user_id)
        if not u:
            return jsonify({'message': 'User not found'}), 404
        return jsonify({'id': u.id, 'username': u.username, 'email': u.email, 'role': u.role})

    @app.route('/users/<int:user_id>', methods=['PUT'])
    def update_user(user_id):
        u = User.query.get(user_id)
        if not u:
            return jsonify({'message': 'User not found'}), 404
        data = request.get_json()
        u.username = data.get('username', u.username)
        u.email = data.get('email', u.email)
        u.role = data.get('role', u.role)
        if 'password' in data:
            u.set_password(data['password'])
        db.session.commit()
        return jsonify({'message': 'User updated'})

    @app.route('/users/<int:user_id>', methods=['DELETE'])
    def delete_user(user_id):
        u = User.query.get(user_id)
        if not u:
            return jsonify({'message': 'User not found'}), 404
        db.session.delete(u)
        db.session.commit()
        return jsonify({'message': 'User deleted'})


    # ---------------- CATEGORY CRUD ----------------
    @app.route('/categories', methods=['POST'])
    def create_category():
        data = request.get_json()
        c = Category(name=data['name'])
        db.session.add(c)
        db.session.commit()
        return jsonify({'message': 'Category created', 'id': c.id})

    @app.route('/categories', methods=['GET'])
    def get_categories():
        cats = Category.query.all()
        return jsonify([{'id': c.id, 'name': c.name} for c in cats])

    @app.route('/categories/<int:cat_id>', methods=['PUT'])
    def update_category(cat_id):
        c = Category.query.get(cat_id)
        if not c:
            return jsonify({'message': 'Category not found'}), 404
        data = request.get_json()
        c.name = data.get('name', c.name)
        db.session.commit()
        return jsonify({'message': 'Category updated'})

    @app.route('/categories/<int:cat_id>', methods=['DELETE'])
    def delete_category(cat_id):
        c = Category.query.get(cat_id)
        if not c:
            return jsonify({'message': 'Category not found'}), 404
        db.session.delete(c)
        db.session.commit()
        return jsonify({'message': 'Category deleted'})


    # ---------------- PRODUCT CRUD WITH IMAGE ----------------
    @app.route('/products', methods=['POST'])
    def create_product():
        if 'image' not in request.files:
            return jsonify({'message': 'No image uploaded'}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({'message': 'No selected file'}), 400

        if not allowed_file(file.filename):
            return jsonify({'message': 'File type not allowed'}), 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Get other form data
        title = request.form.get('title')
        description = request.form.get('description')
        price = float(request.form.get('price', 0))
        qty = int(request.form.get('qty', 0))
        category_id = int(request.form.get('category_id'))

        product = Product(
            title=title,
            description=description,
            price=price,
            qty=qty,
            image=filename,  # store just the filename
            category_id=category_id
        )
        db.session.add(product)
        db.session.commit()
        return jsonify({'message': 'Product created', 'id': product.id, 'image': f'/uploads/{filename}'})


    @app.route('/products', methods=['GET'])
    def get_products():
        products = Product.query.all()
        return jsonify([{
            'id': p.id,
            'title': p.title,
            'description': p.description,
            'price': p.price,
            'qty': p.qty,
            'image': f'/uploads/{p.image}' if p.image else None,
            'category_id': p.category_id
        } for p in products])


    @app.route('/products/<int:prod_id>', methods=['PUT'])
    def update_product(prod_id):
        p = Product.query.get(prod_id)
        if not p:
            return jsonify({'message': 'Product not found'}), 404

        # Update image if uploaded
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                p.image = filename

        p.title = request.form.get('title', p.title)
        p.description = request.form.get('description', p.description)
        p.price = float(request.form.get('price', p.price))
        p.qty = int(request.form.get('qty', p.qty))
        p.category_id = int(request.form.get('category_id', p.category_id))

        db.session.commit()
        return jsonify({'message': 'Product updated', 'image': f'/uploads/{p.image}'})


    @app.route('/products/<int:prod_id>', methods=['DELETE'])
    def delete_product(prod_id):
        p = Product.query.get(prod_id)
        if not p:
            return jsonify({'message': 'Product not found'}), 404
        db.session.delete(p)
        db.session.commit()
        return jsonify({'message': 'Product deleted'})


    # ---------------- CART CRUD ----------------
    @app.route('/cart', methods=['POST'])
    def create_cart_item():
        data = request.get_json()
        item = CartItem(user_id=data['user_id'], product_id=data['product_id'], quantity=data.get('quantity', 1))
        db.session.add(item)
        db.session.commit()
        return jsonify({'message': 'Cart item created', 'id': item.id})

    @app.route('/cart', methods=['GET'])
    def get_cart_items():
        items = CartItem.query.all()
        return jsonify([{'id': i.id, 'user_id': i.user_id, 'product_id': i.product_id, 'quantity': i.quantity} for i in items])

    @app.route('/cart/<int:item_id>', methods=['PUT'])
    def update_cart_item(item_id):
        item = CartItem.query.get(item_id)
        if not item:
            return jsonify({'message': 'Item not found'}), 404
        data = request.get_json()
        item.quantity = data.get('quantity', item.quantity)
        db.session.commit()
        return jsonify({'message': 'Cart item updated'})

    @app.route('/cart/<int:item_id>', methods=['DELETE'])
    def delete_cart_item(item_id):
        item = CartItem.query.get(item_id)
        if not item:
            return jsonify({'message': 'Item not found'}), 404
        db.session.delete(item)
        db.session.commit()
        return jsonify({'message': 'Cart item deleted'})


    # ---------------- ORDER CRUD ----------------
    @app.route('/orders', methods=['POST'])
    def create_order():
        data = request.get_json()
        order = Order(user_id=data['user_id'], total_price=data['total_price'], status=data.get('status', 'pending'))
        db.session.add(order)
        db.session.commit()
        return jsonify({'message': 'Order created', 'id': order.id})

    @app.route('/orders', methods=['GET'])
    def get_orders():
        orders = Order.query.all()
        return jsonify([{'id': o.id, 'user_id': o.user_id, 'total_price': o.total_price, 'status': o.status} for o in orders])

    @app.route('/orders/<int:order_id>', methods=['PUT'])
    def update_order(order_id):
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'message': 'Order not found'}), 404
        data = request.get_json()
        order.total_price = data.get('total_price', order.total_price)
        order.status = data.get('status', order.status)
        db.session.commit()
        return jsonify({'message': 'Order updated'})

    @app.route('/orders/<int:order_id>', methods=['DELETE'])
    def delete_order(order_id):
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'message': 'Order not found'}), 404
        db.session.delete(order)
        db.session.commit()
        return jsonify({'message': 'Order deleted'})


    # ---------------- ORDER ITEM CRUD ----------------
    @app.route('/order-items', methods=['POST'])
    def create_order_item():
        data = request.get_json()
        oi = OrderItem(
            order_id=data['order_id'],
            product_id=data['product_id'],
            quantity=data['quantity'],
            price=data['price']
        )
        db.session.add(oi)
        db.session.commit()
        return jsonify({'message': 'Order item created', 'id': oi.id})

    @app.route('/order-items', methods=['GET'])
    def get_order_items():
        items = OrderItem.query.all()
        return jsonify([{
            'id': i.id,
            'order_id': i.order_id,
            'product_id': i.product_id,
            'quantity': i.quantity,
            'price': i.price
        } for i in items])

    @app.route('/order-items/<int:item_id>', methods=['PUT'])
    def update_order_item(item_id):
        i = OrderItem.query.get(item_id)
        if not i:
            return jsonify({'message': 'Order item not found'}), 404
        data = request.get_json()
        i.quantity = data.get('quantity', i.quantity)
        i.price = data.get('price', i.price)
        db.session.commit()
        return jsonify({'message': 'Order item updated'})

    @app.route('/order-items/<int:item_id>', methods=['DELETE'])
    def delete_order_item(item_id):
        i = OrderItem.query.get(item_id)
        if not i:
            return jsonify({'message': 'Order item not found'}), 404
        db.session.delete(i)
        db.session.commit()
        return jsonify({'message': 'Order item deleted'})


# from flask import jsonify, request
# from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
# from functools import wraps
# from models import db, User, Category, Product, CartItem, Order, OrderItem
#
# # 🔐 Admin decorator
# def admin_required(fn):
#     @wraps(fn)
#     def wrapper(*args, **kwargs):
#         user = User.query.get(int(get_jwt_identity()))
#         if not user or user.role != 'admin':
#             return jsonify({'message': 'Admin only'}), 403
#         return fn(*args, **kwargs)
#     return wrapper
#
#
# def init_routes(app):
#
#     # ---------------- AUTH ----------------
#
#     @app.route('/create-admin', methods=['POST'])
#     def create_admin():
#         from models import db, User  # ensure models are imported
#
#         data = request.get_json()
#
#         if User.query.filter_by(username=data['username']).first():
#             return jsonify({'message': 'Username already exists'}), 400
#
#         admin = User(
#             username=data['username'],
#             email=data['email'],
#             role='admin'  # 👈 gives admin privileges
#         )
#         admin.set_password(data['password'])
#
#         db.session.add(admin)
#         db.session.commit()
#
#         return jsonify({'message': 'Admin user created successfully'})
#
#     @app.route('/register', methods=['POST'])
#     def register():
#         data = request.get_json()
#         if User.query.filter_by(username=data['username']).first():
#             return jsonify({'message': 'Username exists'}), 400
#
#         user = User(username=data['username'], email=data['email'], role='customer')
#         user.set_password(data['password'])
#         db.session.add(user)
#         db.session.commit()
#         return jsonify({'message': 'Registered successfully'}), 201
#
#     @app.route('/login', methods=['POST'])
#     def login():
#         data = request.get_json()
#         user = User.query.filter_by(username=data['username']).first()
#         if user and user.check_password(data['password']):
#             token = create_access_token(identity=str(user.id))
#             return jsonify({'token': token})
#         return jsonify({'message': 'Invalid credentials'}), 401
#
#     # ---------------- PRODUCTS ----------------
#     @app.route('/products', methods=['GET'])
#     def get_products():
#         products = Product.query.all()
#         print(products)  # see what comes out
#         return jsonify([{
#             'id': p.id,
#             'title': p.title,
#             'description': p.description,
#             'price': p.price,
#             'image': p.image,
#             'category': p.category.name if p.category else None
#         } for p in products])
#
#     # ---------------- CART ----------------
#     @app.route('/cart', methods=['GET'])
#     @jwt_required()
#     def get_cart():
#         user_id = int(get_jwt_identity())
#         items = CartItem.query.filter_by(user_id=user_id).all()
#         return jsonify([{
#             'product': i.product.title,
#             'quantity': i.quantity,
#             'price': i.product.price
#         } for i in items])
#
#     @app.route('/cart', methods=['POST'])
#     @jwt_required()
#     def add_to_cart():
#         user_id = int(get_jwt_identity())
#         data = request.get_json()  # expects {"product_id": 1, "quantity": 2}
#
#         # check if item already exists for this user
#         item = CartItem.query.filter_by(user_id=user_id, product_id=data['product_id']).first()
#         if item:
#             item.quantity += data.get('quantity', 1)  # increase quantity if already exists
#         else:
#             item = CartItem(
#                 user_id=user_id,
#                 product_id=data['product_id'],
#                 quantity=data.get('quantity', 1)
#             )
#             db.session.add(item)
#
#         db.session.commit()
#         return jsonify({'message': 'Cart updated'})
#
#     @app.route('/cart/<int:item_id>', methods=['PUT'])
#     @jwt_required()
#     def update_cart_item(item_id):
#         user_id = int(get_jwt_identity())
#         item = CartItem.query.filter_by(id=item_id, user_id=user_id).first()
#         if not item:
#             return jsonify({'message': 'Item not found'}), 404
#
#         data = request.get_json()
#         item.quantity = data.get('quantity', item.quantity)
#         db.session.commit()
#         return jsonify({'message': 'Cart item updated'})
#
#     @app.route('/cart/<int:item_id>', methods=['DELETE'])
#     @jwt_required()
#     def delete_cart_item(item_id):
#         user_id = int(get_jwt_identity())
#         item = CartItem.query.filter_by(id=item_id, user_id=user_id).first()
#         if not item:
#             return jsonify({'message': 'Item not found'}), 404
#
#         db.session.delete(item)
#         db.session.commit()
#         return jsonify({'message': 'Cart item deleted'})
#
#     # ---------------- CHECKOUT ----------------
#     @app.route('/checkout', methods=['POST'])
#     @jwt_required()
#     def checkout():
#         user_id = get_jwt_identity()
#         cart_items = CartItem.query.filter_by(user_id=user_id).all()
#
#         if not cart_items:
#             return jsonify({'message': 'Cart empty'}), 400
#
#         total = sum(i.quantity * i.product.price for i in cart_items)
#
#         order = Order(user_id=user_id, total_price=total)
#         db.session.add(order)
#         db.session.flush()  # get order.id
#
#         for item in cart_items:
#             order_item = OrderItem(
#                 order_id=order.id,
#                 product_id=item.product_id,
#                 quantity=item.quantity,
#                 price=item.product.price
#             )
#             db.session.add(order_item)
#             db.session.delete(item)
#
#         db.session.commit()
#         return jsonify({'message': 'Order placed', 'order_id': order.id})
#
#     # ---------------- ORDER TRACK ----------------
#     @app.route('/orders/<int:order_id>', methods=['GET'])
#     @jwt_required()
#     def track_order(order_id):
#         user_id = get_jwt_identity()
#         order = Order.query.filter_by(id=order_id, user_id=user_id).first()
#         if not order:
#             return jsonify({'message': 'Order not found'}), 404
#
#         return jsonify({
#             'id': order.id,
#             'total': order.total_price,
#             'status': order.status,
#             'created_at': order.created_at
#         })
#
#     # ---------------- ADMIN: CATEGORY ----------------
#     @app.route('/admin/categories', methods=['POST'])
#     @jwt_required()
#     @admin_required
#     def create_category():
#         data = request.get_json()
#         category = Category(name=data['name'])
#         db.session.add(category)
#         db.session.commit()
#         return jsonify({'message': 'Category created'})
#
#     # ---------------- ADMIN: PRODUCT ----------------
#     @app.route('/admin/products', methods=['POST'])
#     @jwt_required()
#     @admin_required
#     def create_product():
#         data = request.get_json()
#         product = Product(
#             title=data['title'],
#             description=data['description'],
#             price=data['price'],
#             image=data.get('image'),
#             category_id=data['category_id']
#         )
#         db.session.add(product)
#         db.session.commit()
#         return jsonify({'message': 'Product created'})
#
#     # ---------------- ADMIN: ORDERS ----------------
#     @app.route('/admin/orders', methods=['GET'])
#     @jwt_required()
#     @admin_required
#     def get_orders():
#         orders = Order.query.all()
#         return jsonify([{
#             'id': o.id,
#             'user_id': o.user_id,
#             'total': o.total_price,
#             'status': o.status
#         } for o in orders])
#
#     @app.route('/admin/orders/<int:order_id>', methods=['PUT'])
#     @jwt_required()
#     @admin_required
#     def update_order(order_id):
#         order = Order.query.get(order_id)
#         if not order:
#             return jsonify({'message': 'Order not found'}), 404
#         data = request.get_json()
#         order.status = data['status']
#         db.session.commit()
#         return jsonify({'message': 'Order updated'})