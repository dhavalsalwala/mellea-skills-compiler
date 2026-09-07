# Installation

## Prerequisites

Mellea Skills Compiler requires a backend to compile skills. You can use either **Claude Code** or **IBM Bob** — pick whichever you have access to and follow the corresponding setup below.

### Claude configuration

Please ensure that the Claude Code is installed by following the guide here: https://code.claude.com/docs/en/quickstart

Set relevant platform-specific environment variables to communicate with your Claude platform.
For example, Claude via LiteLLM Gateway requires following env variables:

```
export ANTHROPIC_BASE_URL = ""
export ANTHROPIC_AUTH_TOKEN = ""
```

or if you have an ANTHROPIC_API_KEY

```
export ANTHROPIC_API_KEY = ""
export ANTHROPIC_BASE_URL = ""
```

### IBM Bob configuration

Please ensure that the IBM Bob shell is installed by following the guide here: https://bob.ibm.com/docs/shell/getting-started/install-and-setup. Only Bob v2.x.x is supported.

IBM Bob authentication works via IBMid, SSO and API key authentication. Please check https://bob.ibm.com/docs/shell/getting-started/install-and-setup#authentication for more details. Set relevant platform-specific environment variables to communicate with your IBM Bob platform.

    For example, API key authentication requires following env variable:

    ```
    export BOB_API_KEY = ""
    ```

### Install project code

Clone code repository

```
git clone https://github.com/generative-computing/mellea-skills-compiler
```

Create Python environment and install library

```bash
# Requires Python >=3.11, <3.14.4
python3 -m venv .venv
source .venv/bin/activate

pip install -e .
```


#### Choose Inference Engine

| Engine | Use Case | Deployment | Configuration | Characteristics |
|--------|----------|-----------|---------------|-----------------|
| **Ollama** | Development, testing, prototyping | Local workstation | `export OLLAMA_API_URL=<api-url>` (default: `http://localhost:11434`) | Lightweight, easy setup, minimal dependencies, no external services required |
| **vLLM** | Production deployments, high-throughput | Local instance or hosted service | `export VLLM_API_URL_RISK_MODEL=<api-url>` and `export VLLM_API_URL_GUARDIAN_MODEL=<api-url>` | Optimized serving, dynamic batching, GPU acceleration, supports multiple model endpoints |

**Engine Selection**: Specify via `--inference-engine` flag in `certify` and `run` commands. Engines are swappable without recompiling skills—risk identification and Guardian verdicts run on the selected backend transparently.


- For Ollama, set API URL in the environment variables:

  ```bash
  export OLLAMA_API_URL=http://localhost:11434 # Ollama api URL
  ```

- For online vLLM, set API URL and API KEY(optionally) in the environment variables:

  ```bash
  # api url and api key of hosted risk model
  export VLLM_API_URL_RISK_MODEL=http://localhost:8000
  export VLLM_API_KEY_RISK_MODEL=YOUR_API_KEY

  # api url and api key of hosted guardian model
  export VLLM_API_URL_GUARDIAN_MODEL=http://localhost:8001
  export VLLM_API_KEY_GUARDIAN_MODEL=YOUR_API_KEY
  ```

- For offline vLLM, there is no need to set API URL and API KEY in the environment variables. Please install `vllm` using pip when using the offline service.
  ```bash
  pip install vllm
  ```
