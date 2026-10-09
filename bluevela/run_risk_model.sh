#!/bin/bash
set -e

VLLM_HOST="${VLLM_HOST:-localhost}"
VLLM_PORT="${VLLM_PORT:-8000}"
VLLM_MODEL="${VLLM_MODEL:-ibm-granite/granite-4.1-3b}"
HEALTH_ENDPOINT="http://${VLLM_HOST}:${VLLM_PORT}/health"
MAX_WAIT_SECONDS=300
POLL_INTERVAL=5

echo "Starting vLLM server..."
if [[ -n "$VLLM_MODEL" ]]; then
    python -m vllm.entrypoints.openai.api_server --model "$VLLM_MODEL" --host "$VLLM_HOST" --port "$VLLM_PORT" &
else
    echo "No vLLM model provided."
    exit 1
fi
VLLM_PID=$!
echo "vLLM server started with PID: $VLLM_PID"

echo "Waiting for vLLM server to be ready at $HEALTH_ENDPOINT..."
elapsed=0
while [[ $elapsed -lt $MAX_WAIT_SECONDS ]]; do
    if curl -s -f "$HEALTH_ENDPOINT" >/dev/null 2>&1; then
        echo "vLLM server is ready."
        break
    fi

    if ! kill -0 "$VLLM_PID" 2>/dev/null; then
        echo "Error: vLLM server process died unexpectedly."
        exit 1
    fi

    sleep "$POLL_INTERVAL"
    elapsed=$((elapsed + POLL_INTERVAL))
    echo "Still waiting... ($elapsed/${MAX_WAIT_SECONDS}s)"
done

if [[ $elapsed -ge $MAX_WAIT_SECONDS ]]; then
    echo "Error: Timed out waiting for vLLM server to be ready."
    exit 1
fi
