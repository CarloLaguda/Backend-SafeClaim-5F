from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/debug')
def debug():
    return jsonify({"messaggio": "Se vedi questo, Flask funziona"}), 200

if __name__ == "__main__":
    app.run(port=8001) # Cambiamo porta per sicurezza