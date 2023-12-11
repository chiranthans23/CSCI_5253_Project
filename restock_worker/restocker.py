import sys
import os
import redis
import requests 
import datetime
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.DEBUG)

redisHost = os.getenv("REDIS_HOST", "localhost")
redisPort = int(os.getenv("REDIS_PORT", "6379"))
requestHost =  os.getenv("REQUEST_HOST", "localhost")
requestPort =  int(os.getenv("REQUEST_PORT", "5000"))

redisClient = redis.Redis(host=redisHost, port=redisPort, decode_responses=True)

LOGGING_QUEUE = "logging"
RESTOCK_QUEUE = "restock"

def place_request(station, item, count):
    URL = f"http://{requestHost}:{requestPort}"
    request_url = f"{URL}/add/{station}/{item}/{count}"
    resp = requests.post(request_url)

    if resp.status_code == 200:
        redisClient.rpush(LOGGING_QUEUE, f"[{datetime.datetime.now()}] Restocked {count} {item}s in station {station} completed")
    else:
        redisClient.rpush(LOGGING_QUEUE, f"[{datetime.datetime.now()}] Couldn't complete restocking {count} {item}s in station {station}")
        log.debug(f"[{datetime.datetime.now()}] Couldn't complete restocking {count} {item}s in station {station} - {resp.text}")
    return

while True:
    try:
        req = redisClient.blpop(RESTOCK_QUEUE, timeout=0)
        req = req[1]
        print(f"Got {req}")
        if len(req.split(", ")) != 3:
            continue
        r = req.split(", ")
        sta, item, cnt = r[0], r[1], r[2]
        place_request(sta, item, cnt)

    except Exception as exp:
        print(f"Exception raised in restock loop: {str(exp)}")
    sys.stdout.flush()
    sys.stderr.flush()