# **Simplicity: An Universal BRC-20 Indexer & OPI Framework**

[![CI/CD Pipeline](https://github.com/The-Universal-BRC-20-Extension/simplicity/actions/workflows/ci.yml/badge.svg)](https://github.com/The-Universal-BRC-20-Extension/simplicity/actions/workflows/ci.yml)
[![Test Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://github.com/The-Universal-BRC20-Extension/simplicity)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/release/python-3110/)

> **The best protocol is the one we build together — block by block.**

**Simplicity** is an open-source, production-ready indexer for the Universal BRC-20 Extension, featuring a powerful and modular **Operation Proposal Improvement (OPI)** framework. It provides a robust, high-performance, and verifiable implementation of the BRC-20 standards and serves as the foundation for an evolving ecosystem of advanced DeFi protocols.

This indexer is the consensus engine that powers the entire ecosystem, transforming raw on-chain data into a structured, queryable state according to a growing set of community-driven standards.

---

## Key Features

- **High Performance:** Sub-20ms API response times for cached queries, optimized for real-time applications.
- **Extensively Tested:** +80% test coverage with a comprehensive suite of unit, integration, and protocol-level tests.
- **Protocol-Complete:** Full implementation of the Universal BRC-20 standard and a growing list of OPIs.
- **Modular OPI Framework:** A pluggable architecture that allows for the seamless addition of new operations like **OPI-1 (`swap`)** without disrupting core functionality.
- **Dockerized:** One-command deployment with Docker Compose for ease of setup.
- **Standardized API:** RESTful API with comprehensive and auto-generated OpenAPI/Swagger documentation.

---

## Architecture: The OPI Framework

Simplicity is architected around a modular **OPI (Operation Proposal Improvement)** framework. This design separates the core indexing engine from the specific logic of each protocol, allowing the system to be extended safely and efficiently.

![Simplicity](simplicity.png)

### How the OPI Framework Works

1.  **Block Ingestion & Parsing:** The core engine fetches new blocks and scans every transaction for `OP_RETURN` outputs.
2.  **OPI Routing:** When a valid BRC-20 JSON is found, the **OPI Router** inspects the `"op"` field. It then routes the transaction data to the specific processor registered for that operation (e.g., `swap`, `no_return`).
3.  **Specialized Processing:** Each OPI processor is a self-contained module with its own parser, validator, and state transition logic. It enforces the rules of its specific operation.
4.  **Atomic State Changes:** If the operation is valid according to the processor's rules, the resulting state changes are committed atomically to the PostgreSQL database. If any validation step fails, the operation is rejected without affecting the state.

This plug-and-play architecture allows the community to propose and integrate new protocols (OPIs) without altering the indexer's core.

---

## Supported Protocols & Operations

### **Universal BRC-20 (Core)**

- `deploy`, `mint`, `transfer`: The foundational operations for creating and moving BRC-20 tokens, handled by the legacy processor.

### **OPI-0: `no_return`**

- **Purpose:** A specialized operation for scenarios requiring proof of token burn or specific on-chain interactions, involving Ordinals and witness data inscriptions.
- **Processor Logic:** The OPI-0 processor validates a unique transaction structure, including checks on witness data and specific output addresses (e.g., transfers to a Satoshi address). It interacts with external services OPI-LC indexer for the validation.

---

## Quick Start

> **Prerequisite:** You must have a fully synced Bitcoin Core node with `txindex=1` enabled.
> See the [Deployment Guide](docs/deployment/README.md) for full setup instructions.

### Docker Compose (Recommended)

1.  **Prepare Environment:**
    ```bash
    cp .env.example .env
    ```
2.  **Configure:**
    - Edit `.env` with your Bitcoin Core RPC credentials and other secrets.
    - Ensure the Docker `DATABASE_URL` and `REDIS_URL` are active.
    - **Crucially, change all default passwords and secrets if deploying publicly.**
3.  **Launch:**
    ```bash
    docker-compose up -d
    ```
4.  **Verify:**
    ```bash
    curl http://localhost:8080/v1/indexer/brc20/health
    # Expected output: { "status": "ok" }
    ```

### Manual Installation

```bash
# Set up your environment (PostgreSQL, Redis) and configure .env
pip install pipenv
pipenv install --dev
pipenv run alembic upgrade head
pipenv run python run.py --continuous
```

> **🔒 Security Warning:**
> If you expose any service to the internet, you **MUST** change all default passwords. Never expose PostgreSQL or Redis databases directly. Use a firewall and secure networking practices.

---

## API Documentation

A comprehensive, interactive API documentation (Swagger UI) is available at `http://localhost:8080/docs` after launching the server.

For a static overview, see the [Full API Documentation](./docs/api/README.md).

### Core Endpoints

```bash
# Health Check
curl http://localhost:8080/v1/indexer/brc20/health

# List all indexed tokens
curl http://localhost:8080/v1/indexer/brc20/list

# Get detailed information for a specific token
curl http://localhost:8080/v1/indexer/brc20/{tick}
```

### OPI Framework Endpoints

```bash
# List all registered and enabled OPIs
curl http://localhost:8080/v1/indexer/brc20/opis

# Get information for a specific OPI
curl http://localhost:8080/v1/indexer/brc20/opis/{opi_id}
```

---

## Testing

The integrity of the protocol is guaranteed by an exhaustive test suite organized by functionality.

```bash
# Run all tests (unit, integration, performance, security)
pipenv run pytest

# Run tests with coverage report
pipenv run pytest --cov=src --cov-report=html
```

---

## Contributing

We welcome contributions from the community! The OPI framework is designed for extensibility, and we encourage developers to propose and build new protocols. Please see our [Contributing Guide](CONTRIBUTING.md) for details on how to get started.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
