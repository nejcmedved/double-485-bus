FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY modbus_bridge.py .

# Expose the TCP server port
EXPOSE 5020

# Run the application
CMD ["python", "-u", "modbus_bridge.py"]
