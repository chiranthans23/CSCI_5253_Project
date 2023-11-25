import os
from flask import jsonify, Flask
from mysql.connector import Error
import mysql.connector
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.DEBUG)

app = Flask(__name__)


connection1 = mysql.connector.connect(
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USERNAME", "root"),
    password=os.getenv("DB_PASSWORD", "c4c_station_pass"),
    database=os.getenv("STATION_1", "station_1")
    )

connection2 = mysql.connector.connect(
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USERNAME", "root"),
    password=os.getenv("DB_PASSWORD", "c4c_station_pass"),
    database=os.getenv("STATION_1", "station_2")
    )

connection3 = mysql.connector.connect(
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USERNAME", "root"),
    password=os.getenv("DB_PASSWORD", "c4c_station_pass"),
    database=os.getenv("STATION_1", "station_3")
    )


print(connection1)
@app.route("/")
def hello():
    """Function to test the functionality of the API"""
    return "Hello, world!"


@app.route("/request/<int:station_num>/<string:item>/<int:count>", methods=["GET"])
def get_item(station_num, item, count):
    """Fetches the item from the pantry of the given station"""
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
        if count > item_count:
            resp = jsonify("can't process the request - more items are requested than available")
            resp.status_code = 404
            return resp
        
        sql = f"UPDATE pantry SET count = {item_count - count} WHERE name = '{item}'"
        cursor.execute(sql)
        connection1.commit()
        
        resp = jsonify("request processed")
        resp.status_code = 200
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
