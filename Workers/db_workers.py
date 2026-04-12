from db.Qdrant import QdrantDB


def save_design_qdrant(plan, connections, session_id, user_id, design_id):
    try:
        print(type(user_id))
        qdrant = QdrantDB()
        qdrant.save_design(plan, connections, design_id, session_id, user_id)
    except Exception as e:
        print("Background save failed:", e)
