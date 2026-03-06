from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from models.story import Story, StoryNode


class StoryRepository:
    """Handles all DB operations for Story and StoryNode models."""

    def __init__(self, db: Session):
        self.db = db

    def get_story_by_id(self, story_id: int) -> Story | None:
        """Fetches story by primary key — returns None if not found."""
        return self.db.query(Story).filter(Story.id == story_id).first()

    def get_story_by_theme(self, theme: str) -> Story | None:
        """Checks if a story already exists for this theme.
            avoids redundant LLM calls by reusing existing stories."""
        return self.db.query(Story).filter(Story.theme == theme).first()

    def get_nodes_by_story_id(self, story_id: int) -> list[StoryNode]:
        """Fetches all nodes belonging to a story."""
        return self.db.query(StoryNode).filter(StoryNode.story_id == story_id).all()

    def create_story(self, story: Story) -> Story:
        """Inserts a new story record into DB."""
        try:
            self.db.add(story)
            self.db.commit()
            self.db.refresh(story)
            return story
        except SQLAlchemyError:
            self.db.rollback()
            raise