# LoanPilot Docker Deployment Guide

## Overview

This guide covers deploying LoanPilot using Docker and Docker Compose, making it easy to deploy in any customer's cloud instance with minimal setup.

## Prerequisites

### Required Software

- Docker Engine 20.10+ or Docker Desktop
- Docker Compose 2.0+ (included with Docker Desktop)
- 2GB+ available RAM
- 5GB+ available disk space

### Required Files

- `.env` file with `ANTHROPIC_API_KEY`
- `data/v3/Non-QM_Matrix.xlsx - Attributes.tsv` (sample data file)

---

## Quick Start (5 Minutes)

### 1. Clone Repository

```bash
git clone https://github.com/reacher42/loanpilot.git
cd loanpilot
```

### 2. Create Environment File

```bash
# Copy example environment file
cp .env.example .env

# Edit with your API key
nano .env
```

Add your Anthropic API key:
```
ANTHROPIC_API_KEY=sk-ant-api03-...
LOG_LEVEL=INFO
DB_PATH=loanpilot.db
```

### 3. Build and Start

```bash
# Build and start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f
```

### 4. Access Application

Open browser: **http://localhost:8000**

---

## Detailed Deployment Steps

### AWS EC2 Deployment

#### 1. Launch EC2 Instance

**Recommended Specifications:**
- Instance Type: `t3.medium` or better
- OS: Amazon Linux 2023 / Ubuntu 22.04
- Storage: 20GB+ EBS volume
- Security Group: Open port 8000 (or configure reverse proxy)

#### 2. Install Docker

**Amazon Linux 2023:**
```bash
# Update system
sudo yum update -y

# Install Docker
sudo yum install docker -y

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in for group changes to take effect
exit
```

**Ubuntu 22.04:**
```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in
exit
```

#### 3. Install Docker Compose

```bash
# Docker Compose is included in modern Docker installations
docker compose version

# If not installed, install manually:
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 4. Clone and Setup

```bash
# Clone repository
git clone https://github.com/reacher42/loanpilot.git
cd loanpilot

# Create .env file
cat > .env << 'EOF'
ANTHROPIC_API_KEY=your-api-key-here
LOG_LEVEL=INFO
DB_PATH=loanpilot.db
EOF

# Edit with actual API key
nano .env
```

#### 5. Initialize Database

```bash
# Create necessary directories
mkdir -p backups web-app/logs

# Run database initialization
docker-compose run --rm loanpilot python3 utils/convert_v3_to_sqlite.py

# Or let the app initialize on first run (will use existing DB if present)
```

#### 6. Start Application

```bash
# Build and start
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f loanpilot
```

#### 7. Configure Security Group

Open port 8000 in AWS Security Group:
- Type: Custom TCP
- Port: 8000
- Source: Your IP or 0.0.0.0/0 (public access)

#### 8. Access Application

```bash
# Get public IP
curl http://checkip.amazonaws.com

# Access: http://<PUBLIC_IP>:8000
```

---

## Docker Commands Reference

### Build and Start

```bash
# Build images
docker-compose build

# Start services in background
docker-compose up -d

# Build and start together
docker-compose up -d --build

# Start with fresh build (no cache)
docker-compose build --no-cache
docker-compose up -d
```

### Stop and Remove

```bash
# Stop services
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop, remove containers, and remove volumes (⚠️ DELETES DATABASE)
docker-compose down -v
```

### View Logs

```bash
# View all logs
docker-compose logs

# Follow logs (real-time)
docker-compose logs -f

# View specific service logs
docker-compose logs -f loanpilot

# View last 100 lines
docker-compose logs --tail=100
```

### Container Management

```bash
# List running containers
docker-compose ps

# Restart services
docker-compose restart

# Restart specific service
docker-compose restart loanpilot

# Execute command in container
docker-compose exec loanpilot bash

# Run one-off command
docker-compose run --rm loanpilot python3 --version
```

### Health Check

```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' loanpilot-app

