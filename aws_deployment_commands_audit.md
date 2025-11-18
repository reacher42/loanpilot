# AWS EC2 Deployment Commands Audit

**Session Date:** 2025-10-17
**Target Instance:** 13.233.95.244 (Amazon Linux 2023)
**SSH Key:** `/Users/rajeevbhardwaj/Projects/Outreach/aws-management/brdwch_dev_kp.pem`

## All Commands Executed (Chronological)

### 1. Initial SSH Connection Test
```bash
# Verify SSH access and check system info
ssh -i /Users/rajeevbhardwaj/Projects/Outreach/aws-management/brdwch_dev_kp.pem \
  -o StrictHostKeyChecking=no \
  -o ConnectTimeout=10 \
  ec2-user@13.233.95.244 \
  "echo 'SSH Connection Successful!' && uname -a && df -h | grep nvme && python3 --version"
```
**Result:** Connection successful, Python 3.9.23, Amazon Linux 2023

### 2. Transfer Deployment Package
```bash
# Upload minimal deployment tarball (102KB)
scp -i /Users/rajeevbhardwaj/Projects/Outreach/aws-management/brdwch_dev_kp.pem \
  -o StrictHostKeyChecking=no \
  loanpilot-deploy-minimal.tar.gz \
  ec2-user@13.233.95.244:~/
```
**Result:** Transfer successful

### 3. Extract Deployment Package
```bash
# Create directory and extract files
ssh -i /Users/rajeevbhardwaj/Projects/Outreach/aws-management/brdwch_dev_kp.pem \
  -o StrictHostKeyChecking=no \
  ec2-user@13.233.95.244 \
  "mkdir -p loanpilot && cd loanpilot && tar -xzf ../loanpilot-deploy-minimal.tar.gz && ls -lh"
```
**Result:** Files extracted - loanpilot.db (552KB), src/, web-app/

### 4. Check Python Environment
```bash
# Verify Python version and check for pip
ssh -i /Users/rajeevbhardwaj/Projects/Outreach/aws-management/brdwch_dev_kp.pem \
  -o StrictHostKeyChecking=no \
  ec2-user@13.233.95.244 \
  "cd loanpilot && python3 --version && which pip3 && ls -la .env 2>/dev/null || echo '.env file not found'"
```
**Result:** Python 3.9.23, pip3 not found, .env missing

### 5. Transfer Environment File
```bash
# Upload .env file with API keys
scp -i /Users/rajeevbhardwaj/Projects/Outreach/aws-management/brdwch_dev_kp.pem \
  -o StrictHostKeyChecking=no \
  .env \
  ec2-user@13.233.95.244:~/loanpilot/
```
**Result:** Transfer successful

### 6. Install pip
```bash
# Install pip using Python's ensurepip module
ssh -i /Users/rajeevbhardwaj/Projects/Outreach/aws-management/brdwch_dev_kp.pem \
  -o StrictHostKeyChecking=no \
  ec2-user@13.233.95.244 \
  "python3 -m ensurepip --user --upgrade && echo '✓ pip installed successfully'"
```
**Result:** pip 21.3.1 installed

### 7. Transfer Requirements File
```bash
# Upload minimal requirements.txt
scp -i /Users/rajeevbhardwaj/Projects/Outreach/aws-management/brdwch_dev_kp.pem \
  -o StrictHostKeyChecking=no \
  /tmp/requirements-minimal.txt \
  ec2-user@13.233.95.244:~/loanpilot/requirements.txt
```
**Result:** Transfer successful

### 8. Install Python Dependencies
```bash
# Install FastAPI, uvicorn, anthropic, pandas, openpyxl
ssh -i /Users/rajeevbhardwaj/Projects/Outreach/aws-management/brdwch_dev_kp.pem \
  -o StrictHostKeyChecking=no \
  ec2-user@13.233.95.244 \
  "cd loanpilot && python3 -m pip install --user -r requirements.txt && echo '✓ All dependencies installed successfully'"
```
**Result:** All packages installed (~50MB total)

### 9. Create Directories and Verify Files
```bash
# Create logs directory and verify key files exist
ssh -i /Users/rajeevbhardwaj/Projects/Outreach/aws-management/brdwch_dev_kp.pem \
  -o StrictHostKeyChecking=no \
  ec2-user@13.233.95.244 \
  "cd loanpilot && mkdir -p web-app/logs && ls -la loanpilot.db && ls -la web-app/main.py && echo '✓ Directories and files verified'"
```
**Result:** Directories created, files verified

### 10. First Application Start Attempt
```bash
# Start FastAPI application with nohup (failed due to missing python-multipart)
ssh -i /Users/rajeevbhardwaj/Projects/Outreach/aws-management/brdwch_dev_kp.pem \
  -o StrictHostKeyChecking=no \
  ec2-user@13.233.95.244 \
  "cd loanpilot/web-app && nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > logs/uvicorn.log 2>&1 &"
```
**Result:** Failed - missing python-multipart dependency

### 11. Check Application Log
```bash
# View error log to diagnose issue
ssh -i /Users/rajeevbhardwaj/Projects/Outreach/aws-management/brdwch_dev_kp.pem \
  -o StrictHostKeyChecking=no \
  ec2-user@13.233.95.244 \
  "cat loanpilot/web-app/logs/uvicorn.log"
```
**Result:** Error - RuntimeError: Form data requires "python-multipart"

