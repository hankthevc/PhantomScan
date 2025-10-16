#!/bin/bash
set -e

echo "🔭 PhantomScan Quick Start"
echo "=========================="
echo ""

# Check Python version
if ! command -v python3.11 &> /dev/null; then
    echo "❌ Python 3.11+ is required but not found."
    echo "   Please install Python 3.11 or higher."
    exit 1
fi

echo "✓ Python 3.11+ detected"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3.11 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -e .[dev]

echo "✓ Dependencies installed"

# Create data directories
echo "📁 Creating data directories..."
mkdir -p data/{raw,processed,feeds,samples}

echo "✓ Data directories created"

# Check if sample data exists
if [ ! -f "data/samples/pypi_seed.jsonl" ]; then
    echo "⚠️  Warning: Sample seed files not found. Pipeline will run in live mode."
    echo "   To run offline demo, ensure data/samples/*.jsonl exist."
fi

# Run pipeline in offline mode if seed data exists
if [ -f "data/samples/pypi_seed.jsonl" ]; then
    echo ""
    echo "🚀 Running radar pipeline (offline mode with sample data)..."
    export RADAR_OFFLINE=1
    radar run-all
    echo "✓ Pipeline complete"
else
    echo ""
    echo "🌐 Running radar pipeline (live mode)..."
    echo "   This will fetch data from PyPI and npm..."
    read -p "   Continue? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        radar run-all
        echo "✓ Pipeline complete"
    else
        echo "Skipping pipeline run."
    fi
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Launch Streamlit app:  make app"
echo "  2. Launch FastAPI:        make api"
echo "  3. Run tests:             make test"
echo "  4. View feeds:            ls -l data/feeds/"
echo ""
echo "📚 For more information, see README.md and DEPLOYMENT.md"
