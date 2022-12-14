import os, io, cv2, json
import hashlib
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_socketio import SocketIO, emit
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from pymongo import MongoClient
from bson.json_util import dumps, loads
from setting import JWT_SECRET_KEY, MONGODB_STRING, DEBUG, HOST, PORT
from PIL import Image
from detect_test import main, detect_cam
from detect_video import detect_video
import numpy as np
import cv2
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint


app = Flask(__name__)
cors = CORS(app, resources={r"/api/*": {"origins": "*"}})
jwt = JWTManager(app)
socketio = SocketIO(app)

ACCESS_EXPIRES = timedelta(hours=2)
app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = ACCESS_EXPIRES

client = MongoClient(MONGODB_STRING)

db = client["pinaapple"]
users_collection = db["users"]
images_collection = db['images']
videos_collection = db['videos']
discovery_collection = db['discovery']

SWAGGER_URL = '/api/docs'
API_URL = '/static/swagger.yaml'
swaggerui_blueprint = get_swaggerui_blueprint(
	SWAGGER_URL,
	API_URL,
	config={
		'app-name': "Fruit....REST-API"
	}
)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)


@app.route('/')
def index():
	return jsonify({'msg': 'OK'})
	# return render_template('login.html')


@app.route('/favicon.ico')
def favicon():
	return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/index')
def home():
	return jsonify({'msg': 'OK'})
	# return render_template('index.html')


@app.route("/register", methods=["POST"])
def register():
	# new_user = request.get_json()
	new_user = {
		'account': request.values.get('account'),
		'password': request.values.get('password'),
		'avatar': request.files.getlist('avatar')[0].read(),
		'name': request.values.get('name'),
		'email': request.values.get('email'),
		'phone': request.values.get('phone') if request.values.get('account') is str else '',
		'permission': 0
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
	# login_details = request.values.to_dict()
	login_details = {
		'account': request.values.get('account'),
		'password': request.values.get('password')
	}
	user_from_db = users_collection.find_one({'account': login_details['account']})  

	if user_from_db:
		encrpted_password = hashlib.sha256(login_details['password'].encode("utf-8")).hexdigest()
		if encrpted_password == user_from_db['password']:
			access_token = create_access_token(identity=user_from_db['account'])
			return jsonify(access_token=access_token, message="Logged in", status='ok'), 200

	return jsonify({'msg': 'The username or password is incorrect'}), 401


@app.route("/user")
@jwt_required()
def profile():
	current_user = get_jwt_identity()
	user_from_db = users_collection.find_one({'account' : current_user})
	if user_from_db:
		del user_from_db['_id'], user_from_db['password'], user_from_db["permission"]
		print(user_from_db)
		return jsonify(user_from_db), 200
	else:
		return jsonify({'msg': 'Profile not found'}), 404


@app.route('/api/album-images')
def album_images():
	data = images_collection.find()

	def del_item(item):
		del item['_id'], item['account'], item['accuracy'], item['class-name']
		return item
	data = [del_item(item) for item in data]
	return jsonify(data), 200


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

	return jsonify(data), 200


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

	return jsonify(data), 200


@app.route('/api/predict_image', methods=['POST'])
@jwt_required()
def predict():
	images = request.files.getlist('image')

	is_count = request.values.get('is_count') == 'true'
	is_cutout = request.values.get('is_cutout') == 'true'
	current_user = get_jwt_identity()

	user = users_collection.find_one({'account': current_user})
	if int(user['permission']) >= 0:
		image = images[0].read()
		image = Image.open(io.BytesIO(image))
		image = image.convert('RGB')
		image = np.array(image)

		data = main(
			images=image,
			dont_show=True,
			crop=is_cutout,
			counted=is_count,
			model_type="Pineapple",
			name_created=user['account'])
		# from pprint import pprint
		# pprint(data)
		insert_images(user['account'], data['path'], data['date-created'], data['model_type'], data['list_box'], data['function'], data['crop_path'],data['path'])
		del data['date-created'], data['model_type'], data['function'], data['user-created']

		return jsonify(data), 200 
	else:
		return jsonify(msg='No permission'), 405	


@app.route('/api/predit_video', methods=['POST'])
@jwt_required()
def predit_video():
	current_user = get_jwt_identity()
	video = request.files.get('video')

	is_count = request.values.get('is_count') == 'true'
	is_cutout = True if request.values.get('is_cutout') == 'true' else False

	user = users_collection.find_one({'account': current_user})
	if user['permission'] > -1:
		video_path = 'static/album-videos/' + str(datetime.now().timestamp()) + '.mp4'
		video = video.save(video_path)
		data = detect_video(
			video=video_path,
			dont_show=True,
			crop=is_cutout,
			counted=is_count,
			model_type="Pineapple",
			name_created=user['account'])
		os.remove(video_path)
		# insert to stupid db
		# stupid insert
		insert_db('videos', data=data)
		del data['date-created'], data['model_type'], data['function'], data['user-created']
		# from pprint import pprint
		# pprint(data)

		return jsonify(data), 200
	else:
		return jsonify(msg="No permission"), 405


def insert_db(collection, data):
	coll = db[collection]
	coll.insert_one(data)

# https://github.com/dxue2012/python-webcam-flask/blob/master/app.py
# https://github.com/liemkg1234/Websocket_FaceMaskDetection/blob/master/app.py
@socketio.on('frame_Input', namespace='/detect')
def getImage(input): #type('str' base64URL)
	input = input.split(",")[1]
	image_data = input

	# Base64_2_PIL
	img_pil = base64_to_pil_image(image_data)
	# PIL_2_CV2
	img_cv2 = np.array(img_pil)

	img = detect_cam(img_cv2)

	#PIL_2_base64URL
	image_data = pil_image_to_base64(img).decode("utf-8")
	image_data = "data:image/jpeg;base64," + image_data

	# Gui frame&class len client
	emit('frame_Output', {'img': image_data}, namespace='/detect')


@app.route('/test')
def test():
	return render_template('cam.html')


if __name__ == '__main__':
	# app.run(host=HOST, port=PORT, debug=DEBUG)
	socketio.run(app, host=HOST, port=PORT, debug=DEBUG)