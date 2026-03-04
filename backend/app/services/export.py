"""Export service for generating PDF and calendar files from trips."""

import logging
from datetime import datetime

from app.models.trip import TripResponse

logger = logging.getLogger(__name__)


def generate_pdf(trip: TripResponse) -> bytes:
    """Generate a PDF from a trip using weasyprint.

    Renders an HTML template with trip details, then converts to PDF.
    """
    from weasyprint import HTML

    html_content = _build_trip_html(trip)
    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes


def _build_trip_html(trip: TripResponse) -> str:
    """Build an HTML document for the trip."""
    j = trip.journey

    # CSS
    css = """
    <style>
        body { font-family: 'Helvetica', 'Arial', sans-serif; color: #212529; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #4c6ef5; font-size: 24px; margin-bottom: 4px; }
        h2 { color: #495057; font-size: 18px; border-bottom: 2px solid #dbe4ff; padding-bottom: 6px; margin-top: 24px; }
        h3 { color: #4c6ef5; font-size: 15px; margin-top: 16px; margin-bottom: 8px; }
        .summary { color: #495057; font-size: 14px; line-height: 1.6; }
        .stats { display: flex; gap: 16px; font-size: 13px; color: #868e96; margin: 8px 0; }
        .city { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 12px 16px; margin: 8px 0; }
        .city-name { font-size: 16px; font-weight: 600; }
        .highlight { font-size: 13px; color: #495057; margin: 2px 0; }
        .day { margin: 16px 0; page-break-inside: avoid; }
        .city-section { page-break-before: auto; }
        .city-section:first-child { page-break-before: avoid; }
        .day-header { background: #4c6ef5; color: white; padding: 8px 12px; border-radius: 6px 6px 0 0; font-size: 14px; font-weight: 600; }
        .weather { font-size: 12px; color: #dbe4ff; margin-left: 8px; }
        .activity { border: 1px solid #dee2e6; border-top: none; padding: 8px 12px; font-size: 13px; }
        .activity:last-child { border-radius: 0 0 6px 6px; }
        .time { color: #4c6ef5; font-weight: 600; min-width: 100px; display: inline-block; }
        .place-name { font-weight: 600; }
        .notes { color: #868e96; font-size: 12px; }
        .transport { background: #f1f3f5; padding: 6px 12px; font-size: 12px; color: #495057; border: 1px solid #dee2e6; border-top: none; }
        .footer { text-align: center; color: #adb5bd; font-size: 11px; margin-top: 32px; border-top: 1px solid #dee2e6; padding-top: 8px; }
        .warning { color: #e67700; font-size: 12px; }
        .score { float: right; background: #40c057; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
    </style>
    """

    # Header
    score_badge = (
        f'<span class="score">Score: {j.review_score}</span>' if j.review_score else ""
    )
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{j.theme}</title>{css}</head><body>
<h1>{j.theme} {score_badge}</h1>
<p class="summary">{j.summary}</p>
<div class="stats">
    <span>{j.total_days} days</span>
    <span>{len(j.cities)} {'city' if len(j.cities) == 1 else 'cities'}</span>
    {'<span>' + str(round(j.total_distance_km)) + ' km</span>' if j.total_distance_km else ''}
    {'<span>Route: ' + j.route + '</span>' if j.route else ''}
</div>
"""

    # Cities
    html += "<h2>Cities</h2>"
    for i, city in enumerate(j.cities):
        accom = ""
        if city.accommodation:
            rating = (
                f" ({city.accommodation.rating})" if city.accommodation.rating else ""
            )
            accom = f'<div class="highlight">Stay: {city.accommodation.name}{rating}</div>'

        highlights = ""
        for h in city.highlights[:4]:
            highlights += f'<div class="highlight">- {h.name}{" -- " + h.description if h.description else ""}</div>'

        html += f"""<div class="city">
    <div class="city-name">{i + 1}. {city.name}, {city.country} ({city.days} {'day' if city.days == 1 else 'days'})</div>
    {'<div class="highlight">' + city.why_visit + '</div>' if city.why_visit else ''}
    {highlights}
    {accom}
</div>"""

    # Day Plans
    if trip.day_plans:
        html += "<h2>Day-by-Day Itinerary</h2>"
        current_city = ""
        for dp in trip.day_plans:
            # Add city section break for grouping
            if dp.city_name != current_city:
                if current_city:
                    html += "</div>"  # close previous city-section
                html += f'<div class="city-section"><h3>{dp.city_name}</h3>'
                current_city = dp.city_name

            weather_str = ""
            if dp.weather:
                w = dp.weather
                weather_str = f'<span class="weather">{w.temperature_low_c:.0f}-{w.temperature_high_c:.0f} C, {w.condition}</span>'

            html += f'<div class="day"><div class="day-header">Day {dp.day_number}: {dp.theme} {weather_str}</div>'

            for a in dp.activities:
                if a.duration_minutes == 0:
                    continue  # Skip hotel departure/arrival markers

                rating = f" ({a.place.rating})" if a.place.rating else ""
                notes = f'<div class="notes">{a.notes}</div>' if a.notes else ""
                warning = (
                    f'<div class="warning">Warning: {a.weather_warning}</div>'
                    if a.weather_warning
                    else ""
                )

                html += f"""<div class="activity">
    <span class="time">{a.time_start} - {a.time_end}</span>
    <span class="place-name">{a.place.name}</span>{rating}
    <span class="notes"> [{a.place.category}]</span>
    {notes}{warning}
</div>"""

            html += "</div>"

        # Close last city-section
        if current_city:
            html += "</div>"

    # Footer
    html += f'<div class="footer">Generated by Regular Everyday Traveller -- {datetime.now().strftime("%B %d, %Y")}</div>'
    html += "</body></html>"

    return html


def generate_ics(trip: TripResponse) -> str:
    """Generate an .ics calendar file from a trip."""
    from datetime import date as date_type

    from icalendar import Calendar, Event

    cal = Calendar()
    cal.add("prodid", "-//Regular Everyday Traveller//EN")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", trip.journey.theme)

    if trip.day_plans:
        for dp in trip.day_plans:
            try:
                day_date = date_type.fromisoformat(dp.date)
            except ValueError:
                continue

            for activity in dp.activities:
                if activity.duration_minutes == 0:
                    continue  # Skip hotel markers

                event = Event()
                # Clean activity name for ICS (strip HTML entities, control chars)
                clean_name = activity.place.name.replace("\n", " ").replace("\r", "").strip()
                event.add("summary", clean_name)

                # Parse times
                try:
                    start_h, start_m = map(int, activity.time_start.split(":"))
                    end_h, end_m = map(int, activity.time_end.split(":"))
                    start_dt = datetime(
                        day_date.year, day_date.month, day_date.day, start_h, start_m
                    )
                    end_dt = datetime(
                        day_date.year, day_date.month, day_date.day, end_h, end_m
                    )
                    event.add("dtstart", start_dt)
                    event.add("dtend", end_dt)
                except (ValueError, TypeError):
                    continue

                if activity.place.address:
                    event.add("location", activity.place.address)

                # Build description
                desc_parts = []
                if activity.notes:
                    desc_parts.append(activity.notes)
                if activity.place.category:
                    desc_parts.append(f"Category: {activity.place.category}")
                if activity.place.rating:
                    desc_parts.append(f"Rating: {activity.place.rating}")
                if activity.weather_warning:
                    desc_parts.append(f"Weather: {activity.weather_warning}")
                if desc_parts:
                    event.add("description", "\n".join(desc_parts))

                event.add("categories", [dp.city_name])
                cal.add_component(event)

    return cal.to_ical().decode("utf-8")
