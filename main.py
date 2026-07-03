from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uuid
import time

app = FastAPI()

# =====================================================
# CORS
# =====================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app-m9xwro.example.com",
        "https://exam.sanand.workers.dev",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# Constants
# =====================================================

EMAIL = "24f1002603@ds.study.iitm.ac.in"

RATE_LIMIT = 8
WINDOW = 10

client_requests = {}

# =====================================================
# Middleware 1 - Rate Limiter
# (Declared FIRST so Request Context runs around it)
# =====================================================

@app.middleware("http")
async def rate_limit(request: Request, call_next):

    client_id = request.headers.get("X-Client-Id", "anonymous")

    now = time.time()

    timestamps = client_requests.get(client_id, [])

    timestamps = [t for t in timestamps if now - t < WINDOW]

    if len(timestamps) >= RATE_LIMIT:
        retry_after = max(1, int(WINDOW - (now - timestamps[0])))

        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={
                "Retry-After": str(retry_after)
            }
        )

    timestamps.append(now)
    client_requests[client_id] = timestamps

    response = await call_next(request)

    return response


# =====================================================
# Middleware 2 - Request Context
# =====================================================

@app.middleware("http")
async def request_context(request: Request, call_next):

    request_id = request.headers.get("X-Request-ID")

    if not request_id:
        request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id

    return response


# =====================================================
# Endpoint
# =====================================================

@app.get("/ping")
async def ping(request: Request):

    return {
        "email": EMAIL,
        "request_id": request.state.request_id
    }