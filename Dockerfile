# 1. Base Image
FROM python:3.10-slim

# 2. Work Directory
WORKDIR /app

# 3. System deps for scientific Python wheels/builds (numpy/scipy/numba/pandapower stack)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ gfortran \
    libopenblas-dev liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# 4. Python packaging tooling (prefer wheels; avoid legacy build failures)
RUN python -m pip install --upgrade pip setuptools wheel

# 5. Dependencies
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

# 6. Copy Code
COPY . .

# 7. Network
EXPOSE 8000

# 8. Run
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
