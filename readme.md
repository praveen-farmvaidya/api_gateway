# API Gateway Service

## Service Description

The API Gateway is the single, unified entry point for all external traffic into the FarmVidhya backend system. It acts as a reverse proxy, security shield, and traffic controller, abstracting the complexity of the internal microservices network from the end-user. Its primary goal is to provide a secure, stable, and consistent public-facing API.

## Role in System Architecture (Execution Flow)

This service is the front door. All client applications (web frontends, mobile apps, third-party integrations) interact exclusively with the API Gateway.

*   **Upstream Triggers:** Receives all incoming HTTP requests from the public internet.
*   **Downstream Dependencies:**
    *   **Identity Service:** For authenticating and authorizing requests. It calls the `/keys/validate` endpoint to validate user API keys and proxies requests for user management (`/signup`, `/login`, `/keys`).
    *   **Queue Service:** Forwards validated, asynchronous job requests to the `/jobs` endpoint.
    *   **Billing Service:** Forwards requests related to user balance checks.
    *   *(Other services as needed)*

## Core Features & Workflow Explanation

1.  **Request Routing:** It maintains a map of public URL paths to internal service addresses. For example, a request to `POST /jobs` is routed to the `queue_service`.
2.  **Authentication Middleware:**
    *   For job submission routes (`/jobs`), it extracts the `Authorization: Bearer <API_KEY>` header. It then makes a synchronous, blocking call to the `identity_service` to validate the key. If the key is invalid, the request is rejected immediately with a `401 Unauthorized` or `403 Forbidden` error.
    *   For user-specific routes (`/keys`), it enforces a simulated JWT authentication by checking for an `x-user-id` header (this would be replaced by full JWT validation in a production system).
3.  **Rate Limiting:** It applies a global rate limit to sensitive endpoints to protect the system from abuse and denial-of-service attacks. The limit is configured via environment variables.
4.  **Request/Response Proxying:** It transparently forwards the client's request body, headers, and query parameters to the appropriate downstream service and returns the downstream service's response and status code to the client. It is robust enough to handle non-JSON error responses without crashing.

## Getting Started (Local Setup)

### Prerequisites

*   Python 3.11+
*   A running instance of all downstream services (Identity, Queue, Billing).

### Installation

1.  Navigate to the `Backend` directory and activate the virtual environment:
    ```bash
    cd ~/Backend
    source venv/bin/activate
    ```
2.  Install dependencies from the root `requirements.txt` file.

### Configuration

Create a `.env` file in the `api_gateway` directory with the following variables.

**.env.example**
```ini
# --- Service Discovery (Addresses of internal services) ---
IDENTITY_SERVICE_URL=http://localhost:8001
QUEUE_SERVICE_URL=http://localhost:8003
BILLING_SERVICE_URL=http://localhost:8004

# --- Rate Limiting ---
# Format: "count/time_unit". e.g., "100/minute", "20/second"
DEFAULT_RATE_LIMIT=100/minute
```

### Running the Service

```bash
# Navigate to the service directory
cd api_gateway

# Run the Uvicorn server
uvicorn main:app --host 0.0.0.0 --port 8000
```
The gateway will be accessible at `http://localhost:8000`.

### Running Tests

*(Test suite to be implemented)*

## Technical Dependencies

*   **Internal Services:** `identity_service`, `queue_service`, `billing_service`
*   **Frameworks:** FastAPI, Uvicorn
*   **Key Libraries:**
    *   `httpx` (for asynchronous downstream requests)
    *   `slowapi` (for rate limiting)

## API Endpoints

This service exposes the **entire public API** for the platform. It proxies requests to the appropriate downstream services. See the documentation of the other services for detailed endpoint specifications.

*   `POST /signup`, `POST /login`, etc. -> Proxied to **Identity Service**
*   `POST /keys`, `GET /keys/user/{user_id}` -> Proxied to **Identity Service**
*   `POST /jobs` -> Proxied to **Queue Service**
*   ...and so on.

## Observability

*   **Logging:** Uses `structlog` for structured, JSON-formatted logs. Key log events include incoming requests, proxying decisions, and authentication failures.
*   **Metrics:** *(To be implemented)* Key metrics to add would be request latency (total, and per-downstream-service), request volume, and status code counts (e.g., 2xx, 4xx, 5xx).
*   **Error Handling:** Catches connection errors to downstream services and returns a `503 Service Unavailable` response. Forwards all other 4xx and 5xx errors from downstream services directly to the client.
