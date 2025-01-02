from llm.llm import determine_message_type, evaluate_answer, generate_explanation
from repositories.chat_session_repo import ChatSessionRepository
from services.book_service import BookService, get_book_service
from services.section_service import SectionService, get_section_service
from models.chat_session import (
    ChatMessage,
    ChatMessageRole,
    ChatMessageType,
    ChatSessionDocument,
    ChatSessionSummary,
)
from models.section import QuestionItem, SectionDocument
from typing import List
import uuid
import random


class ChatService:
    """
    Handles business logic for chat sessions.
    """

    def __init__(
        self,
        chat_session_repo: ChatSessionRepository,
        section_service: SectionService,
        book_service: BookService,
    ):
        self.chat_session_repo = chat_session_repo
        self.section_service = section_service
        self.book_service = book_service
        self.chat_session = None

        self.questions = []
        self.answered_questions = set()
        self.current_question = None

    def init_chat_session(
        self,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        section_ids: List[uuid.UUID],
    ):
        all_questions: List[QuestionItem] = []
        for section_id in section_ids:
            questions_in_section = self.section_service.get_questions_by_section_id(
                section_id
            )
            all_questions.extend(questions_in_section)

        self.chat_session = ChatSessionDocument(
            user_id=user_id,
            document_id=document_id,
            section_ids=section_ids,
            messages=[],
            overall_score=None,
        )
        random.shuffle(all_questions)
        self.questions = all_questions

    def get_next_question(self) -> QuestionItem | None:
        for question in self.questions:
            if question.id not in self.answered_questions:
                self.current_question = question
                self.add_message(
                    message=question.question,
                    type=ChatMessageType.QUESTION,
                    role=ChatMessageRole.ASSISTANT,
                    question_id=question.id,
                )
                return question
        return None

    def process_user_message(self, message: str) -> None | str:
        if message.lower() == "next":
            self.add_message(
                message=message,
                type=ChatMessageType.NEXT_QUESTION,
                role=ChatMessageRole.USER,
            )
            self.answered_questions.add(self.current_question.id)
            next_question = self.get_next_question()
            if next_question is None:
                return "__ALL_DONE__"
            else:
                return next_question.question

        message_type = determine_message_type(
            message=message, question=self.current_question.question
        )
        section: SectionDocument = self.section_service.get_section_by_question_id(
            self.current_question.id
        )
        message_type = ChatMessageType(message_type.type)
        if message_type == ChatMessageType.ANSWER:
            self.add_message(
                message=message,
                type=ChatMessageType.ANSWER,
                role=ChatMessageRole.USER,
                question_id=self.current_question.id,
            )
            response = evaluate_answer(
                answer=message,
                question=self.current_question.question,
                section_content=section.text,
            )
            assistant_message = f"Feedback: {response.feedback}\n\nScore: {response.score} \n\n for next question type 'next'"
            self.add_message(
                message=assistant_message,
                type=ChatMessageType.FEEDBACK,
                role=ChatMessageRole.ASSISTANT,
                question_id=self.current_question.id,
                feedback=response.feedback,
                score=response.score,
            )
            return assistant_message
        elif message_type == ChatMessageType.HELP:
            self.add_message(
                message=message,
                type=ChatMessageType.HELP,
                role=ChatMessageRole.USER,
            )
            response = generate_explanation(
                message=message,
                question=self.current_question.question,
                section_content=section.text,
            )
            self.add_message(
                message=response.explanation,
                type=ChatMessageType.EXPLANATION,
                role=ChatMessageRole.ASSISTANT,
            )
            return response.explanation
        else:
            assistant_message = "Please provide an answer or ask for help. If you want to skip the question, type 'next'."
            self.add_message(
                message=assistant_message,
                type=ChatMessageType.OTHER,
                role=ChatMessageRole.ASSISTANT,
            )
            return assistant_message

    def add_message(
        self,
        message: str,
        type: ChatMessageType,
        role: ChatMessageRole,
        question_id: uuid.UUID | None = None,
        feedback: str | None = None,
        score: float | None = None,
    ) -> None:
        if self.chat_session is None:
            return

        if len(self.chat_session.messages) == 0:
            previous_message = None
        else:
            previous_message = self.chat_session.messages[-1]

        self.chat_session.messages.append(
            ChatMessage(
                role=role,
                content=message,
                type=type,
                previous_message_id=previous_message.id if previous_message else None,
                question_id=question_id if question_id else self.current_question.id,
                feedback=feedback,
                score=score,
            )
        )

    def get_history_messages(self) -> List[ChatMessage]:
        if self.chat_session is None:
            return []
        messages = [
            {"role": message.role.value, "content": message.content}
            for message in self.chat_session.messages
        ]
        return messages

    def finish_chat_session(self) -> None:
        if self.chat_session is None:
            return

        self.chat_session.overall_score = self.calculate_overall_score()
        self.chat_session.number_of_questions = len(self.questions)
        self.chat_session_repo.create(self.chat_session)

    def calculate_overall_score(self) -> float:
        if self.chat_session is None:
            return 0

        assistant_feedback = self.get_assistant_feedback_scores()
        return round(sum(assistant_feedback) / len(assistant_feedback), 1)

    def get_assistant_feedback_scores(self) -> List[float]:
        if self.chat_session is None:
            return []
        return [
            message.score
            for message in self.chat_session.messages
            if message.type == ChatMessageType.FEEDBACK
        ]

    def get_chat_session_summaries(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        section_ids: List[uuid.UUID],
        limit: int = 10,
        offset: int = 0,
    ) -> List[ChatSessionSummary]:
        chat_sessions = self.chat_session_repo.list_chat_sessions(
            user_id=str(user_id),
            document_id=str(document_id),
            section_ids=[str(section_id) for section_id in section_ids],
            limit=limit,
            offset=offset,
        )
        book_sections = self.book_service.get_book_sections(document_id)
        section_titles = [
            f"{section.order}. {section.title}" for section in book_sections
        ]
        summaries = []
        for session in chat_sessions:
            answered_questions = len(
                [
                    msg
                    for msg in session.messages
                    if msg.type == ChatMessageType.FEEDBACK
                ]
            )

            section_titles = self.section_service.get_section_titles(
                session.section_ids
            )

            summaries.append(
                ChatSessionSummary(
                    overall_score=session.overall_score or 0.0,
                    number_of_questions=session.number_of_questions,
                    number_of_answered_questions=answered_questions,
                    section_titles=section_titles,
                    created_at=session.created_at,
                )
            )

        return summaries

    def make_session_summary(self) -> ChatSessionSummary | None:
        if self.chat_session is None:
            return None

        book_sections = self.book_service.get_book_sections(
            self.chat_session.document_id
        )
        filtered_sections = [
            section
            for section in book_sections
            if section.id in self.chat_session.section_ids
        ]
        section_titles = [
            f"{section.order}. {section.name}" for section in filtered_sections
        ]

        return ChatSessionSummary(
            overall_score=self.chat_session.overall_score or 0.0,
            number_of_questions=self.chat_session.number_of_questions,
            number_of_answered_questions=len(self.get_assistant_feedback_scores()),
            section_titles=section_titles,
            created_at=self.chat_session.created_at,
        )


def get_chat_service() -> ChatService:
    return ChatService(
        chat_session_repo=ChatSessionRepository(),
        section_service=get_section_service(),
        book_service=get_book_service(),
    )
