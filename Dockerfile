# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Prevent Python from buffering stdout/stderr (helpful for logs)
ENV PYTHONUNBUFFERED=1

# Set working dir
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your project code
COPY . .

# Expose Django’s default port
EXPOSE 8000

# Default command: run Gunicorn
CMD ["gunicorn", "djangotutorial.wsgi:application", \
     "--bind", "0.0.0.0:8000", "--workers", "3"]
