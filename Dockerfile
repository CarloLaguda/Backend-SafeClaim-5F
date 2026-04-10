# Usa un'immagine Python ufficiale leggera (Alpine è la più piccola)
FROM python:3.11-alpine

# Imposta la directory di lavoro nel container
WORKDIR /app

# Copia il file requirements.txt
COPY requirements.txt .

# Installa le dipendenze Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia tutto il codice del progetto nel container
COPY . .

# Espone la porta 5000 (quella usata da Flask)
EXPOSE 5000

# Imposta variabili d'ambiente per Flask
ENV FLASK_APP=API_Automobilista.py
ENV FLASK_ENV=production

# Comando di avvio dell'applicazione
CMD ["python", "API_Automobilista.py"]
