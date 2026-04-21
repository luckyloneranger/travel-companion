import secrets
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from app.dependencies import get_journey_repo, get_share_repo, require_user
from app.db.repository import JourneyRepository, JourneyShareRepository

router = APIRouter(tags=["sharing"])


@router.post("/api/journeys/{journey_id}/share")
async def share_journey(
    journey_id: UUID,
    user: dict = Depends(require_user),
    journey_repo: JourneyRepository = Depends(get_journey_repo),
    share_repo: JourneyShareRepository = Depends(get_share_repo),
):
    journey = await journey_repo.get(journey_id)
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")
    token = secrets.token_urlsafe(12)
    share = await share_repo.create(journey_id=journey_id, token=token)
    return {"token": share.token, "url": f"/shared/{share.token}"}


@router.delete("/api/journeys/{journey_id}/share")
async def revoke_share(
    journey_id: UUID,
    user: dict = Depends(require_user),
    share_repo: JourneyShareRepository = Depends(get_share_repo),
):
    deleted = await share_repo.delete_by_journey(journey_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Share not found")
    return {"revoked": True}


@router.get("/api/shared/{token}")
async def get_shared_journey(
    token: str,
    share_repo: JourneyShareRepository = Depends(get_share_repo),
    journey_repo: JourneyRepository = Depends(get_journey_repo),
):
    share = await share_repo.get_by_token(token)
    if not share:
        raise HTTPException(status_code=404, detail="Shared journey not found")
    journey = await journey_repo.get(share.journey_id)
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")
    return {
        "id": str(journey.id),
        "destination": journey.destination,
        "start_date": journey.start_date.isoformat() if journey.start_date else None,
        "total_days": journey.total_days,
        "pace": journey.pace,
        "budget": journey.budget,
        "city_sequence": journey.city_sequence,
        "transport_legs": journey.transport_legs,
        "cost_breakdown": journey.cost_breakdown,
    }
