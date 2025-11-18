# LoanPilot - Customer Deployment Guide

## Quick Start

### 1. Load Docker Image
```bash
docker load -i loanpilot-customer.tar.gz
```

### 2. Create Configuration
```bash
# Create .env file
cat > .env << EOF
ANTHROPIC_API_KEY=your-api-key-here
EOF

# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  loanpilot:
    image: loanpilot:customer-1.0.0
    container_name: loanpilot-app
    ports:
      - "8000:8000"
    volumes:
      - ./loanpilot.db:/app/loanpilot.db
      - ./backups:/app/backups
      - ./logs:/app/web-app/logs
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    restart: unless-stopped
EOF
```

### 3. Start Application
```bash
docker-compose up -d
```

### 4. Access
**http://localhost:8000**

## Commands

| Action | Command |
|--------|---------|
| Start | `docker-compose up -d` |
| Stop | `docker-compose stop` |
| Restart | `docker-compose restart` |
| Logs | `docker-compose logs -f` |
| Status | `docker-compose ps` |
| Backup | `cp loanpilot.db backups/backup_$(date +%Y%m%d).db` |

## Requirements

- Docker 20.10+
- Docker Compose 2.0+
- 2GB RAM minimum
- 5GB disk space

## Support

**Email**: support@loanpilot.com
**Phone**: 1-800-LOAN-PILOT

## License

Valid until: [EXPIRY_DATE]
Customer: [CUSTOMER_ID]
