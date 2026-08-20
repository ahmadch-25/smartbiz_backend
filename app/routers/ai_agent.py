from fastapi import APIRouter

from app.schemas.api_response import ApiResponse

router = APIRouter(prefix="/agent", tags=["AI Agent"])


@router.get("/invoke")
def invoke_agent():
    return ApiResponse(status=True, message="success", result={})
