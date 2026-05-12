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

COPY endpoint_5F_log_reg.py .

EXPOSE 6000

CMD ["python", "endpoint_5F_log_reg.py"]