# Test health endpoint
curl http://localhost:8000/health
```

---

## Volume Management

### Persistent Data

The following data persists across container restarts:

```yaml
volumes:
  - ./loanpilot.db:/app/loanpilot.db          # Database file
  - ./backups:/app/backups                     # Backup files
  - ./web-app/logs:/app/web-app/logs          # Application logs
  - ./data:/app/data:ro                        # Sample data (read-only)
```

### Backup Database

```bash
# Manual backup (container running)
docker-compose exec loanpilot cp loanpilot.db backups/manual_backup_$(date +%Y%m%d_%H%M%S).db

# Or copy from host
cp loanpilot.db backups/manual_backup_$(date +%Y%m%d_%H%M%S).db

# Or use built-in backup feature via API
curl -X POST http://localhost:8000/api/database/backup
```

### Restore Database

```bash
# Stop application
docker-compose stop

# Restore from backup
cp backups/loanpilot_backup_YYYYMMDD_HHMMSS.db loanpilot.db

# Start application
docker-compose start

# Or use built-in restore feature via web interface
```

### View Logs

```bash
# View application logs
tail -f web-app/logs/loanpilot.log

# Inside container
docker-compose exec loanpilot tail -f web-app/logs/loanpilot.log
```

---

## Production Configuration

### Environment Variables

Create production `.env` file:

```bash
# API Configuration
ANTHROPIC_API_KEY=sk-ant-api03-your-production-key

# Logging
LOG_LEVEL=WARNING

# Database
DB_PATH=loanpilot.db

# Optional: Set host binding
# UVICORN_HOST=0.0.0.0
# UVICORN_PORT=8000
```

### Reverse Proxy Setup (Nginx)

#### Install Nginx

```bash
# Amazon Linux 2023
sudo yum install nginx -y

# Ubuntu
sudo apt-get install nginx -y
```

#### Configure Nginx

```bash
sudo nano /etc/nginx/conf.d/loanpilot.conf
```

Add configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Increase timeouts for long-running queries
    proxy_read_timeout 300s;
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (if needed in future)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Increase upload size for program uploads
    client_max_body_size 10M;
}
```

#### Start Nginx

```bash
# Test configuration
sudo nginx -t

# Start service
sudo systemctl start nginx
sudo systemctl enable nginx

# Restart after changes
sudo systemctl restart nginx
```

#### Update Security Group

- Close port 8000 (no direct access)
- Open port 80 (HTTP)
- Open port 443 (HTTPS, if using SSL)

### SSL/TLS with Let's Encrypt

```bash
# Install certbot
sudo yum install certbot python3-certbot-nginx -y  # Amazon Linux
sudo apt-get install certbot python3-certbot-nginx -y  # Ubuntu

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
sudo certbot renew --dry-run
```

---

## Monitoring and Maintenance

### Health Checks

```bash
# Container health status
docker-compose ps

# Application health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy", "timestamp": "2025-11-18T14:30:00"}
```

### View Resource Usage

```bash
# Real-time resource usage
docker stats loanpilot-app

# Disk usage
docker system df

# Detailed disk usage
docker system df -v
```

### Log Rotation

Configure log rotation for Docker logs:

```bash
sudo nano /etc/docker/daemon.json
```

Add:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

Restart Docker:

```bash
sudo systemctl restart docker
docker-compose up -d
```

### Cleanup

```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Remove everything unused (⚠️ careful!)
docker system prune -a --volumes
```

---

## Troubleshooting

### Problem: Container Won't Start

**Check logs:**
```bash
docker-compose logs loanpilot
```

**Common causes:**
- Missing `.env` file → Create with ANTHROPIC_API_KEY
- Port 8000 already in use → Change port in docker-compose.yml
- Insufficient memory → Increase instance size

**Solution:**
```bash
# Check what's using port 8000
sudo lsof -i :8000
sudo netstat -tulpn | grep 8000

# Kill process or change port
docker-compose down
# Edit docker-compose.yml to use different port
docker-compose up -d
```

