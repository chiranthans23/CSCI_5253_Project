FROM python:3.9-slim-buster
WORKDIR /app 
COPY requirements.txt .
RUN pip3 install -r requirements.txt
COPY *.py .
EXPOSE 5000
ENV FLASK_APP=rest.py
CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]
