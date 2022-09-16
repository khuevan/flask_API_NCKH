import hashlib
import redis
import datetime
from flask import Flask, request, jsonify, stream_with_context
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from pymongo import MongoClient
import json
from bson.json_util import dumps, loads
from setting import JWT_SECRET_KEY, MONGODB_STRING, DEBUG, HOST, PORT


app = Flask(__name__)
jwt = JWTManager(app)

ACCESS_EXPIRES = datetime.timedelta(hours=1)
app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = ACCESS_EXPIRES

client = MongoClient(MONGODB_STRING)

db = client["pinaapple"]
users_collection = db["users"]
images_collection = db['images']
videos_collection = db['videos']
discovery_collection = db['discovery']


jwt_redis_blocklist = redis.StrictRedis(
    host="localhost", port=5001, db=0, decode_responses=True
)


# Callback function to check if a JWT exists in the redis blocklist
@jwt.token_in_blocklist_loader
def check_if_token_is_revoked(jwt_header, jwt_payload: dict):
    jti = jwt_payload["jti"]
    token_in_redis = jwt_redis_blocklist.get(jti)
    return token_in_redis is not None


@app.route('/')
def index():
	return jsonify({'msg': 'OK'})


@app.route("/register", methods=["POST"])
def register():
	new_user = request.get_json()
	if new_user.account is not str:
		raise
	examplex = {
		'account':'',
		'password': '',
		'name': '',
		"permission": '',
		"avatar": "",
		"email": "",
		"phone": ""
	}
	
	new_user["password"] = hashlib.sha256(new_user["password"].encode("utf-8")).hexdigest() 
	# new_user.update({"name": "","permission": 0,"avatar": "","email": "","phone": ""})
	doc = users_collection.find_one({"account": new_user["account"]})
	if not doc:
		users_collection.insert_one(new_user)
		return jsonify({'msg': 'User created successfully'}), 201
	else:
		return jsonify({'msg': 'Username already exists'}), 409


@app.route("/login", methods=["POST"])
def login():
	login_details = request.get_json()
	# account = request.json.get('account')
	# password = request.json.get('password')
	user_from_db = users_collection.find_one({'account': login_details['account']})  

	if user_from_db:
		encrpted_password = hashlib.sha256(login_details['password'].encode("utf-8")).hexdigest()
		if encrpted_password == user_from_db['password']:
			access_token = create_access_token(identity=user_from_db['account'])
			return jsonify(access_token=access_token), 200

	return jsonify({'msg': 'The username or password is incorrect'}), 401


@app.route('/logout')
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    jwt_redis_blocklist.set(jti, "", ex=ACCESS_EXPIRES)
    return jsonify(msg="Access token revoked")


@app.route("/user")
@jwt_required()
def profile():
	current_user = get_jwt_identity()
	user_from_db = users_collection.find_one({'account' : current_user})
	if user_from_db:
		del user_from_db['_id'], user_from_db['password']
		return jsonify({'profile' : user_from_db }), 200
	else:
		return jsonify({'msg': 'Profile not found'}), 404


@app.route('/api/album-images')
def album_images():
	data = images_collection.find()

	def del_item(item):
		# for item in data:
		del item['_id']   
		del item['account']
		del item['accuracy']
		del item['class-name']
		# print(type(data[0]))
		return item
	data = [del_item(item) for item in data]
	return jsonify(data)


def insert_images(account, img_name, date, model, class_name, accuracy, is_count, is_cutout, path):
	data = {
		'account': account,
		'img-name': img_name,
		'date': date,
		'model': model,
		'class-name': class_name,
		'accuracy': accuracy,
		'is-cutout': is_cutout,
		'is-count': is_count,
		'path': path,
	}
	images_collection.insert_one(data)
	return "success"


def insert_discover(account, title, content, path, category, model):
	data = {
		'account': account,
		'title': title,
		'content': content,
		'path': path,
		'category': category,
		'model': model,
	}
	discovery_collection.insert_one(data)
	return "ok"


@app.route('/api/discovery/characteristics/<model>')
def album_characteristics(model):
	data = []
	for item in discovery_collection.find({'category':'characteristics', 'model': {model}}):
		new_item = {
			'title': item['title'],
			'path': item['path'],
			'model': item['model']
		}
		data.append(new_item)

	return jsonify(data)


@app.route('/api/discovery/<category>')
def category(category):
	data = [] 
	for item in discovery_collection.find({'category':{category}}):
		new_item = {
			'title': item['title'],
			'path': item['path'],
			'account': item['account'],
			'content': item['content']
		}
		data.append(new_item)

	return jsonify(data)


@app.route('/api/detect_image', methods=['POST'])
@jwt_required()
def detect_img():
	image = request.files.get('image')
	is_count = request.values.get('is_count')
	is_cutout = request.values.get('is_cutout')
	current_user = get_jwt_identity()
	user = users_collection.find_one({'account': user})
	if int(user.permission) >= 0:
		image = detect_img(image)
		date = datetime.date.today()
		date = date.strftime('%d/%m/%Y')
			# img_name, date, model, class_name, accuracy, path 
		insert_images(user['account'], img_name, date, model, class_name, accuracy, is_count, is_cutout, path)
		return image
	else:
		return jsonify({'msg': 'no permission'}), 405


if __name__ == '__main__':
	app.run(host=HOST, port=PORT, debug=DEBUG)