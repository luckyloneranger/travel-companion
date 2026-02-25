"""Regional transport configuration for journey planning.

Relies on LLM's built-in knowledge of regional transport options.
Only provides minimal guidance to steer the AI toward appropriate choices.
"""


def get_transport_guidance(origin: str, region: str, user_prefs: list | None = None) -> str:
    """Build transport guidance based on user preferences.
    
    The LLM has extensive knowledge about regional transport - what's popular,
    specific operators, booking tips, etc. We just need to guide it.
    
    Args:
        origin: Origin city/location
        region: Region or country name
        user_prefs: Optional list of TransportMode preferences
        
    Returns:
        Formatted transport guidance string for the prompt
    """
    if user_prefs:
        prefs = ", ".join([t.value if hasattr(t, 'value') else str(t) for t in user_prefs])
        return f"""**TRANSPORT PREFERENCES:** {prefs}

Use these preferred modes when practical, but suggest better regional alternatives if they make more sense for {region}."""
    
    return f"""**TRANSPORT:** Use your knowledge of what's ACTUALLY popular and available in {region}.

Consider:
- What locals and travelers actually use (not just what exists)
- Regional transport culture (trains in Japan/Europe, buses in SE Asia/Latin America, ferries for islands, etc.)
- Specific operators, routes, and booking tips you know
- Realistic durations including boarding/transfers

Available modes: flight, train, bus, drive, ferry
Choose the most appropriate for each leg based on distance, terrain, and regional norms."""
