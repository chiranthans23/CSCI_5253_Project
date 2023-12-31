import os
from flask import jsonify, Flask, request
from mysql.connector import Error
import mysql.connector
from redis import Redis
import logging
import datetime
log = logging.getLogger('werkzeug')
log.setLevel(logging.DEBUG)

app = Flask(__name__)

# envs
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
DB1_HOST = os.getenv("DB1_HOST", "localhost")
DB2_HOST = os.getenv("DB2_HOST", "localhost")
DB3_HOST = os.getenv("DB3_HOST", "localhost")
DB_USERNAME = os.getenv("DB_USERNAME", "USER")
DB_PASSWORD = os.getenv("DB_PASSWORD", "PASS")
REQUEST_Q = "request"
LOGGING_Q = "logging"
THRESHOLD_COUNT = 5

# connecting and setting up initial databases and data
try:
    connection1 = mysql.connector.connect(
        host = DB1_HOST,
        user = DB_USERNAME,
        password = DB_PASSWORD,
        database = "station1"
        )
except:
    connection1 = mysql.connector.connect(
        host = DB1_HOST,
        user = DB_USERNAME,
        password = DB_PASSWORD
        )
    cur = connection1.cursor()
    cur.execute("CREATE DATABASE station1")
    connection1 = mysql.connector.connect(
        host = DB1_HOST,
        user = DB_USERNAME,
        password = DB_PASSWORD,
        database = "station1"
        )
    cur = connection1.cursor()
    cur.execute("CREATE TABLE pantry(id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(255), count INT);")
    cur.execute('INSERT INTO pantry(name, count) VALUES("apple", 10);')
    connection1.commit()
    cur.execute('INSERT INTO pantry(name, count) VALUES("mango", 10);')
    connection1.commit()
    cur.execute('INSERT INTO pantry(name, count) VALUES("banana", 10);')
    connection1.commit()

try:
    connection2 = mysql.connector.connect(
        host = DB2_HOST,
        user = DB_USERNAME,
        password = DB_PASSWORD,
        database = "station2",
        port = 4306
        )
except:
    connection2 = mysql.connector.connect(
        host = DB2_HOST,
        user = DB_USERNAME,
        password = DB_PASSWORD,
        port = 4306
        )
    cur = connection2.cursor()
    cur.execute("CREATE DATABASE station2")
    connection2 = mysql.connector.connect(
        host = DB2_HOST,
        user = DB_USERNAME,
        password = DB_PASSWORD,
        database = "station2",
        port = 4306
        )
    cur = connection2.cursor()
    cur.execute("CREATE TABLE pantry(id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(255), count INT);")
    cur.execute('INSERT INTO pantry(name, count) VALUES("apple", 10);')
    connection2.commit()
    cur.execute('INSERT INTO pantry(name, count) VALUES("mango", 10);')
    connection2.commit()
    cur.execute('INSERT INTO pantry(name, count) VALUES("banana", 10);')
    connection2.commit()

try:
    connection3 = mysql.connector.connect(
        host = DB3_HOST,
        user = DB_USERNAME,
        password = DB_PASSWORD,
        database = "station3",
        port = 5306
        )
except:
    connection3 = mysql.connector.connect(
        host = DB3_HOST,
        user = DB_USERNAME,
        password = DB_PASSWORD,
        port = 5306
        )
    cur = connection3.cursor()
    cur.execute("CREATE DATABASE station3")
    connection3 = mysql.connector.connect(
        host = DB3_HOST,
        user = DB_USERNAME,
        password = DB_PASSWORD,
        database = "station3",
        port = 5306
        )
    cur = connection3.cursor()
    cur.execute("CREATE TABLE pantry(id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(255), count INT);")
    cur.execute('INSERT INTO pantry(name, count) VALUES("apple", 10);')
    connection3.commit()
    cur.execute('INSERT INTO pantry(name, count) VALUES("mango", 10);')
    connection3.commit()
    cur.execute('INSERT INTO pantry(name, count) VALUES("banana", 10);')
    connection3.commit()

queue = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

