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
