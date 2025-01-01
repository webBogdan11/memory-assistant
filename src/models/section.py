import uuid
from typing import List
from pydantic import Field
from src.models.base import NoSQLBaseDocument


class QuestionItem(NoSQLBaseDocument):
    """
    Nested sub-document for questions in 'sections' collection.
    We'll store its own _id as a UUID as well, if you wish.
    """

    question: str
    type: str


class SectionDocument(NoSQLBaseDocument):
    """
    Represents a section in the 'sections' collection.
    """

    book_id: uuid.UUID = Field(..., alias="bookId")
    name: str
    order: int
    start_page: int = Field(..., alias="startPage")
    end_page: int = Field(..., alias="endPage")
    text: str | None = None

    questions: List[QuestionItem] = Field(default_factory=list)
