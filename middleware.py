from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
import json
import jwt
from dotenv import load_dotenv

load_dotenv()


def decode_architekt_cookie(cookie_value: str):
    try:
        from os import environ

        secret = environ.get("JWT_SECRET")
        return jwt.decode(cookie_value, secret, algorithms=["HS256"])
    except:
        return None


class RedisSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        store = request.app.state.redis_store
        arch_cookie = request.cookies.get("architektAi")
        print("arch cookie : ", arch_cookie)

        if arch_cookie:
            decoded = decode_architekt_cookie(arch_cookie)
            print(decoded)
            request.state.user_id = decoded.get("user_id") if decoded else None
        else:
            request.state.user_id = None
        session_id = request.cookies.get("session_id")

        if session_id:
            session = await store.get_session(session_id)
        else:
            session = None

        if not session:
            session_id = await store.create_session(request.state.user_id)
            is_new_session = True
        else:
            is_new_session = False

        await store.track_request(session_id)

        if await store.is_rate_limited(session_id, limit=60):
            return JSONResponse(
                {"error": "Rate limit per minute exceeded"}, status_code=429
            )

        request_count = await store.increment_requests(session_id)

        request.state.session_id = session_id
        request.state.request_count = request_count

        response = await call_next(request)

        if is_new_session:
            response.set_cookie(
                key="session_id",
                value=session_id,
                httponly=True,
                samesite="none",
                secure=True,
            )

        return response


LIMITS = {
    "design": 5,  # heavy → low concurrency
    "chat": 50,  # light → high concurrency
    "auth": 100,
}

MAX_QUEUE = {"design": 50, "chat": 200}


class LoadAwareMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        store = request.app.state.redis_store

        # -------------------------------
        # CLASSIFY ROUTE
        # -------------------------------
        path = request.url.path

        if path.startswith("/design"):
            route_type = "design"
            queue_name = "queue:design"
        elif path.startswith("/chat"):
            route_type = "chat"
            queue_name = "queue:chat"
        else:
            route_type = "auth"
            queue_name = "queue:auth"

        request.state.route_type = route_type

        # -------------------------------
        # CHECK ACTIVE LOAD
        # -------------------------------
        queue_length = await store.get_queue_length(queue_name)
        current_load = await store.get_active(route_type)
        limit = LIMITS[route_type]

        if queue_length > 0 or current_load >= limit:
            if queue_length > MAX_QUEUE[route_type]:
                return JSONResponse({"error": "Server overloaded"}, status_code=503)
            await store.enqueue(queue_name, request)
            return JSONResponse(
                {"status": "queued", "queue": queue_name}, status_code=202
            )
        # -------------------------------
        # ACCEPT REQUEST
        # -------------------------------
        await store.increment_active(route_type)

        try:
            response = await call_next(request)
        finally:
            await store.decrement_active(route_type)

        return response
