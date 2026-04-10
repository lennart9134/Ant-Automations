"""Vision service — SGLang model serving for document understanding.

Serves Phi-4-reasoning-vision-15B for document classification,
form extraction, and visual content understanding.
"""

from fastapi import FastAPI

app = FastAPI(title="Ant Automations Vision", version="0.1.0")


@app.get("/healthz")
async def health() -> dict:
    return {"status": "ok", "service": "vision"}


@app.post("/api/v1/vision/analyze")
async def analyze_image(payload: dict) -> dict:
    """Analyze an image or document using the vision model.

    In production: forwards to SGLang runtime serving Phi-4-reasoning-vision-15B.
    """
    return {
        "model": "phi-4-reasoning-vision-15b",
        "status": "placeholder",
        "result": {},
    }
