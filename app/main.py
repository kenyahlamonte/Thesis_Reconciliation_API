from fastapi import FastAPI

app = FastAPI(title="Hello World", version="0.1.0")

@app.get("/")
async def root():
    return {"message": "Hello World"}