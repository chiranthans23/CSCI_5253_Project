#!/bin/sh

# station dbs
kubectl apply -f station_db/station_secrets.yaml
kubectl apply -f station_db/station_service.yaml
kubectl apply -f station_db/station_deployment.yaml

# for initializing dbs
# kubectl run -it --rm --image=mysql --restart=Never mysql-client -- mysql --host station-mysql --password=c4c_station_pass

# request queue
kubectl apply -f request_queue/request_queue_service.yaml
kubectl apply -f request_queue/request_queue_deployment.yaml

# DB
# CREATE DATABASE station_1;
# CREATE DATABASE station_2;
# CREATE DATABASE station_3;

# USE station_1;
# CREATE TABLE pantry(id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(255), count INT);
# INSERT INTO pantry(name, count) VALUES("apple", 10);

# USE station_2;
# CREATE TABLE pantry(id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(255), count INT);
# INSERT INTO pantry(name, count) VALUES("apple", 10);


# USE station_3;
# CREATE TABLE pantry(id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(255), count INT);
# INSERT INTO pantry(name, count) VALUES("apple", 10);
