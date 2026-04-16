from langchain_core.messages import SystemMessage, HumanMessage
import json
import logging
from ..Prompts.graph_agent import GRAPH_AGENT_PROMPT
from ..LLM.llm import LLM
from ..Evaluators.GraphEvaluator import graph_evaluator
from utils.utils import clean_json

logger = logging.getLogger("graph_agent")
logger.setLevel(logging.INFO)


async def graph_agent(state: dict):
    logger.info("Inside graph_agent.")
    connections = state["connections"]
    query = state["query"]
    logger.debug(f"Received connections: {connections}")
    MAX_RETRIES = 1
    messages = [
        SystemMessage(content=GRAPH_AGENT_PROMPT),
        HumanMessage(content=json.dumps(connections)),
    ]
    llm = LLM()
    stream = state.get("stream")
    if stream:
        await stream({"type": "phase", "data": "Building graph..."})

    for i in range(MAX_RETRIES):
        logger.info(f"Attempt {i+1} of {MAX_RETRIES} for graph_agent.")

        result = await llm.generate(messages)
        print("Graph Builder Respones : ", result)
        if isinstance(result, dict) and result.get("error"):
            return result

        output_text = result.content.strip()  # Clean spaces
        clean = clean_json(output_text)

        print("Clean builder output : ", clean)

        # Check for presence of 'nodes' and 'edges'
        if (
            not isinstance(clean, dict)
            or "nodes" not in clean
            or "edges" not in clean
            or not clean.get("nodes")
            or not clean.get("edges")
        ):
            logger.error("Graph Builder result missing required 'nodes' or 'edges'.")
            return {"error": "Invalid graph output: 'nodes' and 'edges' required."}

        state["graph"] = clean
        logger.debug("Set state['graph'] to LLM output.")

        if stream:
            await stream({"type": "phase", "data": "Evaluating..."})

        evaluation = await graph_evaluator(clean, query)
        if isinstance(evaluation, dict) and evaluation.get("error"):
            break
        logger.info(f"Graph Evaluation result: {evaluation}")

        parsed = evaluation  # already parsed in evluator

        if "is_valid" not in parsed:
            logger.warning(
                "'is_valid' key not present in parsed evaluation. Breaking out of retry loop."
            )
            break
        if not parsed["is_valid"]:
            logger.warning("Evaluation failed, refining the output.")
            if stream:
                await stream({"type": "phase", "data": "Refining..."})

            feedback_message = HumanMessage(
                content=f"""
                                Your design score:
                                {parsed.get('score', 0)}
                                The previous design had following issues:
                                {parsed.get('issues', '')}
                                Please fix them and improve the design.
                                """
            )
            messages.append(feedback_message)
            # Continue loop, MAX_RETRIES=1 means exit anyway
            break
        else:
            logger.info("Evaluation is valid, breaking out of retry loop.")
            break

    logger.info("graph_agent returning state.")
    return state
