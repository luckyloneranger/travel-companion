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
    req = trip.request

    # CSS
    css = """
    <style>
        @page { margin: 1.5cm; }
        body {
            font-family: 'Helvetica', 'Arial', sans-serif;
            color: #1a1a2e;
            max-width: 800px;
            margin: 0 auto;
            padding: 0;
            line-height: 1.5;
        }

        /* ── Cover page ─────────────────────────────────────────── */
        .cover-page {
            page-break-after: always;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            min-height: 85vh;
            text-align: center;
            padding: 40px 20px;
        }
        .cover-title {
            font-size: 32px;
            font-weight: 700;
            color: #4338ca;
            margin-bottom: 16px;
            line-height: 1.2;
        }
        .cover-summary {
            font-size: 16px;
            color: #4b5563;
            max-width: 500px;
            line-height: 1.7;
            margin-bottom: 32px;
        }
        .cover-stats {
            display: flex;
            gap: 24px;
            justify-content: center;
            flex-wrap: wrap;
            margin-bottom: 24px;
        }
        .cover-stat {
            text-align: center;
        }
        .cover-stat-value {
            font-size: 28px;
            font-weight: 700;
            color: #4338ca;
        }
        .cover-stat-label {
            font-size: 12px;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .cover-route {
            font-size: 14px;
            color: #6b7280;
            margin-top: 8px;
            padding: 12px 24px;
            background: #eef2ff;
            border-radius: 24px;
        }
        .cover-travelers {
            font-size: 13px;
            color: #6b7280;
            margin-top: 12px;
        }
        .cover-score {
            display: inline-block;
            background: #059669;
            color: white;
            padding: 4px 16px;
            border-radius: 16px;
            font-size: 13px;
            font-weight: 600;
            margin-top: 16px;
        }
        .cover-divider {
            width: 80px;
            height: 3px;
            background: #4338ca;
            margin: 24px auto;
            border-radius: 2px;
        }
        .cover-date {
            font-size: 13px;
            color: #9ca3af;
            margin-top: 8px;
        }

        /* ── Content pages ──────────────────────────────────────── */
        h2 {
            color: #1e1b4b;
            font-size: 20px;
            border-bottom: 3px solid #c7d2fe;
            padding-bottom: 8px;
            margin-top: 32px;
            margin-bottom: 16px;
        }
        h3 {
            color: #4338ca;
            font-size: 16px;
            margin-top: 20px;
            margin-bottom: 10px;
        }

        /* City cards */
        .city {
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-left: 4px solid #4338ca;
            border-radius: 8px;
            padding: 14px 18px;
            margin: 10px 0;
        }
        .city-name {
            font-size: 17px;
            font-weight: 700;
            color: #1e1b4b;
        }
        .city-days {
            font-size: 12px;
            color: #6b7280;
            font-weight: 400;
        }
        .city-why {
            font-size: 13px;
            color: #4b5563;
            margin: 6px 0;
            font-style: italic;
        }
        .highlight {
            font-size: 13px;
            color: #374151;
            margin: 3px 0;
            padding-left: 12px;
        }
        .highlight::before {
            content: "\\2022";
            color: #4338ca;
            font-weight: bold;
            display: inline-block;
            width: 12px;
            margin-left: -12px;
        }
        .accom {
            font-size: 13px;
            color: #4b5563;
            margin-top: 8px;
            padding: 6px 10px;
            background: #eef2ff;
            border-radius: 4px;
        }

        /* Transport between cities */
        .transport-leg {
            text-align: center;
            font-size: 12px;
            color: #6b7280;
            margin: 4px 0;
            padding: 4px 0;
        }
        .transport-leg .arrow { color: #c7d2fe; font-size: 16px; }

        /* ── Day plans ──────────────────────────────────────────── */
        .day { margin: 18px 0; page-break-inside: avoid; }
        .city-section { page-break-before: auto; }
        .city-section:first-child { page-break-before: avoid; }
        .city-section-header {
            background: #1e1b4b;
            color: white;
            padding: 10px 16px;
            border-radius: 8px;
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 4px;
        }

        .day-header {
            background: linear-gradient(135deg, #4338ca, #6366f1);
            color: white;
            padding: 10px 16px;
            border-radius: 8px 8px 0 0;
            font-size: 15px;
            font-weight: 600;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .day-header-left { flex: 1; }

        /* Weather box in day header */
        .weather-box {
            background: rgba(255, 255, 255, 0.15);
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 400;
            text-align: right;
            line-height: 1.5;
            white-space: nowrap;
        }
        .weather-temp {
            font-weight: 600;
            font-size: 13px;
        }

        /* Weather detail strip below day header */
        .weather-detail-strip {
            background: #eef2ff;
            border: 1px solid #c7d2fe;
            border-top: none;
            padding: 6px 16px;
            font-size: 12px;
            color: #4338ca;
            display: flex;
            gap: 16px;
            flex-wrap: wrap;
        }

        .activity {
            border: 1px solid #e5e7eb;
            border-top: none;
            padding: 10px 16px;
            font-size: 13px;
            display: flex;
            gap: 12px;
            align-items: flex-start;
        }
        .activity:last-child {
            border-radius: 0 0 8px 8px;
        }
        .activity:hover { background: #f9fafb; }
        .time-block {
            min-width: 90px;
            color: #4338ca;
            font-weight: 700;
            font-size: 13px;
            line-height: 1.4;
        }
        .time-duration {
            font-size: 11px;
            color: #9ca3af;
            font-weight: 400;
        }
        .activity-content { flex: 1; }
        .place-name {
            font-weight: 600;
            color: #1e1b4b;
            font-size: 14px;
        }
        .place-category {
            font-size: 11px;
            color: #6b7280;
            background: #f3f4f6;
            padding: 1px 6px;
            border-radius: 4px;
            margin-left: 6px;
        }
        .activity-notes {
            color: #6b7280;
            font-size: 12px;
            margin-top: 3px;
        }
        .activity-cost {
            font-size: 11px;
            color: #059669;
            font-weight: 500;
            margin-top: 2px;
        }
        .warning {
            color: #d97706;
            font-size: 12px;
            margin-top: 3px;
            padding: 2px 6px;
            background: #fffbeb;
            border-radius: 4px;
        }

        .daily-cost {
            text-align: right;
            font-size: 12px;
            color: #059669;
            font-weight: 600;
            padding: 6px 16px;
            border: 1px solid #e5e7eb;
            border-top: none;
            border-radius: 0 0 8px 8px;
            background: #f0fdf4;
        }

        .footer {
            text-align: center;
            color: #9ca3af;
            font-size: 11px;
            margin-top: 40px;
            border-top: 2px solid #e5e7eb;
            padding-top: 12px;
        }
    </style>
    """

    # ── Cover page ─────────────────────────────────────────────────
    route_str = j.route or " > ".join(c.name for c in j.cities)
    travelers_str = ""
    if req:
        parts = [f"{req.travelers.adults} adult{'s' if req.travelers.adults != 1 else ''}"]
        if req.travelers.children:
            parts.append(f"{req.travelers.children} child{'ren' if req.travelers.children != 1 else ''}")
        if req.travelers.infants:
            parts.append(f"{req.travelers.infants} infant{'s' if req.travelers.infants != 1 else ''}")
        travelers_str = ", ".join(parts)

    score_html = ""
    if j.review_score is not None:
        score_html = f'<div class="cover-score">Quality Score: {j.review_score}</div>'

    start_date_str = ""
    if req and req.start_date:
        start_date_str = req.start_date.strftime("%B %d, %Y")

    distance_stat = ""
    if j.total_distance_km:
        distance_stat = f"""
        <div class="cover-stat">
            <div class="cover-stat-value">{round(j.total_distance_km)}</div>
            <div class="cover-stat-label">Kilometers</div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{j.theme}</title>{css}</head><body>

<div class="cover-page">
    <div class="cover-title">{j.theme}</div>
    <div class="cover-divider"></div>
    <div class="cover-summary">{j.summary}</div>
    <div class="cover-stats">
        <div class="cover-stat">
            <div class="cover-stat-value">{j.total_days}</div>
            <div class="cover-stat-label">Days</div>
        </div>
        <div class="cover-stat">
            <div class="cover-stat-value">{len(j.cities)}</div>
            <div class="cover-stat-label">{'City' if len(j.cities) == 1 else 'Cities'}</div>
        </div>
        {distance_stat}
    </div>
    <div class="cover-route">{route_str}</div>
    {"<div class='cover-travelers'>" + travelers_str + "</div>" if travelers_str else ""}
    {"<div class='cover-date'>Starting " + start_date_str + "</div>" if start_date_str else ""}
    {score_html}
</div>
"""

    # ── Cities overview ────────────────────────────────────────────
    html += "<h2>Cities Overview</h2>"
    for i, city in enumerate(j.cities):
        accom = ""
        if city.accommodation:
            rating = (
                f" ({city.accommodation.rating})" if city.accommodation.rating else ""
            )
            nightly = ""
            if city.accommodation.estimated_nightly_usd:
                nightly = f" ~ ${city.accommodation.estimated_nightly_usd:.0f}/night"
            accom = f'<div class="accom">Stay: {city.accommodation.name}{rating}{nightly}</div>'

        highlights = ""
        for h in city.highlights[:5]:
            desc = f" &mdash; {h.description}" if h.description else ""
            highlights += f'<div class="highlight">{h.name}{desc}</div>'

        why_html = f'<div class="city-why">{city.why_visit}</div>' if city.why_visit else ""

        html += f"""<div class="city">
    <div class="city-name">{i + 1}. {city.name}, {city.country} <span class="city-days">({city.days} {'day' if city.days == 1 else 'days'})</span></div>
    {why_html}
    {highlights}
    {accom}
</div>"""

        # Transport leg to next city
        if i < len(j.travel_legs):
            leg = j.travel_legs[i]
            mode_label = leg.mode.value if hasattr(leg.mode, 'value') else str(leg.mode)
            fare_str = f" | {leg.fare}" if leg.fare else ""
            html += f'<div class="transport-leg"><span class="arrow">&#x25BC;</span> {mode_label.title()} to {leg.to_city} ({leg.duration_hours:.1f}h){fare_str}</div>'

    # ── Day-by-Day Itinerary ───────────────────────────────────────
    if trip.day_plans:
        html += "<h2>Day-by-Day Itinerary</h2>"
        current_city = ""
        for dp in trip.day_plans:
            # City section header
            if dp.city_name != current_city:
                if current_city:
                    html += "</div>"  # close previous city-section
                html += f'<div class="city-section"><div class="city-section-header">{dp.city_name}</div>'
                current_city = dp.city_name

            # Weather in day header
            weather_box = ""
            weather_detail = ""
            if dp.weather:
                w = dp.weather
                weather_box = f"""<div class="weather-box">
                    <div class="weather-temp">{w.temperature_low_c:.0f}&deg; &ndash; {w.temperature_high_c:.0f}&deg;C</div>
                    <div>{w.condition}</div>
                </div>"""

                # Detailed weather strip
                detail_parts = []
                if w.precipitation_chance_percent > 0:
                    detail_parts.append(f"Rain: {w.precipitation_chance_percent}%")
                if w.wind_speed_kmh > 0:
                    detail_parts.append(f"Wind: {w.wind_speed_kmh:.0f} km/h")
                if w.humidity_percent > 0:
                    detail_parts.append(f"Humidity: {w.humidity_percent}%")
                if w.uv_index is not None:
                    detail_parts.append(f"UV: {w.uv_index}")
                if detail_parts:
                    weather_detail = f'<div class="weather-detail-strip">{" &nbsp;&bull;&nbsp; ".join(detail_parts)}</div>'

            html += f"""<div class="day">
<div class="day-header">
    <div class="day-header-left">Day {dp.day_number}: {dp.theme}</div>
    {weather_box}
</div>
{weather_detail}"""

            for a in dp.activities:
                if a.duration_minutes == 0:
                    continue  # Skip hotel departure/arrival markers

                rating_str = f" ({a.place.rating})" if a.place.rating else ""
                notes = (
                    f'<div class="activity-notes">{a.notes}</div>' if a.notes else ""
                )
                warning = (
                    f'<div class="warning">{a.weather_warning}</div>'
                    if a.weather_warning
                    else ""
                )
                cost_str = ""
                if a.estimated_cost_usd:
                    cost_str = f'<div class="activity-cost">${a.estimated_cost_usd:.0f}</div>'
                elif a.estimated_cost_local:
                    cost_str = f'<div class="activity-cost">{a.estimated_cost_local}</div>'

                dur_label = ""
                if a.duration_minutes >= 60:
                    h = a.duration_minutes // 60
                    m = a.duration_minutes % 60
                    dur_label = f"{h}h{m}m" if m else f"{h}h"
                else:
                    dur_label = f"{a.duration_minutes}m"

                html += f"""<div class="activity">
    <div class="time-block">{a.time_start} - {a.time_end}<br/><span class="time-duration">{dur_label}</span></div>
    <div class="activity-content">
        <span class="place-name">{a.place.name}</span>{rating_str}<span class="place-category">{a.place.category}</span>
        {notes}{cost_str}{warning}
    </div>
</div>"""

            # Daily cost summary
            if dp.daily_cost_usd:
                html += f'<div class="daily-cost">Day total: ${dp.daily_cost_usd:.0f}</div>'

            html += "</div>"  # close .day

        # Close last city-section
        if current_city:
            html += "</div>"

    # ── Footer ─────────────────────────────────────────────────────
    html += f'<div class="footer">Generated by Regular Everyday Traveller &mdash; {datetime.now().strftime("%B %d, %Y")}</div>'
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
