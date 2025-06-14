from typing import Optional
from sqlmodel import Field, SQLModel

class WebhookLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: str
    payload: str

class Project(SQLModel, table=True):
    id: str = Field(primary_key=True)
    target_url: Optional[str] = None

