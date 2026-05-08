"""Config schema validation."""

from fship.errors import ValidationError


def validate_flavor_exists(flavor: str, config: dict) -> bool:
    """Validate flavor exists in config.

    Args:
        flavor: Flavor name to check
        config: Config dict with flavors key

    Returns:
        True if valid

    Raises:
        ValidationError: If flavor missing
    """
    flavors = config.get("flavors", {})

    if flavor not in flavors:
        available = ", ".join(flavors.keys())
        raise ValidationError(
            f"Flavor {flavor!r} not found in config. "
            f"Available: {available}"
        )
    return True