### 12. Install Missing Dependency
```bash
# Install python-multipart package
ssh -i /Users/rajeevbhardwaj/Projects/Outreach/aws-management/brdwch_dev_kp.pem \
  -o StrictHostKeyChecking=no \
  ec2-user@13.233.95.244 \
  "python3 -m pip install --user python-multipart && echo '✓ python-multipart installed'"
```
**Result:** python-multipart 0.0.20 installed

### 13. Second Application Start Attempt
```bash
# Start application with proper PYTHONPATH
ssh -i /Users/rajeevbhardwaj/Projects/Outreach/aws-management/brdwch_dev_kp.pem \
  -o StrictHostKeyChecking=no \
  ec2-user@13.233.95.244 \
  "cd loanpilot/web-app && PYTHONPATH='..:.' nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > logs/uvicorn.log 2>&1 &"
```
**Result:** Started successfully in background

### 14. Verify Application Running
```bash
# Check process status and view recent logs
ssh -i /Users/rajeevbhardwaj/Projects/Outreach/aws-management/brdwch_dev_kp.pem \
  -o StrictHostKeyChecking=no \
  ec2-user@13.233.95.244 \
  "ps aux | grep '[u]vicorn'; echo '---LOG FILE---'; tail -30 loanpilot/web-app/logs/uvicorn.log"
```
**Result:** Process running (PID 4229), application startup complete

### 15. Test Internal Health Endpoint
```bash
# Test health endpoint from within EC2 instance
ssh -i /Users/rajeevbhardwaj/Projects/Outreach/aws-management/brdwch_dev_kp.pem \
  -o StrictHostKeyChecking=no \
  ec2-user@13.233.95.244 \
  "curl -s http://localhost:8000/api/health | python3 -m json.tool"
```
**Result:** Health check passed - {"success": true, "available": true}

### 16. Test External Access
```bash
# Test health endpoint from local machine (external access)
curl -s --connect-timeout 10 http://13.233.95.244:8000/api/health | python3 -m json.tool
```
**Result:** External access successful - application publicly accessible

### 17. Test Main Page
```bash
# Verify main HTML page loads correctly
curl -s --connect-timeout 10 http://13.233.95.244:8000/ | head -20
```
**Result:** HTML page loads successfully - PRMG Loan Matching Assistant

## Deployment Summary

- **Total SSH commands:** 13
- **Total SCP transfers:** 3
- **Total external curls:** 2
- **Application start attempts:** 2 (first failed, second succeeded)
- **Process ID:** 4229
- **Application status:** Running and accessible on port 8000

## Critical Files Transferred

1. `loanpilot-deploy-minimal.tar.gz` (102KB) - Main deployment package
2. `.env` (126 bytes) - Environment variables with ANTHROPIC_API_KEY
3. `requirements.txt` (101 bytes) - Python dependencies

## Issues Encountered & Resolved

1. **pip not installed** → Installed using `python3 -m ensurepip`
2. **python-multipart missing** → Installed separately after first failure
3. **PYTHONPATH not set** → Added `PYTHONPATH='..:.'` to uvicorn command

## Final State (Initial Deployment)

- Application running on http://13.233.95.244:8000
- Process ID: 4229
- Logs: `/home/ec2-user/loanpilot/web-app/logs/uvicorn.log`
- All health checks passing
- External access confirmed

---

## Post-Deployment Fix (2025-10-17, Later)

### Issue: Context-Aware Queries Failing

**Problem:** Queries with selected programs failing with "Missing required parameters (loan_servicer, program_name)" error.

**Root Cause:** Old parser_anthropic.py doesn't understand context or map natural language to script parameters.

**Solution:** Deployed context-aware parser with Anthropic tool calling.

### Commands Executed for Fix:

1. **Created context_aware_parser.py locally** - New parser with Anthropic tool calling
2. **Updated query_engine.py** - To use new parser with fallback
3. **Deployed to EC2:**
   ```bash
   scp -i brdwch_dev_kp.pem src/context_aware_parser.py ec2-user@13.233.95.244:~/loanpilot/src/
   scp -i brdwch_dev_kp.pem web-app/query_engine.py ec2-user@13.233.95.244:~/loanpilot/web-app/
   ```
4. **Fixed script name mismatch** - Changed `match_programs_by_borrower` to `match_programs`
5. **Redeployed fixed parser:**
   ```bash
   scp -i brdwch_dev_kp.pem src/context_aware_parser.py ec2-user@13.233.95.244:~/loanpilot/src/
   ```
6. **Restarted application:**
   ```bash
   ssh -i brdwch_dev_kp.pem ec2-user@13.233.95.244 \
     "pkill -f uvicorn && cd loanpilot/web-app && \
      PYTHONPATH='..:.' nohup python3 -m uvicorn main:app \
      --host 0.0.0.0 --port 8000 > logs/uvicorn.log 2>&1 &"
   ```

### Current State (v1.1)

- Application running on http://13.233.95.244:8000
- Process ID: 6551
- Parser: **ContextAwareParser with Anthropic tool calling** ✓
- Context-aware queries now working
- All health checks passing
