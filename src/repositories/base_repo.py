# app/repositories/abstract_repository.py

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List
from loguru import logger
from pymongo.collection import Collection
from pymongo import UpdateOne

from src.models.base import NoSQLBaseDocument
from src.db.mongo_connection import get_mongo_database


ModelType = TypeVar("ModelType", bound=NoSQLBaseDocument)


class AbstractRepository(Generic[ModelType], ABC):
    """
    Generic repository for any NoSQLBaseDocument.
    """

    def __init__(self, collection_name: str):
        self._collection_name = collection_name
        self._collection: Collection = get_mongo_database()[collection_name]

    @abstractmethod
    def model_class(self) -> type[ModelType]:
        """
        Subclasses must return the Pydantic Model class
        that inherits from NoSQLBaseDocument.
        """
        pass

    @property
    def collection(self) -> Collection:
        return self._collection

    def create(self, doc: ModelType) -> ModelType:
        """
        Insert into Mongo and return the inserted model (with _id set).
        """
        insert_data = doc.to_mongo()
        self.collection.insert_one(insert_data)

        return doc

    def get(self, id_val: str) -> ModelType | None:
        """
        Retrieve by _id from Mongo, then convert to model.
        """
        data = self.collection.find_one({"_id": id_val})
        if data:
            return self.model_class().from_mongo(data)
        return None

    def update(self, doc: ModelType) -> ModelType:
        """
        Replace existing doc in Mongo with `doc`.
        """
        filter_dict = {"_id": str(doc.id)}
        update_data = doc.to_mongo()
        self.collection.replace_one(filter_dict, update_data, upsert=True)
        return doc

    def delete(self, id_val: str) -> bool:
        """
        Delete a doc by _id, return True if a doc was deleted.
        """
        result = self.collection.delete_one({"_id": id_val})
        return result.deleted_count > 0

    def delete_many(self, filter_dict: dict) -> None:
        """
        Delete all docs based on a filter.
        """
        result = self.collection.delete_many(filter_dict)
        return result.deleted_count

    def list(self, filter_dict: dict = None) -> List[ModelType]:
        """
        Retrieve multiple docs based on a filter.
        """
        if filter_dict is None:
            filter_dict = {}
        cursor = self.collection.find(filter_dict)
        return [self.model_class().from_mongo(d) for d in cursor]

    def bulk_update(self, docs: List[ModelType]) -> None:
        """
        Update multiple documents in a single database operation.
        """
        if not docs:
            return

        operations = [
            UpdateOne({"_id": str(doc.id)}, {"$set": doc.to_mongo()}, upsert=True)
            for doc in docs
        ]
        self.collection.bulk_write(operations)
