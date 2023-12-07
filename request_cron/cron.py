import json
import os
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


from apscheduler.schedulers.background import BackgroundScheduler

log = logging.getLogger('werkzeug')
log.setLevel(logging.DEBUG)

# envs
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
DB_A_HOST = os.getenv("DB_A_HOST", "localhost")
DB_USERNAME = os.getenv("DB_USERNAME", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "rootpass")
AUDIT = os.getenv("AUDIT", "order_audit")
REQUEST_Q = "request"
LOGGING_Q = "logging"

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
    print("station_reqs, req_dict")
    print(station_reqs, req_dict)
    return station_reqs, req_dict
    
# data = [('store_1', 'apple', 10, 9.08), ('store_1', 'banana', 10, 5.0), ('store_2', 'orange', 10, 8.0), 
#         ('store_2', 'milk', 1, 15.0), ('store_3', 'eggs', 10, 3.8), ('store_3', 'apples', 10, 3.8), 
#         ('store_3', 'cereal', 1, 2.5)]

# orders = [("apples", 10), ("banana", 6)]

def optimize_order(data, orders):
    # Create a dictionary to store the optimized order
    stores_len = 3
    stores_map = {"store_1": 0, "store_2": 1, "store_3": 2}
    order_stores = [[] for i in range(stores_len)]

    # Iterate through each order
    for item, quantity_requested in orders:
        # Check if the item is available in the data
        if any(entry[1] == item for entry in data):
            # Filter stores that have the requested item in their inventory
            available_stores = [entry for entry in data if entry[1] == item]

            # Sort stores based on cost per item
            available_stores.sort(key=lambda x: x[3])

            # Iterate through available stores to find the lowest cost
            for entry in available_stores:
                store, _, quantity_available, cost = entry

                # Check if the store has enough quantity
                if quantity_requested <= quantity_available:
                    # Update the optimized order
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
    host = "localhost"
    port = 3000
    addr = f"http://{host}:{port}"
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
    # pass

def place_order_on_stores(order_stores):    
    host = "localhost"
    store_port = 3000
    addr = f"http://{host}:{store_port}"
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
    return uuid.UUID()

def add_final_order_onto_audit_db(order_bills):
    # Add the final order obtained with price onto audit DB
    
    # cur.execute("create table orders(id INT PRIMARY KEY AUTO_INCREMENT, store VARCHAR(25), total float);")
    # cur.execute('create table order_items(id INT PRIMARY KEY AUTO_INCREMENT, order_id int, item varchar(255), quantity int, price float, total_price float, FOREIGN KEY (order_id) REFERENCES orders(id));')
    # for 
    # stmt = session.prepare("
    #     INSERT INTO orders (rowkey, qualifier, info, act_date, log_time)
    #     VALUES (?, ?, ?, ?, ?)
    #     IF NOT EXISTS
    #     ")
    # results = session.execute(stmt, [arg1, arg2, ...])
    pass
    for k, v in order_bills.items():
        if v!=[]:
            items, total = v
            stmt = session.prepare("INSERT INTO orders(id, store, items, total) values ({}, {}, {}, {})")
            stmt = "BEGIN BATCH"
            # stmt += "APPLY BATCH"
            for i in items:
                stmt += f"INSERT INTO order_items(id, order_id, )"




    

def send_satisfied_req_on_q():
    pass
    # Send the final order back on the q, for restock worker to handle

def cron_job():
    full_reqs, req_dict = fetch_requests()
    store_inventory = fetch_items_from_all_stores()
    final_order = process_requests(store_inventory, req_dict)
    # format of final order: [[], [], []] each list inside the big list is the order for that store with the index of the list
    order_bills = place_order_on_stores(final_order)
    print(order_bills)
    add_final_order_onto_audit_db(order_bills)
    # send_satisfied_req_on_q(final_order, full_reqs)


      
if __name__ == "__main__":
    cron_job()
    cluster = Cluster(['0.0.0.0'],port=9042)
    session = cluster.connect('order_audit',wait_for_all_pools=True)
    session.execute('USE order_audit')
    # rows = session.execute('SELECT * FROM orders')
    # for row in rows:
    #     print(row.id,row.total,row.items, row.store)
    # try:
    #     cur1 = connection1.cursor()
    #     cur2 = connection2.cursor()
    #     cur3 = connection3.cursor()
    # except:
    #     Exception("Couldn't connect to the station DBs")







# scheduler = BackgroundScheduler()
# scheduler.add_job(func=print_date_time, trigger="interval", seconds=60)
# scheduler.start()

# # Shut down the scheduler when exiting the app
# atexit.register(lambda: scheduler.shutdown())