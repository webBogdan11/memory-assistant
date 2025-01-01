from src.models.book import BookDocument
from src.repositories.base_repo import AbstractRepository


class BookRepository(AbstractRepository[BookDocument]):
    """
    Concrete repository for the BookDocument model.
    """

    def __init__(self):
        super().__init__(collection_name="books")

    def model_class(self) -> type[BookDocument]:
        return BookDocument
