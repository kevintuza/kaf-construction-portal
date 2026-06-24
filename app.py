from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# This route serves the website when someone goes to the homepage
@app.route('/')
def home():
    return render_template('index.html')

# This route catches the form data when a user hits "Submit"
@app.route('/submit-quote', methods=['POST'])
def submit_quote():
    #Grabs the JSON data sent from the website
    data = request.json

    #Verify if it works.
    print("\n--- New Quote Request ---)")
    print(f"Name: {data.get('name')}")
    print(f"Email: {data.get('email')}")
    print(f"Phone: {data.get('phone')}")
    print(f"Services: {data.get('services')}")
    print(f"Details: {data.get('details')}")
    print("------------------------\n")

    #Sends a mock SUCCESS response back to the website
    # SOON Square API Code will go
    return jsonify({
        "status": "success",
        "message": "Quote request received successfully!"
    }), 200

if __name__ == '__main__':
    #Runs the local server in debug mode
    app.run(debug=True)