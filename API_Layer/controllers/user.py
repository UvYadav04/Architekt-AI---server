from fastapi import Request, HTTPException, status, Response
from fastapi.responses import JSONResponse
import jwt
import os

from ..safeExecution import safeExecution
from bson import ObjectId
from db.Mongo import MongoDB


@safeExecution
async def getUserInfo(request: Request):
    try:
        mongo = MongoDB()
        if mongo is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get info at the moment",
            )
        user_id = getattr(request.state, "user_id", None)

        if not user_id:
            return JSONResponse({"success": True, "userInfo": None})

        userInfo = mongo.get_user({"_id": ObjectId(user_id)})

        if userInfo is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
            )
        userInfo["_id"] = str(userInfo["_id"])
        return JSONResponse({"success": True, "userInfo": userInfo})
    except Exception as e:
        print(e)


@safeExecution
async def login(request: Request, response: Response):
    mongo = MongoDB()
    if mongo is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to login at the moment",
        )

    body = await request.json()
    email = body["email"]
    name = body["name"]
    userDetails = mongo.get_user({"email": email})

    if userDetails is None:
        newUser = mongo.create_user(
            {
                "name": name,
                "email": email,
                "designsCreated": 0,
            }
        )
        user_id = newUser.inserted_id
    else:
        user_id = userDetails["_id"]

    jwt_token = jwt.encode(
        {"user_id": str(user_id)},  # convert ObjectId to string
        os.environ.get("JWT_SECRET"),
        algorithm="HS256",
    )

    response = JSONResponse({"success": True, "message": "Logged in Successfully"})

    response.set_cookie(
        key="architektAi",
        value=jwt_token,
        expires=60 * 60 * 24 * 7,
        secure=True,
        samesite="none",
        httponly=True,
        path="/",
    )

    return response


@safeExecution
async def logout(request: Request, response: Response):
    response = JSONResponse({"success": True, "message": "Logged in Successfully"})
    response.delete_cookie(
        key="architektAi",
        secure=True,
        samesite="none",
        httponly=True,
        path="/",
    )
    return response


@safeExecution
async def design_info(id: str, request: Request):
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please login to access design info.",
        )
    try:
        objectified_design_id = ObjectId(id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid design id format.",
        )
    try:
        objectified_user_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user id format.",
        )
    mongo = MongoDB()
    design = mongo.get_design(
        {"_id": objectified_design_id, "user_id": objectified_user_id}
    )
    if design is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found.",
        )

    if str(design["user_id"]) != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bad Request",
        )
    design["_id"] = str(design["_id"])
    design["user_id"] = str(design["user_id"])
    return {"success": True, "data": design}


@safeExecution
async def designs(request: Request):
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please login to access designs.",
        )
    try:
        objectified_user_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user id format.",
        )
    mongo = MongoDB()
    designs = mongo.get_all_designs({"user_id": objectified_user_id})
    for d in designs:
        d["_id"] = str(d["_id"])
        d["user_id"] = str(d["user_id"])
    return {"success": True, "data": designs}
