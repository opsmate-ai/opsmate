from opsmate.libs.knowledge import (
    Runbook,
    get_runbooks_table,
    DatabaseConnection,
    DocumentIngester,
)
from opsmate.libs.core.types import DocumentIngestion, DocumentIngestionSpec, Metadata

ingestion = DocumentIngestion(
    metadata=Metadata(
        name="k8s-concepts",
        description="Kubernetes Concepts",
    ),
    spec=DocumentIngestionSpec(local_path="./website/content/en/docs/concepts/**/*.md"),
)

ingester = DocumentIngester()


ingester.document_ingestion(ingestion)
