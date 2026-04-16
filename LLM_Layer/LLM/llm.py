import logging
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
import os
from ..Tools.get_components import get_components
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

logger = logging.getLogger("LLM")
logger.setLevel(logging.INFO)


class LLM:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            logger.debug("Creating new instance of LLM class.")
            cls._instance = super().__new__(cls)
        else:
            logger.debug("Using existing instance of LLM class.")
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            logger.debug("LLM instance already initialized; skipping __init__.")
            return  # prevent re-initialization
        logger.info("Initializing LLM instance...")
        GROQ_API_KEY = os.environ["GROQ_API_KEY"]
        logger.debug("Instantiating ChatGroq model.")

        self.planner_model = ChatGroq(
            api_key=GROQ_API_KEY, model="llama-3.3-70b-versatile", temperature=0
        ).bind_tools([get_components])

        self.executor_model = ChatGroq(
            api_key=GROQ_API_KEY,
            model="llama-3.3-70b-versatile",
            temperature=0,
            model_kwargs={
                "tool_choice": "none",
            },  # 🔥 critical
        )
        logger.debug("Binding tools to the model.")
        self._initialized = True
        logger.info("LLM instance initialized.")

    async def generate(self, messages, planner=False):
        logger.info("LLM.generate called.")
        # logger.debug(f"Messages to model: {messages}")
        model = self.planner_model if planner else self.executor_model
        try:
            result = await model.ainvoke(messages)
            logger.info("LLM.generate received result from model.")
            # logger.debug(f"Model result: {result}")
            return result
        except Exception as e:
            logger.error(f"Exception in LLM.generate: {e}")
            # Custom error handling per instructions:
            return {"error": str(e), "type": "error"}

    async def stream(self, messages):
        logger.info("LLM.stream called.")

        try:
            async for chunk in self.executor_model.astream(messages):
                # Each chunk is usually an AIMessageChunk
                content = getattr(chunk, "content", None)

                if content:
                    logger.debug(f"Streaming chunk")

                    yield content  # optional: allows caller to iterate

            logger.info("LLM.stream completed.")

        except Exception as e:
            logger.error(f"Exception in LLM.stream: {e}")
            # Custom error handling per instructions:
            yield {"error": str(e), "type": "error"}
