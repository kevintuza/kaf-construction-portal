import os
import requests
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from markupsafe import escape

# Load the secret keys
load_dotenv()

app = Flask(__name__)

# SECURITY HEADERS
Talisman(app, content_security_policy=None)

# RATE LIMITING
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/submit-quote', methods=['POST'])
@limiter.limit("3 per minute")
def submit_quote():
    data = request.json

    # Grab Clover credentials
    api_key = os.environ.get('CLOVER_API_KEY')
    merchant_id = os.environ.get('CLOVER_MERCHANT_ID')
    environment = os.environ.get('CLOVER_ENVIRONMENT', 'sandbox')

    # Set the correct Clover URL based on environment
    if environment.lower() == 'production':
        base_url = f"https://api.clover.com/v3/merchants/{merchant_id}"
    else:
        base_url = f"https://apisandbox.dev.clover.com/v3/merchants/{merchant_id}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # INPUT SANITIZATION
    client_name = escape(data.get('name', 'Unknown Client'))
    client_email = escape(data.get('email', ''))
    client_phone = escape(data.get('phone', ''))

    services = []
    for service in data.get('services', []):
        services.append(escape(service))

    details = escape(data.get('message', ''))

    try:
        # Creates a Customer Profile in Clover
        customer_payload = {
            "firstName": client_name,
            "emailAddresses": [{"emailAddress": client_email}],
            "phoneNumbers": [{"phoneNumber": client_phone}]
        }

        customer_res = requests.post(f"{base_url}/customers", json=customer_payload, headers=headers)

        if customer_res.status_code not in [200, 201]:
            return jsonify({"status": "error", "message": "Failed to create Clover customer profile."}), 400

        customer_data = customer_res.json()
        customer_id = customer_data.get('id')

        # Creates a Draft Order in Clover
        service_description = f"Requested Services: {', '.join(services)}. Details: {details}"

        order_payload = {
            "state": "open",
            "title": "Website Quote Request",
            "note": service_description,
            "customers": [{"id": customer_id}]
        }

        order_res = requests.post(f"{base_url}/orders", json=order_payload, headers=headers)

        if order_res.status_code not in [200, 201]:
            return jsonify({"status": "error", "message": "Failed to draft Clover order."}), 400

        return jsonify({
            "status": "success",
            "message": "Quote request received! Order drafted in Clover."
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5001)