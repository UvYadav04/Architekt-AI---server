from langchain_core.messages import SystemMessage, HumanMessage
import json
import logging
from ..Prompts.connection_evaluator import CONNECTION_EVALUATOR_PROMPT
from ..LLM.llm import LLM
from utils.utils import clean_json

logger = logging.getLogger("connection_evaluator")
logger.setLevel(logging.INFO)


async def connection_evaluator(
    design, query, functional_requirements, non_functional_requirements
):
    logger.info("Inside connection_evaluator.")
    logger.debug(
        f"Received inputs: query={query}, functional_requirements={functional_requirements}, non_functional_requirements={non_functional_requirements}, design={design}"
    )

    messages = [
        SystemMessage(content=CONNECTION_EVALUATOR_PROMPT),
        HumanMessage(
            content=json.dumps(
                {
                    "query": query,
                    "functional_requirements": functional_requirements,
                    "non_functional_requirements": non_functional_requirements,
                    "design": design,
                }
            )
        ),
    ]

    logger.debug("Instantiating LLM.")
    llm = LLM()
    logger.info("Sending messages to LLM for connection evaluation.")
    response = await llm.generate(messages)
    if isinstance(response, dict) and response.get("error"):
        return response
    logger.info("Received response from LLM.")
    try:
        cleaned = clean_json(response.content)
    except Exception as e:
        logger.error(f"Error cleaning LLM response: {str(e)}")
        return {"error": "invalid response from graph evaluator"}
    return cleaned


def is_fully_connected(components, connections):
    logger.info("Checking if design is fully connected.")
    graph = {c: [] for c in components}

    for a, b in connections:
        graph[a].append(b)
        logger.debug(f"Adding edge: {a} -> {b}")

    visited = set()

    def dfs(node):
        logger.debug(f"DFS visiting node: {node}")
        if node in visited:
            logger.debug(f"Already visited node: {node}")
            return
        visited.add(node)
        for nei in graph[node]:
            dfs(nei)

    dfs(components[0])

    is_connected = len(visited) == len(components)
    logger.info(f"Design fully connected: {is_connected}")
    return is_connected
