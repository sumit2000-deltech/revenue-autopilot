import os
from fastapi import APIRouter, HTTPException
from app.data.database import Base, engine
from app.data import models  # noqa: F401
from app.data.seed import seed
from app.data.analytics import assign_experiment_groups, simulate_treatment_outcomes
from app.agent.batch_runner import run_pipeline_on_treatment_group

router = APIRouter()


@router.post("/admin/seed-and-run")
def seed_and_run(secret: str):
    if secret != os.getenv("ADMIN_SECRET"):
        raise HTTPException(status_code=403, detail="Invalid secret")

    Base.metadata.create_all(bind=engine)
    seed()
    assigned = assign_experiment_groups()
    batch_result = run_pipeline_on_treatment_group(limit=15)  # small, quota-conscious
    conversions = simulate_treatment_outcomes()

    return {
        "seeded": True,
        "groups_assigned": assigned,
        "batch_result": batch_result,
        "simulated_conversions": conversions,
    }