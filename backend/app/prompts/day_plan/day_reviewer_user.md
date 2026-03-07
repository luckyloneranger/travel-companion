Review this batch of day plans for **{destination}**:

**Assigned themes per day:**
{batch_themes}

**Top landmarks by visitor reviews (should be included where relevant):**
{landmarks_section}

**Day plans to review:**
{day_plans_detail}

Score this batch on the 6 dimensions and list specific issues.

Return JSON:
{{
  "score": 75,
  "is_acceptable": true,
  "dimension_scores": {{
    "theme_coverage": 80,
    "landmark_inclusion": 60,
    "activity_variety": 90,
    "duration_realism": 85,
    "pacing_flow": 75,
    "meal_placement": 70,
    "activity_count": 90
  }},
  "summary": "Brief assessment of this batch",
  "issues": [
    {{
      "severity": "major",
      "day_number": 3,
      "category": "theme_coverage",
      "description": "Day 3 assigned 'theme parks' but has no entertainment venues",
      "suggestion": "Replace park visit with Universal Studios or similar attraction"
    }}
  ]
}}
