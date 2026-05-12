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

COPY endpoint_5F_Mail.py .

EXPOSE 11000

CMD ["python", "endpoint_5F_Mail.py"]