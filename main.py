import time
import uuid
from collections import defaultdict
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

# ------------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------------
ALLOWED_ORIGINS = ["https://app-m9xwro.example.com"] 

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
        
        # Explicitly setting it on the final response object
        response.headers["X-Request-ID"] = request_id
        return response

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
                    return Response(
                        content="Rate limit exceeded.", 
                        status_code=429
                    )
                timestamps.append(now)
                
        response = await call_next(request)
        return response

# ------------------------------------------------------------------
# ADD MIDDLEWARES IN CAREFUL ORDER
# ------------------------------------------------------------------
# 1. Rate limiter runs first
app.add_middleware(RateLimitMiddleware)

# 2. Context Middleware runs next
app.add_middleware(RequestContextMiddleware)

# 3. CORSMiddleware is added LAST. 
# Because FastAPI executes middleware bottom-up, adding CORS last means 
# it wraps everything else, allowing it to correctly read and forward our custom headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"], # CRITICAL: Tells the browser it's allowed to read this header
)

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