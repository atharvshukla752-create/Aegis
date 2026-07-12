"""
aegisweb/server.py — the network layer for AegisWeb.
Run this from inside the aegisweb/ folder: python server.py
"""

import os
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

import chat

app = FastAPI()

# Change this to something only you know. Every request must include it.
AEGIS_SECRET = "change-this-to-your-own-secret"


def check_auth(x_aegis_key: str = Header(default="")):
    if x_aegis_key != AEGIS_SECRET:
        raise HTTPException(status_code=401, detail="Invalid or missing key")


class MessageRequest(BaseModel):
    user_input: str


@app.post("/api/send_message")
def send_message(req: MessageRequest, x_aegis_key: str = Header(default="")):
    check_auth(x_aegis_key)
    return chat.send_message(req.user_input)


@app.get("/api/stats")
def get_stats(x_aegis_key: str = Header(default="")):
    check_auth(x_aegis_key)
    return chat.get_stats()


@app.get("/")
def root():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "chat.html"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
uvicorn.run(app, host="0.0.0.0", port=port)
