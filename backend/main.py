import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional, Set

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import asyncpg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ENGINE: AsyncEngine | None = None
ASYNC_SESSION: sessionmaker | None = None
CLIENTS: Set[WebSocket | asyncio.Queue ] = set()
CLIENTS_LOCK = asyncio.Lock()

# dedicated asyncpg connection for LISTEN/NOTIFY
LISTENER_CONN: Optional[asyncpg.Connection] = None
NOTIFY_CHANNEL = os.getenv("NOTIFY_CHANNEL", "counter_changes")


def _pg_config_from_env():
    return {
        "user": os.getenv("PGUSER", os.getenv("DB_USER", "postgres")),
        "password": os.getenv("PGPASSWORD", os.getenv("DB_PASSWORD", "")),
        "database": os.getenv("PGDATABASE", "db_trigger_ws"),
        "host": os.getenv("PGHOST", "localhost"),
        "port": int(os.getenv("PGPORT", os.getenv("DB_PORT", "5432"))),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    global ENGINE, ASYNC_SESSION, LISTENER_CONN, NOTIFY_CHANNEL
    cfg = _pg_config_from_env()
    logger.info("Starting up, connecting to Postgres %s@%s:%s/%s", cfg["user"], cfg["host"], cfg["port"], cfg["database"])
    user = cfg["user"]
    password = cfg["password"]
    host = cfg["host"]
    port = cfg["port"]
    database = cfg["database"]
    database_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
    ENGINE = create_async_engine(database_url, future=True)
    ASYNC_SESSION = sessionmaker(bind=ENGINE, class_=AsyncSession, expire_on_commit=False)

    # set up a dedicated asyncpg listener connection for NOTIFY events
    try:
        LISTENER_CONN = await asyncpg.connect(user=user, password=password, database=database, host=host, port=port, timeout=5)

        def _pg_notify_handler(conn, pid, channel, payload):
            # schedule async handling
            task = asyncio.create_task(_handle_notify(payload))
            # yield   # FastAPI app runs here
            # task.cancel()   # shutdown: cancel worker

        await LISTENER_CONN.add_listener(NOTIFY_CHANNEL, _pg_notify_handler)
        logger.info("Listening for Postgres notifications on channel '%s'", NOTIFY_CHANNEL)
    except Exception:
        logger.exception("Failed to start asyncpg listener; continuing without DB notifications")

    # shutdown
    yield
    if ASYNC_SESSION:
        ASYNC_SESSION = None
    if ENGINE:
        await ENGINE.dispose()
        ENGINE = None
    if LISTENER_CONN:
        try:
            # remove listener and close
            await LISTENER_CONN.remove_listener(NOTIFY_CHANNEL, None)
        except Exception:
            pass
        try:
            await LISTENER_CONN.close()
        except Exception:
            pass
        LISTENER_CONN = None

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _broadcast_count(count: int) -> None:
    message = json.dumps({"count": count})
    async with CLIENTS_LOCK:
        clients = list(CLIENTS)
    for client in clients:
        try:
            if isinstance(client, WebSocket):
                await client.send_text(message)
            elif isinstance(client, asyncio.Queue):
                await client.put(count)
        except Exception:
            async with CLIENTS_LOCK:
                CLIENTS.discard(client)


async def _get_current_count() -> Optional[int]:
    global ASYNC_SESSION
    if ASYNC_SESSION is None:
        return None
    async with ASYNC_SESSION() as session:
        try:
            result = await session.execute(text("SELECT count FROM counters LIMIT 1"))
            row = result.fetchone()
            if not row:
                return None
            # row may be a tuple-like or mapping
            try:
                return int(row[0])
            except Exception:
                return int(row["count"])
        except Exception:
            return None


async def _increment_and_get_count(retries: int = 3) -> int:
    global ASYNC_SESSION
    if ASYNC_SESSION is None:
        raise RuntimeError("Database engine not initialized")

    for attempt in range(retries):
        async with ASYNC_SESSION() as session:
            try:
                async with session.begin():
                    result = await session.execute(text("UPDATE counters SET count = count + 1 RETURNING count"))
                    row = result.fetchone()
                    if row:
                        try:
                            return int(row[0])
                        except Exception:
                            return int(row["count"])
                    else:
                        raise RuntimeError("No counter row found to increment")
            except Exception:
                if attempt < retries - 1:
                    await asyncio.sleep(0.05)
                    continue
                raise

    raise RuntimeError("Failed to increment count after retries")


async def _handle_notify(payload: Optional[str]) -> None:
    """Handle Postgres NOTIFY: parse payload for count and broadcast."""
    try:
        if payload:
            data = json.loads(payload)
            if isinstance(data, dict) and "count" in data:
                count = int(data["count"])
                await _broadcast_count(count)
    except Exception:
        logger.exception("Error handling Postgres notification: %s", payload)


@app.get("/")
async def root():
    return {"message": "DB Trigger SSE and WS Backend", "version": "1.0"}

# when server reloads or shuts down, SSE connection will require manual ctrl-c
@app.get("/sse")
async def sse_endpoint(request: Request):
    """Server-Sent Events endpoint for real-time count updates."""
    async def event_generator(queue: asyncio.Queue):
        try:
            while True:
                count = await queue.get()
                yield f"data: {json.dumps({'count': count})}\n\n"
        except Exception:
            async with CLIENTS_LOCK:
                CLIENTS.discard(queue)
            raise
        finally:
            async with CLIENTS_LOCK:
                queue.task_done()
                CLIENTS.discard(queue)

    # Keep connection open and yield updates
    queue = asyncio.Queue()
    # Add to a list of SSE clients
    async with CLIENTS_LOCK:
        CLIENTS.add(queue)
    current = await _get_current_count()
    current = current if current is not None else 0
    queue.put_nowait(current)

    return StreamingResponse(event_generator(queue), media_type="text/event-stream")


# when server reloads, websocket will disconnect
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time count updates."""
    await websocket.accept()
    async with CLIENTS_LOCK:
        CLIENTS.add(websocket)
    # Send initial count on connect
    try:
        current = await _get_current_count()
        logger.info(f"Sent initial count {current} to WebSocket client")
        if current is not None:
            await websocket.send_text(json.dumps({"count": current}))
    except Exception:
        logger.exception("Failed to send initial count to websocket client")
    try:
        while True:
            # keep the connection alive; updates come from NOTIFY broadcasts
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
        async with CLIENTS_LOCK:
            CLIENTS.discard(websocket)
    except Exception:
        async with CLIENTS_LOCK:
            CLIENTS.discard(websocket)
        raise


@app.get("/api/v1/count")
async def get_current_count():
    """Get the current count from the database."""
    global ENGINE, ASYNC_SESSION
    if ENGINE is None or ASYNC_SESSION is None:
        raise HTTPException(status_code=500, detail="Database engine not initialized")

    current = await _get_current_count()
    if current is None:
        raise HTTPException(status_code=404, detail="No count found")

    return {"count": current}


@app.patch("/api/v1/count")
async def increment_count():
    global ENGINE, ASYNC_SESSION
    if ENGINE is None or ASYNC_SESSION is None:
        raise HTTPException(status_code=500, detail="Database engine not initialized")

    try:
        new_count = await _increment_and_get_count()
        # Note: Broadcasting is handled by the database trigger via NOTIFY
    except Exception as e:
        logger.exception("Database error while incrementing count")
        raise HTTPException(status_code=500, detail=str(e))

    return {"count": new_count}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
