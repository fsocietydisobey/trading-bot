import logging
from flask import Flask, jsonify
from blueprints.auth import auth_bp
from blueprints.data import data_bp
from api.routes import api_bp
from db.mongo import mongo
import os
from config.settings import settings
from influxdb_client import InfluxDBClient

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = settings.SECRET_KEY or os.environ.get('SECRET_KEY')
app.config['MONGO_URI'] = settings.MONGO_URI

# Initialize database connections
mongo.init_app(app)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(data_bp, url_prefix='/data')
app.register_blueprint(api_bp, url_prefix='/api')

@app.route('/health')
def health():
    status = {"mongo": "unknown", "influx": "unknown"}
    # Mongo check
    try:
        mongo.db.command('ping')
        status["mongo"] = "ok"
    except Exception as e:
        status["mongo"] = f"error: {e}"

    # Influx check
    try:
        client = InfluxDBClient(url=settings.INFLUX_URL, token=settings.INFLUX_TOKEN, org=settings.INFLUX_ORG)
        h = client.health()
        if getattr(h, "status", "").lower() == "pass":
            status["influx"] = "ok"
        else:
            status["influx"] = f"error: {getattr(h, 'message', 'unknown')}"
        client.close()
    except Exception as e:
        status["influx"] = f"error: {e}"

    http_code = 200 if status["mongo"] == "ok" and status["influx"] == "ok" else 503
    return jsonify(status), http_code

@app.route('/health/influx')
def health_influx():
    try:
        client = InfluxDBClient(url=settings.INFLUX_URL, token=settings.INFLUX_TOKEN, org=settings.INFLUX_ORG)
        h = client.health()
        client.close()
        ok = getattr(h, "status", "").lower() == "pass"
        return jsonify({"influx": "ok" if ok else "error"}), 200 if ok else 503
    except Exception as e:
        return jsonify({"influx": f"error: {e}"}), 503

@app.route('/health/mongo')
def health_mongo():
    try:
        mongo.db.command('ping')
        return jsonify({"mongo": "ok"}), 200
    except Exception as e:
        return jsonify({"mongo": f"error: {e}"}), 503

@app.route('/')
def hello_world():
    logging.debug('Hello World!')
    return 'Hello World!'

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
