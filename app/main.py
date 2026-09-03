from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.data.database import Base, engine
from app.data import models  # noqa: F401
from app.api.routes import router
from app.api.admin import router as admin_router
from app.api.customer_routes import router as customer_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Revenue Autopilot")

app.include_router(router)
app.include_router(admin_router)
app.include_router(customer_router)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")