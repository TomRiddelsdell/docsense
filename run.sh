#!/bin/bash
# Run the application with Doppler secrets injected

echo "Starting Trading Algorithm Document Analyzer with Doppler..."
echo "Project: docsense | Config: dev"
echo ""

# Run the application with doppler
doppler run -- python main.py
