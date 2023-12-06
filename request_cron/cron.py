import os
from flask import jsonify, Flask, request
from mysql.connector import Error
import mysql.connector
from redis import Redis
import logging
import datetime
import time
import atexit

from apscheduler.schedulers.background import BackgroundScheduler

log = logging.getLogger('werkzeug')
log.setLevel(logging.DEBUG)

# app = Flask(__name__)

# envs
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USERNAME = os.getenv("DB_USERNAME", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "rootpass")
STORE_1 = os.getenv("STORE_1", "store_1")
STORE_2 = os.getenv("STORE_2", "store_2")
STORE_3 = os.getenv("STORE_3", "store_3")
REQUEST_Q = "request"
LOGGING_Q = "logging"
# THRESHOLD_COUNT = 5

connection1 = mysql.connector.connect(
    host = DB_HOST,
    user = DB_USERNAME,
    password = DB_PASSWORD,
    database = STORE_1
    )

connection2 = mysql.connector.connect(
    host = DB_HOST,
    user = DB_USERNAME,
    password = DB_PASSWORD,
    database = STORE_2
    )

connection3 = mysql.connector.connect(
    host = DB_HOST,
    user = DB_USERNAME,
    password = DB_PASSWORD,
    database = STORE_3
    )


queue = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

print(connection1)

def fetch_requests():
    # Fetch reqs from req queue 
    # req fmt: station_num, item, item_req_cnt
    # queue.rpush(REQUEST_Q, "1, apples, 4")
    req_dict = {}
    station_reqs = []
    while queue.llen(REQUEST_Q) > 0:
        r = queue.lpop(REQUEST_Q).split(",")
        station, item, count = int(r[0]), r[1].strip().lower(), int(r[2])
        if item in req_dict:
            req_dict[item]+=count
        else:
            req_dict[item] = count
        station_reqs.append(r)
    print(station_reqs, req_dict)
    return station_reqs, req_dict
    # pass    

def process_requests(req_dict):
    # Do cost optimization orders here and place on store DB's
    # the final order sent to process_req must have unique items only
    data = fetch_items_from_all_stores()
    print(data)
    # pass

def fetch_items_from_all_stores():
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
        print(result)
        if result and len(result)>0:
            for rec in result:
                lt = list(rec)
                lt[0] = store_s
                store_invtry.append(tuple(lt))

    except Exception as e:
        return f"Exception occurred while fetching items from {store_s}: {str(e)}"
    print(store_invtry)
    return store_invtry



def add_final_order_onto_audit_db():
    # Add the final order obtained with price onto audit DB - cassandra
    pass

def send_satisfied_req_on_q():
    pass
    # Send the final order back on the q, for restock worker to handle


def cron_job():
    full_reqs, req_dict = fetch_requests()
    process_requests(req_dict)
      
if __name__ == "__main__":
    cron_job()
    # try:
    #     cur1 = connection1.cursor()
    #     cur2 = connection2.cursor()
    #     cur3 = connection3.cursor()
    # except:
    #     Exception("Couldn't connect to the station DBs")

    # app.run(host="0.0.0.0", port=5000)






# scheduler = BackgroundScheduler()
# scheduler.add_job(func=print_date_time, trigger="interval", seconds=60)
# scheduler.start()

# # Shut down the scheduler when exiting the app
# atexit.register(lambda: scheduler.shutdown())