# LoanPilot Docker Quick Start

## 🚀 Deploy in 3 Commands

```bash
# 1. Clone repository
git clone https://github.com/reacher42/loanpilot.git
cd loanpilot

# 2. Setup environment
cp .env.example .env
nano .env  # Add your ANTHROPIC_API_KEY

# 3. Start with Docker
docker-compose up -d
```

Access: **http://localhost:8000**

---

## 📋 Prerequisites

- Docker 20.10+ installed
- Docker Compose 2.0+ installed
- Anthropic API key

### Install Docker

**Amazon Linux 2023:**
```bash
sudo yum install docker -y
sudo systemctl start docker
sudo usermod -aG docker $USER
```

**Ubuntu 22.04:**
```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

Then log out and back in.

---

## 🎯 Common Commands

### Start/Stop
```bash
docker-compose up -d        # Start in background
docker-compose stop         # Stop containers
docker-compose restart      # Restart
docker-compose down         # Stop and remove containers
```

### Logs
```bash
docker-compose logs -f      # Follow logs
docker-compose logs --tail=100  # Last 100 lines
```

### Status
```bash
docker-compose ps           # Container status
docker stats loanpilot-app  # Resource usage
curl http://localhost:8000/api/health  # Health check
```

### Updates
```bash
git pull origin main
docker-compose up -d --build
```

---

## 🗂️ Data Persistence

The following directories persist across container restarts:

- `./loanpilot.db` - Main database
- `./backups/` - Database backups
- `./web-app/logs/` - Application logs
- `./data/` - Sample data (read-only)

### Backup Database

```bash
# Via UI: Database → Manage Backups → Create Backup

# Or manually:
docker-compose exec loanpilot cp loanpilot.db backups/manual_backup_$(date +%Y%m%d).db
```

---

## 🔧 Configuration

Edit `.env` file:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-api03-...

# Optional
LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR
DB_PATH=loanpilot.db    # Database file path
```

Restart after changes:
```bash
docker-compose restart
```

---

## 🌐 Production Deployment

### AWS EC2

1. **Launch EC2 instance** (t3.medium or better)
2. **Install Docker** (see above)
3. **Configure Security Group**: Open port 8000
4. **Deploy**:
   ```bash
   git clone https://github.com/reacher42/loanpilot.git
   cd loanpilot
   cp .env.example .env
   nano .env  # Add API key
   docker-compose up -d
   ```

5. **Access**: http://YOUR_EC2_IP:8000

### Nginx Reverse Proxy

```bash
# Install Nginx
sudo yum install nginx -y

# Configure
sudo nano /etc/nginx/conf.d/loanpilot.conf
```

Add:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    client_max_body_size 10M;
}
```

Start Nginx:
```bash
sudo systemctl start nginx
sudo systemctl enable nginx
```

Update Security Group: Close port 8000, open port 80.

---

## 🐛 Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs loanpilot

# Common fixes:
# - Check .env has valid API key
# - Check port 8000 is available: sudo lsof -i :8000
# - Rebuild: docker-compose up -d --build
```

### Database not persisting

```bash
# Check volume mounts
docker inspect loanpilot-app | grep -A 10 Mounts

# Ensure database exists
ls -l loanpilot.db
```

### Permission errors

```bash
# Fix permissions
chmod 666 loanpilot.db
chmod 777 backups/ web-app/logs/

# Restart
docker-compose restart
```

### Out of disk space

```bash
# Clean up
docker system prune -a
rm backups/loanpilot_backup_2024*.db  # Remove old backups
```

---

## 📚 Documentation

- **[DOCKER_DEPLOYMENT_GUIDE.md](DOCKER_DEPLOYMENT_GUIDE.md)** - Comprehensive deployment guide
- **[README.md](README.md)** - Project overview
- **[PROGRAM_UPLOAD_GUIDE.md](PROGRAM_UPLOAD_GUIDE.md)** - Upload new programs
- **[DATABASE_RESET_GUIDE.md](DATABASE_RESET_GUIDE.md)** - Database management

---

## 🔐 Security Checklist

Before production deployment:

- ✅ Set strong API key in `.env`
- ✅ Use Nginx reverse proxy
- ✅ Enable HTTPS with SSL certificate
- ✅ Restrict Security Group rules
- ✅ Set up regular backups
- ✅ Review logs regularly
- ✅ Keep Docker and images updated

---

## 💡 Tips

### Auto-start on boot

Docker Compose services start automatically after reboot (restart: unless-stopped).

### Monitor health

```bash
watch -n 5 'docker-compose ps && curl -s http://localhost:8000/api/health'
```

### Access container shell

```bash
docker-compose exec loanpilot bash
```

### Custom port

Edit `docker-compose.yml`:
```yaml
ports:
  - "8080:8000"  # Access on port 8080
```

---

## 🆘 Need Help?

1. Check logs: `docker-compose logs -f`
2. Review [DOCKER_DEPLOYMENT_GUIDE.md](DOCKER_DEPLOYMENT_GUIDE.md)
3. Check GitHub issues

---

## Quick Reference Card

| What | Command |
|------|---------|
| **Start** | `docker-compose up -d` |
| **Stop** | `docker-compose stop` |
| **Logs** | `docker-compose logs -f` |
| **Status** | `docker-compose ps` |
| **Restart** | `docker-compose restart` |
| **Update** | `git pull && docker-compose up -d --build` |
| **Backup** | Database → Manage Backups → Create |
| **Health** | `curl http://localhost:8000/api/health` |
| **Shell** | `docker-compose exec loanpilot bash` |

---

**Ready to deploy?** Start with: `./docker-start.sh`
