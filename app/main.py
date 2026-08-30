from fastapi import FastAPI
from app.data.database import Base, engine
from app.data import models  # noqa: F401 — needed so tables register with Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Revenue Autopilot")


@app.get("/")
def read_root():
    return {"status": "Revenue Autopilot is running"}