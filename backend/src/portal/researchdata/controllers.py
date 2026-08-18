from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from portal.auth.dependencies import get_current_user, require_admin
from portal.auth.models import UserAccount
from portal.researchdata.services import (
    EditForbidden,
    ErasedError,
    RegistrationError,
    ResearchDataService,
)


class ProfessorRegistration(BaseModel):
    name: str = Field(min_length=1)
    username: str = Field(min_length=1)
    password: str = Field(min_length=8)
    emails: list[str] | None = None
    resume: str | None = None


class ProfessorEdit(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    emails: list[str] | None = None
    resume: str | None = None


def create_researchdata_router(service: ResearchDataService) -> APIRouter:
    router = APIRouter(tags=["professors"])

    @router.get("/professors")
    def list_professors(
        q: str | None = Query(default=None, max_length=100),
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> dict:
        items, total = service.search_professors(q, page, page_size)
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @router.get("/professors/{professor_id}")
    def get_professor(
        professor_id: int,
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    ) -> dict:
        try:
            return service.get_profile(
                professor_id, article_page=page, article_page_size=page_size
            )
        except KeyError:
            raise HTTPException(status_code=404, detail="Professor not found") from None

    @router.post("/admin/professors", status_code=201)
    def register_professor(
        body: ProfessorRegistration,
        _: UserAccount = Depends(require_admin),
    ) -> dict:
        try:
            return service.register_professor(
                name=body.name,
                username=body.username,
                password=body.password,
                emails=body.emails,
                resume=body.resume,
            )
        except RegistrationError:
            raise HTTPException(
                status_code=400, detail="Username already exists"
            ) from None

    @router.patch("/professors/{professor_id}")
    def edit_professor(
        professor_id: int,
        body: ProfessorEdit,
        actor: UserAccount = Depends(get_current_user),
    ) -> dict:
        try:
            return service.update_professor(
                researcher_id=professor_id,
                actor=actor,
                name=body.name,
                emails=body.emails,
                resume=body.resume,
            )
        except EditForbidden:
            raise HTTPException(
                status_code=403,
                detail="You may only edit your own professor data",
            ) from None
        except ErasedError:
            raise HTTPException(
                status_code=400, detail="Professor data has been erased"
            ) from None
        except KeyError:
            raise HTTPException(status_code=404, detail="Professor not found") from None

    @router.get("/professors/{professor_id}/personal-data")
    def get_personal_data(
        professor_id: int,
        actor: UserAccount = Depends(get_current_user),
    ) -> dict:
        try:
            return service.personal_data(professor_id, actor)
        except EditForbidden:
            raise HTTPException(
                status_code=403, detail="Not allowed to access this personal data"
            ) from None
        except KeyError:
            raise HTTPException(status_code=404, detail="Professor not found") from None

    @router.delete("/professors/{professor_id}/personal-data")
    def erase_personal_data(
        professor_id: int,
        actor: UserAccount = Depends(get_current_user),
    ) -> dict:
        try:
            return service.erase_personal_data(professor_id, actor)
        except EditForbidden:
            raise HTTPException(
                status_code=403, detail="Not allowed to erase this personal data"
            ) from None
        except KeyError:
            raise HTTPException(status_code=404, detail="Professor not found") from None

    return router
