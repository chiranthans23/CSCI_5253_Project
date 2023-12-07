import json
import os
from flask import jsonify, Flask, request
from mysql.connector import Error
import mysql.connector
from redis import Redis
import logging
import datetime
import time
import atexit
import requests

# envs
log = logging.getLogger('werkzeug')
log.setLevel(logging.DEBUG)

# envs
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
DB1_HOST = os.getenv("DB1_HOST", "localhost")
DB2_HOST = os.getenv("DB2_HOST", "localhost")
DB3_HOST = os.getenv("DB3_HOST", "localhost")
DB_USERNAME = os.getenv("DB_USERNAME", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "rootpass")
STORE_1 = os.getenv("STORE_1", "store_1")
STORE_2 = os.getenv("STORE_2", "store_2")
STORE_3 = os.getenv("STORE_3", "store_3")
REQUEST_Q = "request"
LOGGING_Q = "logging"
THRESHOLD_COUNT = 10

app = Flask(__name__)

# Creating and initializing store DB's
try: 
    connection1 = mysql.connector.connect(
        host = DB1_HOST,
        user = DB_USERNAME,
        password = DB_PASSWORD,
        database = STORE_1,
        # port = 3305
        )
except:
    connection1 = mysql.connector.connect(
        host = DB1_HOST,
        user = DB_USERNAME,
        password = DB_PASSWORD,
        # port = 3305
        )
    cur = connection1.cursor()
    cur.execute("CREATE DATABASE store_1")
    connection1 = mysql.connector.connect(
        host = DB1_HOST,
        user = DB_USERNAME,
        password = DB_PASSWORD,
        database = STORE_1,
        # port = 3305
        )
    cur = connection1.cursor()
    cur.execute("CREATE TABLE store(id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(255), quantity INT, price float);")
    cur.execute('INSERT INTO store(name, quantity, price) VALUES("apple", 10, 9.18);')
    connection1.commit()
    cur.execute('INSERT INTO store(name, quantity, price) VALUES("banana", 1, 5);')
    connection1.commit()
    cur.execute('INSERT INTO store(name, quantity, price) VALUES("mango", 3, 2.35);')
    connection1.commit()

try: 
    connection2 = mysql.connector.connect(
        host = DB2_HOST,
        user = DB_USERNAME,
        password = DB_PASSWORD,
        database = STORE_2,
        # port = 4305
        )
except:
    connection2 = mysql.connector.connect(
        host = DB2_HOST,
        user = DB_USERNAME,
        password = DB_PASSWORD,
        # port = 4305
        )
    cur = connection2.cursor()
    cur.execute("CREATE DATABASE store_2")
    connection2 = mysql.connector.connect(
        host = DB2_HOST,
        user = DB_USERNAME,
        password = DB_PASSWORD,
        database = STORE_2,
        # port = 4305
        )
    cur = connection2.cursor()
    cur.execute("CREATE TABLE store(id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(255), quantity INT, price float);")
    cur.execute('INSERT INTO store(name, quantity, price) VALUES("orange", 10, 8);')
    connection2.commit()
    cur.execute('INSERT INTO store(name, quantity, price) VALUES("milk", 1, 15);')
    connection2.commit()
    cur.execute('INSERT INTO store(name, quantity, price) VALUES("eggs", 3, 2);')
    connection2.commit()

try: 
    connection3 = mysql.connector.connect(
        host = DB3_HOST,
        user = DB_USERNAME,
        password = DB_PASSWORD,
        database = STORE_3,
        # port = 5305
        )
except:
    connection3 = mysql.connector.connect(
        host = DB3_HOST,
        user = DB_USERNAME,
        password = DB_PASSWORD,
        # port = 5305
        )
    cur = connection3.cursor()
    cur.execute("CREATE DATABASE store_3")
    connection3 = mysql.connector.connect(
        host = DB3_HOST,
        user = DB_USERNAME,
        password = DB_PASSWORD,
        database = STORE_3,
        # port = 5305
        )
    cur = connection3.cursor()
    cur.execute("CREATE TABLE store(id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(255), quantity INT, price float);")
    cur.execute('INSERT INTO store(name, quantity, price) VALUES("eggs", 10, 3.80);')
    connection3.commit()
    cur.execute('INSERT INTO store(name, quantity, price) VALUES("apples", 15, 4.23);')
    connection3.commit()
    cur.execute('INSERT INTO store(name, quantity, price) VALUES("cereal", 3, 5.12);')
    connection3.commit()

