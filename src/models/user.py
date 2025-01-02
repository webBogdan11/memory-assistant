from pydantic import EmailStr, Field

from models.base import NoSQLBaseDocument


class UserDocument(NoSQLBaseDocument):
    """
    Represents a user in the 'users' collection.
    """

    email: EmailStr
    password: str = Field(..., alias="password")
    name: str
