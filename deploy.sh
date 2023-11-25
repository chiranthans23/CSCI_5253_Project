#!/bin/sh

# station dbs
kubectl apply -f station_db/station_secrets.yaml
kubectl apply -f station_db/station_service.yaml
kubectl apply -f station_db/station_deployment.yaml

# for initializing dbs
# kubectl run -it --rm --image=mysql --restart=Never mysql-client -- mysql --host station-mysql --password=c4c_station_pass
