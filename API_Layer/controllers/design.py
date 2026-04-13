import asyncio
import json
import logging
from db.Mongo import MongoDB
import time
from Workers.db_workers import save_design_qdrant
from fastapi import status, HTTPException
from utils.utils import clean_json
from API_Layer.safeExecution import safeExecution

logger = logging.getLogger("design_pipeline")
logger.setLevel(logging.INFO)
from fastapi.responses import StreamingResponse


@safeExecution
async def design_pipeline(
    user_id: str,
    session_id: str,
    query: str,
    level: str,
    agentPipeline,
    background_tasks,
):
    queue = asyncio.Queue()
    mongo = MongoDB()

    user_designs = mongo.get_all_designs({"user_id": user_id})

    if user_designs and len(user_designs) >= 2:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="You can only create 5 designs in free tier.",
        )

    async def stream_fn(msg):
        logger.debug(f"Streaming message to queue: {msg}")
        await queue.put(msg)
        await asyncio.sleep(0)

    async def run():
        logger.info(f"Starting agentPipeline.run with query='{query}', level='{level}'")
        response = await agentPipeline.run(query, stream_fn, level)

        output = {}
        data = response["data"]

        if response["type"] != "error" and data is not None:
            graph = clean_json(data["graph"])
            connections = clean_json(data["connections"])
            plan = clean_json(data["plan"])

            if graph and plan and connections:
                newDesign = mongo.create_design(
                    {
                        "user_id": user_id,
                        "chatCounts": 0,
                        "created_at": time.time(),
                        "graph": graph,
                        "plan": plan,
                        "connections": connections,
                    }
                )

                mongo.update_user({"_id": user_id}, {"$inc": {"designsCreated": 1}})

                design_id = str(newDesign.inserted_id)

                output["designId"] = design_id

                background_tasks.add_task(
                    save_design_qdrant,
                    plan,
                    connections,
                    session_id,
                    str(user_id),
                    design_id,
                )
                await queue.put({"type": "final", "data": output})

        else:
            await queue.put({"type": "error", "data": data})

        await queue.put(None)  # end signal

    async def event_generator():
        asyncio.create_task(run())

        while True:
            item = await queue.get()
            print("got item : ", item)
            if item is None:
                break
            print("yielding:", item)
            yield json.dumps(item) + "<END>\n\n"
            await asyncio.sleep(0.01)
            print("yield finished for:", item)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Transfer-Encoding": "chunked",
        },
    )
