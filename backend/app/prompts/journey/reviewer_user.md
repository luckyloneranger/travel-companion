Review this {total_days}-day journey plan:

**Travel Dates:** {travel_dates}
**Route:** {route}

**Request:**
- Origin: {origin}
- Region: {region}
- Interests: {interests}
- Pace: {pace}
- Travelers: {travelers_description}
- Budget: {budget_tier}
- Must include: {must_include}
- Avoid: {avoid}
- Transport preference: {travel_mode}

**Cities:**
{cities_detail}

**Travel Legs:**
{travel_detail}

{landmarks_context}

**Step-by-step evaluation process:**
1. Start each dimension at 60 (average). Award points for quality, deduct for issues.
2. Score each of the 5 dimensions from 0-100
3. Compute the weighted final score
4. Apply deductions from theme/landscape validation to interest_alignment
5. List every issue with severity, category, description, and suggestion
6. Determine is_acceptable (score >= 70 AND zero critical issues)

**CALIBRATION — what scores mean:**
- 90+: Exceptional plan that a travel expert would praise. RARE.
- 80-89: Strong plan with minor improvements possible. GOOD but not perfect.
- 70-79: Acceptable plan with noticeable gaps (missing attractions, suboptimal routing).
- 60-69: Below average — needs Planner fixes before presenting to user.
- <60: Seriously flawed — major rework needed.

**EXAMPLE: A plan scoring 68 (needs fixing):**
```json
{{
  "dimension_scores": {{
    "time_feasibility": 72,
    "route_logic": 65,
    "transport_appropriateness": 70,
    "city_balance": 60,
    "interest_alignment": 68
  }},
  "is_acceptable": false,
  "score": 68,
  "issues": [
    {{
      "severity": "major",
      "category": "balance",
      "description": "Nara given 2 days with its own hotel, but is universally visited as a day trip from Kyoto/Osaka",
      "suggestion": "Make Nara a full_day excursion from Kyoto, reallocate its 2 days to Tokyo or Osaka"
    }},
    {{
      "severity": "major",
      "category": "interest_alignment",
      "description": "User requested 'food' interest but no city has a food-focused experience theme",
      "suggestion": "Add street food or culinary experience themes to at least 2 cities"
    }},
    {{
      "severity": "minor",
      "category": "routing",
      "description": "Route backtracks: Tokyo → Kyoto → Tokyo → Osaka. Osaka is between Tokyo and Kyoto",
      "suggestion": "Reorder to Tokyo → Osaka → Kyoto to eliminate backtracking"
    }}
  ],
  "summary": "Plan has structural issues: Nara should be a day trip, food interest is unaddressed, and route backtracks. Needs Planner fixes."
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
