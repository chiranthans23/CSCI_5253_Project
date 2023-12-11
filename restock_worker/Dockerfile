FROM python:3.8-alpine

RUN  pip3 install redis requests
WORKDIR /srv
COPY    restocker.py /srv
CMD [ "python3", "restocker.py"]
