"""Tips generator module.

Generates personalized activity tips for travel itineraries.

Usage:
    from app.generators.tips import TipsGenerator
    
    generator = TipsGenerator()
    tips = await generator.generate(schedule)
"""

from app.generators.tips.generator import TipsGenerator

__all__ = ["TipsGenerator"]