print(connection1)
@app.route("/")
def hello():
    """Function to test the functionality of the API"""
    # log.debug(f"[{datetime.datetime.now()}] Recieved request for {request.url} ")
    # log.debug(f"[{datetime.datetime.now()}] Successfully completed request for {request.url}")

    # queue.rpush(LOGGING_Q,f"[{datetime.datetime.now()}] Successfully completed request for {request.url}")
    return "Hello, world!"

@app.route("/add/<int:station_num>/<string:item>/<int:count>", methods=["POST"])
def put_item(station_num, item, count):
    """ Adds the given amount of item to the specified station"""
    log.debug(f"[{datetime.datetime.now()}] Recieved request for {request.url} with data {(station_num, item, count)}")
    
    if station_num not in [1, 2, 3]:
        return jsonify("wrong station number!")
    
    try:
        cursor = connection1.cursor()
        if station_num == 2:
            cursor = connection2.cursor()
        elif station_num == 3:
            cursor = connection3.cursor()
    except:
        return jsonify("not connected to db")
    
    sql = f"SELECT count FROM pantry WHERE name = '{item}'"

    try:
        print(sql)
        cursor.execute(sql)
        result = cursor.fetchone()

        if not result:
            resp = jsonify("the requested item doesn't exist in the pantry")
            resp.status_code = 404
            return resp

        print(result[0])
        item_count = result[0]
        sql = f"UPDATE pantry SET count = {item_count + count} WHERE name = '{item}'"
        cursor.execute(sql)
        connection1.commit()

        queue.rpush(LOGGING_Q, f"[{datetime.datetime.now()}] added {count} {item}s in station {station_num} completed and the current count is {item_count + count}")

        resp = jsonify("request processed")
        resp.status_code = 200
        return resp
    
    except Exception as exception:
        resp = jsonify(f"couldn't process the request - {str(exception)}")
        resp.status_code = 400
        return resp

@app.route("/request/<int:station_num>/<string:item>/<int:count>", methods=["GET"])
def get_item(station_num, item, count):
    """Fetches the item from the pantry of the given station"""
    log.debug(f"[{datetime.datetime.now()}] Recieved request for {request.url} with data {(station_num, item, count)}")
    if station_num not in [1, 2, 3]:
        return jsonify("wrong station number!")
    try:
        cursor = connection1.cursor()
        if station_num == 2:
            cursor = connection2.cursor()
        elif station_num == 3:
            cursor = connection3.cursor()
    except:
        return jsonify("not connected to db")
    
    sql = f"SELECT count FROM pantry WHERE name = '{item}'"
    try:
        print(sql)
        cursor.execute(sql)
        result = cursor.fetchone()

        if not result:
            resp = jsonify("the requested item doesn't exist in the pantry")
            resp.status_code = 404
            return resp

        print(result[0])
        
    
        item_count = result[0]
        if count > item_count or item_count < THRESHOLD_COUNT:
            resp = jsonify("can't process the request - more items are requested than available")
            resp.status_code = 200
            return resp
        
        sql = f"UPDATE pantry SET count = {item_count - count} WHERE name = '{item}'"
        cursor.execute(sql)
        connection1.commit()
        
        queue.rpush(LOGGING_Q, f"[{datetime.datetime.now()}] request for {count} {item}s in station {station_num} completed and the current count is {item_count - count}")

        if item_count - count < THRESHOLD_COUNT:
            queue.rpush(LOGGING_Q, f"[{datetime.datetime.now()}] self-requested for {THRESHOLD_COUNT - item_count + count} {item}s in station {station_num} as it went lesser than threshold")
            queue.rpush(REQUEST_Q, f"{station_num},{item},{THRESHOLD_COUNT - item_count + count}")

        resp = jsonify("request processed")
        resp.status_code = 200
        # log.debug(f"[{datetime.datetime.now()}] Successfully completed request {request.url}")
        return resp
    
    except Exception as exception:
        resp = jsonify(f"couldn't process the request - {str(exception)}")
        resp.status_code = 400
        return resp
    
      
if __name__ == "__main__":

    try:
        cur1 = connection1.cursor()
        cur2 = connection2.cursor()
        cur3 = connection3.cursor()
    except:
        Exception("Couldn't connect to the station DBs")

    app.run(host="0.0.0.0", port=5000)
