Review this {total_days}-day journey plan:

**Travel Dates:** {travel_dates}
**Route:** {route}

**Request:**
- Origin: {origin}
- Region: {region}
- Interests: {interests}
- Pace: {pace}

**Cities:**
{cities_detail}

**Travel Legs:**
{travel_detail}

**Step-by-step evaluation process:**
1. Score each of the 5 dimensions (timing, routing, transport, balance, interest_alignment) from 0-100
2. Compute the weighted final score
3. List every issue found with severity, category, description, and suggestion
4. Determine is_acceptable (score >= 70 AND zero critical issues)

**EXAMPLE OUTPUT** (adapt to the actual plan):
```json
{{
  "dimension_scores": {{
    "time_feasibility": 85,
    "route_logic": 92,
    "transport_appropriateness": 78,
    "city_balance": 80,
    "interest_alignment": 90
  }},
  "is_acceptable": true,
  "score": 85,
  "issues": [
    {{
      "severity": "minor",
      "category": "transport",
      "description": "Bus from CityA to CityB takes 6h but a train does it in 3h",
      "suggestion": "Switch to the express train service for a faster, more comfortable journey"
    }}
  ],
  "summary": "Solid plan with efficient routing. Minor transport optimization possible on one leg."
}}
```

Return JSON:
```json
{{
  "dimension_scores": {{
    "time_feasibility": 0-100,
    "route_logic": 0-100,
    "transport_appropriateness": 0-100,
    "city_balance": 0-100,
    "interest_alignment": 0-100
  }},
  "is_acceptable": true/false,
  "score": 0-100,
  "issues": [
    {{
      "severity": "critical|major|minor",
      "category": "timing|routing|transport|balance|interest_alignment|safety|seasonal",
      "description": "Specific problem with evidence",
      "suggestion": "Concrete actionable fix"
    }}
  ],
  "summary": "Overall assessment in 1-2 sentences"
}}
```

Return ONLY the JSON object. No markdown fences, no text before or after.
