import os
import uuid # generates unique IDs so Square doesn't double-charge
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from square_legacy.client import Client

# Load the secret keys from the .env file
load_dotenv()

app = Flask(__name__)

# Initialize the Square Client
square_client = Client(
    access_token=os.environ.get('SQUARE_ACCESS_TOKEN'),
    environment=os.environ.get('SQUARE_ENVIRONMENT', 'sandbox')
)

# This route serves the website when someone goes to the homepage
@app.route('/')
def home():
    return render_template('index.html')

# This route catches the form data when a user hits "Submit"
@app.route('/submit-quote', methods=['POST'])
def submit_quote():
    #Grabs the JSON data sent from the website
    data = request.json
    location_id = os.environ.get('SQUARE_LOCATION_ID')

    #Extract data from the frontend form
    client_name = data.get('name', 'Unkown Client')
    client_email = data.get('email')
    client_phone = data.get('phone')
    services = data.get('services', [])
    details = data.get('message', '')

    try:
        # Create a Customer Profile in Square
        customer_body = {
            "idempotency_key": str(uuid.uuid4()),  # Ensures this request only processes once
            "given_name": client_name,
            "email_address": client_email,
            "phone_number": client_phone
        }
        customer_response = square_client.customers.create_customer(body=customer_body)

        if customer_response.is_error():
            return jsonify({"status": "error", "message": "Failed to create customer profile."}), 400

        # Grab the new Customer ID that Square just generated
        customer_id = customer_response.body['customer']['id']

        # Create an Order (Square requires an order before creating an invoice)
        service_description = f"Requested Services: {', '.join(services)}. Details: {details}"

        order_body = {
            "idempotency_key": str(uuid.uuid4()),
            "order": {
                "location_id": location_id,
                "customer_id": customer_id,
                "line_items": [
                    {
                        "name": "Custom Construction Estimate",
                        "note": service_description,
                        "quantity": "1",
                        "base_price_money": {
                            "amount": 0,  # Starts as a $0.00 draft until you update it with the real price
                            "currency": "USD"
                        }
                    }
                ]
            }
        }
        order_response = square_client.orders.create_order(body=order_body)

        if order_response.is_error():
            return jsonify({"status": "error", "message": "Failed to create order."}), 400

        # Grab the new Order ID
        order_id = order_response.body['order']['id']

        # Create the Draft Invoice
        invoice_body = {
            "idempotency_key": str(uuid.uuid4()),
            "invoice": {
                "location_id": location_id,
                "order_id": order_id,
                "primary_recipient": {
                    "customer_id": customer_id
                },
                "payment_requests": [
                    {
                        "request_type": "BALANCE",
                        "due_date": "2026-07-15",  # Placeholder due date
                    }
                ],
                "delivery_method": "EMAIL",
                "title": "K.A.F. Construction Quote Request"
            }
        }
        invoice_response = square_client.invoices.create_invoice(body=invoice_body)

        if invoice_response.is_error():
            return jsonify({"status": "error", "message": "Failed to draft invoice."}), 400

        # If all 3 steps succeed, send a success message back to the website
        return jsonify({
            "status": "success",
            "message": "Quote request received! Invoice draft generated in Square."
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
        app.run(debug=True, port=5001)