def printDebugOutput(response):
    s = response.text
    try:
        j = json.loads(s)
        print("Response is", response)
        print(j)
    except json.JSONDecodeError:
        return response

@app.route("/items", methods=["GET"])
def fetch_all_items():
    store_invtry = []
    sql = "SELECT * from store"
    # store fmt: id, item, qty, price
    store_s = "store_1"
    try:
        cursor = connection1.cursor()
    except:
        return f"Could not connect to {store_s}"
    
    try:
        cursor.execute(sql)
        result = cursor.fetchall()
        print(f"result from {store_s}")
        print(result)
        if result and len(result)>0:
            for rec in result:
                lt = list(rec)
                lt[0] = store_s
                store_invtry.append(tuple(lt))

    except Exception as e:
        return f"Exception occurred while fetching items from {store_s}: {str(e)}"
    
    store_s = "store_2"
    try:
        cursor = connection2.cursor()
    except:
        return f"Could not connect to {store_s}"
    
    try:
        cursor.execute(sql)
        result = cursor.fetchall()
        print(f"result from {store_s}")
        print(result)
        if result and len(result)>0:
            for rec in result:
                lt = list(rec)
                lt[0] = store_s
                store_invtry.append(tuple(lt))

    except Exception as e:
        return f"Exception occurred while fetching items from {store_s}: {str(e)}"

    store_s = "store_3"    
    try:
        cursor = connection3.cursor()
    except:
        return f"Could not connect to {store_s}"
    
    try:
        cursor.execute(sql)
        result = cursor.fetchall()
        print(f"result from {store_s}")
        print(result)
        if result and len(result)>0:
            for rec in result:
                lt = list(rec)
                lt[0] = store_s
                store_invtry.append(tuple(lt))

    except Exception as e:
        return f"Exception occurred while fetching items from {store_s}: {str(e)}"
    print(store_invtry)
    return jsonify(store_invtry)

@app.route("/order/<int:store_num>", methods=["POST"])
def order_items(store_num):
    """ Places the order to the specified store"""
    order_json = request.get_json()
    # example format: {'apples': 10, 'banana': 20}
    print(order_json)
    order_list = json.loads(order_json)
    order_bill = []
    order_total = 0.0
    if store_num not in [1, 2, 3]:
        return jsonify("wrong store number!")
    
    try:
        cursor = connection1.cursor()
        if store_num == 2:
            cursor = connection2.cursor()
        elif store_num == 3:
            cursor = connection3.cursor()
    except:
        return jsonify("not connected to db")
    
    for item, qty in order_list:

        sql = f"SELECT quantity, price FROM store WHERE name = '{item}'"
        try:
            print(sql)
            cursor.execute(sql)
            result = cursor.fetchone()

            if not result:
                print(item, qty)
                resp = jsonify("the requested item doesn't exist in the store")
                resp.status_code = 404
                return resp

            print(result[0])
            item_qty = result[0]
            item_qty_to_set = item_qty - qty
            if item_qty - qty < THRESHOLD_COUNT:
                item_qty_to_set = THRESHOLD_COUNT
            sql = f"UPDATE store SET quantity = {item_qty_to_set} WHERE name = '{item}'"
            cursor.execute(sql)
            connection1.commit()

            price = result[1]
            order_total+=(qty*price)
            order_bill.append((item, qty, price, qty*price))
        
        except Exception as exception:
            resp = jsonify(f"couldn't process the request - {str(exception)}")
            resp.status_code = 400
            return resp

    resp = jsonify({
        "status": "request processed",
        "order_total": order_total,
        "order_bill": order_bill
    })

    resp.status_code = 200
    return resp
    
if __name__ == "__main__":
    try:
        cur1 = connection1.cursor()
        cur2 = connection2.cursor()
        cur3 = connection3.cursor()
    except:
        Exception("Couldn't connect to the station DBs")
    app.run(host="0.0.0.0", port=3000)

