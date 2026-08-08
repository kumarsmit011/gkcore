#!/bin/bash
set -e

echo "Initializing database migrations..."
gkdb --init
gkdb --migrate

# Optional: Check if the config file exists
if [ "$ENVIRONMENT" ]; then
    echo "Starting GKCore with ${ENVIRONMENT} config..."
    exec gkserve --${ENVIRONMENT}
elif [ "$PYRAMID_CONFIG_FILE" ]; then
    echo "Starting GKCore with config: ${PYRAMID_CONFIG_FILE}..."
    exec gkserve ${PYRAMID_CONFIG_FILE}
else
    echo "Starting GKCore with production config..."
    gkserve
fi
