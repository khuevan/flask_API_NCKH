Not thing here 😶‍🌫️🤫

# Flask API predict Fruit Pineapple🍍, Mangosteen

## Installation
Install with __pip__:
```bash
pip install -r requirements.txt
```
## Configuring
create file **.env**:
```
HOST=0.0.0.0
PORT=5000
DOMAIN=http://127.0.0.1:5000/
DEBUG=True
JWT_SECRET_KEY=thien-ngu
MONGODB_STRING=mongodb://localhost:27017/
```
## Run Flask
```bash
py main.py
```
Default port: `5000`<br>
Swagger document page: [https://127.0.0.1:5000/api/docs](https://127.0.0.1:5000/api/docs)

### TensorflowJs 

__Model__ url:
[http://127.0.0.1:5000/static/model/model.json](http://127.0.0.1:5000/static/model/model.json)


## MongoDB
```bash
mongorestore --verbose dump
```