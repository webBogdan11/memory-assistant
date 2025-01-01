import uuid
from abc import ABC
from typing import Type, TypeVar, Generic
from pydantic import BaseModel, ConfigDict
from pydantic import Field, UUID4
from datetime import datetime, UTC


T = TypeVar("T", bound="NoSQLBaseDocument")


class BasePydanticModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )


class NoSQLBaseDocument(BasePydanticModel, Generic[T], ABC):
    """
    Base Pydantic model for NoSQL documents that:
      - Internally uses a UUID field named `id`.
      - Externally stores `_id` as a string in Mongo.
      - Provides from_mongo() / to_mongo() methods.
      - Inherits from ABC for clarity that it's a base / abstract class.
    """

    id: UUID4 = Field(default_factory=uuid.uuid4, alias="_id")

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), alias="createdAt"
    )
    updated_at: datetime | None = Field(default=None, alias="updatedAt")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    @classmethod
    def from_mongo(cls: Type[T], data: dict) -> T:
        """Convert Mongo doc {"_id": str, ...} -> Pydantic model with `id` = UUID."""
        if not data:
            raise ValueError("Data is empty or None.")

        _id_str = data.pop("_id", None)
        if not _id_str:
            raise ValueError("Missing '_id' in the Mongo document.")

        data["id"] = UUID4(_id_str)

        return cls(**data)

    def to_mongo(self, **kwargs) -> dict:
        """
        Convert this model to a dict suitable for Mongo.
        - Move `id` -> `_id`, as string
        - Convert any nested UUID fields to str
        """
        exclude_unset = kwargs.pop("exclude_unset", False)
        by_alias = kwargs.pop("by_alias", True)
        mode = kwargs.pop("mode", "json")

        parsed = self.model_dump(
            exclude_unset=exclude_unset, by_alias=by_alias, mode=mode, **kwargs
        )

        return parsed
