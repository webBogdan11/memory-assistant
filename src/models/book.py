import uuid
from pydantic import Field
from models.base import NoSQLBaseDocument, BasePydanticModel


class BookMetadata(BasePydanticModel):
    """
    Sub-model for the 'metadata' field.
    """

    pages: int
    doc_size: float = Field(..., alias="docSize")


class BookDocument(NoSQLBaseDocument):
    """
    Represents a document in the 'documents' collection.
    """

    user_id: uuid.UUID = Field(..., alias="userId")

    title: str
    type: str
    s3_path: str = Field(..., alias="s3Path")

    metadata: BookMetadata = Field(default_factory=BookMetadata)
    first_page: int | None = Field(None, alias="firstPage")
