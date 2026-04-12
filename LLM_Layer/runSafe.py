import asyncio
import logging

logger = logging.getLogger("runSafe")
logger.setLevel(logging.INFO)


def classify_error(err):
    msg = str(err).lower()
    logger.debug(f"Classifying error message: {msg}")

    if "rate" in msg or "timeout" in msg:
        logger.info("Error classified as RUNTIME and retryable")
        return {"type": "RUNTIME", "retryable": True}

    if "empty" in msg or "json" in msg:
        logger.info("Error classified as INVALID_OUTPUT and not retryable")
        return {"type": "INVALID_OUTPUT", "retryable": False}

    logger.info("Error classified as UNKNOWN and retryable")
    return {"type": "UNKNOWN", "retryable": True}


def decrement_retry(state, agent_name):
    retries = state.get("retries", {})
    retries[agent_name] = retries.get(agent_name, 0) - 1
    logger.info(
        f"Decremented retries for agent '{agent_name}' to {retries[agent_name]}"
    )
    return retries


def reset_retry(state, agent_name, max_retries=2):
    retries = state.get("retries", {})
    retries[agent_name] = max_retries
    logger.info(f"Reset retries for agent '{agent_name}' to {max_retries}")
    return retries


async def runAgentSafe(agentFn, state):
    try:
        logger.info(
            f"Running agent function: {getattr(agentFn, '__name__', str(agentFn))}"
        )
        result = await agentFn(state)
        print("result : ", result)
        if result is None or (isinstance(result, dict) and result.get("error")):
            logger.error("Empty or invalid response encountered from agent.")
            raise ValueError("Empty or invalid response")
        logger.info("Agent ran successfully.")
        return {"success": True, "data": result}

    except Exception as err:
        logger.error(f"Error in runAgentSafe: {err}", exc_info=True)
        error_info = classify_error(err)

        return {
            "success": False,
            "error": {
                "type": error_info["type"],
                "message": str(err),
                "retryable": error_info["retryable"],
                "agent": getattr(agentFn, "__name__", str(agentFn)),
            },
        }


async def runAgentSafelyWrapper(state, agent_fn, agent_name):
    logger.info(f"Running agent safely wrapper for: {agent_name}")

    res = await runAgentSafe(agent_fn, state)

    if not res["success"]:
        logger.warning(
            f"Agent '{agent_name}' failed with error: {res['error']}. Decrementing retry count."
        )
        return {
            **state,
            "error": res["error"],
            "retries": decrement_retry(state, agent_name),
        }

    new_state = res["data"]
    logger.info(
        f"Agent '{agent_name}' ran successfully. Resetting retry count and merging new state."
    )
    return {
        **state,
        **new_state,
        "error": None,
        "retries": reset_retry(state, agent_name),
    }


def checkResultStatus(currentAgent, nextAgent):
    def route_after_agent(state):
        error = state.get("error")
        retries = state.get("retries", {}).get(currentAgent, 0)
        if error:
            logger.warning(
                f"Agent '{currentAgent}' encountered error: {error}. Retries left: {retries}"
            )
            if error.get("retryable") and retries > 0:
                logger.info(f"Retrying agent '{currentAgent}' again.")
                return currentAgent
            logger.info(f"No retries left for agent '{currentAgent}'. Moving to end.")
            return "end"
        logger.info(
            f"No error in agent '{currentAgent}'. Moving to next agent '{nextAgent}'."
        )
        return nextAgent

    return route_after_agent
