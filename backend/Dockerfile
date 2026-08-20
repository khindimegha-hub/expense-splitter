FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (better layer caching — only reinstalls if requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

EXPOSE 5000

# Use Flask's built-in server for simplicity (fine for a portfolio project;
# a production deployment would use gunicorn instead — see Day 9 note)
ENV FLASK_APP=run.py
CMD ["python", "run.py"]