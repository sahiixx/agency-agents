"""A2A + agent card + cloud chat proxy server for agency-agents."""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn, json
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage
from providers import get_cloud_llm

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
    """Proxy chat requests to the cloud LLM backbone using agency-agents persona.
    Cloud-only — requires ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY."""
    try:
        llm = get_cloud_llm()
        response = llm.invoke([
            SystemMessage(content="You are a helpful AI assistant powered by agency-agents, a multi-persona agent system."),
            HumanMessage(content=body.input),
        ], max_tokens=body.max_tokens)
        return {"ok": True, "output": response.content, "source": "agency-agents (cloud)"}
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"Cloud LLM failed: {e}"}, status_code=502)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8766)
