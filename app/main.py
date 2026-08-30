from fastapi import FastAPI

app = FastAPI(title="Revenue Autopilot")


@app.get("/")
def read_root():
    return {"status": "Revenue Autopilot is running"}