from langchain.tools import tool


@tool
def get_components(use_case: str, requirements: list[str] = []):
    """Fetch system design components based on use case and requirements"""

    use_case = use_case.lower()
    reqs = [r.lower() for r in requirements]

    components = []

    components.extend(
        [
            {"name": "Load Balancer", "purpose": "distribute incoming traffic"},
            {"name": "API Gateway", "purpose": "routing, auth, rate limiting"},
            {"name": "Application Server", "purpose": "core business logic"},
        ]
    )

    if "chat" in use_case or "messaging" in use_case:
        components.extend(
            [
                {
                    "name": "WebSocket Gateway",
                    "purpose": "real-time bidirectional communication",
                },
                {"name": "Redis", "purpose": "pub/sub and presence tracking"},
                {
                    "name": "Message Queue (Kafka)",
                    "purpose": "async message processing",
                },
                {
                    "name": "NoSQL Database (Cassandra)",
                    "purpose": "message storage at scale",
                },
                {"name": "Notification Service", "purpose": "push notifications"},
                {"name": "Media Storage (S3)", "purpose": "file/image storage"},
            ]
        )

    if "payment" in use_case or "ecommerce" in use_case:
        components.extend(
            [
                {"name": "Payment Gateway", "purpose": "handle transactions"},
                {"name": "Order Service", "purpose": "manage orders"},
                {"name": "Inventory Service", "purpose": "track stock"},
                {"name": "Relational Database", "purpose": "transaction consistency"},
                {"name": "Cache (Redis)", "purpose": "fast product lookup"},
            ]
        )

    if "stream" in use_case or "video" in use_case:
        components.extend(
            [
                {"name": "CDN", "purpose": "content delivery"},
                {"name": "Object Storage", "purpose": "store media files"},
                {"name": "Transcoding Service", "purpose": "convert video formats"},
                {"name": "Queue (Kafka)", "purpose": "processing pipeline"},
            ]
        )

    if "low latency" in reqs:
        components.append({"name": "Cache (Redis)", "purpose": "reduce response time"})

    if "high scalability" in reqs:
        components.extend(
            [
                {"name": "Sharding", "purpose": "horizontal scaling of database"},
                {"name": "Auto Scaling", "purpose": "handle variable load"},
            ]
        )

    if "fault tolerance" in reqs or "reliable" in reqs:
        components.extend(
            [
                {"name": "Replication", "purpose": "data redundancy"},
                {"name": "Failover System", "purpose": "handle node failures"},
            ]
        )

    if "security" in reqs or "encryption" in reqs:
        components.extend(
            [
                {
                    "name": "Authentication Service",
                    "purpose": "user identity management",
                },
                {
                    "name": "Encryption Service",
                    "purpose": "secure data at rest/in transit",
                },
            ]
        )

    seen = set()
    unique_components = []

    for comp in components:
        if comp["name"] not in seen:
            unique_components.append(comp)
            seen.add(comp["name"])

    return {"components": unique_components}
