#!/bin/sh

# station dbs
kubectl apply -f station_db/station_secrets.yaml
kubectl apply -f station_db/station_service.yaml
kubectl apply -f station_db/station_deployment.yaml


# for initializing dbs
# kubectl run -it --rm --image=mysql --restart=Never mysql-client -- mysql --host station-mysql1 --password=c4c_station_pass
# DB
# CREATE DATABASE station_1;
# CREATE DATABASE station_2;
# CREATE DATABASE station_3;

# USE station_1;
# CREATE TABLE pantry(id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(255), count INT);
# INSERT INTO pantry(name, count) VALUES("apple", 10);
# INSERT INTO pantry(name, count) VALUES("mango", 10);
# INSERT INTO pantry(name, count) VALUES("banana", 10);

# USE station_2;
# CREATE TABLE pantry(id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(255), count INT);
# INSERT INTO pantry(name, count) VALUES("apple", 10);
# INSERT INTO pantry(name, count) VALUES("mango", 10);
# INSERT INTO pantry(name, count) VALUES("banana", 10);


# USE station_3;
# CREATE TABLE pantry(id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(255), count INT);
# INSERT INTO pantry(name, count) VALUES("apple", 10);
# INSERT INTO pantry(name, count) VALUES("mango", 10);
# INSERT INTO pantry(name, count) VALUES("banana", 10);




# request queue
kubectl apply -f request_queue/request_queue_service.yaml
kubectl apply -f request_queue/request_queue_deployment.yaml

sleep 4
# logger
kubectl apply -f logger/logger_deployment.yaml

# sleep 30
# # request server
# kubectl apply -f request_server/request_server_service.yaml
# kubectl apply -f request_server/request_server_deployment.yaml

# # store server
kubectl apply -f store_server/store_server_service.yaml
kubectl apply -f store_server/store_server_deployment.yaml


helm install audit-cas \
    --set dbUser.password=audit_pass \
    oci://REGISTRY_NAME/REPOSITORY_NAME/cassandra