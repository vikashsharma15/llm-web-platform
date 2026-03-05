from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from models.story import Story, StoryNode


class StoryRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_story_by_id(self, story_id: int) -> Story | None:
        return self.db.query(Story).filter(Story.id == story_id).first()

    def get_nodes_by_story_id(self, story_id: int) -> list[StoryNode]:
        return self.db.query(StoryNode).filter(StoryNode.story_id == story_id).all()

    def create_story(self, story: Story) -> Story:
        try:
            self.db.add(story)
            self.db.commit()
            self.db.refresh(story)
            return story
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e