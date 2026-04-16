from pymongo import MongoClient
from typing import Optional
import os


class MongoDB:
    _instance: Optional["MongoDB"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(MongoDB, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self.uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.db_name = os.getenv("DB_NAME")
        self.client = MongoClient(self.uri)
        self.db = self.client[self.db_name]

        # Collections
        self.users = self.db["users"]
        self.chats = self.db["chats"]
        self.designs = self.db["designs"]

        self._initialized = True

    # =========================
    # USER COLLECTION
    # =========================
    def create_user(self, user_data: dict):
        return self.users.insert_one(user_data)

    def get_user(self, query: dict):
        return self.users.find_one(query)

    def is_admin(self, query: dict):
        user_info = self.users.find_one(query)
        if user_info is None:
            return False
        else:
            return user_info.get("email") == "dineshnirban01@gmail.com"

    def update_user(self, query: dict, update: dict):
        return self.users.update_one(query, update)

    # =========================
    # CHAT COLLECTION
    # =========================
    def create_chat(self, chat_data: dict):
        return self.chats.insert_one(chat_data)

    def get_chat(self, query: dict):
        return self.chats.find_one(query)

    def add_message(self, chat_id, message: dict):
        return self.chats.update_one({"_id": chat_id}, {"$push": {"messages": message}})

    # =========================
    # DESIGN COLLECTION
    # =========================
    def create_design(self, design_data: dict):
        return self.designs.insert_one(design_data)

    def get_design(self, query: dict):
        return self.designs.find_one(query)

    def update_design(self, query: dict, update: dict):
        return self.designs.update_one(query, update)

    def get_all_designs(self, query: dict):
        return list(self.designs.find(query))

    # =========================
    # GENERIC METHODS
    # =========================
    def delete_one(self, collection_name: str, query: dict):
        return self.db[collection_name].delete_one(query)

    def find_many(self, collection_name: str, query: dict):
        return list(self.db[collection_name].find(query))
