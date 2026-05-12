FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    flask \
    flask-cors \
    scikit-learn \
    numpy \
    google-genai \
    requests \
    python-dotenv

COPY endpoint_5F_RAG_Assistente.py .

EXPOSE 12000

CMD ["python", "endpoint_5F_RAG_Assistente.py"]