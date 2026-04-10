# Use a lightweight official Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir flask flask-cors pymongo requests

# Copy application files
COPY Sinistro.py /app/

# Expose default Flask port
EXPOSE 5000

# Run the application
CMD ["python", "Sinistro.py"]
