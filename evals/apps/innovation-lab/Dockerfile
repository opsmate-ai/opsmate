FROM python:3.12-slim

COPY . /app

WORKDIR /app

RUN pip install flask mysql-connector-python

CMD ["python", "app.py"]
