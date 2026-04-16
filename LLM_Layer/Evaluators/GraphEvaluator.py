from langchain_core.messages import SystemMessage, HumanMessage
import json
import logging
from ..Prompts.graph_evaluator import GRAPH_EVALUATOR_PROMPT
from ..LLM.llm import LLM
from utils.utils import clean_json

logger = logging.getLogger("graph_evaluator")
logger.setLevel(logging.INFO)


async def graph_evaluator(design, query):
    logger.info("Inside graph_evaluator.")
    messages = [
        SystemMessage(content=GRAPH_EVALUATOR_PROMPT),
        HumanMessage(
            content=json.dumps(
                {
                    "Description": query,
                    "Graph": design,
                }
            )
        ),
    ]

    llm = LLM()
    logger.debug("Sending messages to LLM for evaluation.")
    response = await llm.generate(messages)
    print("Evaluator Graph Response : ", response)

    if isinstance(response, dict) and response.get("error"):
        return response
    logger.info("Received response from LLM.")
    try:
        cleaned = clean_json(response.content)
    except Exception as e:
        logger.error(f"Error cleaning LLM response: {str(e)}")
        return {"error": "invalid response from graph evaluator"}
    return cleaned
