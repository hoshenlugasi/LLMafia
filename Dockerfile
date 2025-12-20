# Production Dockerfile for Social Turing Test (Mafia Game)
# Python 3.11 slim base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy all application files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose Flask port
EXPOSE 5000

# Run with gunicorn using single worker to avoid file-based race conditions
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000", "web_player:app"]
