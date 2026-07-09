from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.api.call import router as call_router
from app.websocket.voice_bot import router as voice_router
from app.db.db_service import init_db


app = FastAPI(title="CRM Calling Agent")

@app.on_event("startup")
def startup_event():
    init_db()

app.include_router(call_router)
app.include_router(voice_router)

# Serve the static frontend index.html at root /
@app.get("/")
def home():
    return FileResponse("frontend/index.html")
