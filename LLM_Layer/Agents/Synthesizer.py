from langchain_core.messages import SystemMessage, HumanMessage
import json
from ..Prompts.synthesizer import SYNTHESIZER_PROMPT
from ..LLM.llm import LLM
from ..Evaluators.ConnectionEvaluator import connection_evaluator
from utils.utils import clean_json


async def synthesizer_agent(state: dict):
    import logging

    logger = logging.getLogger("synthesizer_agent")
    MAX_RETRIES = 1

    logger.info("Inside synthesizer agent.")

    plan = state["plan"]
    functional_requirements = plan["functional_requirements"]
    non_functional_requirements = plan["non_functional_requirements"]
    query = state["query"]
    stream = state.get("stream")

    logger.info(f"Processing query: {query}")

    if stream:
        await stream({"type": "phase", "data": "Creating Connections..."})

    messages = [
        SystemMessage(content=SYNTHESIZER_PROMPT),
        HumanMessage(content=json.dumps(plan)),
    ]

    llm = LLM()

    for i in range(MAX_RETRIES):
        logger.info(f"Attempt {i+1} of {MAX_RETRIES} for synthesizer_agent.")

        result = await llm.generate(messages)
        if isinstance(result, dict) and result.get("error"):
            return result
        output_text = result.content

        print("synthesier output : ", output_text)

        try:
            output_json = clean_json(output_text)
        except Exception:
            return {"error": "invalid response"}

        if (
            not isinstance(output_json, dict)
            or "flows" not in output_json
            or "components" not in output_json
        ):
            return {"error": "invalid response"}

        state["connections"] = output_json

        if stream:
            await stream({"type": "phase", "data": "Evaluating..."})

        evaluation = await connection_evaluator(
            output_text, query, functional_requirements, non_functional_requirements
        )
        if isinstance(evaluation, dict) and evaluation.get("error"):
            break

        parsed = evaluation  # already parsed
        if "is_valid" not in parsed:
            logger.warning(
                "'is_valid' key not present in parsed evaluation. Breaking out of retry loop."
            )
            break
        if parsed["is_valid"]:
            logger.info("Evaluation is valid, breaking out of retry loop.")
            break

        logger.warning("Evaluation failed. Refining output.")

        if stream:
            await stream({"type": "phase", "data": "Refining..."})

        feedback_message = HumanMessage(
            content=(
                f"The previous design had connectivity issues:\n"
                f"{parsed.get('connectivity_issues','')}\n"
                "Some missing component:\n"
                f"{parsed.get('missing_components','')}\n"
                "Some extra components:\n"
                f"{parsed.get('extra_components','')}\n"
                "Please fix them and improve the design."
            )
        )
        messages.append(feedback_message)

    logger.info("Synthesizer agent returning state.")
    return state
