#!/bin/bash
# Install requests library and dependencies for TrueNAS Scale

echo "=========================================="
echo "Installing Python requests library"
echo "=========================================="

# Create local Python packages directory
echo "[1/6] Creating local packages directory..."
mkdir -p /root/.local/lib/python3.11/site-packages

# Move to temp directory
cd /tmp

# Download requests and dependencies
echo "[2/6] Downloading requests..."
curl -L https://files.pythonhosted.org/packages/63/70/2bf7780ad2d390a8d301ad0b550f1581eadbd9a20f896afe06353c2a2913/requests-2.32.3-py3-none-any.whl -o requests.whl

echo "[3/6] Downloading urllib3..."
curl -L https://files.pythonhosted.org/packages/76/c6/c88e154df9c4e1a2a66ccf0005a88dfb2650c1dffb6f5ce603dfbd452ce3/urllib3-2.2.2-py3-none-any.whl -o urllib3.whl

echo "[4/6] Downloading certifi..."
curl -L https://files.pythonhosted.org/packages/12/90/3c9ff0512038035f59d279fddeb79f5f1eccd8859f06d6163c58798b9487/certifi-2024.8.30-py3-none-any.whl -o certifi.whl

echo "[5/6] Downloading charset-normalizer..."
curl -L https://files.pythonhosted.org/packages/63/09/c1bc53dab74b1816a00d8d030de5bf98f724c52c1635e07681d312f20be8/charset_normalizer-3.3.2-py3-none-any.whl -o charset_normalizer.whl

echo "[6/6] Downloading idna..."
curl -L https://files.pythonhosted.org/packages/d2/53/d23a97e0a2c690d40b165d1062e2c4ccc796be458a1ce59f6ba030434663/idna-3.8-py3-none-any.whl -o idna.whl

# Extract all packages
echo ""
echo "Installing packages..."
python3 -m zipfile -e requests.whl /root/.local/lib/python3.11/site-packages/
python3 -m zipfile -e urllib3.whl /root/.local/lib/python3.11/site-packages/
python3 -m zipfile -e certifi.whl /root/.local/lib/python3.11/site-packages/
python3 -m zipfile -e charset_normalizer.whl /root/.local/lib/python3.11/site-packages/
python3 -m zipfile -e idna.whl /root/.local/lib/python3.11/site-packages/

# Clean up
echo ""
echo "Cleaning up temporary files..."
rm -f /tmp/*.whl

# Test installation
echo ""
echo "=========================================="
echo "Testing installation..."
echo "=========================================="
python3 -c "import requests; print(f'✓ requests {requests.__version__} installed successfully!')"

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Installation complete!"
    echo ""
    echo "You can now run WANwatcher with:"
    echo "  python3 /root/wanwatcher/wanwatcher.py"
else
    echo ""
    echo "✗ Installation failed. Please check the errors above."
fi

cd /root
