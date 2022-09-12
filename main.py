import hashlib
import datetime
from flask import Flask, request, jsonify, stream_with_context
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from pymongo import MongoClient


app = Flask(__name__)
jwt = JWTManager(app)
app.config['JWT_SECRET_KEY'] = ''
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(days=1)

client = MongoClient("mongodb://localhost:27017/") 
db = client["pinaapple"]
users_collection = db["users"]


@app.route("/api/register", methods=["POST"])
def register():
	new_user = request.get_json()
	new_user["password"] = hashlib.sha256(new_user["password"].encode("utf-8")).hexdigest() 
	doc = users_collection.find_one({"username": new_user["username"]}) 
	if not doc:
		users_collection.insert_one(new_user)
		return jsonify({'msg': 'User created successfully'}), 201
	else:
		return jsonify({'msg': 'Username already exists'}), 409


@app.route("/api/login", methods=["POST"])
def login():
	login_details = request.get_json()
	user_from_db = users_collection.find_one({'username': login_details['username']})  

	if user_from_db:
		encrpted_password = hashlib.sha256(login_details['password'].encode("utf-8")).hexdigest()
		if encrpted_password == user_from_db['password']:
			access_token = create_access_token(identity=user_from_db['username'])
			return jsonify(access_token=access_token), 200

	return jsonify({'msg': 'The username or password is incorrect'}), 401


@app.route("/api/user", methods=["GET"])
@jwt_required
def profile():
	current_user = get_jwt_identity()
	user_from_db = users_collection.find_one({'username' : current_user})
	if user_from_db:
		del user_from_db['_id'], user_from_db['password']
		return jsonify({'profile' : user_from_db }), 200
	else:
		return jsonify({'msg': 'Profile not found'}), 404


@app.route("/api/streamcontex", methods=['POST'])
def camera():
    def gen():
        # get image from request ?
        # process ?
        # yield ?
        # return ?
        yield '?'
        yield 'work?'
        yield 'dunno'
    return app.response_class(stream_with_context(gen()))


if __name__ == '__main__':
	app.run()