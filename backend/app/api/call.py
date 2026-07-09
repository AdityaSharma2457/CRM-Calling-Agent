from fastapi import APIRouter
from pydantic import BaseModel

from app.services.mcube_service import MCubeService

router = APIRouter()

mcube = MCubeService()


class CallRequest(BaseModel):
    phone: str


@router.post("/call")
def call_student(req: CallRequest):

    call_id = mcube.make_call(req.phone)

    return {
        "status": "Calling",
        "call_id": call_id
    }