# Deploy Guide

## Directory Structure

```
deploy/
├── docker-compose.yml
├── Dockerfile
├── .dockerignore
├── scripts/
│   ├── mac/
│   │   ├── start.sh
│   │   └── stop.sh
│   ├── linux/
│   │   ├── start.sh
│   │   └── stop.sh
│   ├── windows/
│   │   ├── start.bat
│   │   └── stop.bat
│   └── docker/
│       ├── start.sh
│       └── stop.sh
└── README.md
```

## Usage

### 1. Native Deployment (No Docker)

#### Mac

```bash
cd deploy/scripts/mac
chmod +x *.sh
./start.sh      # Start services
./stop.sh       # Stop services
```

#### Linux

```bash
cd deploy/scripts/linux
chmod +x *.sh
./start.sh      # Start services
./stop.sh       # Stop services
```

#### Windows

```cmd
cd deploy\scripts\windows
start.bat       # Start services
stop.bat        # Stop services
```

### 2. Docker Deployment

#### All Platforms

```bash
cd deploy/scripts/docker
chmod +x *.sh
./start.sh      # Build and start containers
./stop.sh       # Stop and remove containers
```

#### Or use docker-compose directly

```bash
cd deploy
docker compose up -d      # Start
docker compose down       # Stop
docker compose logs -f    # View logs
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| BACKEND_PORT | 8001 | Backend server port |
| FRONTEND_PORT | 3008 | Frontend dev server port |

## Ports

- **Backend**: http://localhost:8001
- **Frontend**: http://localhost:3008
