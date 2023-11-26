FROM python:3.8-alpine

RUN  pip3 install redis
WORKDIR /srv
COPY    logs.py /srv
CMD [ "python3", "logger.py"]
