#!/bin/bash
# SilentHUD Native Launcher
# Runs the application directly from source to ensure full system environment access.

# Navigate to project directory
cd "/home/isaacdev14/Desktop/projects/personal projects/SilentHUD"

# Run with virtual environment python
# Pass all arguments to the script
sudo ./venv/bin/python main.py "$@"
