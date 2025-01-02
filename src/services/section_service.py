from io import BytesIO
import pypdf
from repositories.section_repo import SectionRepository
from repositories.book_repo import BookRepository
from services.book_service import BookService, get_book_service
from models.section import QuestionItem, SectionDocument
from llm.llm import (
    generate_questions,
    get_section_info,
    SectionInfoList,
    improve_question,
)
import uuid


class SectionService:
    """
    Handles business logic for books/documents.
    """

    def __init__(
        self,
        book_service: BookService,
        section_repo: SectionRepository,
    ):
        self.book_service = book_service
        self.section_repo = section_repo

    def get_sections_by_book_id(self, book_id: uuid.UUID) -> list[SectionDocument]:
        return self.section_repo.list({"bookId": str(book_id)})

    def create_sections_magically(
        self,
        book_id: uuid.UUID,
        example_titles: list[str],
        start_page: int,
        content_end_page: int,
        preface_start_page: int,
        preface_end_page: int,
    ) -> list[SectionDocument]:
        book_content_file = self.book_service.get_book_content(book_id)
        if not book_content_file:
            raise ValueError("Book content not found")

        preface_text = self.book_service.get_pages_text(
            file_data=book_content_file,
            start_page=preface_start_page,
            end_page=preface_end_page,
        )
        section_info_list = get_section_info(
            content=preface_text, example_titles=example_titles
        )
        filtered_sections = [
            section
            for section in section_info_list.sections_info
            if section.page_number <= content_end_page
        ]

        self.book_service.add_book_start_page(book_id, start_page)

        created_sections = []
        sorted_info = sorted(filtered_sections, key=lambda x: x.page_number)
        for idx, section_info in enumerate(sorted_info):
            # If there's a "next" section, end_page = next start_page - 1
            if idx < len(sorted_info) - 1:
                next_start = sorted_info[idx + 1].page_number
                end_page = next_start
            else:
                end_page = content_end_page

            text = self.book_service.get_pages_text(
                file_data=book_content_file,
                start_page=section_info.page_number + start_page - 2,
                end_page=end_page + start_page - 3,
            )

            section_document = SectionDocument(
                book_id=book_id,
                name=section_info.title,
                start_page=section_info.page_number,
                end_page=end_page,
                text=text,
                order=idx + 1,
            )
            saved = self.section_repo.create(section_document)
            created_sections.append(saved)

        return created_sections

    def delete_section(self, section_id: uuid.UUID) -> None:
        """
        Deletes a section by its ID and reorders remaining sections.
        """
        section = self.section_repo.get(str(section_id))
        if not section:
            raise ValueError(f"Section with id {section_id} not found")

        # Get all sections for the same book
        book_sections = self.section_repo.list({"bookId": str(section.book_id)})
        deleted_order = section.order

        # Delete the section first
        self.section_repo.delete(str(section_id))

        # Prepare sections that need to be updated
        sections_to_update = [
            section
            for section in book_sections
            if section.id != section_id and section.order > deleted_order
        ]

        # Update their order
        for section in sections_to_update:
            section.order -= 1

        # Bulk update all modified sections
        if sections_to_update:
            self.section_repo.bulk_update(sections_to_update)

    def update_section(
        self,
        section_id: uuid.UUID,
        new_name: str,
        new_start_page: int,
        new_end_page: int,
    ) -> SectionDocument:
        section = self.section_repo.get(str(section_id))
        if not section:
            raise ValueError(f"Section with id {section_id} not found")

        pages_changed = (
            section.start_page != new_start_page or section.end_page != new_end_page
        )
        section.name = new_name
        section.start_page = new_start_page
        section.end_page = new_end_page

        if pages_changed:
            book = self.book_service.get_book(section.book_id)
            book_content_file = self.book_service.get_book_content(section.book_id)
            if not book_content_file:
                raise ValueError("Book content not found")
            updated_text = self.book_service.get_pages_text(
                file_data=book_content_file,
                start_page=new_start_page + book.first_page - 2,
                end_page=new_end_page + book.first_page - 3,
            )
            section.text = updated_text

        updated_section = self.section_repo.update(section)
        return updated_section

    def delete_all_sections(self, book_id: uuid.UUID) -> None:
        """
        Deletes all sections associated with a book.
        """
        self.section_repo.delete_many({"bookId": str(book_id)})

    def add_section_to_book(
        self, book_id: uuid.UUID, start_page: int, end_page: int, title: str, order: int
    ) -> SectionDocument:
        book_content_file = self.book_service.get_book_content(book_id)
        book = self.book_service.get_book(book_id)
        if not book_content_file:
            raise ValueError("Book content not found")

        # Get text content for the section
        text = self.book_service.get_pages_text(
            file_data=book_content_file,
            start_page=start_page + book.first_page - 2,
            end_page=end_page + book.first_page - 3,
        )

        existing_sections = self.get_sections_by_book_id(book_id)
        if order == -1 or order >= len(existing_sections):
            new_order = len(existing_sections) + 1
        else:
            sections_to_update = []
            for section in existing_sections:
                if section.order >= order:
                    section.order += 1
                    sections_to_update.append(section)
            if sections_to_update:
                self.section_repo.bulk_update(sections_to_update)
            new_order = order

        section = SectionDocument(
            book_id=book_id,
            name=title,
            start_page=start_page,
            end_page=end_page,
            text=text,
            order=new_order,
        )

        return self.section_repo.create(section)

    def generate_questions_magically(
        self, section_id: uuid.UUID, num_questions: int
    ) -> list[QuestionItem]:
        section = self.section_repo.get(str(section_id))
        if not section:
            raise ValueError(f"Section with id {section_id} not found")

        if not section.text:
            raise ValueError(f"Section with id {section_id} has no text")

        questions = generate_questions(section.text, num_questions)
        questions_to_create = [
            QuestionItem(question=question.question, type="general")
            for question in questions.questions
        ]
        section.questions.extend(questions_to_create)
        self.section_repo.update(section)
        return questions_to_create

    def get_questions_by_section_id(self, section_id: uuid.UUID) -> list[QuestionItem]:
        section = self.section_repo.get(str(section_id))
        if not section:
            raise ValueError(f"Section with id {section_id} not found")
        return section.questions

    def get_question_by_id(
        self, question_id: uuid.UUID, section_id: uuid.UUID
    ) -> QuestionItem:
        section = self.section_repo.get(str(section_id))
        if not section:
            raise ValueError(f"Section with id {section_id} not found")

        question = self.section_repo.get_question(
            section_id=str(section_id), question_id=str(question_id)
        )
        if not question:
            raise ValueError(f"Question with id {question_id} not found")
        return question

    def modify_question_magically(
        self, question_id: uuid.UUID, section_id: uuid.UUID, feedback: str
    ) -> QuestionItem:
        section = self.section_repo.get(str(section_id))
        if not section:
            raise ValueError(f"Section with id {section_id} not found")

        question = self.get_question_by_id(question_id, section_id)
        if not question:
            raise ValueError(f"Question with id {question_id} not found")
        improved_question = improve_question(question.question, feedback)
        question.question = improved_question.question
        self.section_repo.update_question(str(section_id), question)
        return question

    def delete_question(self, question_id: uuid.UUID, section_id: uuid.UUID) -> str:
        section = self.section_repo.get(str(section_id))
        if not section:
            raise ValueError(f"Section with id {section_id} not found")

        question = self.get_question_by_id(question_id, section_id)
        if not question:
            raise ValueError(f"Question with id {question_id} not found")
        self.section_repo.delete_question(str(section_id), str(question_id))
        return str(question.id)

    def add_question(
        self, section_id: uuid.UUID, question: str, type: str = "general"
    ) -> QuestionItem:
        section = self.section_repo.get(str(section_id))
        if not section:
            raise ValueError(f"Section with id {section_id} not found")

        question_item = QuestionItem(question=question, type=type)
        section.questions.append(question_item)
        self.section_repo.update(section)

        return question_item

    def update_question(
        self,
        question_id: uuid.UUID,
        section_id: uuid.UUID,
        question: str,
        type: str | None = None,
    ) -> QuestionItem:
        section = self.section_repo.get(str(section_id))
        if not section:
            raise ValueError(f"Section with id {section_id} not found")

        question_item = self.get_question_by_id(question_id, section_id)
        if not question_item:
            raise ValueError(f"Question with id {question_id} not found")
        question_item.question = question
        if type:
            question_item.type = type
        self.section_repo.update_question(str(section_id), question_item)
        return question_item

    def get_section_by_question_id(self, question_id: uuid.UUID) -> SectionDocument:
        section = self.section_repo.get_section_by_question_id(str(question_id))
        if not section:
            raise ValueError(f"Question with id {question_id} not found")
        return section


def get_section_service():
    book_service = get_book_service()
    section_repo = SectionRepository()
    return SectionService(book_service, section_repo)
