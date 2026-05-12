FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    flask \
    flask-cors \
    pymongo[srv] \
    dnspython \
    mysql-connector-python \
    cloudinary \
    google-genai \
    requests \
    python-dotenv

COPY endpoint_5F_Sinistri_User.py .
COPY Storage.py .

EXPOSE 7000

CMD ["python", "endpoint_5F_Sinistri_User.py"]