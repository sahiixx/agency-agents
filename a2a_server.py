"""A2A + agent card + chat proxy server for agency-agents."""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn, json, httpx
from pydantic import BaseModel

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "deepseek-v4-flash:cloud"

app = FastAPI(title="agency-agents A2A")

class ChatRequest(BaseModel):
    skill: str = "chat"
    input: str
    max_tokens: int = 1024

@app.get("/.well-known/agent.json")
async def agent_card():
    return JSONResponse(json.load(open("agent-card.json")))

@app.get("/health")
async def health():
    return {"status": "ok", "service": "agency-agents"}

@app.post("/a2a/chat")
async def a2a_chat(body: ChatRequest):
    """Proxy chat requests to Ollama using agency-agents persona."""
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": "You are a helpful AI assistant powered by agency-agents, a multi-persona agent system."},
                {"role": "user", "content": body.input}
            ],
            "stream": False,
            "options": {"num_predict": body.max_tokens}
        })
        if resp.status_code == 200:
            data = resp.json()
            output = data.get("message", {}).get("content", "")
            return {"ok": True, "output": output, "source": "agency-agents"}
        return JSONResponse({"ok": False, "error": f"Ollama returned {resp.status_code}"}, status_code=502)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8766)
