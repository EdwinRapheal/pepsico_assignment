from flask import Flask, request, jsonify
from models import db, User
from config import Config
from utils import validate_create_user_payload, username_exists, email_exists
import jwt
import datetime
from functools import wraps

app = Flask(__name__)
app.config.from_object(Config)


# Initialize the database
db.init_app(app)


# Create the database tables
with app.app_context():
    db.create_all()


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('x-access-tokens')

        if not token:
            return jsonify({'message': 'Token is missing'}), 403

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.filter_by(id=data['user_id']).first()
        except Exception as e:
            return jsonify({'message': 'Token is invalid', 'error': str(e)}), 403

        return f(current_user, *args, **kwargs)

    return decorated


@app.route('/')
def hello_world():
    return 'Hello, World!'


@app.route('/auth/register', methods=['POST'])
def add_user():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input"}), 404

    if not validate_create_user_payload(data):
        return jsonify({'error': 'Bad Request', 'message': 'Please provide username, email, and password'}), 400

    if username_exists(data['username']):
        return jsonify({'error': 'Username already exists'}), 400

    if email_exists(data['email']):
        return jsonify({'error': 'User exists with the same email'}), 400

    new_user = User(
        username=data["username"],
        email=data["email"],
        first_name=data['first_name'],
        last_name=data['last_name']
    )
    new_user.set_password(data['password'])
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'success': True, 'message': 'User created successfully'}), 201


@app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'error': 'Could not verify user'}), 401

    email = data['email']
    password = data['password']

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({"error": 'email or password is incorrect'}), 401

    token = jwt.encode({'user_id': user.id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)}, app.config['SECRET_KEY'], algorithm="HS256")

    return jsonify({'token': token})


@app.route('/auth/profile', methods=['GET'])
@token_required
def get_user_profile(user_object):
    if not user_object:
        return jsonify({"error": "User not found"}), 401
    user_details = {
        "username": user_object.username,
        "email": user_object.email,
        "first_name": user_object.first_name,
        "last_name": user_object.last_name,
    }
    return jsonify(user_details), 200


@app.route('/auth/profile', methods=['PUT'])
@token_required
def update_profile(user_object):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input"}), 404

    if user_object.username != data["username"]:
        # User has changed his/her username. So need to check the username availability
        new_username_user = User.query.filter_by(username=data["username"]).first()
        if new_username_user.username == data["username"]:
            return jsonify({"error": "User already exists with that username"}), 404

    if user_object.email != data["email"]:
        # User has changes his/her email-id. So need to check if there is any duplication users found
        new_email_user = User.query.filter_by(email=data["email"]).first()
        if new_email_user.email == data["email"]:
            return jsonify({"error": "User already exists with the same email"}), 404            

    user_object.username = data.get('username')
    user_object.email = data.get('email')
    user_object.first_name = data.get('first_name')
    user_object.last_name = data.get('last_name')

    db.session.add(user_object)
    db.session.commit()

    return jsonify({"success": True, "message":"User updated successfully"})


if __name__ == '__main__':
    app.run(port=5001, debug=True)
