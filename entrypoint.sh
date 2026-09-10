#!/bin/sh
set -e

export OLLAMA_API_URL="${OLLAMA_HOST}"

# Execute whatever command was passed to docker run (or CMD)
exec "$@"
