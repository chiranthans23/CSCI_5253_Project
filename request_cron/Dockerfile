FROM python:3.9-slim-buster
WORKDIR /app 
COPY requirements.txt .
RUN pip3 install -r requirements.txt
COPY *.py .
CMD [ "python3", "cron.py"]