### Problem: Database Not Persisting

**Check volume mounts:**
```bash
docker-compose config

# Verify volume mapping
docker inspect loanpilot-app | grep -A 10 Mounts
```

**Solution:**
```bash
# Ensure database file exists on host
ls -l loanpilot.db

# Recreate with correct volumes
docker-compose down
docker-compose up -d
```

### Problem: API Key Not Working

**Verify environment variable:**
```bash
# Check if variable is set
docker-compose exec loanpilot env | grep ANTHROPIC

# Check .env file
cat .env
```

**Solution:**
```bash
# Update .env file
nano .env

# Recreate container to pick up new env vars
docker-compose down
docker-compose up -d
```

### Problem: Permission Denied Errors

**Check file permissions:**
```bash
ls -la loanpilot.db backups/ web-app/logs/
```

**Solution:**
```bash
# Fix permissions
chmod 666 loanpilot.db
chmod 777 backups/
chmod 777 web-app/logs/

# Or run container with user permissions (advanced)
# Edit docker-compose.yml and add:
# user: "${UID}:${GID}"
```

### Problem: Health Check Failing

**Test manually:**
```bash
# Inside container
docker-compose exec loanpilot curl http://localhost:8000/health

# From host
curl http://localhost:8000/health
```

**Check logs:**
```bash
docker-compose logs loanpilot | grep -i error
```

### Problem: Out of Disk Space

**Check usage:**
```bash
df -h
docker system df
```

**Clean up:**
```bash
# Remove old backups
rm backups/loanpilot_backup_202501*.db

# Clean Docker system
docker system prune -a

# Compress old logs
gzip web-app/logs/*.log
```

---

## Updating Application

### Pull Latest Changes

```bash
# Stop application
docker-compose stop

# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose up -d --build

# Verify
docker-compose logs -f
```

### Rollback to Previous Version

```bash
# Stop current version
docker-compose down

# Checkout previous version
git log --oneline  # Find commit hash
git checkout <commit-hash>

# Rebuild and start
docker-compose up -d --build
```

---

## Advanced Configuration

### Custom Port Mapping

Edit `docker-compose.yml`:

```yaml
ports:
  - "8080:8000"  # Map host port 8080 to container port 8000
```

### Multiple Environments

Create environment-specific compose files:

**docker-compose.prod.yml:**
```yaml
version: '3.8'

services:
  loanpilot:
    restart: always
    environment:
      - LOG_LEVEL=WARNING
```

**Usage:**
```bash
# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Development
docker-compose up -d
```

### Resource Limits

Add to `docker-compose.yml`:

```yaml
services:
  loanpilot:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

---

## Security Best Practices

### 1. API Key Security

- ✅ Store API key in `.env` file (never commit)
- ✅ Use environment variables in container
- ✅ Restrict `.env` file permissions: `chmod 600 .env`
- ⚠️ Never log API keys

### 2. Network Security

- ✅ Use reverse proxy (Nginx) in production
- ✅ Enable HTTPS with SSL/TLS certificates
- ✅ Restrict direct access to port 8000
- ✅ Use AWS Security Groups / firewall rules

### 3. Container Security

- ✅ Run containers as non-root user (advanced)
- ✅ Use specific image tags (not `latest`)
- ✅ Scan images for vulnerabilities
- ✅ Keep Docker and images updated

### 4. Data Security

- ✅ Regular database backups
- ✅ Encrypt backups at rest
- ✅ Secure backup storage location
- ✅ Test restore procedures

---

## Performance Optimization

### 1. Docker Build Cache

```bash
# Use BuildKit for faster builds
export DOCKER_BUILDKIT=1
docker-compose build
```

### 2. Image Size Optimization

The Dockerfile uses multi-stage builds to minimize image size:
- Builder stage: Compile dependencies
- Final stage: Runtime only (~200MB vs ~1GB)

### 3. Application Performance

- CPU: 2+ cores recommended
- RAM: 2GB+ for optimal performance
- Storage: SSD recommended for database

---

## Migration Guide

### From Direct Installation to Docker

#### 1. Backup Current Data

```bash
# Backup database
cp loanpilot.db loanpilot_pre_docker_backup.db

