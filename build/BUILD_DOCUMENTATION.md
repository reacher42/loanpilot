# LoanPilot Production Build Documentation

**INTERNAL USE ONLY - NOT FOR CUSTOMER DISTRIBUTION**

## Overview

This document describes the process for building secure, customer-specific Docker images of LoanPilot with:
- Bytecode compilation (no source code)
- Time-limited license validation
- Comment/docstring removal
- Minimal image size

---

## Build Architecture

### Multi-Stage Build Process

```
Source Code
    ↓
[Stage 1: Builder]
    - Strip comments/docstrings (AST transformation)
    - Compile to bytecode (.pyc files)
    - Remove .py source files
    ↓
[Stage 2: Runtime]
    - Copy only bytecode
    - Copy dependencies
    - Embed license token
    - Create minimal runtime image
    ↓
Production Image
```

### Security Features

1. **No Source Code**: Only .pyc bytecode files in final image
2. **License Validation**: HMAC-signed tokens with expiry dates
3. **Minimal Attack Surface**: No docs, tests, or utility scripts
4. **Non-root User**: Runs as unprivileged `loanpilot` user
5. **No Comments**: All docstrings and comments stripped

---

## Building Images

### Quick Build (Demo Customer)

```bash
cd /path/to/loanpilot

# Build with defaults
./build/build_production.sh

# Results in: loanpilot:DEMO-1.0.0
```

### Customer-Specific Build

```bash
# Build for specific customer with expiry date
./build/build_production.sh \
  --customer ACME-Corp \
  --expiry 2025-12-31 \
  --version 1.0.0

# Results in: loanpilot:ACME-Corp-1.0.0
```

### Build Parameters

| Parameter | Description | Default | Example |
|-----------|-------------|---------|---------|
| `--customer` | Customer identifier | DEMO | ACME-Corp |
| `--expiry` | License expiry date | 2025-12-31 | 2026-06-30 |
| `--version` | Version number | 1.0.0 | 1.2.3 |

---

## License Token Generation

### How Tokens Work

Tokens use HMAC-SHA256 signatures to prevent tampering:

```
Format: {DATE}:{CUSTOMER_ID}:{SIGNATURE}
Example: 2025-12-31:ACME-Corp:a1b2c3d4e5f67890
```

**Signature Calculation:**
```python
import hmac
import hashlib

SECRET_KEY = b"loanpilot-2024-secure-key-change-per-customer"
message = f"{date}:{customer_id}".encode()
signature = hmac.new(SECRET_KEY, message, hashlib.sha256).hexdigest()[:16]
token = f"{date}:{customer_id}:{signature}"
```

### Manual Token Generation

```bash
# Generate token for customer
python3 -c "
import hmac
import hashlib

secret = b'loanpilot-2024-secure-key-change-per-customer'
date = '2025-12-31'
customer = 'ACME-Corp'
message = f'{date}:{customer}'.encode()
sig = hmac.new(secret, message, hashlib.sha256).hexdigest()[:16]
print(f'{date}:{customer}:{sig}')
"
```

### License Token Security

- **SECRET_KEY**: Embedded in `web-app/license_validator.py`
- **Change per customer**: Optional (use different SECRET_KEY for each customer)
- **Signature length**: 16 chars (128-bit security)
- **Cannot be forged**: Requires SECRET_KEY to generate valid signature

---

## Export & Distribution

### Create Distribution Package

```bash
# Export built image
./build/export_image.sh \
  --customer ACME-Corp \
  --version 1.0.0 \
  --output ./distribution

# Results in: ./distribution/loanpilot-ACME-Corp-v1.0.0.tar.gz
```

### Package Contents

```
loanpilot-ACME-Corp-v1.0.0/
├── loanpilot-ACME-Corp-v1.0.0.tar.gz  # Docker image (~90MB)
├── docker-compose.yml                  # Container config
├── .env.example                        # API key template
├── install.sh                          # Installation script
├── verify.sh                           # Health check script
├── README.txt                          # Customer instructions
├── SHA256SUMS                          # Checksum verification
└── data/v3/                            # Sample data
    └── Non-QM_Matrix.xlsx - Attributes.tsv
```

### Distribution Package Size

| Component | Uncompressed | Compressed |
|-----------|--------------|------------|
| Docker image | ~250MB | ~90MB |
| Sample data | ~60KB | ~15KB |
| Scripts/docs | ~10KB | ~3KB |
| **Total** | ~250MB | ~90MB |

---

## Testing Built Images

### Local Testing

```bash
# Load image
docker load -i distribution/loanpilot-ACME-Corp-v1.0.0/loanpilot-ACME-Corp-v1.0.0.tar.gz

# Run container
docker run -d \
  --name loanpilot-test \
  -p 8000:8000 \
  -e ANTHROPIC_API_KEY=test-key \
  loanpilot:ACME-Corp-1.0.0

# Check logs
docker logs loanpilot-test

# Test health
curl http://localhost:8000/api/health

# Cleanup
docker stop loanpilot-test && docker rm loanpilot-test
```

