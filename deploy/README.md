# Deploy Guide

## Directory Structure

```
deploy/
└── scripts/
    ├── mac/
    ├── linux/
    ├── windows/
    └── docker/
        ├── docker-compose.yml
        ├── start.sh
        └── stop.sh

frontend/
├── Dockerfile
└── nginx.conf

backend/
└── Dockerfile
```

## Docker Deployment (Recommended)

```bash
cd deploy/scripts/docker
./start.sh      # Build and start
./stop.sh       # Stop
```

### Ports

- **Frontend**: http://localhost:3008
- **Backend**: http://localhost:8001

## Native Deployment

### Mac

```bash
cd deploy/scripts/mac
./start.sh
./stop.sh
```

### Linux

```bash
cd deploy/scripts/linux
./start.sh
./stop.sh
```

### Windows

```cmd
cd deploy\scripts\windows
start.bat
stop.bat
```
