from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from systems.dashboard.routes import dashboard, leads, cases, settings, services, parser

app = FastAPI(title="Alexey Bot Dashboard", version="1.0.0")

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

@app.get("/twa")
async def get_twa():
    return FileResponse(os.path.join("systems/dashboard/interface", "twa.html"))

# Serve static files LAST (this catches all other routes)
app.mount("/", StaticFiles(directory="systems/dashboard/interface", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
