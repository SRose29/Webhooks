from fastapi import FastAPI, Request, HTTPException
from sqlmodel import SQLModel, Session, create_engine, select
from models import WebhookLog, Project
from pydantic import BaseModel
import httpx

app = FastAPI()
engine = create_engine("sqlite:///webhooks.db")
SQLModel.metadata.create_all(engine)

class RegisterRequest(BaseModel):
    project_id: str

class SetTargetRequest(BaseModel):
    target_url: str

@app.post("/register")
def register_project(data: RegisterRequest):
    with Session(engine) as session:
        if session.get(Project, data.project_id):
            raise HTTPException(400, "Project already exists.")
        project = Project(id=data.project_id)
        session.add(project)
        session.commit()
    return {"message": "Registered", "project_id": data.project_id}

@app.post("/set-target/{project_id}")
def set_target(project_id: str, data: SetTargetRequest):
    with Session(engine) as session:
        project = session.get(Project, project_id)
        if not project:
            raise HTTPException(404, "Project not found.")
        project.target_url = data.target_url
        session.add(project)
        session.commit()
    return {"message": "Target URL updated."}

@app.post("/hook/{project_id}")
async def receive_hook(project_id: str, request: Request):
    body = await request.body()
    with Session(engine) as session:
        project = session.get(Project, project_id)
        if not project:
            raise HTTPException(404, "Project not found.")
        log = WebhookLog(project_id=project_id, payload=body.decode())
        session.add(log)
        session.commit()
        # Forward if target is set
        if project.target_url:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(project.target_url, data=body)
            except Exception:
                pass  # fail silently for now
    return {"message": "Received"}

@app.get("/logs/{project_id}")
def get_logs(project_id: str):
    with Session(engine) as session:
        logs = session.exec(select(WebhookLog).where(WebhookLog.project_id == project_id)).all()
        return [{"id": log.id, "payload": log.payload} for log in logs]

@app.post("/replay/{project_id}")
def replay_logs(project_id: str):
    with Session(engine) as session:
        project = session.get(Project, project_id)
        if not project or not project.target_url:
            raise HTTPException(404, "Project or target not found.")
        logs = session.exec(select(WebhookLog).where(WebhookLog.project_id == project_id)).all()
        for log in logs:
            try:
                httpx.post(project.target_url, data=log.payload)
            except Exception:
                pass
    return {"message": f"Replayed {len(logs)} logs."}
