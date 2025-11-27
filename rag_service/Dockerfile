FROM python:3.11-slim

# 設置工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 複製 requirements
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用代碼
COPY . .

# 暴露端口（會被 docker-compose override）
EXPOSE 8000 8001

# 默認命令（會被 docker-compose override）
CMD ["uvicorn", "public_service:app", "--host", "0.0.0.0", "--port", "8000"]
