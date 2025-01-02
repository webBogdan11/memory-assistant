from models.chat_session import ChatMessage, ChatSessionDocument, ChatSessionSummary
from models.section import QuestionItem
from repositories.base_repo import AbstractRepository
from services.section_service import SectionService
from typing import List
import uuid
import random


class ChatSessionRepository(AbstractRepository[ChatSessionDocument]):
    """
    Concrete repository for the ChatSessionDocument model.
    """

    def __init__(self):
        super().__init__(collection_name="chat_sessions")

    def model_class(self) -> type[ChatSessionDocument]:
        return ChatSessionDocument

    def list_chat_sessions(
        self,
        user_id: str,
        document_id: str,
        section_ids: List[str],
        limit: int = 10,
        offset: int = 0,
    ) -> List[ChatSessionDocument]:
        filter_dict = {
            "userId": user_id,
            "documentId": document_id,
            "sectionIds": {"$in": section_ids},
        }

        cursor = (
            self.collection.find(filter_dict)
            .sort("createdAt", -1)
            .skip(offset)
            .limit(limit)
        )

        return [self.model_class().from_mongo(d) for d in cursor]