# Backup logs
tar -czf logs_backup.tar.gz web-app/logs/
```

#### 2. Install Docker

Follow installation steps above for your OS.

#### 3. Build and Start

```bash
# Clone fresh or use existing directory
cd loanpilot

# Create .env with same API key
cp .env.example .env
nano .env  # Add API key

# Start with existing database
docker-compose up -d
```

#### 4. Verify

```bash
# Check logs
docker-compose logs -f

# Test application
curl http://localhost:8000/health

# Test web interface
# Open: http://localhost:8000
```

---

## FAQ

### Q: Can I use existing database file?

Yes! Place `loanpilot.db` in the project root before starting Docker. The volume mount will use it.

### Q: How do I update the sample data TSV?

Replace `data/v3/Non-QM_Matrix.xlsx - Attributes.tsv` and restart:
```bash
docker-compose restart
```

### Q: Can I access the container shell?

Yes:
```bash
docker-compose exec loanpilot bash
```

### Q: How do I change the port?

Edit `docker-compose.yml` ports section:
```yaml
ports:
  - "9000:8000"  # Now accessible on port 9000
```

### Q: How much disk space is needed?

- Docker images: ~500MB
- Database: ~1MB (grows with uploaded programs)
- Logs: ~10MB/day (depends on usage)
- Backups: ~1MB per backup
- **Total**: 2-5GB recommended

### Q: Can I run multiple instances?

Yes, use different ports and database files:
```bash
# Instance 1 (default)
docker-compose up -d

# Instance 2 (custom port and database)
docker-compose -f docker-compose.yml -p loanpilot2 up -d
# Edit ports and volume mounts in compose file
```

---

## Support and Maintenance

### Regular Maintenance Tasks

**Daily:**
- Monitor application logs
- Check disk space
- Verify backups are created

**Weekly:**
- Review resource usage
- Clean up old backups (keep last 7)
- Update Docker images if needed

**Monthly:**
- Update OS packages
- Review security patches
- Test restore procedures

### Monitoring Script

Create `monitor.sh`:

```bash
#!/bin/bash

echo "=== LoanPilot Status ==="
docker-compose ps

echo -e "\n=== Health Check ==="
curl -s http://localhost:8000/health | jq .

echo -e "\n=== Resource Usage ==="
docker stats --no-stream loanpilot-app

echo -e "\n=== Disk Usage ==="
df -h | grep -E "Filesystem|/$"

echo -e "\n=== Recent Logs ==="
docker-compose logs --tail=10 loanpilot
```

Run:
```bash
chmod +x monitor.sh
./monitor.sh
```

---

## Related Documentation

- [README.md](README.md) - Project overview
- [loanpilot_aws_deployment.md](loanpilot_aws_deployment.md) - Original AWS deployment
- [PROGRAM_UPLOAD_GUIDE.md](PROGRAM_UPLOAD_GUIDE.md) - Program upload feature
- [DATABASE_RESET_GUIDE.md](DATABASE_RESET_GUIDE.md) - Database management

---

## Quick Reference

| Task | Command |
|------|---------|
| **Start** | `docker-compose up -d` |
| **Stop** | `docker-compose stop` |
| **Restart** | `docker-compose restart` |
| **Logs** | `docker-compose logs -f` |
| **Status** | `docker-compose ps` |
| **Shell** | `docker-compose exec loanpilot bash` |
| **Rebuild** | `docker-compose up -d --build` |
| **Remove** | `docker-compose down` |
| **Backup** | `cp loanpilot.db backups/backup_$(date +%Y%m%d).db` |
| **Health** | `curl http://localhost:8000/health` |

---

**Need Help?** Check logs first: `docker-compose logs -f loanpilot`
