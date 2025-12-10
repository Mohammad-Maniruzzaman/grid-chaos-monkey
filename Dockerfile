# 1. Base Image: Official lightweight Python
FROM python:3.10-slim

# 2. Work Directory inside the container
WORKDIR /app

# 3. Copy dependencies and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy the rest of the app
COPY . .

# 5. Open the port
EXPOSE 8000

# 6. Run the API
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]