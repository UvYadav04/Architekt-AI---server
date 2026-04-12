import functools
import inspect
import logging
from fastapi.responses import JSONResponse
from fastapi import HTTPException


def safeExecution(fn):

    if inspect.iscoroutinefunction(fn):

        @functools.wraps(fn)
        async def async_wrapper(*args, **kwargs):
            try:
                return await fn(*args, **kwargs)

            except HTTPException as e:
                raise

            except Exception as e:
                logging.exception(f"Async error in {fn.__name__}")

                return JSONResponse(
                    status_code=500,
                    content={"success": False, "message": "Internal Server Error"},
                )

        return async_wrapper

    else:

        @functools.wraps(fn)
        def sync_wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)

            except HTTPException as e:
                # ✅ Same here
                raise

            except Exception as e:
                logging.exception(f"Sync error in {fn.__name__}")

                return JSONResponse(
                    status_code=500,
                    content={"success": False, "message": "Internal Server Error"},
                )

        return sync_wrapper
