from fastapi import FastAPI

app = FastAPI(title="NetMind AI")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "NetMind AI backend"}