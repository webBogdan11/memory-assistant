from models.user import UserDocument
from repositories.base_repo import AbstractRepository


class UserRepository(AbstractRepository[UserDocument]):
    """
    Concrete repository for the UserDocument model.
    """

    def __init__(self):
        super().__init__(collection_name="users")

    def model_class(self) -> type[UserDocument]:
        return UserDocument

    # Example of a custom query
    def find_by_email(self, email: str) -> UserDocument | None:
        data = self.collection.find_one({"email": email})
        if data:
            return self.model_class().from_mongo(data)
        return None
