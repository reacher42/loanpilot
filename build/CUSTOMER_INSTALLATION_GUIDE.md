# LoanPilot Installation Guide

## System Requirements

### Hardware
- **CPU**: 2+ cores recommended
- **RAM**: 2GB minimum, 4GB recommended
- **Disk**: 5GB available space
- **Network**: Internet connection for API access

### Software
- **Docker**: Version 20.10 or later
- **Docker Compose**: Version 2.0 or later
- **Operating System**: Linux, macOS, or Windows with WSL2

---

## Installation Steps

### 1. Extract Package

```bash
# Extract the distribution package
tar -xzf loanpilot-CUSTOMER-v1.0.0.tar.gz
cd loanpilot-CUSTOMER-v1.0.0/
```

### 2. Verify Package Integrity

```bash
# Verify checksum (Linux/macOS)
sha256sum -c SHA256SUMS

# Should show: loanpilot-CUSTOMER-v1.0.0.tar.gz: OK
```

### 3. Install Docker (if needed)

**Ubuntu/Debian:**
```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# Log out and back in
```

**Amazon Linux 2023:**
```bash
sudo yum install docker -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
# Log out and back in
```

**macOS/Windows:**
- Install Docker Desktop from: https://www.docker.com/products/docker-desktop

### 4. Run Installation Script

```bash
# Make script executable (if needed)
chmod +x install.sh

# Run installation
./install.sh
```

The script will:
1. Check Docker installation
2. Load the Docker image
3. Create configuration files
4. Start the application

### 5. Configure API Key

Edit the `.env` file and add your Anthropic API key:

```bash
nano .env
```

Change:
```
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

To your actual API key:
```
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx...
```

Save and exit (Ctrl+X, Y, Enter).

### 6. Restart Application

```bash
docker-compose restart
```

### 7. Access Application

Open your web browser and navigate to:

**http://localhost:8000**

---

## Common Commands

### Start/Stop Application

```bash
# Start
docker-compose up -d

# Stop
docker-compose stop

# Restart
docker-compose restart

# View status
docker-compose ps
```

### View Logs

```bash
# Follow logs in real-time
docker-compose logs -f

# View last 100 lines
docker-compose logs --tail=100

# View specific service logs
docker-compose logs loanpilot
```

### Health Check

```bash
# Run verification script
./verify.sh

# Or check manually
curl http://localhost:8000/api/health
```

### Backup Database

```bash
# Database is in ./loanpilot.db
# Backups are automatically created in ./backups/

# Manual backup
docker-compose exec loanpilot cp /app/loanpilot.db /app/backups/manual_backup_$(date +%Y%m%d).db

# Or copy from host
cp loanpilot.db backups/manual_backup_$(date +%Y%m%d).db
```

---

## Troubleshooting

### Application Won't Start

**Check logs:**
```bash
docker-compose logs loanpilot
```

**Common causes:**
1. **Missing API key**: Edit `.env` and add valid key
2. **Port 8000 in use**: Change port in `docker-compose.yml`
3. **Docker not running**: Start Docker service
4. **Insufficient resources**: Increase Docker memory/CPU limits

### License Expired

If you see a "License Expired" message:

1. Contact support@loanpilot.com
2. Provide your customer ID
3. Request license renewal

Typical renewal time: 1-2 business days

### Cannot Connect to Application

**Check container status:**
```bash
docker-compose ps
```

**Verify health:**
```bash
curl http://localhost:8000/api/health
```

**Restart application:**
```bash
docker-compose restart
```

### Database Issues

**Reset database:**
```bash
# Backup first!
cp loanpilot.db loanpilot.db.backup

# Reset via web interface:
# Database → Reset Database
```

**Restore from backup:**
```bash
# Stop application
docker-compose stop

# Restore database
cp backups/loanpilot_backup_YYYYMMDD_HHMMSS.db loanpilot.db

