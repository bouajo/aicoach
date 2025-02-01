import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# Définissez votre token de vérification (doit être identique à celui configuré dans Meta)
WHATSAPP_VERIFY_TOKEN = "secret-token"


@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        verify_token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if verify_token == WHATSAPP_VERIFY_TOKEN:
            return challenge, 200
        return "Token de vérification incorrect", 403

    elif request.method == 'POST':
        data = request.json
        print("Notification reçue :", data)
        return jsonify(success=True), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
