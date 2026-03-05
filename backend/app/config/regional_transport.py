"""Regional transport guidance for journey planning.

Generates transport guidance for LLM prompts using the LLM's own
regional knowledge instead of hardcoded profiles.
"""


def get_transport_guidance(origin: str, region: str, user_prefs: list | None = None) -> str:
    """Build transport guidance for use in LLM prompts.

    Instead of maintaining hardcoded profiles for every region, this
    instructs the LLM to apply its own knowledge of regional transport
    norms when planning travel legs.

    Args:
        origin: Origin city or location name.
        region: Region or country name.
        user_prefs: Optional list of transport mode preferences.

    Returns:
        Formatted transport guidance string for use in LLM prompts.
    """
    if user_prefs:
        prefs = ", ".join(
            [t.value if hasattr(t, "value") else str(t) for t in user_prefs]
        )
        return (
            f"**TRANSPORT GUIDANCE:**\n"
            f"User's preferred modes: {prefs}\n\n"
            f"Use these preferred modes when available for travel between cities "
            f"in/around {region}. Fall back to the most practical regional "
            f"alternatives when the preferred mode isn't viable.\n\n"
            f"Apply your knowledge of what transport is actually popular, "
            f"reliable, and available for tourists in this region."
        )

    return (
        f"**TRANSPORT GUIDANCE for {region}:**\n"
        f"Use your knowledge of real transport options in this region.\n"
        f"Consider:\n"
        f"- What modes locals and tourists actually use between these cities\n"
        f"- Popular bus/train operators, airlines, or ferry services\n"
        f"- Realistic travel times and booking recommendations\n"
        f"- Whether overnight transport (sleeper trains/buses) makes sense\n"
        f"- Scenic vs. fast route trade-offs\n\n"
        f"IMPORTANT: Choose transport modes that are ACTUALLY AVAILABLE in "
        f"this specific region. Don't default to trains if the region lacks "
        f"rail infrastructure. Don't suggest driving if it's impractical."
    )
