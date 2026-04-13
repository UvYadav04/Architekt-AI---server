import os
import requests
from fastapi import Request
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
import asyncio
import json
from ..safeExecution import safeExecution
from db.Qdrant import QdrantDB
from LLM_Layer.LLM.llm import LLM
from langchain_core.messages import SystemMessage, HumanMessage
from LLM_Layer.Prompts.chat_prompt import CHAT_SYSTEM_PROMPT


@safeExecution
async def handleQuery(
    query: str,
    user_id: str,
    design_id: str,
    session_id: str,
):
    qdrant = QdrantDB()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID is required for chat",
        )
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session ID is required for chat",
        )
    if not design_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Design ID is required for chat",
        )

    relatedContext = qdrant.search_design(query, user_id, design_id)
    relatedChat = qdrant.search_chat(query, user_id, design_id, session_id, limit=10)
    if relatedContext is not None:
        relatedContext = " ".join(relatedContext)
    if relatedChat is not None:
        relatedChat = " ".join(relatedChat)


    async def streamer_generator():
        messages = [
            SystemMessage(content=CHAT_SYSTEM_PROMPT),
            HumanMessage(
                content=json.dumps(
                    {
                        "query": query,
                        "previous_chat": relatedChat,
                        "relevant_context": relatedContext,
                    }
                )
            ),
        ]
        chat_response = ""
        llm = LLM()
        async for token in llm.stream(messages):
            chat_response += token

            yield json.dumps({"type": "text", "content": token}) + "<END>"
            await asyncio.sleep(0)

        # 🔥 AFTER STREAM COMPLETES → SAVE
        qdrant.save_chat(
            texts=[query, chat_response],
            session_id=session_id,
            user_id=user_id,
            design_id=design_id,
        )

    return StreamingResponse(
        streamer_generator(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 🔥 critical for nginx
            "Transfer-Encoding": "chunked",
        },
    )
