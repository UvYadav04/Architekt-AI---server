import asyncio
import json
import logging
from db.Mongo import MongoDB
import time
from Workers.db_workers import save_design_qdrant
from utils.utils import clean_json

logger = logging.getLogger("design_pipeline")
logger.setLevel(logging.INFO)


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

    if user_designs and len(user_designs) >= 5:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="You can only create 5 designs in free tier.",
        )

    def stream_fn(msg):
        logger.debug(f"Streaming message to queue: {msg}")
        queue.put_nowait(msg)

    async def run():
        logger.info(f"Starting agentPipeline.run with query='{query}', level='{level}'")
        response = await agentPipeline.run(query, stream_fn, level)
        print(response)
        output = {}
        data = response["data"]
        if response["type"] != "error" and data is not None:
            graph = clean_json(data["graph"])
            connections = clean_json(data["connections"])
            plan = clean_json(data["plan"])

            if graph is not None and plan is not None and connections is not None:
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
                # output["plan"] = plan
                # output["connections"] = connections
                # output["graph"] = graph
                design_id = str(newDesign.inserted_id)
                stringified_user_id = str(user_id)
                output["designId"] = design_id
                background_tasks.add_task(
                    save_design_qdrant,
                    plan,
                    connections,
                    session_id,
                    stringified_user_id,
                    design_id,
                )
                logger.info(
                    "agentPipeline.run completed, putting final response to queue."
                )
                await queue.put({"type": "final", "data": output})
        else:
            logger.info("agentPipeline.run completed, putting final response to queue.")
            await queue.put({"type": "error", "data": data})

        logger.debug("Putting end signal (None) to queue.")
        await queue.put(None)  # end signal

    logger.info("Creating background task to run agent pipeline.")
    asyncio.create_task(run())

    while True:
        item = await queue.get()
        # logger.debug(f"Received item from queue: {item}")
        if item is None:
            logger.info("Received end signal from queue, breaking loop.")
            break
        stringified = json.dumps(item)
        # logger.debug(f"Yielding stringified item: {stringified}")
        yield stringified

        # Route to get design by id: /info/:id
