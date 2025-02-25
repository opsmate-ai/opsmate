from sqlalchemy import Engine
from opsmate.workflow.models import SQLModel as WorkflowSQLModel
from opsmate.ingestions.models import SQLModel as IngestionModel
from opsmate.dbq.dbq import SQLModel as DBQSQLModel
from opsmate.libs.config import config


async def on_startup(engine: Engine):
    WorkflowSQLModel.metadata.create_all(engine)
    IngestionModel.metadata.create_all(engine)
    DBQSQLModel.metadata.create_all(engine)
