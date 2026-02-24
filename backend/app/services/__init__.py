"""Services for external API integrations and business logic.

Organized into:
- external/: API client wrappers (Azure OpenAI, Google APIs)
- internal/: Algorithmic services (optimization, scheduling)
"""

# External API services
from app.services.external import (
    AzureOpenAIService,
    GooglePlacesService,
    GoogleRoutesService,
)

# Internal algorithmic services
from app.services.internal import (
    RouteOptimizer,
    ScheduleBuilder,
)

__all__ = [
    # External
    "AzureOpenAIService",
    "GooglePlacesService",
    "GoogleRoutesService",
    # Internal
    "RouteOptimizer",
    "ScheduleBuilder",
]
