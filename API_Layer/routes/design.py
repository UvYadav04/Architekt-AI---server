from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from ..controllers.design import design_pipeline
from LLM_Layer.index import AgentPipeline
from fastapi import APIRouter, BackgroundTasks
from fastapi import status, HTTPException
from bson import ObjectId
from API_Layer.safeExecution import safeExecution

router = APIRouter()


@router.post("/create-design")
@safeExecution
async def run_pipeline(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()
    agentPipeline = AgentPipeline()
    query = body["query"]
    level = body["level"]

    user_id = getattr(request.state, "user_id", None)
    session_id = getattr(request.state, "session_id", None)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please login to send a query.",
        )
    objectified_user_id = ObjectId(user_id)

    return StreamingResponse(
        design_pipeline(
            objectified_user_id,
            session_id,
            query,
            level,
            agentPipeline=agentPipeline,
            background_tasks=background_tasks,
        ),
        media_type="text/event-stream",
    )
