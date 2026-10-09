#!/bin/bash
set -e

VLLM_HOST="${VLLM_HOST:-localhost}"
VLLM_PORT_1="${VLLM_PORT_1}"
VLLM_MODEL_1="${VLLM_MODEL_1}"
VLLM_PORT_2="${VLLM_PORT_2}"
VLLM_MODEL_2="${VLLM_MODEL_2}"
HEALTH_ENDPOINT_1="http://${VLLM_HOST}:${VLLM_PORT_1}/health"
HEALTH_ENDPOINT_2="http://${VLLM_HOST}:${VLLM_PORT_2}/health"
MAX_WAIT_SECONDS=300
POLL_INTERVAL=5

cleanup() {
    if [[ -n "$VLLM_PID_1" ]] && kill -0 "$VLLM_PID_1" 2>/dev/null; then
        echo "Stopping vLLM server 1 (PID: $VLLM_PID_1)..."
        kill "$VLLM_PID_1" 2>/dev/null || true
        wait "$VLLM_PID_1" 2>/dev/null || true
        echo "vLLM server 1 stopped."
    fi
    if [[ -n "$VLLM_PID_2" ]] && kill -0 "$VLLM_PID_2" 2>/dev/null; then
        echo "Stopping vLLM server 2 (PID: $VLLM_PID_2)..."
        kill "$VLLM_PID_2" 2>/dev/null || true
        wait "$VLLM_PID_2" 2>/dev/null || true
        echo "vLLM server 2 stopped."
    fi
}

trap cleanup EXIT INT TERM

echo "Starting vLLM server 1 (${VLLM_MODEL_1} on port ${VLLM_PORT_1})..."
CUDA_VISIBLE_DEVICES=0 python -m vllm.entrypoints.openai.api_server --model "$VLLM_MODEL_1" --max_model_len 8192 --host "$VLLM_HOST" --port "$VLLM_PORT_1" --api-key msc-test &
VLLM_PID_1=$!
echo "vLLM server 1 started with PID: $VLLM_PID_1"

echo "Starting vLLM server 2 (${VLLM_MODEL_2} on port ${VLLM_PORT_2})..."
CUDA_VISIBLE_DEVICES=1 python -m vllm.entrypoints.openai.api_server --model "$VLLM_MODEL_2" --max_model_len 8192 --host "$VLLM_HOST" --port "$VLLM_PORT_2" &
VLLM_PID_2=$!
echo "vLLM server 2 started with PID: $VLLM_PID_2"

echo "Waiting for vLLM servers to be ready..."
elapsed=0
server1_ready=false
server2_ready=false
while [[ $elapsed -lt $MAX_WAIT_SECONDS ]]; do
    if [[ "$server1_ready" == "false" ]] && curl -s -f "$HEALTH_ENDPOINT_1" >/dev/null 2>&1; then
        echo "vLLM server 1 is ready."
        server1_ready=true
    fi
    if [[ "$server2_ready" == "false" ]] && curl -s -f "$HEALTH_ENDPOINT_2" >/dev/null 2>&1; then
        echo "vLLM server 2 is ready."
        server2_ready=true
    fi

    if [[ "$server1_ready" == "true" ]] && [[ "$server2_ready" == "true" ]]; then
        echo "Both vLLM servers are ready."
        break
    fi

    if ! kill -0 "$VLLM_PID_1" 2>/dev/null; then
        echo "Error: vLLM server 1 process died unexpectedly."
        exit 1
    fi
    if ! kill -0 "$VLLM_PID_2" 2>/dev/null; then
        echo "Error: vLLM server 2 process died unexpectedly."
        exit 1
    fi

    sleep "$POLL_INTERVAL"
    elapsed=$((elapsed + POLL_INTERVAL))
    echo "Still waiting... ($elapsed/${MAX_WAIT_SECONDS}s)"
done

if [[ $elapsed -ge $MAX_WAIT_SECONDS ]]; then
    echo "Error: Timed out waiting for vLLM servers to be ready."
    exit 1
fi

echo "Running certify command..."
export PYTHONPATH=$REPO_ROOT/src
export OPENAI_API_KEY="msc-test"
export OPENAI_BASE_URL="http://${VLLM_HOST}:${VLLM_PORT_1}/v1"
python -m mellea_skills_compiler.cli certify examples/weather/weather_mellea --inference-engine vllm
CERTIFY_EXIT_CODE=$?

echo "Certify command completed with exit code: $CERTIFY_EXIT_CODE"

echo "Shutting down vLLM servers..."
kill "$VLLM_PID_1" 2>/dev/null || true
kill "$VLLM_PID_2" 2>/dev/null || true
wait "$VLLM_PID_1" 2>/dev/null || true
wait "$VLLM_PID_2" 2>/dev/null || true
echo "vLLM servers terminated."

exit $CERTIFY_EXIT_CODE
