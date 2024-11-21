from fastapi import FastAPI
from typing import List, Literal
from opsmate.libs.core.types import Model
from pydantic import BaseModel, Field
from opsmate.libs.providers import Client as ProviderClient, ClientBag

client_bag = ProviderClient.clients_from_env()
app = FastAPI()


class Health(BaseModel):
    status: Literal["ok", "faulty"] = Field(title="status", default="ok")


@app.get("/api/v1/health", response_model=Health)
def health():
    return Health(status="ok")


@app.get("/api/v1/models", response_model=List[Model])
def models():
    return ProviderClient.models_from_clientbag(client_bag)
