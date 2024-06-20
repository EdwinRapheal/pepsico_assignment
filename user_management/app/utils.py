from models import User


def validate_create_user_payload(request_json):
    if not request_json or \
        'username' not in request_json or \
            'email' not in request_json or \
                'password' not in request_json:
        return False
    else:
        return True


def username_exists(username):
    try:
        user_object = User.query.filter_by(username=username).first()
    except Exception as e:
        # Log the exception e
        return False
    return user_object


def email_exists(email):
    try:
        user_object = User.query.filter_by(email=email).first()
    except Exception as e:
        return False
    return user_object
