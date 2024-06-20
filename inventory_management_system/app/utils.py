def validate_create_inventory_payload(request_json):
    if not request_json or \
        'name' not in request_json or \
            'quantity' not in request_json or \
                'price' not in request_json or \
                    'category' not in request_json:
        return False
    else:
        return True
