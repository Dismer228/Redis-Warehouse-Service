import re
import redis
from flask import (Flask, request, jsonify, abort)

warehouseRegex = "^[A-Z0-9]{1,10}$"

def create_app():
    app = Flask(__name__)
    redisClient = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True) # type your Redis ip and port here

    # Function to create a Redis key for a warehouse    
    def warehouseKey(warehouse_id):
        return f'Warehouse:{warehouse_id}'
    

    # PUT request for warehouse registration
    @app.route('/warehouse', methods=['PUT'])
    def register_warehouse():
        reqBody = request.json

        # Extract warehouse data from request body
        warehouse_id = reqBody.get('id')
        warehouse_adresas = reqBody.get('adresas')
        warehouse_plotasM2 = reqBody.get('plotasM2')


    # Validate the warehouse ID using the regular expression
        if redisClient.exists(warehouseKey(warehouse_id)):
            return ('Sandelys su tokiu ID jau užregistruotas'), 400

    # Storing warehouse data in Redis (hash set)
        warehouse_data = {
            'id': warehouse_id,
            'adresas': warehouse_adresas,
            'plotasM2': warehouse_plotasM2
        }

    # Storing warehouse information in Redis
        redisClient.hset(warehouseKey(warehouse_id), mapping=warehouse_data)

        return ("Sandėlys užregistruotas."), 201

    # GET request for warehouse information
    @app.route('/warehouse/<warehouse_id>', methods=['GET'])
    def get_warehouse(warehouse_id):
        if re.search(warehouseRegex, warehouse_id) is not None:
            # Getting warehouse data from Redis
            warehouse = redisClient.hgetall(warehouseKey(warehouse_id))

            if warehouse:
            # Construct a response object with warehouse information
                warehouse_info = {
                "id": warehouse_id,
                "adresas": warehouse.get("adresas"),
                "plotasM2": int(warehouse.get("plotasM2"))  # Convert stored value to int
            }
                return (warehouse_info), 200
            else:
                return (f"Sandelys su nuruodytu ID nerastas"), 404

    # DELETE request for de-registration of a warehouse     
    @app.route('/warehouse/<warehouse_id>', methods=['DELETE'])
    def delete_warehouse(warehouse_id):
        if re.search(warehouseRegex, warehouse_id) is not None:
        # Check if the warehouse exists in Redis
            warehouse = redisClient.hgetall(warehouseKey(warehouse_id))

        if warehouse:
            # Deleting a warehouse from Redis
            redisClient.delete(warehouseKey(warehouse_id))

            inventory_key = f'{warehouse_id}:inventory'
            redisClient.delete(inventory_key)
            return 'Sandelys išregistruotas.', 200
        else:
            return 'Sandelys su nuruodytu ID nerastas.', 404
        
    # GET method for warehouse inventory
    @app.route('/warehouse/<warehouse_id>/inventory', methods=['GET'])
    def get_warehouse_inventory(warehouse_id):
        if re.search(warehouseRegex, warehouse_id) is not None:
        # Get inventory hash from Redis
            inventory_key = f'{warehouse_id}:inventory'
            inventory = redisClient.hkeys(inventory_key)

            if inventory:
                return ({"inventory": inventory}), 200
            else:
                return 'Sandelys nerastas.', 400
        
       # Get inventory quantities
    @app.route('/warehouse/<warehouse_id>/inventory/<inventory_id>', methods=['GET'])
    def get_inventory_amount(warehouse_id, inventory_id):
        if re.search(warehouseRegex, warehouse_id) is not None:
        # Redis inventory key
            inventory_key = f'{warehouse_id}:inventory'
        
        # Check if the inventory item exists
            if redisClient.hexists(inventory_key, inventory_id):
            # Get the sum of the item
                amount = redisClient.hget(inventory_key, inventory_id)
                return jsonify(int(amount)), 200
            else:
                return 'Inventorius arba sendelys nerastas', 404


    # Register new inventory
    @app.route('/warehouse/<warehouse_id>/inventory', methods=['PUT'])
    def add_inventory_to_warehouse(warehouse_id):
        if re.search(warehouseRegex, warehouse_id) is not None:

            req_body = request.json
            inventory_id = req_body.get("id")
            amount = req_body.get("amount")


        # Store inventory in Redis using the warehouse inventory hash
            inventory_key = f'{warehouse_id}:inventory'
            redisClient.hset(inventory_key, inventory_id, amount)

            return 'Inventorius įregistruotas', 201
        else:
            return 'Sandelys su nuruodytu ID nerastas.', 404
        
 

    # To record other inventory quantities
    @app.route('/warehouse/<warehouse_id>/inventory/<inventory_id>', methods=['POST'])
    def update_inventory_amount(warehouse_id, inventory_id):
        if re.search(warehouseRegex, warehouse_id) is not None:
        # Getting a new amount from the request body
            try:
                new_amount = int(request.data)  # Only the new amount is expected to be entered in the corpus as a number
            except (ValueError, TypeError):
                return ("Netinkama reikšmė"), 404

            if new_amount <= 0:
                return ("Reikšmė turi buti daugiau negu 0"), 400

            inventory_key = f'{warehouse_id}:inventory'
        
        # Check if the inventory item exists
            if redisClient.hexists(inventory_key, inventory_id):
            # Update item quantity
                redisClient.hset(inventory_key, inventory_id, new_amount)
                return ("Inventoriaus kiekis pakeistas."), 200
            else:
                return 'Inventorius arba sandelys nerastas.', 404
        
    # Remove inventory from storage
    @app.route('/warehouse/<warehouse_id>/inventory/<inventory_id>', methods=['DELETE'])
    def delete_inventory_item(warehouse_id, inventory_id):
        if re.search(warehouseRegex, warehouse_id) is not None:
            inventory_key = f'{warehouse_id}:inventory'
    
            if redisClient.hexists(inventory_key, inventory_id):
            # Delete an item from the warehouse inventory
                redisClient.hdel(inventory_key, inventory_id)
                return 'Inventorius pašalintas', 200
            else:
                return 'Inventorius arba sandelys nerastas', 404

    @app.route('/warehouse/<warehouse_id>/inventory/<inventory_id>/change', methods=['POST'])
    def adjust_inventory_amount(warehouse_id, inventory_id):
        if re.search(warehouseRegex, warehouse_id) is not None:

            inventory_key = f'{warehouse_id}:inventory'

        # Get the JSON body containing the adjustment amount
            req_body = request.get_json()
            quantity = req_body

        # Validate the input housing
            if not isinstance(quantity, int):
                return jsonify({"message": "Invalid quantity format. Must be an integer."}), 400

        # Check whether a specific stock item is in stock
            if redisClient.hexists(inventory_key, inventory_id):
            # Obtain the current quantity of an inventory item
                current_amount = int(redisClient.hget(inventory_key, inventory_id))

            # Adjust the amount according to the quantity received
                new_amount = current_amount + quantity

            # Updating stock levels in Redis
                redisClient.hset(inventory_key, inventory_id, new_amount)
                return ('Operacija sėkminga'), 200
            else:
                return ('Sandėlys ar inventorius sistemoje nerasti'), 404


    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
