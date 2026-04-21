"""Review pipeline — LLM scoring + iterative fix loop.

7-dimension quality review, fixer swaps from candidate pool,
tracks best plan across iterations (max 5, threshold 80).
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from app.prompts.loader import PromptLoader
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LLM response schemas
# ---------------------------------------------------------------------------


class LLMReviewResponse(BaseModel):
    """Schema for structured LLM reviewer output."""

    overall_score: int = Field(..., ge=0, le=100)
    is_acceptable: bool = Field(default=True)
    issues: list[str] = Field(default_factory=list)
    dimension_scores: dict[str, float] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ReviewResult:
    """Result from a single review pass."""

    score: int  # 0-100
    is_acceptable: bool
    issues: list[str]
    dimension_scores: dict[str, float]


@dataclass
class ReviewFixResult:
    """Result from the iterative review+fix loop."""

    best_plan: Any  # CurationOutput or similar
    best_score: int
    iterations_used: int
    final_issues: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class ReviewPipeline:
    """Iterative LLM review + fix pipeline for curated day plans."""

    def __init__(self, llm_service: LLMService):
        self.llm = llm_service
        self.prompts = PromptLoader("review")

    async def review(
        self,
        plan: Any,
        city_name: str,
        pace: str,
        day_count: int,
    ) -> ReviewResult:
        """Score a plan using the LLM reviewer.

        Args:
            plan: The curated plan (serialisable to JSON).
            city_name: City being reviewed.
            pace: Pace tier (relaxed / moderate / packed).
            day_count: Number of days in the plan.

        Returns:
            ReviewResult with score, acceptability, issues, and per-dimension scores.
        """
        system_prompt = self.prompts.load("reviewer_system")
        user_template = self.prompts.load("reviewer_user")

        plan_json = json.dumps(plan, default=str, indent=2) if not isinstance(plan, str) else plan

        user_prompt = user_template.format(
            city_name=city_name,
            day_count=day_count,
            pace=pace,
            plan_json=plan_json,
        )

        result = await self.llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=LLMReviewResponse,
            temperature=0.3,
        )

        return ReviewResult(
            score=result.overall_score,
            is_acceptable=result.is_acceptable,
            issues=result.issues,
            dimension_scores=result.dimension_scores,
        )

    async def fix(
        self,
        plan: Any,
        issues: list[str],
        candidates: list[dict],
        already_used: set[str],
        city_name: str,
    ) -> Any:
        """Fix reviewer issues using the LLM fixer.

        Args:
            plan: Current plan to fix.
            issues: List of issues from the reviewer.
            candidates: Full candidate pool.
            already_used: Set of google_place_ids already in the plan.
            city_name: City being fixed.

        Returns:
            Fixed plan in the same format as input.
        """
        system_prompt = self.prompts.load("fixer_system")
        user_template = self.prompts.load("fixer_user")

        unused = [c for c in candidates if c.get("google_place_id") not in already_used]

        plan_json = json.dumps(plan, default=str, indent=2) if not isinstance(plan, str) else plan

        user_prompt = user_template.format(
            city_name=city_name,
            issues_json=json.dumps(issues, indent=2),
            plan_json=plan_json,
            unused_candidates_json=json.dumps(unused, default=str, indent=2),
        )

        # Fixer returns the plan in the same structure — use unstructured generation
        # and parse as JSON, since the plan schema varies.
        raw = await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.4,
        )

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Fixer returned invalid JSON, keeping current plan")
            return plan

    def _collect_used_ids(self, plan: Any) -> set[str]:
        """Extract google_place_ids from a plan structure.

        Handles both dict-based and list-of-days structures.
        """
        used: set[str] = set()
        if isinstance(plan, dict):
            days = plan.get("days", [])
        elif isinstance(plan, list):
            days = plan
        else:
            return used

        for day in days:
            activities = day.get("activities", []) if isinstance(day, dict) else []
            for activity in activities:
                place_id = None
                if isinstance(activity, dict):
                    place_id = activity.get("google_place_id") or activity.get("place", {}).get("google_place_id")
                if place_id:
                    used.add(place_id)
        return used

    async def review_and_fix(
        self,
        plan: Any,
        city_name: str,
        pace: str,
        day_count: int,
        candidates: list[dict],
        max_iterations: int = 5,
        min_score: int = 80,
    ) -> ReviewFixResult:
        """Iterative review+fix loop. Returns best plan across iterations.

        Args:
            plan: Initial curated plan.
            city_name: City being reviewed.
            pace: Pace tier.
            day_count: Number of days.
            candidates: Full candidate pool for the fixer.
            max_iterations: Maximum review+fix cycles.
            min_score: Minimum acceptable score.

        Returns:
            ReviewFixResult with the best plan seen across all iterations.
        """
        best_plan = plan
        best_score = 0
        last_result: ReviewResult | None = None

        for i in range(max_iterations):
            result = await self.review(plan, city_name, pace, day_count)
            last_result = result

            logger.info(
                "Review iteration %d/%d for %s: score=%d, acceptable=%s, issues=%d",
                i + 1,
                max_iterations,
                city_name,
                result.score,
                result.is_acceptable,
                len(result.issues),
            )

            if result.score > best_score:
                best_score = result.score
                best_plan = plan

            if result.score >= min_score and result.is_acceptable:
                return ReviewFixResult(
                    best_plan=best_plan,
                    best_score=best_score,
                    iterations_used=i + 1,
                    final_issues=[],
                )

            # Fix if not the last iteration
            if i < max_iterations - 1:
                already_used = self._collect_used_ids(plan)
                plan = await self.fix(plan, result.issues, candidates, already_used, city_name)

        return ReviewFixResult(
            best_plan=best_plan,
            best_score=best_score,
            iterations_used=max_iterations,
            final_issues=last_result.issues if last_result else [],
        )
