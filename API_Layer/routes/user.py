from fastapi import APIRouter, Request, Response
from API_Layer.controllers.user import getUserInfo, login, logout, designs, design_info
from API_Layer.safeExecution import safeExecution

router = APIRouter()


@router.get("/user-info")
@safeExecution
async def get_user_info(request: Request):
    return await getUserInfo(request)


@router.post("/login")
@safeExecution
async def login_user(request: Request, response: Response):
    return await login(request, response)


@router.post("/logout")
@safeExecution
async def login_user(request: Request, response: Response):
    return await logout(request, response)


@router.get("/designs")
@safeExecution
async def get_user_desings(request: Request):
    return await designs(request)


@router.get("/design/{id}")
@safeExecution
async def get_design_info(id: str, request: Request):
    return await design_info(id, request)
