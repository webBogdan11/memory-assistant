from models.section import QuestionItem, SectionDocument
from repositories.base_repo import AbstractRepository


class SectionRepository(AbstractRepository[SectionDocument]):
    """
    Concrete repository for the SectionDocument model.
    """

    def __init__(self):
        super().__init__(collection_name="sections")

    def model_class(self) -> type[SectionDocument]:
        return SectionDocument

    def get_question(self, section_id: str, question_id: str) -> QuestionItem | None:
        result = self.collection.find_one(
            {"_id": section_id, "questions._id": question_id},
            {"questions.$": 1},  # Project only the matching question
        )
        if result and result.get("questions"):
            return QuestionItem.from_mongo(result["questions"][0])
        return None

    def update_question(self, section_id: str, question: QuestionItem) -> bool:
        """Update a specific question directly"""
        result = self.collection.update_one(
            {"_id": section_id, "questions._id": str(question.id)},
            {"$set": {"questions.$": question.to_mongo()}},
        )
        return result.modified_count > 0

    def delete_question(self, section_id: str, question_id: str) -> bool:
        """Delete a specific question from a section

        Args:
            section_id: The ID of the section containing the question
            question_id: The ID of the question to delete

        Returns:
            bool: True if the question was successfully deleted, False otherwise
        """
        result = self.collection.update_one(
            {"_id": section_id}, {"$pull": {"questions": {"_id": question_id}}}
        )
        return result.modified_count > 0

    def get_section_by_question_id(self, question_id: str) -> SectionDocument | None:
        """Find a section that contains a specific question ID.

        Args:
            question_id: The ID of the question to search for

        Returns:
            SectionDocument: The section containing the question, or None if not found
        """
        result = self.collection.find_one({"questions._id": question_id})
        if result:
            return self.model_class().from_mongo(result)
        return None
