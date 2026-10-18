
import time
import uuid
import json
import logging
from collections import deque
from datetime import datetime, timezone

from fastapi import FastAPI, Query, Request
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

app = FastAPI()

START_TIME = time.monotonic()

REQUEST_COUNTER = Counter(
    "http_requests_total",
    "Total HTTP requests"
)

logs = deque(maxlen=1000)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("observability")


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())

    REQUEST_COUNTER.inc()

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception:
        status_code = 500
        raise
    finally:
        entry = {
            "level": "INFO" if status_code < 500 else "ERROR",
            "ts": datetime.now(timezone.utc).isoformat(),
            "path": request.url.path,
            "request_id": request_id,
            "method": request.method,
            "status_code": status_code
        }

        logs.append(entry)
        logger.info(json.dumps(entry))

    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/")
def home():
    return {"message": "Observability API running"}


@app.get("/work")
def work(n: int = Query(default=1, ge=0, le=100000)):
    total = sum(range(n))
    return {
        "email": "24f3004934@ds.study.iitm.ac.in",
        "done": n
    }


@app.get("/metrics")
def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "uptime_s": float(max(0, time.monotonic() - START_TIME))
    }


@app.get("/logs/tail")
def logs_tail(limit: int = Query(default=10, ge=1, le=1000)):
    return list(logs)[-limit:]