### Verification Checklist

- [ ] No .py source files in image (except `__init__.py`)
- [ ] Only .pyc bytecode files present
- [ ] No documentation files (.md)
- [ ] No utils/ directory
- [ ] No test files
- [ ] License validation works (startup check)
- [ ] Application starts successfully
- [ ] Health endpoint responds
- [ ] API endpoints functional
- [ ] Database operations work

### Verification Commands

```bash
IMAGE_TAG="loanpilot:ACME-Corp-1.0.0"

# Check for source files (should be 0 or only __init__.py)
docker run --rm $IMAGE_TAG find /app -name "*.py" ! -name "__init__.py" | wc -l

# Check for bytecode files (should be many)
docker run --rm $IMAGE_TAG find /app -name "*.pyc" | wc -l

# Check for docs (should be 0)
docker run --rm $IMAGE_TAG find /app -name "*.md" | wc -l

# Check for utils (should fail with error)
docker run --rm $IMAGE_TAG test -d /app/utils && echo "EXISTS" || echo "NOT FOUND"

# Check license token
docker inspect $IMAGE_TAG --format='{{.Config.Env}}' | grep LICENSE
```

---

## Image Contents Analysis

### What's Included

**Application Code (bytecode only):**
- `/app/web-app/*.pyc` - FastAPI application
- `/app/src/*.pyc` - Core modules
- `/app/data/v3/*.tsv` - Sample data

**Static Files:**
- `/app/web-app/static/` - HTML, CSS, JS

**Dependencies:**
- `/root/.local/` - Python packages

### What's Excluded

- All `.py` source files (except essential `__init__.py`)
- All `.md` documentation
- `utils/` directory
- `tests/` directory
- Helper scripts
- Build files
- Git history

### Image Size Breakdown

```bash
# Analyze image layers
docker history loanpilot:ACME-Corp-1.0.0

# Detailed analysis with dive
dive loanpilot:ACME-Corp-1.0.0
```

---

## License Management

### Setting Expiry Dates

**Trial licenses** (30-90 days):
```bash
./build/build_production.sh \
  --customer Trial-ACME \
  --expiry $(date -d '+30 days' +%Y-%m-%d)
```

**Annual licenses**:
```bash
./build/build_production.sh \
  --customer ACME-Corp \
  --expiry 2026-01-01
```

**Permanent/Long-term**:
```bash
./build/build_production.sh \
  --customer ACME-Premium \
  --expiry 2035-12-31
```

### License Renewal Process

1. **Customer requests renewal**
2. **Build new image with extended date:**
   ```bash
   ./build/build_production.sh \
     --customer ACME-Corp \
     --expiry 2026-12-31 \
     --version 1.0.1
   ```
3. **Export and send to customer:**
   ```bash
   ./build/export_image.sh \
     --customer ACME-Corp \
     --version 1.0.1
   ```
4. **Customer updates**: Load new image and restart

### Handling Expiry

**Application behavior when expired:**
- Fails to start (startup check)
- Returns HTTP 403 on all requests (middleware check)
- Shows friendly HTML error page
- Logs license expiry

**Warning period (30 days before expiry):**
- Application continues to work
- Logs warning messages
- No user-facing warnings (silent grace period)

---

## Customization Per Customer

### Unique SECRET_KEY Per Customer

For enhanced security, use different SECRET_KEY for each customer:

1. **Edit `web-app/license_validator.py`** before building:
   ```python
   SECRET_KEY = b"customer-specific-secret-key-ACME-Corp-2024"
   ```

2. **Build image**:
   ```bash
   ./build/build_production.sh --customer ACME-Corp --expiry 2025-12-31
   ```

3. **Document SECRET_KEY** in secure location (password manager)

### Custom Branding (Optional)

Edit `web-app/static/index.html` before building:
- Replace "LoanPilot" with "LoanPilot for ACME Corp"
- Add customer logo
- Customize colors

### Different Port Mapping

Customer can change port in their `docker-compose.yml`:
```yaml
ports:
  - "9000:8000"  # Custom port
```

---

## Troubleshooting Builds

### Build Fails: "Module not found"

**Cause**: Missing dependencies in requirements.txt

**Fix**:
```bash
# Add missing package
echo "astor==0.8.1" >> requirements.txt
./build/build_production.sh
```

### Build Fails: AST Parse Error

**Cause**: Syntax error in Python files

**Fix**:
```bash
# Find problematic file
python3 -m py_compile web-app/*.py

# Fix syntax error
# Rebuild
```

### Image Too Large

**Current size**: ~250MB uncompressed, ~90MB compressed

**To reduce**:
1. Use Alpine base image (risky, compatibility issues)
2. Remove unused dependencies from requirements.txt
3. Exclude large files in .dockerignore.production

### License Validation Not Working

**Check token generation**:
```bash
python3 web-app/license_validator.py
```

**Check embedded token**:
```bash
docker inspect loanpilot:CUSTOMER-1.0.0 --format='{{.Config.Env}}' | grep LICENSE
```

