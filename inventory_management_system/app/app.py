from flask import Flask, request, jsonify
from models import db, Inventory
from config import Config
from utils import validate_create_inventory_payload

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


@app.route('/inventory/create', methods=['POST'])
def create_inventory():
    """
    This function will create a new inventory with the mandatory fields
        name
        description
        quantity
        price
        category
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input"}), 404

    if not validate_create_inventory_payload(data):
        return jsonify({'error': 'Bad Request', 'message': 'Please provide item name, quantity, price and category'}), 400

    inventory_already_available = Inventory.query.filter_by(name=data.get('name')).first()
    if inventory_already_available:
        return jsonify({"error": "Inventory already available with the given name"}), 401

    new_item = Inventory(
        name=data.get('name'),
        description=data.get('description'),
        quantity=data.get('quantity'),
        price=data.get('price'),
        category=data.get('category')
    )

    db.session.add(new_item)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Inventory created successfully'}), 201


@app.route('/inventory/read/<int:inventory_id>', methods=['GET'])
def get_inventory_details(inventory_id):
    """
    This function will retrieve the individual inventory details
    Args:
        inventory_id: Integer
    """
    item = Inventory.query.filter_by(id=inventory_id).first()
    if item:
        item_details = {
            "name": item.name,
            "description": item.description,
            "quantity": item.quantity,
            "price": item.price,
            "category": item.category
        }
        return jsonify({"success": True, "item_details": item_details}), 201
    else:
        return jsonify({"error": "Inventory not found with the specified id"}), 400


@app.route('/inventory/update/<int:inventory_id>', methods=['PUT'])
def update_inventory(inventory_id):
    """
    This function will update the inventory details with the specified inventory
    Args:
        inventory_id: Integer
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input"}), 404

    if not validate_create_inventory_payload(data):
        return jsonify({'error': 'Bad Request', 'message': 'Please provide item name, quantity, price and category'}), 400

    item = Inventory.query.filter_by(id=inventory_id).first()
    if item:
        item.description = data.get('description', '')
        item.quantity = data.get('quantity')
        item.price = data.get('price')
        item.category = data.get('category')

        db.session.add(item)
        db.session.commit()
    else:
        return jsonify({"error": "Inventory not found with specified id"})

    return jsonify({"success": True, "message": "Succesfully update the inventory"})


@app.route('/inventory/delete/<int:inventory_id>', methods=['POST'])
def delete_inventory(inventory_id):
    """
    This function will delete an inventory related to a specified inventory id
    Args:
        inventory_id: Integer
    Returns:
        success response if successful else error response
    """
    item = Inventory.query.filter_by(id=inventory_id).first()
    if item:
        db.session.delete(item)
        db.session.commit()
    else:
        return jsonify({"error": "Inventory not found with specified id"})

    return jsonify({"success": True, "inventory": "Inventory successfully deleted"})


@app.route('/inventory/category', methods=['GET'])
def get_categories():
    """
    This function will list down all the inventory categories avaialble in the DB
    Returns:
        {
            "success": True,
            "categories": []
        }
    """
    categories = []
    for inventory in Inventory.query.with_entities(Inventory.category).distinct():
        categories.append(inventory.category)
    
    return jsonify({"success": True, "categories": categories})


@app.route('/inventory/search', methods=['POST'])
def inventory_search():
    """
    This API will fetch the inventory records that matches with the user specified details.
    Users can specify a string to match against the name or description of the inventory.
    Also users can specify the category to match against the inventories.
    Categories can be selected from the response of the GET API "/inventory/category"
    Function Payload:
        {
            "search_string": "",
            "category": "",
            "page_number": <Page number for pagination>
            "per_page": <records per page in pagination>
        }
    Response:
        Sucess if found
        empty if not found
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid search string"})

    search_text = data.get("search_string", "").lower()
    category = data.get("category", "").lower()
    page_number = data.get("page_number", 1)
    per_page = data.get("per_page", 10)

    if category:
        inventory_query = Inventory.query.filter(db.and_(
            Inventory.category == category,
            db.or_(
                Inventory.name.contains(search_text),
                Inventory.description.contains(search_text)
                )
            )
        )
    else:
        inventory_query = Inventory.query.filter(db.or_(
            Inventory.name.contains(search_text),
            Inventory.description.contains(search_text)
            )
        )

    pagination = inventory_query.paginate(page=page_number, per_page=per_page)

    inventory_items = []
    for item in pagination.items:
        each_inventory = {
            "id": item.id,
            "name": item.name,
            "description": item.description,
            "quantity": item.quantity,
            "price": item.price,
            "category": item.category
        }
        inventory_items.append(each_inventory)

    return jsonify({
        "items": inventory_items,
        "total_items": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
    })


if __name__ == '__main__':
    app.run(debug=True)
