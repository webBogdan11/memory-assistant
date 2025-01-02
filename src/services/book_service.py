from models.section import SectionDocument
from repositories.book_repo import BookRepository
from repositories.section_repo import SectionRepository
from services.s3_storage import S3StorageService
import uuid
from models.book import BookDocument, BookMetadata
import pypdf
from io import BytesIO


class BookService:
    """
    Handles business logic for books/documents.
    """

    def __init__(
        self,
        book_repo: BookRepository,
        s3_storage: S3StorageService,
        section_repo: SectionRepository,
    ):
        self.book_repo = book_repo
        self.s3_storage = s3_storage
        self.section_repo = section_repo

    def _get_pages_count(self, file_data: bytes) -> int:
        pdf_reader = pypdf.PdfReader(BytesIO(file_data))
        return len(pdf_reader.pages)

    def get_pages_text(self, file_data: bytes, start_page: int, end_page: int) -> str:
        pdf_reader = pypdf.PdfReader(BytesIO(file_data))
        return "\n".join(
            [
                pdf_reader.pages[i].extract_text()
                for i in range(start_page, end_page + 1)
            ]
        )

    def _get_s3_key(self, s3_path: str) -> str:
        return s3_path.split("/", 3)[-1] if s3_path.startswith("s3://") else s3_path

    def upload_book(
        self, file_data: bytes, title: str, type: str, user_id: uuid.UUID
    ) -> BookDocument:
        """
        Uploads a book to S3 and returns the S3 key.
        """
        user_id = str(user_id)
        book_docs = self.book_repo.list(filter_dict={"userId": user_id, "title": title})
        if book_docs:
            raise ValueError("Book with this title already exists")

        unique_key = f"{user_id}/{title}_{uuid.uuid4()}"
        s3_key = self.s3_storage.upload_file(file_data, unique_key)
        pages_count = self._get_pages_count(file_data)
        # count doc size in mb
        doc_size = len(file_data) / (1024 * 1024)
        book_doc = BookDocument(
            user_id=user_id,
            title=title,
            type=type,
            s3_path=s3_key,
            metadata=BookMetadata(pages=pages_count, doc_size=doc_size),
        )
        return self.book_repo.create(book_doc)

    def get_books_by_user_id(self, user_id: uuid.UUID) -> list[BookDocument]:
        return self.book_repo.list({"userId": str(user_id)})

    def delete_book(self, book_id: uuid.UUID) -> None:
        book = self.get_book(book_id)
        if not book:
            raise ValueError("Book not found")

        s3_key = self._get_s3_key(book.s3_path)
        print(s3_key)
        self.s3_storage.delete_file(s3_key)
        self.book_repo.delete(str(book_id))

    def get_book(self, book_id: uuid.UUID) -> BookDocument | None:
        return self.book_repo.get(str(book_id))

    def get_book_content(self, book_id: uuid.UUID) -> bytes | None:
        book = self.get_book(book_id)
        if not book:
            return None
        s3_key = self._get_s3_key(book.s3_path)
        return self.s3_storage.get_file(s3_key)

    def add_book_start_page(self, book_id: uuid.UUID, start_page: int):
        book = self.get_book(book_id)
        if not book:
            return None
        book.first_page = start_page
        return self.book_repo.update(book)

    def get_book_sections(
        self, book_id: uuid.UUID, with_questions: bool = False
    ) -> list[SectionDocument]:
        book = self.get_book(book_id)
        if not book:
            return None

        filter_dict = {"bookId": str(book_id)}
        if with_questions:
            filter_dict["questions.0"] = {"$exists": True}

        return self.section_repo.list(filter_dict)


def get_book_service() -> BookService:
    return BookService(
        book_repo=BookRepository(),
        s3_storage=S3StorageService(),
        section_repo=SectionRepository(),
    )
