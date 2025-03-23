FROM python:3.12-slim

RUN pip install flask mysql-connector-python

COPY app.py /app/app.py

WORKDIR /app

CMD ["python", "app.py"]
