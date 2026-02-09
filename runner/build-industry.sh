#!/bin/sh
set -e

# ---- Configuration ----
VENV_DIR=".venv"
PYTHON_BIN="python3"
REQUIREMENTS_FILE="requirements.txt"
BUILD_DIR="build"

BUILD_CV_INDUSTRY_SCRIPT="build-cv-industry.py"

# ---- Create virtual environment if it doesn't exist ----
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    $PYTHON_BIN -m venv "$VENV_DIR"
fi

# ---- Activate virtual environment ----
echo "Activating virtual environment..."
. "$VENV_DIR/bin/activate"

# ---- Upgrade pip ----
pip install --upgrade pip

# ---- Install requirements ----
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "Installing requirements..."
    pip install -r "$REQUIREMENTS_FILE"
else
    echo "ERROR: $REQUIREMENTS_FILE not found"
    exit 1
fi

# ---- Enter build directory ----
if [ ! -d "$BUILD_DIR" ]; then
    echo "ERROR: $BUILD_DIR directory not found"
    exit 1
fi

cd "$BUILD_DIR"

# ---- Run build script ----
if [ -f "$BUILD_CV_INDUSTRY_SCRIPT" ]; then
    echo "Running $BUILD_CV_INDUSTRY_SCRIPT..."
    python "$BUILD_CV_INDUSTRY_SCRIPT"
else
    echo "ERROR: $BUILD_CV_INDUSTRY_SCRIPT not found in $BUILD_DIR"
    exit 1
fi

echo "Industry CV build completed successfully."
