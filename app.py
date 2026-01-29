from flask import Flask
from flask_cors import CORS
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from models import db
from routes import init_routes

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecommerce.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'super-secret-key'  # change this in production

db.init_app(app)
jwt = JWTManager(app)
init_routes(app)

# with app.app_context():
#     db.create_all()
@app.route('/')
def hello_world():

    return jsonify({
        "status": "ok",
        "message": "API is running"
    })
if __name__ == '__main__':
    app.run(debug=True)