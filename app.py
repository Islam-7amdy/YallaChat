from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import datetime, json, pathlib

app = FastAPI(title="Yalla Chat - Starter (Local)")

BASE = pathlib.Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

class ConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        self.active_connections[websocket] = username
        await self.broadcast_system(f"{username} joined the chat")

    def disconnect(self, websocket: WebSocket):
        username = self.active_connections.get(websocket, "Unknown")
        if websocket in self.active_connections:
            del self.active_connections[websocket]
        return username

    async def broadcast(self, message: dict):
        dead = []
        for ws in list(self.active_connections.keys()):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for d in dead:
            self.disconnect(d)

    async def broadcast_system(self, text: str):
        msg = {"type":"system", "text": text, "time": datetime.datetime.utcnow().isoformat() + "Z"}
        await self.broadcast(msg)

manager = ConnectionManager()

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await manager.connect(websocket, username)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                obj = json.loads(data)
            except Exception:
                obj = {"type":"chat", "text": data}
            msg = {
                "type": obj.get("type","chat"),
                "from": username,
                "text": obj.get("text",""),
                "time": datetime.datetime.utcnow().isoformat() + "Z"
            }
            await manager.broadcast(msg)
    except WebSocketDisconnect:
        left_user = manager.disconnect(websocket)
        await manager.broadcast_system(f"{left_user} left the chat")

@app.get("/health")
async def health():
    return {"status":"ok"}
