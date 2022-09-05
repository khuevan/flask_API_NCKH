from flask import Flask, request, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your secret key'

d


@app.route('/login', methods=['GET'])
def login():
    return make_response(
        'OK', 200, {"Content": "OK"}
    )


if __name__ == "__main__":
	app.run(debug = False)
