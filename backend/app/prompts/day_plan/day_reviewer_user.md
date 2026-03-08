Review this batch of day plans for **{destination}**:

**Assigned themes per day:**
{batch_themes}

**Top landmarks by visitor reviews (should be included where relevant):**
{landmarks_section}

**Day plans to review:**
{day_plans_detail}

**CALIBRATION — what scores mean:**
- 90+: Exceptional day plans a travel expert would praise. RARE.
- 80-89: Strong plans with minor tweaks possible.
- 70-79: Acceptable with noticeable gaps.
- 60-69: Below average — needs Day Fixer. THIS IS COMMON for first attempts.
- <60: Seriously flawed.

Score this batch on all 7 dimensions. Start each at 60 and adjust based on evidence.

Return JSON:
{{
  "score": 0-100,
  "is_acceptable": true/false,
  "dimension_scores": {{
    "theme_coverage": 0-100,
    "landmark_inclusion": 0-100,
    "activity_variety": 0-100,
    "duration_realism": 0-100,
    "geographic_coherence": 0-100,
    "pacing_flow": 0-100,
    "meal_placement": 0-100
  }},
  "summary": "Brief assessment of this batch",
  "issues": [
    {{
      "severity": "critical|major|minor",
      "day_number": 1,
      "category": "theme_coverage|landmark_inclusion|activity_variety|duration_realism|geographic_coherence|pacing_flow|meal_placement|activity_count",
      "description": "Specific problem with evidence",
      "suggestion": "Concrete fix — name specific places to swap"
    }}
  ]
}}
