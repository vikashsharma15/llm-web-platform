import uuid
from typing import Optional
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Cookie, Response, BackgroundTasks
from sqlalchemy.orm import Session
from db.database import get_db, SessionLocal
from models.story import Story, StoryNode

from models.job import StoryJob
from schemas.story import(
    CompleteStoryResponse,
    CompleteStoryNodeResponse,
    CreateStoryRequest,
)
from schemas.job import StoryJobResponse
from core.story_generators import StoryGenerator

logger = logging.getLogger(__name__)

#Example backend - URL/api/stories/create-story
router = APIRouter(
    prefix="/stories",
    tags=["stories"]
)

# Function session_id return karega
# Matlab user authenticated hai
#  (at least session present hai)
def get_session_id(session_id: Optional[str]= Cookie(None)):
    if not session_id:
        session_id = str(uuid.uuid4())
    return session_id


# when you create something new
@router.post("/create",response_model=StoryJobResponse) #response_model works here like output blueprint
def create_story(
    request: CreateStoryRequest,
    background_tasks: BackgroundTasks,
    response: Response,
    session_id: str =Depends(get_session_id),
    db: Session =Depends(get_db)
):
    response.set_cookie(key="session_id", value=session_id, httponly=True)

    job_id = str(uuid.uuid4())

    job = StoryJob(
        job_id=job_id,
        session_id=session_id,
        theme=request.theme,
    )

    try:
        db.add(job)
        db.commit()
        db.refresh(job)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create story job: {e}")
        raise HTTPException(status_code=500, detail="Failed to create story job")

    # Offload heavy work to background, don't block the request
    background_tasks.add_task(
        generate_story_task,
        job_id=job.job_id,
      
        theme=request.theme, 
        session_id=session_id
    )
    print("JOB ID RECEIVED:", job_id),
    return job

def generate_story_task(job_id: str, theme: str, session_id: str):
    db = SessionLocal()
    try:
        job = db.query(StoryJob).filter(StoryJob.job_id == job_id).first()
        if not job:
            logger.error(f"Job not found: {job_id}")
            return

        try:
            job.status = "processing"
            db.commit()

            story = StoryGenerator.generate_story(db, session_id, theme)
            
            # ADD THESE LOGS
            logger.info(f"Story generated: {story}")
            logger.info(f"Story ID: {story.id}")

            job.story_id = story.id
            job.status = "completed"
            job.completed_at = datetime.now()
            db.commit()

            logger.info(f"Job updated with story_id: {job.story_id}")

        except Exception as e:
            logger.error(f"Story generation failed: {e}", exc_info=True)  # exc_info=True full traceback dega
            job.status = "failed"
            job.completed_at = datetime.now()
            job.error = str(e)
            db.commit()
    finally:
        db.close()


@router.get("/{story_id}/complete", response_model=CompleteStoryResponse)
def get_complete_story(story_id: int,db: Session = Depends(get_db)):
    story = db.query(Story).filter(Story.id== story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    complete_story = build_complete_story(db, story)
    return complete_story   


def build_complete_story(db: Session, story:Story)-> CompleteStoryResponse:
    nodes =  db.query(StoryNode).filter(StoryNode.story_id == story.id).all()
    node_dict = {}
    for node in nodes:
        node_response = CompleteStoryNodeResponse(
            id=node.id,
            content=node.content,
            is_ending=node.is_ending,
            is_winning_ending=node.is_winning_ending,
            options=node.options
        )
        node_dict[node.id]= node_response
    root_node = next((node for node in nodes if node.is_root), None)
    if not root_node:
        raise HTTPException(status_code=404, detail="story root node not found")

    return CompleteStoryResponse(
        id=story.id,
        title=story.title,
        session_id=story.session_id,
        createdAt=story.created_at,
        root_node=node_dict[root_node.id],
        all_nodes=node_dict
    )