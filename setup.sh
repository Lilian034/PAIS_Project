#!/bin/bash

echo “================================”
echo “PAIS 系統快速部署腳本”
echo “================================”
echo “”

# 檢查 Docker
if ! command -v docker &> /dev/null; then
echo “錯誤: Docker 未安裝”
echo “請先安裝 Docker Desktop: https://www.docker.com/products/docker-desktop”
exit 1
fi

echo “Docker 已安裝”
docker –version
echo “”

# 檢查 docker-compose
if ! command -v docker-compose &> /dev/null; then
echo “錯誤: docker-compose 未安裝”
exit 1
fi

echo “docker-compose 已安裝”
docker-compose –version
echo “”

# 檢查 .env 檔案
if [ ! -f .env ]; then
echo “.env 檔案不存在，從範本複製…”
cp .env.example .env
echo “請編輯 .env 檔案，填入你的 GEMINI_API_KEY”
echo “”
read -p “按 Enter 繼續（確保已填入 API Key）…”
fi

# 建立必要資料夾
echo “建立資料夾結構…”
mkdir -p documents
mkdir -p chat_history
mkdir -p generated_content
mkdir -p logs
mkdir -p qdrant_storage
mkdir -p frontend
echo “資料夾建立完成”
echo “”

# 檢查前端檔案
if [ ! -f frontend/index.html ]; then
echo “前端檔案不存在於 frontend/ 資料夾”
echo “請將你的 HTML/CSS/JS 檔案放入 frontend/ 資料夾”
exit 1
fi

# 建立 Docker 容器
echo “開始建立 Docker 容器…”
docker-compose build

if [ $? -ne 0 ]; then
echo “建立失敗”
exit 1
fi

echo “容器建立完成”
echo “”

# 啟動服務

echo “啟動所有服務…”
docker-compose up -d

if [ $? -ne 0 ]; then
echo “啟動失敗”
exit 1
fi

echo “”
echo “================================”
echo “部署完成！”
echo “================================”
echo “”
echo “服務狀態:”
docker-compose ps
echo “”
echo “訪問以下網址:”
echo “  - 前端頁面: http://localhost”
echo “  - API 文件: http://localhost:8000/docs”
echo “  - Qdrant Dashboard: http://localhost:6333/dashboard”
echo “  - n8n: http://localhost:5678”
echo “”
echo “下一步:”
echo “  1. 將文件放入 documents/ 資料夾”
echo “  2. 執行: curl -X POST http://localhost:8000/api/ingest -H ‘Content-Type: application/json’ -d ‘{"folder_path":"documents"}’”
echo “  3. 開始使用聊天功能！”
echo “”
echo “查看日誌: docker-compose logs -f”
echo “⏹停止服務: docker-compose down”
echo “”