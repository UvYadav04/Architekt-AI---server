import logging
import uuid
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from dotenv import load_dotenv
from fastembed import TextEmbedding
from API_Layer.safeExecution import safeExecution


load_dotenv()
import os

logger = logging.getLogger("QdrantDB")
logger.setLevel(logging.INFO)


class QdrantDB:
    _instance = None

    DESIGN_COLLECTION = "architekt_design_collection"
    CHAT_COLLECTION = "architekt_chat_collection"

    @safeExecution
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            logger.debug("Creating new QdrantDB instance.")
            cls._instance = super().__new__(cls)
        return cls._instance

    @safeExecution
    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        logger.info("Initializing QdrantDB...")
        url = os.environ.get("QDRANT_URL")
        api_key = os.environ.get("QDRANT_API_KEY")
        self.client = QdrantClient(url=url, api_key=api_key, check_compatibility=False)

        self.embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        self.vector_size = 384

        self._ensure_collections()

        self._initialized = True
        logger.info("QdrantDB initialized.")

    @safeExecution
    def _ensure_collections(self):
        logger.info("Ensuring required collections exist...")

        for collection in [self.DESIGN_COLLECTION, self.CHAT_COLLECTION]:
            if not self.client.collection_exists(collection):
                logger.info(f"Creating collection: {collection}")

                self.client.create_collection(
                    collection_name=collection,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE,
                    ),
                )
            else:
                logger.info(f"Collection already exists: {collection}")

            self._ensure_indexes(collection)

    @safeExecution
    def _ensure_indexes(self, collection: str):
        logger.info(f"Ensuring indexes for {collection}")

        try:
            # user_id index
            self.client.create_payload_index(
                collection_name=collection,
                field_name="user_id",
                field_schema="keyword",
            )

            # design_id index
            self.client.create_payload_index(
                collection_name=collection,
                field_name="design_id",
                field_schema="keyword",
            )

            # optional: type index (very useful)
            self.client.create_payload_index(
                collection_name=collection,
                field_name="session_id",
                field_schema="keyword",
            )

        except Exception as e:
            logger.warning(f"Index creation warning (likely already exists): {e}")

    @safeExecution
    def _embed(self, texts: List[str]) -> List[List[float]]:
        return list(self.embedder.embed(texts))

    @safeExecution
    def handle_design(self, plan, connections):
        FR = plan["functional_requirements"]
        NFR = plan["non_functional_requirements"]
        components = plan["components"]
        flows = connections["flows"]

        # Build adjacency
        from collections import defaultdict

        adj = defaultdict(set)

        for a, b in flows:
            adj[a].add(b)
            adj[b].add(a)

        chunks = []

        for comp in components:
            name = comp["name"]
            reason = comp.get("reason", "")

            neighbors = list(adj[name])  # 1-hop connections

            content = f"""
            Component: {name}
            Purpose: {reason}
            Connected to: {", ".join(neighbors)}
            """

            chunk = {
                "type": "component",
                "name": name,
                "content": content,
                "connections": neighbors,
            }

            chunks.append(chunk)

        return chunks

    @safeExecution
    def save_design(
        self,
        plan,
        connections,
        design_id,
        session_id,
        user_id,
        payloads: Optional[List[dict]] = None,
    ):
        chunks = self.handle_design(plan, connections)

        logger.info(f"Saving design data ({len(chunks)} items)")
        texts = [chunk["content"] for chunk in chunks]
        vectors = self._embed(texts)

        points = []
        for i, vector in enumerate(vectors):
            payload = payloads[i] if payloads else {}

            payload.update(
                {
                    "text": texts[i],
                    "type": "design",
                    "session_id": session_id,
                    "user_id": user_id,
                    "design_id": design_id,
                }
            )

            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload=payload,
                )
            )

        self.client.upsert(
            collection_name=self.DESIGN_COLLECTION,
            points=points,
        )

    @safeExecution
    def save_chat(
        self,
        texts: List[str],
        session_id: str,
        user_id: str,
        design_id: str,
        payloads: Optional[List[dict]] = None,
    ):
        logger.info(f"Saving chat for session {session_id}")
        vectors = self._embed(texts)
        points = []
        for i, vector in enumerate(vectors):
            payload = payloads[i] if payloads else {}

            payload.update(
                {
                    "text": texts[i],
                    "session_id": session_id,
                    "user_id": user_id,
                    "design_id": design_id,
                    "type": "chat",
                }
            )

            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload=payload,
                )
            )

        self.client.upsert(
            collection_name=self.CHAT_COLLECTION,
            points=points,
        )

    @safeExecution
    def search_design(self, query: str, user_id: str, design_id: str, limit: int = 5):
        query_vector = self._embed([query])[0]
        result = self.client.query_points(
            collection_name=self.DESIGN_COLLECTION,
            query=query_vector,
            limit=limit,
            query_filter={
                "must": [
                    {"key": "user_id", "match": {"value": user_id}},
                    {"key": "design_id", "match": {"value": design_id}},
                ]
            },
        )
        if result is None or result.points is None:
            return None
        texts = [point.payload["text"] for point in result.points]
        return texts

    @safeExecution
    def search_chat(
        self, query: str, user_id: str, design_id: str, session_id: str, limit: int = 5
    ):
        query_vector = self._embed([query])[0]

        result = self.client.query_points(
            collection_name=self.CHAT_COLLECTION,
            query=query_vector,
            limit=limit,
            query_filter={
                "must": [
                    {"key": "user_id", "match": {"value": user_id}},
                    {"key": "design_id", "match": {"value": design_id}},
                    {"key": "session_id", "match": {"value": session_id}},
                ]
            },
        )
        if result is None or result.points is None:
            return None
        texts = [point.payload["text"] for point in result.points]
        return texts
