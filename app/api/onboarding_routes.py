from fastapi import APIRouter
from app.models.schemas import OnboardingStepSave, OnboardingFinalizeRequest
from app.services.tenant_service import save_onboarding_draft, get_onboarding_draft, finalize_society_onboarding

router = APIRouter(prefix="/onboarding", tags=["Society Digital Onboarding"])

@router.post("/step")
def api_save_step(data: OnboardingStepSave):
    return save_onboarding_draft(data)

@router.get("/draft/{contact}")
def api_get_draft(contact: str):
    return get_onboarding_draft(contact)

@router.post("/finalize")
def api_finalize(data: OnboardingFinalizeRequest):
    return finalize_society_onboarding(data)
