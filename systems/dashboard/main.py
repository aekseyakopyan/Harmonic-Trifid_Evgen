from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import subprocess
from systems.dashboard.routes import dashboard, leads, cases, settings, services, parser

app = FastAPI(title="Alexey Bot Dashboard", version="1.0.0")

# CORS: разрешаем только конкретные источники (wildcard + credentials запрещён по стандарту)
_allowed_origins = [
    o.strip()
    for o in os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:8000,http://localhost:3000,http://127.0.0.1:8000"
    ).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Include API routers BEFORE static files
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(leads.router, prefix="/api/leads", tags=["Leads"])
app.include_router(cases.router, prefix="/api/cases", tags=["Cases"])
app.include_router(services.router, prefix="/api/services", tags=["Services"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])
app.include_router(parser.router, prefix="/api/parser", tags=["Parser"])

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Alexey Dashboard API is running"}


@app.get("/api/system/status")
async def system_status():
    """Check if key bot processes are running via pgrep"""
    processes = {
        "alexey": "systems/alexey/main",
        "gwen": "systems/gwen",
        "parser": "apps/today_parser",
        "miniapp": "miniapp/api",
    }
    status = {}
    for name, pattern in processes.items():
        result = subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True
        )
        status[name] = "running" if result.returncode == 0 else "stopped"
    return status

@app.get("/twa")
async def get_twa():
    return FileResponse(os.path.join("systems/dashboard/interface", "twa.html"))

# Serve static files LAST (this catches all other routes)
app.mount("/", StaticFiles(directory="systems/dashboard/interface", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
