from flask import Flask, request, jsonify
from models import db, User, Post, Comment
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


@app.route('/')
def hello_world():
    return 'Hello, World!'


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


@app.route('/blog/auth/register', methods=['POST'])
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


@app.route('/blog/auth/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'error': 'Bad Request', 'message': 'Could not verify user'}), 401

    email = data['email']
    password = data['password']

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({"error": 'email or password is incorrect'}), 401

    token = jwt.encode({'user_id': user.id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)}, app.config['SECRET_KEY'], algorithm="HS256")

    return jsonify({'token': token})


@app.route('/blog/posts/create', methods=['POST'])
@token_required
def create_post(user):
    """
    This method is used to create a new post with a payload
    {
        "title": "",
        "content": "",
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input"}), 404

    if "title" not in data or "content" not in data:
        return jsonify({'error': 'Bad Request', 'message': 'Please provide title, and content'}), 400

    post = Post(
        title=data.get('title'),
        content=data.get('content'),
        user_id=user.id
    )
    try:
        db.session.add(post)
        db.session.commit()
    except Exception as e:
        # Log the exception
        return jsonify({"error": "error while saving the post"})

    return jsonify({"success": True, "message": "Post was created successfully"}), 201


@app.route('/blog/posts', methods=['GET'])
def get_blog_posts():
    """
    This API is to list all blog posts available
    """
    post_objects = Post.query.all()
    post_json = {"posts": []}
    for post in post_objects:
        each_post = {
            "title": post.title,
            "content": post.content,
            "author": post.author.username
        }
        post_json["posts"].append(each_post)

    return jsonify({"success": True, "posts": post_json["posts"]}), 201


@app.route('/blog/posts/<int:post_id>', methods=['GET'])
def get_single_post(post_id):
    """
    This function will return a single post with the given post id
    """
    post_object = Post.query.filter_by(id=post_id).first()
    if post_object:
        post = {
            "title": post_object.title,
            "content": post_object.content,
            "author": post_object.author.username
        }
        return jsonify({"success": True, "post": post}), 201
    else:
        return jsonify({"error": "Post not found"}), 401


@app.route('/blog/posts/update/<int:post_id>', methods=['PUT'])
@token_required
def update_post(user, post_id):
    """
    This function will update the post with the given post id
    """
    post_data = request.get_json()
    if not post_data:
        return jsonify({'error': 'Bad Request', "message": "Invalid input"}), 404

    if "title" not in post_data or "content" not in post_data:
        return jsonify({'error': 'Bad Request', 'message': 'Please provide title, and content'}), 400

    post_object = Post.query.filter_by(id=post_id).first()
    if not post_object:
        return jsonify({'error': 'Post not found with given id'}), 401

    post_object.title = post_data.get('title', '')
    post_object.content = post_data.get('content', '')
    post_object.updated_at = post_data.get('updated', datetime.datetime.now())

    db.session.add(post_object)
    db.session.commit()

    return jsonify({"success": True, "message":"post successfully updated"}), 201


@app.route('/blog/posts/delete/<int:post_id>', methods=['DELETE'])
@token_required
def delete_post(user, post_id):
    post_object = Post.query.filter_by(id=post_id).first()
    if not post_object:
        return jsonify({"error": "Post not found with given post id"}), 401

    try:
        db.session.delete(post_object)
        db.session.commit()
    except Exception as e:
        # Log the exception
        return jsonify({"error":"Error deleting the post"}), 500
    return jsonify({"success": True, "message": "Post deleted successfully"}), 201


@app.route('/blog/posts/<int:post_id>/comments', methods=['POST'])
@token_required
def add_comment(user, post_id):
    comment_data = request.get_json()
    if not comment_data:
        return jsonify({'error': 'Bad Request', "message": "Invalid input"}), 404

    if "content" not in comment_data:
        return jsonify({'error': 'Bad Request', 'message': 'Please provide content'}), 400

    post_object = Post.query.filter_by(id=post_id).first()
    if not post_object:
        return jsonify({'error': 'Error finding the post object'}), 401

    try:
        comment = Comment(
            post_id=post_object.id,
            content=comment_data["content"],
            user_id=user.id
        )
        db.session.add(comment)
        db.session.commit()
    except Exception as e:
        # Log the exception
        return jsonify({'error': "Failed to create comment"}), 500

    return jsonify({'success': True, 'message': "Comment created successfully"}), 200


if __name__ == '__main__':
    app.run(port=5003, debug=True)
