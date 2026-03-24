FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY frontend/package*.json ./frontend/
RUN cd frontend && npm install && cd ..

COPY backend ./backend
COPY frontend/src ./frontend/src
COPY frontend/public ./frontend/public
COPY frontend/index.html ./frontend/index.html
COPY frontend/vite.config.ts ./frontend/vite.config.ts
COPY frontend/tsconfig*.json ./frontend/tsconfig.json
COPY frontend/.env* ./frontend/

ENV PYTHONUNBUFFERED=1
ENV BACKEND_PORT=8001
ENV FRONTEND_PORT=3008

EXPOSE $BACKEND_PORT $FRONTEND_PORT

CMD ["bash", "deploy/scripts/start.sh"]
