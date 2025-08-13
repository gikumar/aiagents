#!/bin/bash
# requirements_sync.sh

# Set the backend directory path
BACKEND_DIR="backend"
REQUIREMENTS_FILE="$BACKEND_DIR/requirements.txt"

# Check if backend directory exists
if [ ! -d "$BACKEND_DIR" ]; then
    echo "Error: $BACKEND_DIR directory not found!"
    exit 1
fi

# Check if requirements.txt exists
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "Error: $REQUIREMENTS_FILE not found!"
    exit 1
fi

echo "=== CURRENT REQUIREMENTS AUDIT ==="
echo "Working directory: $BACKEND_DIR"
echo "Requirements file: $REQUIREMENTS_FILE"
echo ""

echo "Packages installed but NOT in requirements.txt:"
pip freeze | grep -v -f "$REQUIREMENTS_FILE"

echo -e "\nPackages in requirements.txt but NOT installed:"
comm -23 <(sort "$REQUIREMENTS_FILE") <(pip freeze | sort)

echo -e "\n=== GENERATING NEW REQUIREMENTS ==="
echo "Installing pipreqs..."
pip install pipreqs

echo "Backing up current requirements.txt..."
cp "$REQUIREMENTS_FILE" "$REQUIREMENTS_FILE.backup"

echo "Generating new requirements.txt based on code imports..."
pipreqs "$BACKEND_DIR" --force

echo -e "\n=== COMPARISON ==="
echo "Old requirements.txt saved as $REQUIREMENTS_FILE.backup"
echo "New requirements.txt generated!"
echo -e "\nDifference:"
if diff "$REQUIREMENTS_FILE.backup" "$REQUIREMENTS_FILE" >/dev/null; then
    echo "No changes - files are identical"
else
    echo "Changes detected:"
    diff "$REQUIREMENTS_FILE.backup" "$REQUIREMENTS_FILE"
fi

echo -e "\n=== SUMMARY ==="
echo "✓ Backup created: $REQUIREMENTS_FILE.backup"
echo "✓ New requirements generated: $REQUIREMENTS_FILE"
echo "✓ Review the differences above and commit if satisfied"