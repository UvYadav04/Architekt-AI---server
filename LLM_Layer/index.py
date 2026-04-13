import logging
from langgraph.graph import StateGraph
from typing import Literal, TypedDict

from .Agents.Planner import planner_agent
from .Agents.GraphBuilder import graph_agent
from .Agents.Synthesizer import synthesizer_agent
from .Agents.Researcher import researcher_agent
from .runSafe import checkResultStatus, runAgentSafelyWrapper
import json
from utils.utils import clean_json

_pipeline_log = logging.getLogger("AgentPipeline")

phases = Literal[
    "Planning", "Evaluating", "Refining", "Connecting", "Building", "almost done..."
]


initialRetries = {
    "planner": 2,
    "Synthesizer": 2,
    "graph_builder": 2,
}


class DesignState(TypedDict, total=False):
    query: str
    plan: dict
    connections: str
    graph: dict
    level: str
    currentPhase: phases
    retries: dict
    error: str | None
    stream: callable


class AgentPipeline:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            _pipeline_log.debug("Created new AgentPipeline singleton instance.")
        else:
            _pipeline_log.debug("Returning existing AgentPipeline singleton instance.")
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            self.logger = logging.getLogger("AgentPipeline")
            self.logger.debug("AgentPipeline already initialized; skipping __init__.")
            return

        self.logger = logging.getLogger("AgentPipeline")
        self.logger.setLevel(logging.DEBUG)

        self.logger.info("Initializing AgentPipeline instance...")
        self.graph = StateGraph(DesignState)
        self._build_graph()
        self.logger.debug("Graph built and compiled.")
        self.app = self.graph.compile()
        self._initialized = True
        self.initialRetries = initialRetries
        self.logger.info("AgentPipeline initialized.")

    async def end_node(self, state):
        self.logger.debug(
            "end_node invoked; state keys: %s, error=%s",
            list(state.keys()) if isinstance(state, dict) else type(state),
            state.get("error") if isinstance(state, dict) else None,
        )
        error = state.get("error")
        if error is not None:
            self.logger.warning(f"End node: detected error: {error}")
            return {
                "status": "failed",
                "error": error,
            }
        graph = state.get("graph")
        # self.logger.info(f"End node returning graph: {graph}")
        return {"graph": graph}

    async def planner_node(self, state):
        self.logger.info("Planner node invoked.")
        self.logger.debug(
            "Planner context: phase=%s, retries=%s",
            state.get("currentPhase"),
            state.get("retries"),
        )
        result = await runAgentSafelyWrapper(state, planner_agent, "planner")
        # self.logger.debug(f"Planner node result: {result}")
        return result

    async def synthesizer_node(self, state):
        self.logger.info("Synthesizer node invoked.")
        self.logger.debug(
            "Synthesizer context: phase=%s, retries=%s",
            state.get("currentPhase"),
            state.get("retries"),
        )
        result = await runAgentSafelyWrapper(state, synthesizer_agent, "synthesizer")
        # self.logger.debug(f"Synthesizer node result: {result}")
        return result

    async def graph_builder_node(self, state):
        self.logger.info("Graph builder node invoked.")
        self.logger.debug(
            "Graph builder context: phase=%s, retries=%s",
            state.get("currentPhase"),
            state.get("retries"),
        )
        result = await runAgentSafelyWrapper(state, graph_agent, "graph_builder")
        # self.logger.debug(f"Graph builder node result: {result}")
        return result

    def _build_graph(self):
        self.logger.info("Building agent graph...")
        self.graph.add_node("planner", self.planner_node)
        self.graph.add_node("synthesizer", self.synthesizer_node)
        self.graph.add_node("graph_builder", self.graph_builder_node)
        self.graph.add_node("end", self.end_node)

        self.logger.debug("Adding conditional edges to the graph.")
        self.graph.add_conditional_edges(
            "planner", checkResultStatus("planner", "synthesizer")
        )
        self.graph.add_conditional_edges(
            "synthesizer", checkResultStatus("synthesizer", "graph_builder")
        )
        self.graph.add_conditional_edges(
            "graph_builder", checkResultStatus("graph_builder", "end")
        )

        self.graph.set_entry_point("planner")
        self.graph.set_finish_point("end")
        self.logger.info("Agent graph is built and entry/finish points set.")

    def extract_output(self, state):
        error = state.get("error")
        if error is not None:
            return {"type": "error", "data": error}
        plan = state.get("plan")
        connections = state.get("connections")
        graph = state.get("graph")
        return {
            "data": {"plan": plan, "connections": connections, "graph": graph},
            "type": "result",
        }

    async def run(self, query: str, stream_fn, level="intermediate"):
        self.logger.info(
            "Starting pipeline run (query_len=%d, level=%r, stream_fn=%s).",
            len(query) if query else 0,
            level,
            "set" if stream_fn is not None else "none",
        )
        self.logger.debug("Pipeline query: %r", query)
        self.logger.debug("Pipeline initial retries: %s", self.initialRetries)
        payload = {
            "query": query,
            "level": level,
            "retries": self.initialRetries,
            "stream": stream_fn,
        }
        try:
            result = await self.app.ainvoke(payload)
        except Exception:
            self.logger.exception("Pipeline ainvoke failed")
            raise
        self.logger.info("Pipeline run completed.")
        # self.logger.debug("Pipeline run result: %s", result)
        return self.extract_output(result)
