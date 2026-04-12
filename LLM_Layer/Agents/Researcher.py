from langchain_core.messages import SystemMessage, HumanMessage
import json
from ..Prompts.synthesizer import SYNTHESIZER_PROMPT


def researcher_agent(state: dict):
    MAX_RETRIES = 2

    plan = state["plan"]

    messages = [
        SystemMessage(content=SYNTHESIZER_PROMPT),
        HumanMessage(content=json.dumps(plan)),
    ]

    for i in range(MAX_RETRIES):
        result = llm.invoke(messages)

        output_text = result.content

        evaluation = evaluator.invoke({"design": output_text})

        state["connections"] = output_text

        if evaluation["is_valid"]:
            break

        feedback_message = HumanMessage(
            content=f"""
                        The previous design had issues:
                        {evaluation["issues"]}
                        
                        Please fix them and improve the design.
                        """
        )

        messages.append(feedback_message)

    return {**state, "connections": output_text}
