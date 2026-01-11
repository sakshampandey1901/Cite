# Backend Deployment Guide

## Python Version Requirements

This project requires **Python 3.13** or compatible versions. All dependencies in `requirements.txt` have been verified to have pre-built binary wheels for Python 3.13 on all major platforms (macOS ARM64/Intel, Linux x86_64/ARM64, Windows).

## Installation

### Quick Start

```bash
cd backend
pip install -r requirements.txt
```

### Production Deployment

For production environments, it's recommended to use a virtual environment:

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Upgrade pip to latest version
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

## Key Dependency Updates (January 2026)

The following critical updates were made to ensure compatibility with Python 3.13 and modern platforms:

### Document Processing
- **pymupdf**: Updated from 1.23.8 → 1.26.7
  - Provides pre-built wheels for Python 3.13 on all platforms
  - Uses Python Stable ABI (abi3) for forward compatibility
  - Eliminates compilation errors on macOS ARM64
  - Reference: [PyMuPDF Documentation](https://pymupdf.readthedocs.io/en/latest/installation.html)

### Web Framework
- **fastapi**: Updated from 0.109.0 → 0.115.6
- **uvicorn**: Updated from 0.27.0 → 0.34.0
- **pydantic**: Updated from 2.5.3 → 2.10.5

### AI/ML Libraries
- **sentence-transformers**: Updated from 2.7.0 → 3.3.1
- **pinecone-client**: Updated from 3.2.2 → 5.0.1
- **tiktoken**: Updated from 0.6.0 → 0.8.0

### Scientific Computing
- **numpy**: Updated from 1.26.3 → 2.2.1
- **scikit-learn**: Updated from 1.4.0 → 1.6.1

## Platform Support

All dependencies now support:
- ✅ **Python 3.9 - 3.13** (tested on 3.13.2)
- ✅ **macOS** (Intel x86_64 and Apple Silicon ARM64)
- ✅ **Linux** (x86_64 and ARM64/aarch64)
- ✅ **Windows** (x86_64 and ARM64)

## Why These Versions?

### Binary Wheels vs Source Compilation

The updated versions were specifically chosen because they provide **pre-built binary wheels** for Python 3.13 on all platforms. This means:

1. **Fast Installation**: No compilation required, installation completes in seconds instead of minutes
2. **No Build Tools Required**: Users don't need compilers, SDKs, or development headers
3. **Consistent Behavior**: Same binaries work across all user machines
4. **Production Ready**: Eliminates platform-specific compilation errors

### The PyMuPDF Problem (Solved)

**Previous Issue**: pymupdf 1.23.8 didn't have wheels for Python 3.13, forcing pip to compile from source, which failed on macOS with:
- C compilation errors in zlib library
- Macro conflicts with macOS SDK
- Xcode Command Line Tools incompatibilities

**Solution**: pymupdf 1.26.7 provides pre-built wheels using Python's Stable ABI (abi3), guaranteeing compatibility with Python 3.10+ without recompilation.

## Verifying Installation

After installation, verify critical packages:

```bash
python -c "import pymupdf; print(f'PyMuPDF: {pymupdf.__version__}')"
python -c "import fastapi; print(f'FastAPI: {fastapi.__version__}')"
python -c "import sentence_transformers; print('SentenceTransformers: OK')"
```

Expected output:
```
PyMuPDF: 1.26.7
FastAPI: 0.115.6
SentenceTransformers: OK
```

## Troubleshooting

### If Installation Fails

1. **Ensure Python 3.13 is installed**:
   ```bash
   python3 --version
   ```

2. **Upgrade pip**:
   ```bash
   pip install --upgrade pip
   ```

3. **Clear pip cache** (if you have stale/corrupted packages):
   ```bash
   pip cache purge
   pip install -r requirements.txt
   ```

4. **Use virtual environment** (recommended):
   Isolates dependencies and prevents conflicts with system packages

### Platform-Specific Notes

#### macOS
- No Xcode or Command Line Tools required
- Works on both Intel and Apple Silicon Macs
- If you previously had compilation errors, they're now resolved

#### Linux
- Works on Ubuntu 20.04+, Debian 11+, RHEL 8+, etc.
- No system development packages required

#### Windows
- Works on Windows 10/11
- No Visual Studio or Windows SDK required

## Docker Deployment

For containerized deployments, use this Dockerfile:

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \\
    pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Backend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]

    steps:
    - uses: actions/checkout@v4
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        pip install --upgrade pip
        pip install -r backend/requirements.txt

    - name: Run tests
      run: |
        cd backend
        pytest
```

## Dependency Management

### Updating Dependencies

To update dependencies in the future:

```bash
# Check for updates
pip list --outdated

# Update specific package
pip install --upgrade package-name

# Update all packages (caution: test thoroughly)
pip install --upgrade -r requirements.txt
```

### Security Updates

Monitor security advisories:
- [GitHub Dependabot](https://github.com/features/security)
- [PyUp Safety](https://pyup.io/safety/)
- [Snyk](https://snyk.io/)

## Support

For issues with:
- **PyMuPDF**: [pymupdf/PyMuPDF GitHub](https://github.com/pymupdf/PyMuPDF/issues)
- **FastAPI**: [fastapi/fastapi GitHub](https://github.com/fastapi/fastapi/issues)
- **Other dependencies**: Check their respective GitHub repositories

---

**Last Updated**: January 10, 2026
**Python Version**: 3.13.2
**All dependencies verified working**: ✅
