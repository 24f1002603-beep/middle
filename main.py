import time
import uuid
from collections import defaultdict
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

# ------------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------------
ASSIGNED_ORIGIN = "https://app-m9xwro.example.com"

RATE_LIMIT_WINDOW = 10.0  
MAX_REQUESTS = 8          

client_buckets = defaultdict(list)

# ------------------------------------------------------------------
# MIDDLEWARE 1: Request Context
# ------------------------------------------------------------------
class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())
        
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

app.add_middleware(RequestContextMiddleware)

# ------------------------------------------------------------------
# MIDDLEWARE 2: Dynamic CORS & Preflight Handler
# ------------------------------------------------------------------
class DynamicCorsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        
        # Intercept browser preflight (OPTIONS) requests immediately
        if request.method == "OPTIONS":
            response = Response(status_code=200)
            if origin:
                response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
            response.headers["Access-Control-Allow-Headers"] = "X-Request-ID, X-Client-Id, Content-Type, Authorization"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Expose-Headers"] = "X-Request-ID"
            return response

        # Regular requests (GET /ping)
        response = await call_next(request)
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Expose-Headers"] = "X-Request-ID"
        return response

app.add_middleware(DynamicCorsMiddleware)

# ------------------------------------------------------------------
# MIDDLEWARE 3: Per-Client Rate Limiting
# ------------------------------------------------------------------
class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/ping":
            client_id = request.headers.get("X-Client-Id")
            if client_id:
                now = time.time()
                timestamps = client_buckets[client_id]
                
                while timestamps and now - timestamps[0] > RATE_LIMIT_WINDOW:
                    timestamps.pop(0)
                
                if len(timestamps) >= MAX_REQUESTS:
                    # Make sure rate limit errors also return CORS headers so the browser reads them!
                    origin = request.headers.get("origin")
                    headers = {"Access-Control-Expose-Headers": "X-Request-ID"}
                    if origin:
                        headers["Access-Control-Allow-Origin"] = origin
                        headers["Access-Control-Allow-Credentials"] = "true"
                    
                    req_id = getattr(request.state, "request_id", "")
                    if req_id:
                        headers["X-Request-ID"] = req_id
                        
                    return Response(
                        content="Rate limit exceeded.", 
                        status_code=429,
                        headers=headers
                    )
                timestamps.append(now)
                
        response = await call_next(request)
        return response

app.add_middleware(RateLimitMiddleware)

# ------------------------------------------------------------------
# ENDPOINT: GET /ping
# ------------------------------------------------------------------
@app.get("/ping")
async def ping(request: Request):
    req_id = getattr(request.state, "request_id", "unknown")
    return {
        "email": "24f1002603@ds.study.iitm.ac.in",
        "request_id": req_id
    }