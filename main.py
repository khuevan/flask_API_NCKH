import os, io, cv2, json
import hashlib
import redis
import datetime
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from pymongo import MongoClient
from bson.json_util import dumps, loads
from setting import JWT_SECRET_KEY, MONGODB_STRING, DEBUG, HOST, PORT
from PIL import Image
from detect_test import main
import numpy as np
import cv2
from flask_cors import CORS

app = Flask(__name__)
cors = CORS(app, resources={r"/api/*": {"origins": "*"}})
jwt = JWTManager(app)
socketio = SocketIO(app)


ACCESS_EXPIRES = datetime.timedelta(hours=2)
app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = ACCESS_EXPIRES

client = MongoClient(MONGODB_STRING)

db = client["pinaapple"]
users_collection = db["users"]
images_collection = db['images']
videos_collection = db['videos']
discovery_collection = db['discovery']


# jwt_redis_blocklist = redis.StrictRedis(
#     host="localhost", port=5001, db=0, decode_responses=True



# Callback function to check if a JWT exists in the redis blocklist
# @jwt.token_in_blocklist_loader
# def check_if_token_is_revoked(jwt_header, jwt_payload: dict):
#     jti = jwt_payload["jti"]
#     token_in_redis = jwt_redis_blocklist.get(jti)
#     return token_in_redis is not None


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


# @app.route('/logout')
# @jwt_required()
# def logout():
#     jti = get_jwt()["jti"]
#     jwt_redis_blocklist.set(jti, "", ex=ACCESS_EXPIRES)
#     return jsonify(msg="Access token revoked")


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


def insert_images(account, img_name, date, model, list_box, function_usage, crop_path, path):
	data = {
		'account': account,
		'img-name': img_name,
		'date': date,
		'model': model,
		'list_box': list_box,
		'function_usage': function_usage,
		'crop_path': crop_path,
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


@app.route('/api/predict-image', methods=['POST'])
@jwt_required()
def predict():
	images = request.files.getlist('image')
	# print(images)
	is_count = True if request.values.get('is_count')=='true' else False
	is_cutout = True if request.values.get('is_cutout')=='true' else False
	current_user = get_jwt_identity()

	user = users_collection.find_one({'account': current_user})
	if int(user['permission']) >= 0:
		for image in images:
			image = image.read()
			image = Image.open(io.BytesIO(image))
			image = image.convert('RGB')
			image = np.array(image)

			date = datetime.date.today()
			date = date.strftime('%d/%m/%Y')
			data = main(
				images='./data/images/pine.jpg',
				dont_show=True,
				crop=is_cutout,
				counted=is_count,
				model_type="Pineapple",
				name_created=user['account'])
			from pprint import pprint
			pprint(data)
			insert_images(user['account'], data['image'], data['date-created'], data['model_type'], data['list_box'], data['function'], data['crop_path'],data['path'])
		return jsonify({'data': 'not yet'}) 
	else:
		return jsonify({'msg': 'no permission'}), 405


@socketio.on('image')
def image(data_image):
    sbuf = StringIO()
    sbuf.write(data_image)

    # decode and convert into image
    b = io.BytesIO(base64.b64decode(data_image))
    pimg = Image.open(b)

    # converting RGB to BGR, as opencv standards
    frame = cv2.cvtColor(np.array(pimg), cv2.COLOR_RGB2BGR)

    # Process the image frame
    frame = imutils.resize(frame, width=700)
    frame = cv2.flip(frame, 1)
    imgencode = cv2.imencode('.jpg', frame)[1]

    # base64 encode
    stringData = base64.b64encode(imgencode).decode('utf-8')
    b64_src = 'data:image/jpg;base64,'
    stringData = b64_src + stringData

    # emit the frame back
    emit('response_back', stringData)


if __name__ == '__main__':
	app.run(host=HOST, port=5000, debug=DEBUG)
	# socketio.run(app=app, host=HOST, port=PORT, debug=DEBUG)