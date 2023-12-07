import json
from pprint import pprint
import os
from pytz import utc
from flask import jsonify
from redis import Redis
from mysql.connector import Error
import mysql.connector
import uuid
import logging
import datetime
import time
import atexit
import requests

from cassandra.cluster import Cluster
from cassandra.query import BatchStatement
from cassandra import ConsistencyLevel


from apscheduler.schedulers.background import BackgroundScheduler

log = logging.getLogger('werkzeug')
log.setLevel(logging.DEBUG)

# envs
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Flask store servers
F_STORE_PORT = os.getenv("F_STORE_PORT", "3000")
F_STORE_HOST = os.getenv("F_STORE_HOST", "localhost")

DB_A_HOST = os.getenv("DB_A_HOST", "localhost")
DB_USERNAME = os.getenv("DB_USERNAME", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "rootpass")
AUDIT = os.getenv("AUDIT", "order_audit")
REQUEST_Q = "request"
LOGGING_Q = "logging"
RESTOCK_Q = "restock"

queue = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def printDebugOutput(response):
    s = response.text
    try:
        j = json.loads(s)
        print("Response is", response)
        print(j)
    except json.JSONDecodeError:
        return response
    
def fetch_requests():
    # Fetch reqs from req queue 
    # req fmt: station_num, item, item_req_cnt
    req_dict = {}
    station_reqs = []
    while queue.llen(REQUEST_Q) > 0:
        r = [i.strip() for i in queue.lpop(REQUEST_Q).split(",")]
        station, item, count = int(r[0]), r[1].lower(), int(r[2])
        if item in req_dict:
            req_dict[item]+=count
        else:
            req_dict[item] = count
        station_reqs.append(r)
    print("station_reqs, req_dict")
    print(station_reqs, req_dict)
    return station_reqs, req_dict

def optimize_order(data, orders):
    # Create a dictionary to store the optimized order - Example format given below
    # data = [('store_1', 'apple', 10, 9.08), ('store_1', 'banana', 10, 5.0), ('store_2', 'orange', 10, 8.0), 
    #         ('store_2', 'milk', 1, 15.0), ('store_3', 'eggs', 10, 3.8), ('store_3', 'apples', 10, 3.8), 
    #         ('store_3', 'cereal', 1, 2.5)]

    # orders = [("apples", 10), ("banana", 6)]
    stores_len = 3
    stores_map = {"store_1": 0, "store_2": 1, "store_3": 2}
    order_stores = [[] for i in range(stores_len)]

    for item, quantity_requested in orders:
        if any(entry[1] == item for entry in data):
            # Filter stores that have the requested item in their inventory
            available_stores = [entry for entry in data if entry[1] == item]
            available_stores.sort(key=lambda x: x[3])
            for entry in available_stores:
                store, _, quantity_available, cost = entry
                if quantity_requested <= quantity_available:
                    order_stores[stores_map[store]].append((item, quantity_requested))
                    quantity_requested-=quantity_requested
                    break
                else:
                    order_stores[stores_map[store]].append((item, quantity_available))
                    quantity_requested-=quantity_available
        if quantity_requested != 0:
            print("The store isnt able to satisfy the given request.")

    return order_stores

def fetch_items_from_all_stores():
    addr = f"http://{F_STORE_HOST}:{F_STORE_PORT}"
    url = addr + f"/items"
    response = requests.get(url)
    print(response, type(response))
    if response.ok:
        printDebugOutput(response)
    else:
        return "Some error occurred in fetch_items_from_all_stores"
    return json.loads(response.text)
    
def process_requests(data, req_dict):
    # Do cost optimization orders here and place on store DB's
    # the final order sent to process_req must have unique items only
    orders = []
    for item, qty in req_dict.items():
        orders.append((item, qty))
    print("orders")
    print(orders)
    optimized_order = optimize_order(data, orders)
    print("optimized_order")
    print(optimized_order)
    return optimized_order

def place_order_on_stores(order_stores):    
    addr = f"http://{F_STORE_HOST}:{F_STORE_PORT}"
    order_bills = {}
    order_bills["1"] = []
    order_bills["2"] = []
    order_bills["3"] = []
    for store_num, order in enumerate(order_stores):
        if len(order)!=0:
            url = addr + f"/order/{store_num+1}"
            response = requests.post(url, json=json.dumps(order))
            if response.ok:
                printDebugOutput(response)
                resp = json.loads(response.text)
                order_bills[str(store_num+1)] = (resp["order_bill"], resp["order_total"])
            else:
                print(response.status_code, response.text)
                print("Some error occurred on place_order_on_stores")
    return order_bills

def gen_uuid():
    return uuid.uuid4()

def add_final_order_onto_audit_db(order_bills):
    # Add the final order obtained with price onto audit DB
    for k, v in order_bills.items():
        if v!=[]:
            items, total = v
            order_uuid = gen_uuid()
            print(v)
            stmt = session.prepare("INSERT INTO orders(id, timestamp, store, items, total) values (?,?,?,?,?)")
            try:
                res = session.execute(stmt, [order_uuid, datetime.datetime.now(), int(k), items, float(total)])
            except Exception as e:
                return f"Exception occurred on add_final_order_onto_audit_db - orders insert: {str(e)}"
            
            insert_item = session.prepare("INSERT INTO order_items(id, timestamp, order_id, name, price, quantity, total_price) VALUES (?, ?, ?, ?, ?, ?, ?)")
            batch = BatchStatement(consistency_level=ConsistencyLevel.QUORUM)
            for i in items:
                batch.add(insert_item, (gen_uuid(), datetime.datetime.now(), order_uuid, str(i[0]), float(i[2]), int(i[1]), float(i[3])))
            try:
                res = session.execute(batch)
            except Exception as e:
                return f"Exception occurred on add_final_order_onto_audit_db - order_items insert: {str(e)}"
    print("Added orders onto audit DB - successful!")

def send_satisfied_req_on_q(full_reqs):
    # Send the final order back on the q, for restock worker to handle
    for req in full_reqs:
        queue.rpush(RESTOCK_Q, ", ".join(req))

def cron_job():
    full_reqs, req_dict = fetch_requests()
    store_inventory = fetch_items_from_all_stores()
    # format of final order: [[], [], []] each list inside the big list is the order for that store with the index of the list
    final_order = process_requests(store_inventory, req_dict)

    order_bills = place_order_on_stores(final_order)
    print(order_bills)
    exc = add_final_order_onto_audit_db(order_bills)
    if exc:
        print("\n\nEXCEPTION OCCURRED on audit_db")
        print(exc)
    send_satisfied_req_on_q(full_reqs)

if __name__ == "__main__":
    cluster = Cluster(['0.0.0.0'],port=9042)
    session = cluster.connect('order_audit',wait_for_all_pools=True)
    session.execute('USE order_audit')
    # cron_job()
    scheduler = BackgroundScheduler()
    print("STARTED JOB  - cron\n\n")
    scheduler.configure(timezone=utc)
    logging.getLogger("apscheduler.scheduler").setLevel(logging.DEBUG)
    scheduler.add_job(func=cron_job, trigger="interval", seconds=60)
    scheduler.start()

    print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))

    try:
        # This is here to simulate application activity (which keeps the main thread alive).
        while True:
            time.sleep(5)
    except (KeyboardInterrupt, SystemExit):
        # Not strictly necessary if daemonic mode is enabled but should be done if possible
        scheduler.shutdown()
    