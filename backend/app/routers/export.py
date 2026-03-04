"""Export router -- PDF and calendar download endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.db.repository import TripRepository
from app.dependencies import require_user, get_trip_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trips", tags=["export"])


@router.get("/{trip_id}/export/pdf")
async def export_pdf(
    trip_id: str,
    repo: TripRepository = Depends(get_trip_repository),
    user: dict = Depends(require_user),
):
    """Download trip as PDF."""
    trip = await repo.get_trip(trip_id)
    if not trip:
        raise HTTPException(404, "Trip not found")
    owner = await repo.get_trip_user_id(trip_id)
    if owner is not None and owner != user["sub"]:
        raise HTTPException(404, "Trip not found")

    from app.services.export import generate_pdf

    try:
        pdf_bytes = generate_pdf(trip)
    except Exception as exc:
        logger.exception("PDF generation failed for trip %s", trip_id)
        raise HTTPException(500, "PDF generation failed")

    filename = f"trip-{trip.journey.theme.replace(' ', '-').lower()[:30]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{trip_id}/export/calendar")
async def export_calendar(
    trip_id: str,
    repo: TripRepository = Depends(get_trip_repository),
    user: dict = Depends(require_user),
):
    """Download trip as .ics calendar file."""
    trip = await repo.get_trip(trip_id)
    if not trip:
        raise HTTPException(404, "Trip not found")
    owner = await repo.get_trip_user_id(trip_id)
    if owner is not None and owner != user["sub"]:
        raise HTTPException(404, "Trip not found")

    from app.services.export import generate_ics

    try:
        ics_content = generate_ics(trip)
    except Exception as exc:
        logger.exception("Calendar generation failed for trip %s", trip_id)
        raise HTTPException(500, "Calendar generation failed")

    filename = f"trip-{trip.journey.theme.replace(' ', '-').lower()[:30]}.ics"
    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
