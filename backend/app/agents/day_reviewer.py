import logging

from app.models.day_review import DayReviewResult
from app.prompts import day_plan_prompts
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)


class DayReviewerAgent:
    """Reviews a batch of day plans for quality using LLM."""

    def __init__(self, llm: LLMService):
        self.llm = llm

    async def review_batch(
        self,
        day_plans_detail: str,
        batch_themes: str,
        landmarks_section: str,
        destination: str,
    ) -> DayReviewResult:
        """Review a batch of day plans and return quality score + issues."""
        system_prompt = day_plan_prompts.load("day_reviewer_system")
        user_prompt = day_plan_prompts.load("day_reviewer_user").format(
            destination=destination,
            batch_themes=batch_themes,
            landmarks_section=landmarks_section,
            day_plans_detail=day_plans_detail,
        )

        logger.info("[DayReviewer] Reviewing batch for %s", destination)

        from app.config.planning import should_use_search_grounding
        if should_use_search_grounding("full"):
            result, _citations = await self.llm.generate_structured_with_search(
                system_prompt, user_prompt, schema=DayReviewResult
            )
        else:
            result = await self.llm.generate_structured(
                system_prompt, user_prompt, schema=DayReviewResult
            )

        logger.info(
            "[DayReviewer] Batch score: %d (acceptable=%s, %d issues)",
            result.score, result.is_acceptable, len(result.issues),
        )
        return result
