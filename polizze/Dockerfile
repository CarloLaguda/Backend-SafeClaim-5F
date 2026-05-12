FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    flask \
    flask-cors \
    pymongo[srv] \
    dnspython \
    mysql-connector-python \
    requests \
    python-dotenv

COPY endpoint_5F_Polizze.py .

EXPOSE 9000

CMD ["python", "endpoint_5F_Polizze.py"]