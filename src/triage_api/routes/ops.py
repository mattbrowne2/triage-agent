from importlib.metadata import version

from fastapi import APIRouter

from triage_api.models import HealthResponse, VersionResponse


PACKAGE_NAME = "incident-triage"

router = APIRouter()


@router.get("/health")
def get_health() -> HealthResponse:
    return HealthResponse()


@router.get("/version")
def get_version() -> VersionResponse:
    return VersionResponse(version=version(PACKAGE_NAME))
