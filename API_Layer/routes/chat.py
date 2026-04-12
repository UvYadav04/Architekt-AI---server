from fastapi import APIRouter, Request, Response
from requests.sessions import session
from API_Layer.controllers.chat import handleQuery
from fastapi import status, HTTPException
import json
from bson import ObjectId
import os
from db.Mongo import MongoDB
from API_Layer.safeExecution import safeExecution


router = APIRouter()


@router.post("/query")
@safeExecution
async def handleChat(request: Request, response: Response):
    try:
        body = await request.json()
        query = body.get("query")
        design_id = body.get("design_id")
        mongo = MongoDB()

        user_id = getattr(request.state, "user_id", None)
        session_id = getattr(request.state, "session_id", None)
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Please login to send a query.",
            )
        if design_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please select a valid design.",
            )

        # Get user info
        try:
            objectified_user_id = ObjectId(user_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user id format.",
            )
        userInfo = mongo.get_user({"_id": objectified_user_id})

        if userInfo is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Please login to send a query.",
            )

        # Get design info
        try:
            objectified_design_id = ObjectId(design_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid design id format.",
            )
        designInfo = mongo.get_design({"_id": objectified_design_id})

        if designInfo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Design not found.",
            )

        # Check chatCounts on designInfo
        chat_allowed = int(os.environ.get("USER_CHAT_ALLOWED", 12))
        design_chat_counts = designInfo.get("chatCounts", 0)
        if design_chat_counts >= chat_allowed:
            raise HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail=f"You can do only {chat_allowed} queries for each design in free tier.",
            )

        # Increment chatCounts by one
        mongo.update_design({"_id": objectified_design_id}, {"$inc": {"chatCounts": 1}})

        # Call handleQuery
        return await handleQuery(
            query,
            user_id,
            design_id,
            session_id,
        )
    except Exception as e:
        print(e)
        return json.dumps({"type": "error", "message": str(e)}) + "<END>"
