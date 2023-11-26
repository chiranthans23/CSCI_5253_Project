import sys
import os
import redis

redisHost = os.getenv("REDIS_HOST", "localhost")
redisPort = int(os.getenv("REDIS_PORT", "6379"))

redisClient = redis.Redis(host=redisHost, port=redisPort, decode_responses=True)

while True:
    try:
        work = redisClient.blpop("logging", timeout=0)
        print(work[1])
    except Exception as exp:
        print(f"Exception raised in log loop: {str(exp)}")
    sys.stdout.flush()
    sys.stderr.flush()