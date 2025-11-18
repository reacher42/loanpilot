# LoanPilot AWS EC2 Deployment

## Deployment Overview

**Instance:** 15.206.158.95 (Amazon Linux 2023)
**Instance ID:** i-0bf598ab9281ca565 (birdwatch-dev)
**Deployment Date:** 2025-10-17
**Last Updated:** 2025-11-04 (Adaptive model selector deployed - production-ready)
**Architecture:** Minimal dependencies (Anthropic API only, no PyTorch)

## Access URLs

- **Main App:** http://15.206.158.95:8000
- **API Docs:** http://15.206.158.95:8000/api/docs
- **Health:** http://15.206.158.95:8000/api/health

## Deployment Architecture

### Key Components
- **Backend:** FastAPI + Uvicorn (Python 3.9.23)
- **Query Parser:** Context-aware parser with Anthropic tool calling
- **Model Selection:** Adaptive model selector with automatic fallback (PRODUCTION-READY)
  - Primary: claude-3-5-sonnet-20241022
  - Fallback chain: claude-3-5-sonnet-20240620 → claude-3-sonnet-20240229
  - Never fails due to model deprecation
- **Query Matching:** Structured tool/function calling for script routing
- **Text Formatting:** Anthropic API for readable English output (adaptive models)
- **Database:** SQLite (loanpilot.db, 552KB)
- **Port:** 8000 (publicly accessible)

### Dependencies (Minimal)
```
fastapi>=0.100.0
uvicorn>=0.23.0
anthropic>=0.3.0
python-dotenv>=1.0.0
pandas>=2.0.0
openpyxl>=3.1.0
python-multipart
```

**Total package size:** ~50MB (vs 3GB+ with PyTorch/sentence-transformers)

## Directory Structure
```
/home/ec2-user/loanpilot/
├── loanpilot.db                   # SQLite database
├── .env                            # API keys (ANTHROPIC_API_KEY)
├── src/
│   ├── adaptive_model_selector.py # Adaptive model selection with fallback ⭐ NEW
│   ├── context_aware_parser.py   # Context-aware parser with Anthropic tool calling ⭐
│   ├── parser_anthropic.py       # Legacy parser (fallback)
│   └── llm_rewriter.py
└── web-app/
    ├── main.py                   # FastAPI application
    ├── query_engine.py           # Query execution engine
    ├── text_formatter.py         # Anthropic-based text formatting
    ├── parsers.py                # Result parsers
    ├── logs/
    │   └── uvicorn.log           # Application logs
    └── static/
        └── index.html            # Frontend (HTMX + TailwindCSS)
```

## Management Commands

### SSH Access
```bash
# Using DNS name (recommended)
ssh -i /Users/rajeevbhardwaj/Projects/Outreach/aws-management/brdwch_dev_kp.pem \
  ec2-user@ec2-15-206-158-95.ap-south-1.compute.amazonaws.com

# Or using IP address
ssh -i /Users/rajeevbhardwaj/Projects/Outreach/aws-management/brdwch_dev_kp.pem \
  ec2-user@15.206.158.95
```

### Check Application Status
```bash
# Check if running
ssh -i brdwch_dev_kp.pem ec2-user@13.233.95.244 "ps aux | grep '[u]vicorn'"

# View logs (tail)
ssh -i brdwch_dev_kp.pem ec2-user@13.233.95.244 \
  "tail -50 loanpilot/web-app/logs/uvicorn.log"

# Follow logs in real-time
ssh -i brdwch_dev_kp.pem ec2-user@13.233.95.244 \
  "tail -f loanpilot/web-app/logs/uvicorn.log"
```

### Restart Application
```bash
ssh -i brdwch_dev_kp.pem ec2-user@13.233.95.244 \
  "pkill -f uvicorn && cd loanpilot/web-app && \
   PYTHONPATH='..:.' nohup python3 -m uvicorn main:app \
   --host 0.0.0.0 --port 8000 > logs/uvicorn.log 2>&1 &"
```

### Stop Application
```bash
ssh -i brdwch_dev_kp.pem ec2-user@13.233.95.244 "pkill -f uvicorn"
```

### Update Application
```bash
# 1. Transfer updated files
scp -i brdwch_dev_kp.pem <local-file> ec2-user@13.233.95.244:~/loanpilot/<path>

# 2. Restart application (see above)
```

### Update Environment Variables
```bash
# Edit .env file
ssh -i brdwch_dev_kp.pem ec2-user@13.233.95.244 "nano loanpilot/.env"

# Restart required after .env changes
```

## Key Features Deployed

1. **Program Matching**
   - Natural language query interface
   - Anthropic API for query matching
   - Card-based results with metrics

2. **Parameter Queries**
   - Technical expressions converted to plain English
   - Parameter-specific cards with icons
   - Popup details for all parameters

3. **Sample Profiles**
   - 6 diverse borrower profiles
   - Random selection on each load
   - Auto-clear previous selections

4. **Context Parameters**
   - Selected programs filtering
   - Servicer selection (Prime/LoanStream)
   - Borrower criteria integration

## Troubleshooting

### Application Not Responding
```bash
# Check if process is running
ps aux | grep uvicorn

# Check logs for errors
tail -100 loanpilot/web-app/logs/uvicorn.log

# Verify database exists
ls -lh loanpilot/loanpilot.db

# Test health endpoint locally
curl http://localhost:8000/api/health
```

### Port Already in Use
```bash
# Find process using port 8000
netstat -tlnp | grep 8000

# Kill process
kill -9 <PID>
```

### Permission Issues
```bash
# Fix file permissions
chmod 644 loanpilot/.env
chmod -R 755 loanpilot/web-app
```

## Security Notes

- **API Key:** ANTHROPIC_API_KEY stored in `.env` file (not in version control)
- **Database:** Read-only SQLite database (no writes from web app)
- **Port 8000:** Open in security group (ensure only necessary IPs have access)
- **No authentication:** Consider adding auth layer for production

## Performance

- **Cold start:** ~2-3 seconds
- **Query execution:** 1-3 seconds (Anthropic API latency)
- **Text formatting:** 1-2 seconds (cached after first use)
- **Concurrent users:** Tested up to 10 simultaneous requests

## Deployment History

**v1.2 (2025-11-04) - PRODUCTION-READY:**
- ⭐ Deployed adaptive model selector with automatic fallback
- API calls can never fail due to model deprecation
- Automatic model fallback chain for resilience
- Updated IP: 15.206.158.95 (instance: i-0bf598ab9281ca565)
- Updated files:
  - NEW: src/adaptive_model_selector.py
  - UPDATED: src/context_aware_parser.py (uses adaptive selector)
  - UPDATED: web-app/text_formatter.py (uses adaptive selector)

**v1.1 (2025-10-17):**
- Deployed context-aware parser with Anthropic tool calling
- Fixed script name mismatch (match_programs_by_borrower → match_programs)
- Enhanced parameter extraction with formal tool definitions
- Support for context-aware queries with selected programs

**v1.0 (2025-10-17):**
- Initial deployment with minimal dependencies
- Anthropic-only architecture (removed PyTorch/sentence-transformers)
- FastAPI + HTMX + TailwindCSS stack
- Deployed on EC2 13.233.95.244
- Removed Electron app support

## Contact & Support

For issues or updates, refer to project repository and check logs first.
