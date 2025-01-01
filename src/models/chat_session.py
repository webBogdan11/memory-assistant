from datetime import datetime
import uuid
from typing import List, Literal
from pydantic import Field
from enum import Enum
from src.models.base import NoSQLBaseDocument, BasePydanticModel


class ChatMessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessageType(Enum):
    NEXT_QUESTION = "next_question"
    QUESTION = "question"
    ANSWER = "answer"
    FEEDBACK = "feedback"
    EXPLANATION = "explanation"
    HELP = "help"
    OTHER = "other"


class ChatMessage(NoSQLBaseDocument):
    """
    Sub-document for messages inside a chat session.
    """

    previous_message_id: uuid.UUID | None = Field(None, alias="previousMessageId")

    role: ChatMessageRole
    type: ChatMessageType
    content: str

    feedback: str | None = None
    score: float | None = None
    question_id: uuid.UUID | None = Field(None, alias="questionId")


class ChatSessionDocument(NoSQLBaseDocument):
    """
    Represents a chat session in the 'chatSessions' collection.
    """

    user_id: uuid.UUID = Field(..., alias="userId")
    document_id: uuid.UUID = Field(..., alias="documentId")

    section_ids: List[uuid.UUID] = Field(default_factory=list, alias="sectionIds")

    messages: List[ChatMessage] = Field(default_factory=list)

    overall_score: float | None = Field(None, alias="overallScore")
    number_of_questions: int = Field(0, alias="numberOfQuestions")


class ChatSessionSummary(BasePydanticModel):
    overall_score: float
    number_of_questions: int
    number_of_answered_questions: int
    section_titles: List[str]

    created_at: datetime
