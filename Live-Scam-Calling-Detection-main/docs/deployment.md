# Sentinel AI Deployment Guide

## 1. Local Desktop (Electron + Python Backend)

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Run backend API
python -m backend.app

# 3. Build & launch Electron app
cd frontend/electron
npm install
npm start
```

## 2. Docker Production Deployment

```bash
docker-compose up --build -d
```
