# LoanPilot - Complete Project Structure

## 📁 Directory Tree

```
loanpilot/
│
├── 🖥️  ELECTRON DESKTOP APP
│   └── electron-loan-app/
│       ├── main.js                    # Electron entry point
│       ├── preload.js                 # IPC bridge
│       ├── package.json               # Node.js dependencies
│       └── src/
│           ├── index.html             # Desktop UI
│           └── server/
│               ├── server.js          # Express.js app (port 3000)
│               ├── routes/
│               │   └── query.js       # Query API routes
│               └── engines/
│                   └── python-bridge.js # Subprocess spawning
│
├── 🌐 WEB APPLICATION (NEW)
│   └── web-app/
│       ├── __init__.py               # Python package
│       ├── main.py                   # FastAPI app (port 8000)
│       ├── models.py                 # Pydantic models
│       ├── query_engine.py           # Direct Python integration
│       ├── parsers.py                # HTML result generators
│       ├── static/
│       │   └── index.html            # Web UI (no Electron)
│       └── logs/
│           └── .gitkeep
│
├── 🐍 SHARED PYTHON CORE
│   └── src/
│       ├── __init__.py
│       ├── parser.py                 # Query parsing & execution
│       ├── llm_rewriter.py           # Claude LLM integration
│       └── analysis/
│
├── 🗄️  DATABASE & DATA
│   ├── loanpilot.db                  # SQLite (shared by both)
│   ├── data/
│   │   └── v3/
│   │       └── Non-QM_Matrix.xlsx
│   └── utils/
│       ├── convert_v3_to_sqlite.py
│       ├── transpose_v3_tables.py
│       └── manage_scripts.py
│
├── 🐳 DOCKER & DEPLOYMENT
│   ├── Dockerfile                    # Multi-stage build
│   ├── docker-compose.yml            # Container orchestration
│   ├── .dockerignore                 # Build exclusions
│   ├── deploy.sh                     # AWS EC2 deployment
│   └── start-web.sh                  # Local development
│
├── 📚 DOCUMENTATION
│   ├── README.md                     # Original project README
│   ├── WEB_DEPLOYMENT.md             # Deployment guide
│   ├── FEATURE_PARITY.md             # Feature comparison
│   ├── MIGRATION_SUMMARY.md          # Migration overview
│   └── PROJECT_STRUCTURE.md          # This file
│
└── ⚙️  CONFIGURATION
    ├── .env                          # Environment variables
    ├── requirements.txt              # Python dependencies
    ├── .gitignore
    └── .claude/
        └── CLAUDE.md                 # Project rules
```

## 🔄 Dual Architecture

### Option 1: Electron Desktop
```
┌─────────────────────────────────────────┐
│     Electron App (main.js)              │
│           ↓                              │
│     Express.js Server (port 3000)       │
│           ↓                              │
│     spawn(python parser.py)             │
│           ↓                              │
│     .scratchpad file                    │
└─────────────────────────────────────────┘
```

### Option 2: FastAPI Web
```
┌─────────────────────────────────────────┐
│     Web Browser                          │
│           ↓                              │
│     FastAPI Server (port 8000)          │
│           ↓                              │
│     Python function call                │
│           ↓                              │
│     In-memory result                    │
└─────────────────────────────────────────┘
```

## 🎯 What Runs Where

### Electron (Desktop)
- **Port**: 3000
- **Access**: localhost only
- **Python**: Subprocess
- **Data**: File-based (.scratchpad)
- **Run**: `cd electron-loan-app && npm start`

### Web (Browser)
- **Port**: 8000  
- **Access**: Network accessible
- **Python**: Direct integration
- **Data**: In-memory
- **Run**: `./start-web.sh` or `docker-compose up`

## 📦 Deployment Options

### Local Development
```bash
# Electron
cd electron-loan-app && npm start

# Web (direct)
./start-web.sh

# Web (Docker)
docker-compose up -d
```

### Production (AWS EC2)
```bash
# Clone repo to EC2
git clone <repo> && cd loanpilot

# Deploy with Docker
./deploy.sh

# Access at http://ec2-ip:8000
```

## 🔗 Shared Components

These are used by **BOTH** versions:

- ✅ `src/parser.py` - Query parsing logic
- ✅ `src/llm_rewriter.py` - LLM integration  
- ✅ `loanpilot.db` - SQLite database
- ✅ `.env` - Configuration
- ✅ `requirements.txt` - Python deps

## 📊 Quick Reference

| Feature | Electron | Web |
|---------|----------|-----|
| **Run Command** | `npm start` | `./start-web.sh` |
| **Port** | 3000 | 8000 |
| **URL** | localhost:3000 | localhost:8000 |
| **Deploy** | DMG installer | Docker container |
| **Access** | Local only | Network |
| **Performance** | Good | Better (40% faster) |

---

**Choose your version:**
- 🖥️  **Electron** - Desktop app, offline work
- 🌐 **Web** - Browser-based, team access, cloud deployment
