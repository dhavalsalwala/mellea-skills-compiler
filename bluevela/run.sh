#!/bin/bash
set -e

HEALTH_ENDPOINT_RISK="http://${VLLM_HOST}:${VLLM_RISK_MODEL_PORT}/health"
HEALTH_ENDPOINT_GUARDIAN="http://${VLLM_HOST}:${VLLM_GUARDIAN_MODEL_PORT}/health"
MAX_WAIT_SECONDS=300
POLL_INTERVAL=5

cleanup() {
    if [[ -n "$VLLM_RISK_MODEL_PID" ]] && kill -0 "$VLLM_RISK_MODEL_PID" 2>/dev/null; then
        echo "Stopping vLLM Risk Model server (PID: $VLLM_RISK_MODEL_PID)..."
        kill "$VLLM_RISK_MODEL_PID" 2>/dev/null || true
        wait "$VLLM_RISK_MODEL_PID" 2>/dev/null || true
        echo "vLLM Risk Model server stopped."
    fi
    if [[ -n "$VLLM_GUARDIAN_MODEL_PID" ]] && kill -0 "$VLLM_GUARDIAN_MODEL_PID" 2>/dev/null; then
        echo "Stopping vLLM Guardian Model server (PID: $VLLM_GUARDIAN_MODEL_PID)..."
        kill "$VLLM_GUARDIAN_MODEL_PID" 2>/dev/null || true
        wait "$VLLM_GUARDIAN_MODEL_PID" 2>/dev/null || true
        echo "vLLM Guardian Model server stopped."
    fi
}

trap cleanup EXIT INT TERM

echo "Starting vLLM Risk Model server (${VLLM_RISK_MODEL} on port ${VLLM_RISK_MODEL_PORT})..."
CUDA_VISIBLE_DEVICES=0 python -m vllm.entrypoints.openai.api_server --model "$VLLM_RISK_MODEL" --max_model_len 8192 --host "$VLLM_HOST" --port "$VLLM_RISK_MODEL_PORT" --api-key "$VLLM_API_KEY_RISK_MODEL" &
VLLM_RISK_MODEL_PID=$!
echo "vLLM Risk Model server started with PID: $VLLM_RISK_MODEL_PID"

echo "Starting vLLM Guardian Model server (${VLLM_GUARDIAN_MODEL} on port ${VLLM_GUARDIAN_MODEL_PORT})..."
CUDA_VISIBLE_DEVICES=1 python -m vllm.entrypoints.openai.api_server --model "$VLLM_GUARDIAN_MODEL" --max_model_len 8192 --host "$VLLM_HOST" --port "$VLLM_GUARDIAN_MODEL_PORT" &
VLLM_GUARDIAN_MODEL_PID=$!
echo "vLLM Guardian Model server started with PID: $VLLM_GUARDIAN_MODEL_PID"

echo "Waiting for vLLM servers to be ready..."
elapsed=0
server1_ready=false
server2_ready=false
while [[ $elapsed -lt $MAX_WAIT_SECONDS ]]; do
    if [[ "$server1_ready" == "false" ]] && curl -s -f "$HEALTH_ENDPOINT_RISK" >/dev/null 2>&1; then
        echo "vLLM Risk Model server is ready."
        server1_ready=true
    fi
    if [[ "$server2_ready" == "false" ]] && curl -s -f "$HEALTH_ENDPOINT_GUARDIAN" >/dev/null 2>&1; then
        echo "vLLM Guardian Model server is ready."
        server2_ready=true
    fi

    if [[ "$server1_ready" == "true" ]] && [[ "$server2_ready" == "true" ]]; then
        echo "Both vLLM servers are ready."
        break
    fi

    if ! kill -0 "$VLLM_RISK_MODEL_PID" 2>/dev/null; then
        echo "Error: vLLM Risk Model server process died unexpectedly."
        exit 1
    fi
    if ! kill -0 "$VLLM_GUARDIAN_MODEL_PID" 2>/dev/null; then
        echo "Error: vLLM Guardian Model server process died unexpectedly."
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
export OPENAI_API_KEY="$VLLM_API_KEY_RISK_MODEL"
export OPENAI_BASE_URL="http://${VLLM_HOST}:${VLLM_RISK_MODEL_PORT}/v1"
export VLLM_API_URL_RISK_MODEL: "http://${VLLM_HOST}:${VLLM_RISK_MODEL_PORT}"
export VLLM_API_URL_GUARDIAN_MODEL: "http://${VLLM_HOST}:${VLLM_GUARDIAN_MODEL_PORT}"
python -m mellea_skills_compiler.cli certify examples/weather/weather_mellea --inference-engine vllm
CERTIFY_EXIT_CODE=$?

echo "Certify command completed with exit code: $CERTIFY_EXIT_CODE"

echo "Shutting down vLLM servers..."
kill "$VLLM_RISK_MODEL_PID" 2>/dev/null || true
kill "$VLLM_GUARDIAN_MODEL_PID" 2>/dev/null || true
wait "$VLLM_RISK_MODEL_PID" 2>/dev/null || true
wait "$VLLM_GUARDIAN_MODEL_PID" 2>/dev/null || true
echo "vLLM servers terminated."

exit $CERTIFY_EXIT_CODE
