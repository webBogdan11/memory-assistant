from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from loguru import logger

from src.config import settings


class MongoDatabaseConnector:
    """Singleton pattern for MongoClient"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            try:
                client = MongoClient(settings.MONGO_DATABASE_HOST)
                client.admin.command("ping")
                cls._instance = client
                logger.info("Successfully connected to MongoDB")
            except ConnectionFailure as e:
                logger.error(f"Couldn't connect to MongoDB: {e}")
                raise
        return cls._instance


def get_mongo_database():
    """Get the main MongoDB database handle"""
    connection = MongoDatabaseConnector()
    return connection[settings.MONGO_DATABASE_NAME]
