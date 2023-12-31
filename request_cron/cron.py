import json
import os
from redis import Redis
import uuid
import logging
import datetime
import requests
from pymongo import MongoClient

log = logging.getLogger('werkzeug')
log.setLevel(logging.DEBUG)

# envs
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Flask store servers
F_STORE_PORT = os.getenv("F_STORE_PORT", "3000")
F_STORE_HOST = os.getenv("F_STORE_HOST", "localhost")

# DB_A_HOST = os.getenv("DB_A_HOST", "localhost")
# DB_USERNAME = os.getenv("DB_USERNAME", "root")
# DB_PASSWORD = os.getenv("DB_PASSWORD", "rootpass")

REQUEST_Q = "request"
LOGGING_Q = "logging"
RESTOCK_Q = "restock"


AUDIT_HOST = os.getenv("AUDIT_HOST", "localhost")

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
    queue.rpush(LOGGING_Q, f"[{datetime.datetime.now()}] - cron - Fetched requests from request queue")
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
            queue.rpush(LOGGING_Q, f"[{datetime.datetime.now()}] - cron - The store isn't able to satisfy the given request")
    return order_stores

def fetch_items_from_all_stores():
    addr = f"http://{F_STORE_HOST}:{F_STORE_PORT}"
    url = addr + f"/items"
    response = requests.get(url)
    if response.ok:
        printDebugOutput(response)
    else:
        queue.rpush(LOGGING_Q, f"[{datetime.datetime.now()}] - cron - Some error occurred while fetching items from all stores and message: {response.text}")
        return json.loads(f"Error while fetching items from all store DBs with message: {response.text}")
    return json.loads(response.text)
    
def process_requests(data, req_dict):
    # Do cost optimization orders here and place on store DB's
    # the final order sent to process_req must have unique items only
    orders = []
    for item, qty in req_dict.items():
        orders.append((item, qty))
    optimized_order = optimize_order(data, orders)
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
                queue.rpush(LOGGING_Q, f"[{datetime.datetime.now()}] - cron - Some error occurred while placing order to stores with status code: {response.status_code} and with text: {response.text}")
                return json.loads(f"Error occurred while placing order to stores with status code: {response.status_code} and with text: {response.text}")
    return order_bills

def gen_uuid():
    return uuid.uuid4()

def add_final_order_onto_audit_db(order_bills):
    # Add the final order obtained with price onto audit DB
    for k, v in order_bills.items():
        if v!=[]:
            items, total = v
            order_uuid = gen_uuid()
            doc1 = {
                "id": order_uuid,
                "timestamp": str(datetime.datetime.now()),
                "store": int(k), 
                "items": items,
                "total": float(total)
            }
            db["orders"].insert_one(doc1)
            
            docs = []
            
            for i in items:
                docs.append({
                    "id": gen_uuid(),
                    "timestamp": str(datetime.datetime.now()),
                    "order_id": order_uuid,
                    "name": str(i[0]),
                    "price": float(i[2]),
                    "quantity": int(i[1]),
                    "total_price": float(i[3])
                })
            db["order_items"].insert_many(docs)

    queue.rpush(LOGGING_Q, f"[{datetime.datetime.now()}] - cron - Added orders onto audit DB - successful!")

def send_satisfied_req_on_q(full_reqs):
    # Send the final order back on the q, for restock worker to handle
    for req in full_reqs:
        queue.rpush(LOGGING_Q, f"[{datetime.datetime.now()}] - cron - Sending full request back to C4C server on restock queue")
        queue.rpush(RESTOCK_Q, ", ".join(req))

def cron_job():
    full_reqs, req_dict = fetch_requests()
    store_inventory = fetch_items_from_all_stores()
    if "Error" in store_inventory:
        return "Error occurred when fetching items from all stores"
    # format of final order: [[], [], []] each list inside the big list is the order for that store with the index of the list
    final_order = process_requests(store_inventory, req_dict)

    order_bills = place_order_on_stores(final_order)
    exc = add_final_order_onto_audit_db(order_bills)
    if exc:
        queue.rpush(LOGGING_Q, f"[{datetime.datetime.now()}] - cron - Exception occurred while adding final order details onto audit DB with message: {exc}")
        return
    send_satisfied_req_on_q(full_reqs)

if __name__ == "__main__":
    client = MongoClient(AUDIT_HOST, 27017, uuidRepresentation = 'standard')
    db = client['order_audit']
    
    queue.rpush(LOGGING_Q, f"[{datetime.datetime.now()}] - cron - Cron job started")
    cron_job()
    queue.rpush(LOGGING_Q, f"[{datetime.datetime.now()}] - cron - Cron job ended")