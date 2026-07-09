from fastapi import FastAPI
from app.api.call import router as call_router
from app.websocket.voice_bot import router as voice_router


app = FastAPI(title="CRM Calling Agent")

app.include_router(call_router)
app.include_router(voice_router)

@app.get("/")
def home():
    return {
        "status":"running"
    }
