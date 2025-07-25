#!/bin/bash
# configure_gunicorn_env.sh
# This script updates the Gunicorn service file to load environment variables from a .env file.

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Configuring Gunicorn to use .env file...${NC}"

# Find Gunicorn service file
SERVICE_FILE=$(systemctl status gunicorn | grep -oE '/etc/systemd/system/gunicorn.service')

if [ -z "$SERVICE_FILE" ]; then
    echo -e "${YELLOW}Gunicorn service file not found in /etc/systemd/system/. Please locate it manually and add the EnvironmentFile directive.${NC}"
    exit 1
fi

echo "Found Gunicorn service file at: $SERVICE_FILE"

# Check if EnvironmentFile is already set
if grep -q "EnvironmentFile" "$SERVICE_FILE"; then
    echo "Gunicorn service is already configured to use an environment file."
else
    # Add EnvironmentFile directive
    sudo sed -i '/\[Service\]/a EnvironmentFile=/var/www/ost/.env' "$SERVICE_FILE"
    echo "Added EnvironmentFile directive to Gunicorn service."
fi

# Reload systemd and restart Gunicorn
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "Restarting Gunicorn service..."
sudo systemctl restart gunicorn

echo -e "${GREEN}Gunicorn configuration updated successfully!${NC}" 