# Start application
docker-compose start
```

---

## Updating LoanPilot

When a new version is released:

1. **Backup your data:**
   ```bash
   cp loanpilot.db loanpilot.db.backup
   cp -r backups backups.backup
   ```

2. **Stop current version:**
   ```bash
   docker-compose down
   ```

3. **Extract new version** to a different directory

4. **Copy your data:**
   ```bash
   cp loanpilot.db.backup new-version/loanpilot.db
   cp -r backups.backup new-version/backups
   cp .env new-version/.env
   ```

5. **Start new version:**
   ```bash
   cd new-version
   ./install.sh
   ```

---

## Security Best Practices

### 1. Protect API Key

- Never share your `.env` file
- Keep API key confidential
- Rotate keys periodically
- Use separate keys for dev/prod

### 2. Network Security

**Production deployment:**
- Use reverse proxy (Nginx)
- Enable HTTPS/SSL
- Restrict network access
- Use firewall rules

### 3. Regular Backups

- Backup database daily
- Keep backups offsite
- Test restore procedures
- Automate with cron:

```bash
# Add to crontab
0 2 * * * cd /path/to/loanpilot && cp loanpilot.db backups/auto_backup_$(date +\%Y\%m\%d).db
```

### 4. Monitor Resources

```bash
# Check disk space
df -h

# Check memory usage
docker stats loanpilot-app

# View container resource limits
docker inspect loanpilot-app | grep -A 10 Resources
```

---

## Production Deployment

### Behind Nginx Reverse Proxy

**Install Nginx:**
```bash
sudo yum install nginx -y  # Amazon Linux
sudo apt install nginx -y  # Ubuntu
```

**Configure:**
```bash
sudo nano /etc/nginx/conf.d/loanpilot.conf
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Increase timeouts
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }

    # File upload size
    client_max_body_size 10M;
}
```

**Start Nginx:**
```bash
sudo systemctl start nginx
sudo systemctl enable nginx
```

### Enable SSL with Let's Encrypt

```bash
# Install certbot
sudo yum install certbot python3-certbot-nginx -y

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
```

---

## Support

### Contact Information

- **Email**: support@loanpilot.com
- **Phone**: 1-800-LOAN-PILOT
- **Hours**: Monday-Friday, 9AM-5PM EST

### When Contacting Support

Please provide:
1. Customer ID
2. Version number
3. Error messages or logs
4. Steps to reproduce issue
5. System information (OS, Docker version)

### License Information

- Your license is valid until the expiry date
- Renewal reminders are sent 30 days before expiry
- Contact support to extend or renew license

---

## Additional Resources

### System Commands

```bash
# Check Docker version
docker --version

# Check disk space
df -h

# Check running containers
docker ps

# Check image details
docker images loanpilot

# Clean up Docker resources
docker system prune -a
```

### Performance Tuning

**For high-traffic deployments:**

1. Increase Docker resources in `docker-compose.yml`:
```yaml
services:
  loanpilot:
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 4G
```

2. Use faster storage (SSD recommended)

3. Monitor performance:
```bash
docker stats loanpilot-app
```

---

## Frequently Asked Questions

**Q: Can I change the port from 8000?**

A: Yes, edit `docker-compose.yml`:
```yaml
ports:
  - "9000:8000"  # Access on port 9000
```

**Q: How do I access from other computers?**

A: Use your server's IP address:
```
http://SERVER_IP:8000
```

Ensure firewall allows port 8000.

**Q: Can I run multiple instances?**

A: Yes, but use different ports and database files for each instance.

**Q: Where are the logs stored?**

A: In `./logs/` directory (volume-mounted from container).

**Q: How do I upgrade my license?**

A: Contact support@loanpilot.com with your customer ID.

---

## Quick Reference

| Task | Command |
|------|---------|
| **Start** | `docker-compose up -d` |
| **Stop** | `docker-compose stop` |
| **Restart** | `docker-compose restart` |
| **Logs** | `docker-compose logs -f` |
| **Status** | `docker-compose ps` |
| **Health** | `./verify.sh` |
| **Backup** | `cp loanpilot.db backups/backup_$(date +%Y%m%d).db` |

---

**Need Help?** Contact support@loanpilot.com
