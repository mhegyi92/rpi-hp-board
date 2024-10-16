#!/bin/bash

app_name="rpi-hp-board"
app_directory="/home/rpi/rpi-hp-board"
user="rpi"

# Create the systemd service file
service_file="/etc/systemd/system/${app_name}.service"

echo "Creating systemd service for ${app_name}..."

sudo bash -c "cat > $service_file" <<EOL
[Unit]
Description=${app_name} python application
After=multi-user.target

[Service]
Type=simple
ExecStart=${app_directory}/.venv/bin/python ${app_directory}/main.py
WorkingDirectory=${app_directory}
Restart=always
User=${user}
Environment="DISPLAY=:0"
Environment="WAYLAND_DISPLAY=wayland-0"

[Install]
WantedBy=multi-user.target
EOL

# Reload systemd to apply the new service
echo "Reloading systemd daemon for ${app_name}..."
sudo systemctl daemon-reload

# Enable the service to start on boot
echo "Enabling ${app_name} service..."
sudo systemctl enable ${app_name}.service

# Start the service immediately
echo "Starting ${app_name} service..."
sudo systemctl start ${app_name}.service

echo "${app_name} service created and started."
