# 1. Base Image
FROM python:3.10-slim

# 2. Work Directory
WORKDIR /app

# 3. Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy Code
COPY . .

# 5. Network
EXPOSE 8000

# 6. Run (UPDATED PATH)
# We now tell uvicorn to look inside the 'src' package for 'api'
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]