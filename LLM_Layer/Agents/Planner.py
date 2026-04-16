from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
import json
import logging
from ..Tools.get_components import get_components
from ..Prompts.planner import PLANNER_PROMPT
from ..LLM.llm import LLM
from utils.utils import clean_json

logger = logging.getLogger("planner_agent")
logger.setLevel(logging.INFO)


async def planner_agent(state: dict):
    logger.info("Starting planner_agent")

    messages = [
        SystemMessage(content=PLANNER_PROMPT),
        HumanMessage(
            content=json.dumps({"query": state["query"], "level": state["level"]})
        ),
    ]

    stream = state.get("stream")
    if stream is not None:
        await stream({"type": "phase", "data": "Planning..."})

    llm = LLM()

    while True:
        logger.debug("Sending messages to LLM for planning")
        response = await llm.generate(messages,True)
        if isinstance(response, dict) and response.get("error"):
            return response

        # Tool call handling
        if hasattr(response, "tool_calls") and response.tool_calls:
            logger.info("LLM requested tool call, invoking get_components")
            tool_call = response.tool_calls[0]
            args = tool_call.get("args", {})
            tool_result = get_components.invoke(args)
            messages.append(response)
            messages.append(
                ToolMessage(
                    content=json.dumps(tool_result), tool_call_id=tool_call["id"]
                )
            )
            continue

        # JSON Parse and Validation
        parsed = clean_json(response.content)
        print("Planner Response : ",parsed)

        logger.info("LLM returned plan.")

        # Requirement check
        if (
            not isinstance(parsed, dict)
            or "functional_requirements" not in parsed
            or "non_functional_requirements" not in parsed
            or "components" not in parsed
        ):
            logger.error("Missing required fields in LLM response plan.")
            return {"error": "invalid response from planner agent"}

        state["plan"] = parsed
        break

    logger.info("planner_agent completed")
    return state
