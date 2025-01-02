from pydantic import EmailStr, Field

from models.base import NoSQLBaseDocument
from db.mongo_connection import get_mongo_database


class UserDocument(NoSQLBaseDocument):
    """
    Represents a user in the 'users' collection.
    """

    email: EmailStr
    password: str = Field(..., alias="password")
    name: str


user = UserDocument(
    email="marlo@bondo.ai",
    password="MARLO123BONDO",
    name="Marlo"
)

print(get_mongo_database().users.find_one({"email": "marlo@bondo.ai"}))
