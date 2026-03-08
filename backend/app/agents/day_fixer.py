import json
import logging

from app.models.internal import AIPlan
from app.prompts import day_plan_prompts
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)


class DayFixerAgent:
    """Fixes day plan quality issues identified by the reviewer."""

    def __init__(self, llm: LLMService):
        self.llm = llm

    async def fix_batch(
        self,
        current_plan: AIPlan,
        issues: list,
        candidates: list,
        destination: str,
        already_used: set[str] | None = None,
    ) -> AIPlan:
        """Fix quality issues in a batch of day plans."""
        system_prompt = day_plan_prompts.load("day_fixer_system")

        issues_detail = "\n".join(
            f"- [{i.severity}] Day {i.day_number} ({i.category}): {i.description} → {i.suggestion}"
            for i in issues
        )

        candidate_entries = [
            {"place_id": c.place_id, "name": c.name, "types": c.types[:3], "rating": c.rating}
            for c in candidates[:30]
        ]

        already_used_text = ""
        if already_used:
            already_used_text = ", ".join(sorted(already_used))

        user_prompt = day_plan_prompts.load("day_fixer_user").format(
            destination=destination,
            issues_detail=issues_detail,
            current_plan_json=json.dumps(current_plan.model_dump(), indent=2),
            candidates_json=json.dumps(candidate_entries, indent=2),
            already_used_ids=already_used_text,
        )

        logger.info("[DayFixer] Fixing %d issues for %s", len(issues), destination)

        return await self.llm.generate_structured(
            system_prompt, user_prompt, schema=AIPlan
        )
