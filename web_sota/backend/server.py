import time
from collections import deque
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
import httpx


_START_TIME = time.time()

# In-memory log ring buffer for /api/logs (UI-only, not persisted).
_LOG_BUFFER: deque[dict[str, Any]] = deque(maxlen=500)
_LOG_SEQ = 0


def _log(level: str, kind: str, detail: str, meta: dict[str, Any] | None = None) -> None:
    global _LOG_SEQ
    _LOG_SEQ += 1
    _LOG_BUFFER.append(
        {
            "id": str(_LOG_SEQ),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            "level": level,
            "kind": kind,
            "detail": detail,
            "meta": meta or {},
        }
    )


# In-memory avatar/OSC stubs (web UI backend; the real control plane lives in
# src/vrchat_mcp/server.py over MCP on :10795).
_AVATAR_STATE: dict[str, Any] = {"current_avatar": None, "parameters": {}}
_OSC_STATS = {"messages_sent": 0, "messages_received": 0}


@asynccontextmanager
async def lifespan(app: FastAPI):
    _log("INFO", "server", "web backend started")
    yield


app = FastAPI(title="vrchat-mcp", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "vrchat-mcp"}


@app.post("/api/shutdown")
async def shutdown():
    _log("INFO", "server", "shutdown requested via /api/shutdown")
    return {"ok": True}


# --- LLM passthrough (Ollama / LM Studio) ---


@app.get("/api/llm/providers")
async def llm_providers():
    providers = []
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get("http://127.0.0.1:11434/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                providers.append({"id": "ollama", "label": "Ollama", "base_url": "http://127.0.0.1:11434/v1", "models": models, "needs_key": False})
    except Exception:
        providers.append({"id": "ollama", "label": "Ollama", "base_url": "http://127.0.0.1:11434/v1", "models": [], "needs_key": False})
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get("http://127.0.0.1:1234/v1/models")
            if resp.status_code == 200:
                data = resp.json()
                models = [m["id"] for m in data.get("data", [])]
                providers.append({"id": "lmstudio", "label": "LM Studio", "base_url": "http://127.0.0.1:1234/v1", "models": models, "needs_key": False})
    except Exception:
        providers.append({"id": "lmstudio", "label": "LM Studio", "base_url": "http://127.0.0.1:1234/v1", "models": [], "needs_key": False})
    return {"providers": providers}


@app.post("/api/llm/chat")
async def llm_chat(body: dict):
    provider = body.get("provider", "ollama")
    model = body.get("model", "llama3.2:3b")
    prompt = body.get("prompt") or body.get("message", "")
    base = "http://127.0.0.1:1234/v1" if provider == "lmstudio" else "http://127.0.0.1:11434/v1"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{base}/chat/completions", json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
            })
            if resp.status_code == 200:
                data = resp.json()
                return {"response": data["choices"][0]["message"]["content"]}
            return {"response": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"response": f"Error: {e}"}


# --- Web UI control plane (mirrors MCP manage_* ops, lightweight stubs) ---


@app.post("/api/v1/manage_system")
async def manage_system(body: dict):
    operation = (body or {}).get("operation", "status")
    if operation == "status":
        return {"data": {
            "server": "vrchat-mcp",
            "version": "14.1.0",
            "status": "running",
            "components": {
                "osc": True,
                "avatar": True,
                "inspector": True,
                "rest_api": False,
                "pipeline": False,
            },
        }}
    if operation == "metrics":
        uptime = time.time() - _START_TIME
        return {"data": {
            "uptime_seconds": round(uptime, 1),
            "throughput_rps": 0.0,
            "error_rate": 0.0,
            "avg_response_ms": 0.0,
        }}
    return JSONResponse(status_code=400, content={"error": f"Unknown operation: {operation}"})


@app.post("/api/v1/manage_osc")
async def manage_osc(body: dict):
    operation = (body or {}).get("operation", "stats")
    if operation == "stats":
        return {"data": dict(_OSC_STATS)}
    if operation == "send":
        address = (body or {}).get("address", "")
        args = (body or {}).get("args", [])
        _OSC_STATS["messages_sent"] += 1
        _log("INFO", "tool_call", f"OSC send {address} {args}")
        return {"success": True, "data": {"address": address, "args": args}}
    return JSONResponse(status_code=400, content={"error": f"Unknown operation: {operation}"})


@app.post("/api/v1/manage_avatar")
async def manage_avatar(body: dict):
    operation = (body or {}).get("operation", "get_state")
    if operation == "get_state":
        return {"data": dict(_AVATAR_STATE)}
    if operation == "load":
        avatar_id = (body or {}).get("avatar_id", "")
        _AVATAR_STATE["current_avatar"] = avatar_id
        _log("INFO", "tool_call", f"Avatar load {avatar_id}")
        return {"success": True, "data": {"current_avatar": avatar_id}}
    if operation == "set_param":
        parameter = (body or {}).get("parameter", "")
        value = (body or {}).get("value")
        if parameter:
            _AVATAR_STATE["parameters"][parameter] = value
        _log("INFO", "tool_call", f"Avatar set_param {parameter}={value}")
        return {"success": True, "data": {"parameter": parameter, "value": value}}
    if operation == "get_param":
        parameter = (body or {}).get("parameter", "")
        return {"value": _AVATAR_STATE["parameters"].get(parameter)}
    return JSONResponse(status_code=400, content={"error": f"Unknown operation: {operation}"})


_TOOLS = [
    {"name": "manage_avatar", "description": "Avatar state and parameter management"},
    {"name": "manage_osc", "description": "OSC protocol send/stats"},
    {"name": "manage_world", "description": "World discovery (REST required)"},
    {"name": "manage_economy", "description": "Creator economy (REST required)"},
    {"name": "manage_social", "description": "Friends/users/notifications (REST required)"},
    {"name": "manage_input", "description": "Input simulation over OSC"},
    {"name": "manage_system", "description": "System health, telemetry, auth"},
]


@app.get("/api/v1/tools/")
@app.get("/api/v1/tools")
async def list_tools():
    return _TOOLS


@app.get("/api/skills")
async def list_skills():
    return []


# --- Logs ring buffer ---


@app.get("/api/logs")
async def get_logs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    level: str = Query(default=""),
    kind: str = Query(default=""),
    search: str = Query(default=""),
    sort: str = Query(default="desc"),
    after_id: str = Query(default=""),
):
    entries = list(_LOG_BUFFER)
    if level:
        entries = [e for e in entries if e["level"] == level]
    if kind:
        entries = [e for e in entries if e["kind"] == kind]
    if search:
        q = search.lower()
        entries = [e for e in entries if q in str(e["detail"]).lower()]
    if after_id:
        try:
            seq = int(after_id)
            entries = [e for e in entries if int(e["id"]) > seq]
        except ValueError:
            pass
    if sort == "desc":
        entries = entries[::-1]
    total = len(entries)
    return {"entries": entries[offset:offset + limit], "total": total}


@app.get("/api/logs/export")
async def export_logs(format: str = Query(default="json")):
    entries = list(_LOG_BUFFER)
    if format == "csv":
        lines = ["id,timestamp,level,kind,detail"]
        for e in entries:
            detail = str(e["detail"]).replace('"', '""')
            lines.append(f'{e["id"]},{e["timestamp"]},{e["level"]},{e["kind"]},"{detail}"')
        return PlainTextResponse("\n".join(lines), media_type="text/csv")
    return JSONResponse(entries)


@app.delete("/api/logs")
async def clear_logs():
    _LOG_BUFFER.clear()
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
