from fastapi import FastAPI

app = FastAPI(title="Hello World", version="0.1.1")

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/healthy")
def health():
    return {"status": "ok"}