### Application Won't Start

**Check logs**:
```bash
docker logs loanpilot-test
```

**Common issues**:
- Missing `__init__.py` files
- Broken imports (bytecode compilation issue)
- Missing dependencies

---

## Version Management

### Semantic Versioning

Format: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes, incompatible API
- **MINOR**: New features, backwards compatible
- **PATCH**: Bug fixes

### Tagging Strategy

```bash
# Build with version
./build/build_production.sh --version 1.2.3 --customer ACME

# Results in tags:
# - loanpilot:ACME-1.2.3
# - loanpilot:ACME-latest
```

### Release Checklist

- [ ] Test thoroughly in staging
- [ ] Update VERSION in build scripts
- [ ] Build production images
- [ ] Test exported packages
- [ ] Update customer documentation
- [ ] Create release notes
- [ ] Notify customers
- [ ] Archive old versions

---

## Security Considerations

### What This Protects Against

✓ **Casual inspection**: No readable source code
✓ **Quick modifications**: Bytecode harder to patch
✓ **Documentation leaks**: No internal docs in image
✓ **Unauthorized use**: Time-limited licenses
✓ **License bypass**: HMAC-signed tokens

### What This Doesn't Protect Against

✗ **Determined reverse engineering**: Bytecode can be decompiled
✗ **Clock manipulation**: Customer can change system time
✗ **Container inspection**: Can extract files from image
✗ **Memory dumps**: Can analyze running process
✗ **Network analysis**: Can intercept API calls

### Defense in Depth

**Primary defenses**:
1. Legal agreements and contracts
2. API key control (you control Anthropic access)
3. Customer relationship management
4. Regular license renewals

**Secondary defenses** (this build system):
1. Code obfuscation (bytecode)
2. License validation
3. Minimal attack surface

---

## Maintenance

### Regular Tasks

**Monthly**:
- Review expiring licenses
- Test build process
- Update dependencies

**Quarterly**:
- Security audit
- Update base images
- Review customer feedback

**Annually**:
- Major version releases
- Architecture review
- License renewal campaigns

### Updating Dependencies

```bash
# Update requirements.txt
pip list --outdated

# Test compatibility
pip install -r requirements.txt
python3 -m pytest tests/

# Rebuild and test
./build/build_production.sh
```

### Rotating SECRET_KEY

**If SECRET_KEY is compromised**:

1. Generate new SECRET_KEY
2. Update `web-app/license_validator.py`
3. Rebuild ALL customer images
4. Distribute new images to ALL customers
5. Document incident

---

## Build Performance

### Typical Build Times

- **Clean build**: 5-8 minutes
- **Cached build**: 2-3 minutes
- **Export package**: 1-2 minutes

### Optimization Tips

```bash
# Use BuildKit for faster builds
export DOCKER_BUILDKIT=1

# Parallel builds (multiple customers)
./build/build_production.sh --customer ACME & \
./build/build_production.sh --customer BETA & \
wait
```

---

## Customer Delivery

### Secure Transfer Methods

1. **Encrypted email** (for small packages <25MB)
2. **Secure FTP/SFTP**
3. **Private S3 bucket** with pre-signed URLs
4. **Customer portal** with download links

### Delivery Checklist

- [ ] Build image for customer
- [ ] Export distribution package
- [ ] Verify SHA256 checksum
- [ ] Test installation script
- [ ] Prepare transfer method
- [ ] Send package securely
- [ ] Send installation instructions
- [ ] Provide support contact
- [ ] Document delivery date
- [ ] Schedule follow-up

---

## Contact & Support

**Internal Build Issues**:
- Review build logs
- Check this documentation
- Contact DevOps team

**Customer Issues**:
- Guide to CUSTOMER_INSTALLATION_GUIDE.md
- Provide support@loanpilot.com contact

---

## Appendix

### File Locations

```
loanpilot/
├── Dockerfile.production          # Production Dockerfile
├── .dockerignore.production       # Aggressive exclusions
├── build/
│   ├── prepare_sources.py         # Comment/docstring stripper
│   ├── build_production.sh        # Build automation
│   ├── export_image.sh            # Export/packaging
│   ├── BUILD_DOCUMENTATION.md     # This file
│   └── CUSTOMER_INSTALLATION_GUIDE.md
└── web-app/
    └── license_validator.py       # License validation module
```

### Example Build Session

```bash
# Full workflow: build → export → test

# 1. Build image
./build/build_production.sh \
  --customer TestCorp \
  --expiry 2025-06-30 \
  --version 1.0.0

# 2. Export package
./build/export_image.sh \
  --customer TestCorp \
  --version 1.0.0

# 3. Test installation
cd distribution/loanpilot-TestCorp-v1.0.0/
./install.sh

# 4. Verify
./verify.sh

# 5. Package for delivery
cd ..
tar -czf loanpilot-TestCorp-v1.0.0.tar.gz loanpilot-TestCorp-v1.0.0/
```

---

**Last Updated**: 2025-11-18
**Version**: 1.0.0
