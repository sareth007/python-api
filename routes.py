import os
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from models import db, User, Category, Product, CartItem, Order, OrderItem

# Use absolute path so Flask can always find the folder
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def init_routes(app: Flask):
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # =====================================================
    # SERVE UPLOADED IMAGES (OPEN IN BROWSER)
    # =====================================================
    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # =====================================================
    # USER CRUD
    # =====================================================
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

    # =====================================================
    # CATEGORY CRUD
    # =====================================================
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

    # =====================================================
    # PRODUCT CRUD WITH IMAGE UPLOAD
    # =====================================================
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
            image=filename,
            category_id=category_id
        )
        db.session.add(product)
        db.session.commit()

        image_url = request.host_url + 'uploads/' + filename

        return jsonify({
            'message': 'Product created',
            'id': product.id,
            'image_url': image_url
        })

    @app.route('/products', methods=['GET'])
    def get_products():
        products = Product.query.all()
        result = []

        for p in products:
            image_url = request.host_url + 'uploads/' + p.image if p.image else None
            result.append({
                'id': p.id,
                'title': p.title,
                'description': p.description,
                'price': p.price,
                'qty': p.qty,
                'image_url': image_url,
                'category_id': p.category_id
            })

        return jsonify(result)

    @app.route('/products/<int:prod_id>', methods=['DELETE'])
    def delete_product(prod_id):
        p = Product.query.get(prod_id)
        if not p:
            return jsonify({'message': 'Product not found'}), 404

        # delete image file also
        if p.image:
            path = os.path.join(app.config['UPLOAD_FOLDER'], p.image)
            if os.path.exists(path):
                os.remove(path)

        db.session.delete(p)
        db.session.commit()
        return jsonify({'message': 'Product deleted'})

    # =====================================================
    # CART CRUD
    # =====================================================
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

    # =====================================================
    # ORDER CRUD
    # =====================================================
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

    # =====================================================
    # ORDER ITEMS
    # =====================================================
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