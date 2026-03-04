"""Export router -- PDF and calendar download endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.db.repository import TripRepository
from app.dependencies import get_trip_repository

router = APIRouter(prefix="/api/trips", tags=["export"])


@router.get("/{trip_id}/export/pdf")
async def export_pdf(
    trip_id: str,
    repo: TripRepository = Depends(get_trip_repository),
):
    """Download trip as PDF."""
    trip = await repo.get_trip(trip_id)
    if not trip:
        raise HTTPException(404, "Trip not found")

    from app.services.export import generate_pdf

    pdf_bytes = generate_pdf(trip)

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
):
    """Download trip as .ics calendar file."""
    trip = await repo.get_trip(trip_id)
    if not trip:
        raise HTTPException(404, "Trip not found")

    from app.services.export import generate_ics

    ics_content = generate_ics(trip)

    filename = f"trip-{trip.journey.theme.replace(' ', '-').lower()[:30]}.ics"
    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
