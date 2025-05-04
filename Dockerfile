FROM python:3.13-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ergani_parameters.db .
COPY main.py .


# Expose the port the app runs on
EXPOSE 8040

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8040"]