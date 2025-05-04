#!/bin/bash
# Script to run pytest for the fuel_blending package

echo "Ensuring execution from project root: /home/ubuntu/fuel_blending"
cd /home/ubuntu/fuel_blending || exit 1

echo "Running pytest..."
python3 -m pytest

