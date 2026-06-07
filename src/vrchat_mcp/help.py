"""
VRChat MCP Help System

This module provides a comprehensive help system for the VRChat MCP,
offering different levels of technical detail and information.
"""

import textwrap
from enum import Enum, auto
from typing import Any


class HelpLevel(Enum):
    """Different levels of technical detail for help content."""

    BEGINNER = auto()  # Non-technical, simple explanations
    INTERMEDIATE = auto()  # Some technical details
    ADVANCED = auto()  # Full technical details
    DEVELOPER = auto()  # Internal implementation details


class HelpCategory(Enum):
    """Categories for organizing help content."""

    GETTING_STARTED = "Getting Started"
    AVATAR_CONTROL = "Avatar Control"
    PARAMETERS = "Parameters"
    ANIMATIONS = "Animations"
    EXPRESSIONS = "Expressions"
    NPC = "NPC Conversations"
    TROUBLESHOOTING = "Troubleshooting"
    DEVELOPER = "Developer Reference"
    SECURITY = "Security"
    PERFORMANCE = "Performance"


class HelpEntry:
    """A single help entry with content at different technical levels."""

    def __init__(
        self,
        name: str,
        description: str,
        category: HelpCategory,
        examples: list[dict[str, Any]] | None = None,
        notes: dict[HelpLevel, str] | None = None,
        related: list[str] | None = None,
        command: str | None = None,
        params: dict[str, str] | None = None,
        returns: str | None = None,
        see_also: list[str] | None = None,
    ):
        self.name = name
        self.description = description
        self.category = category
        self.examples = examples or []
        self.notes = notes or {}
        self.related = related or []
        self.command = command
        self.params = params or {}
        self.returns = returns
        self.see_also = see_also or []

    def format(self, level: HelpLevel = HelpLevel.INTERMEDIATE) -> str:
        """Format the help entry for the specified technical level."""
        lines = []

        # Header
        lines.append(f"\n{'=' * 80}")
        lines.append(f"{self.name.upper()}")
        lines.append(f"Category: {self.category.value}")
        lines.append(f"{'=' * 80}")

        # Description
        lines.append("\nDESCRIPTION:")
        lines.append(textwrap.fill(self.description, width=78))

        # Command syntax if available
        if self.command:
            lines.append("\nUSAGE:")
            lines.append(f"  {self.command}")

            if self.params:
                lines.append("\nPARAMETERS:")
                max_param_len = max(len(p) for p in self.params)
                for param, desc in self.params.items():
                    lines.append(f"  {param.ljust(max_param_len)}  {desc}")

        # Examples
        if self.examples:
            lines.append("\nEXAMPLES:")
            for i, example in enumerate(self.examples, 1):
                lines.append(f"\n  Example {i}:")
                if "description" in example:
                    lines.append(f"  {example['description']}")
                if "code" in example:
                    lines.append(f"  {example['code']}")
                if "output" in example:
                    lines.append("  Expected output:")
                    lines.append(f"    {example['output']}")

        # Notes for the current level
        if level in self.notes:
            lines.append("\nNOTES:")
            lines.append(textwrap.fill(self.notes[level], width=78))

        # Related topics
        if self.related:
            lines.append("\nRELATED TOPICS:")
            lines.append("  " + ", ".join(self.related))

        # See also
        if self.see_also:
            lines.append("\nSEE ALSO:")
            lines.append("  " + ", ".join(self.see_also))

        return "\n".join(lines)


class HelpSystem:
    """Comprehensive help system for VRChat MCP."""

    def __init__(self):
        self.entries: dict[str, HelpEntry] = {}
        self._load_help_entries()

    def _load_help_entries(self):
        """Load all help entries into the system."""
        # Avatar Control
        self.add_entry(
            HelpEntry(
                name="Loading Avatars",
                description="Change the current avatar in VRChat.",
                category=HelpCategory.AVATAR_CONTROL,
                command="load_avatar(avatar_id: str, parameters: Optional[Dict[str, Any]] = None)",
                params={
                    "avatar_id": "The ID of the avatar to load",
                    "parameters": "Optional parameters to set after loading",
                },
                examples=[
                    {
                        "description": "Load an avatar by ID",
                        "code": "await mcp.load_avatar(avatar_id='avtr_12345678-90ab-cdef-1234-567890abcdef')",
                    },
                    {
                        "description": "Load an avatar and set initial parameters",
                        "code": """await mcp.load_avatar(
    avatar_id='avtr_12345678-90ab-cdef-1234-567890abcdef',
    parameters={
        'MyParameter': 1.0,
        'MyBoolParameter': True
    }
)""",
                    },
                ],
                notes={
                    HelpLevel.BEGINNER: "You can find avatar IDs in the VRChat website URL when viewing an avatar.",
                    HelpLevel.ADVANCED: (
                        "The avatar change is not guaranteed to be immediate. "
                        "Listen for the 'avatar_changed' event for confirmation."
                    ),
                    HelpLevel.DEVELOPER: "Sends an OSC message to /avatar/change with the avatar ID.",
                },
                related=["Setting Parameters", "Avatar Events"],
                see_also=["https://docs.vrchat.com/docs/avatars"],
            )
        )

        # Parameter Interpolation
        self.add_entry(
            HelpEntry(
                name="Parameter Interpolation",
                description="Smoothly transition between parameter values over time.",
                category=HelpCategory.PARAMETERS,
                command="set_parameter(avatar_id, name, value, interpolate=True, duration=1.0, easing='linear')",
                params={
                    "avatar_id": "The ID of the avatar to update",
                    "name": "Name of the parameter to interpolate",
                    "value": "Target value to interpolate to",
                    "interpolate": "Whether to interpolate (True) or set immediately (False)",
                    "duration": "Duration of the interpolation in seconds",
                    "easing": "Easing function to use (e.g., 'linear', 'ease_in_out_quad')",
                },
                examples=[
                    {
                        "description": "Smoothly transition a parameter over 2 seconds",
                        "code": """await mcp.set_parameter(
    avatar_id='avtr_12345678',
    name='Viseme',
    value=1.0,
    interpolate=True,
    duration=2.0,
    easing='ease_in_out_cubic'
)""",
                    },
                    {
                        "description": "Interpolate multiple parameters simultaneously",
                        "code": """await mcp.set_parameters(
    avatar_id='avtr_12345678',
    parameters={
        'Viseme': 1.0,
        'GestureLeft': 2.0
    },
    interpolate=True,
    duration=1.5,
    easing='ease_out_sine'
)""",
                    },
                ],
                notes={
                    HelpLevel.BEGINNER: "Smooth transitions make animations look more natural and polished.",
                    HelpLevel.INTERMEDIATE: (
                        "Different easing functions can create different visual effects. "
                        "Try 'ease_in_out_quad' for subtle movements or 'bounce_out' for playful bounces."
                    ),
                    HelpLevel.ADVANCED: (
                        "Interpolation runs in a background task at ~60fps. "
                        "Use stop_parameter_interpolation() to cancel an in-progress transition."
                    ),
                    HelpLevel.DEVELOPER: (
                        "Uses a dedicated InterpolationManager with support for multiple easing functions. "
                        "Each parameter is interpolated independently with its own timing."
                    ),
                },
                related=["Setting Parameters", "Avatar State Management"],
                see_also=["https://easings.net/ for visual examples of easing functions"],
            )
        )

        # Add more help entries for other features...

    def add_entry(self, entry: HelpEntry):
        """Add a help entry to the system."""
        key = entry.name.lower().replace(" ", "_")
        self.entries[key] = entry

    def get_help(
        self,
        topic: str | None = None,
        level: HelpLevel | str = HelpLevel.INTERMEDIATE,
        category: HelpCategory | None = None,
    ) -> str:
        """Get help for a specific topic or list available topics.

        Args:
            topic: The topic to get help for, or None to list all topics
            level: The technical level of the help content
            category: Filter topics by category

        Returns:
            Formatted help text
        """
        if isinstance(level, str):
            level = HelpLevel[level.upper()]

        if topic is None:
            return self._list_topics(level, category)

        key = topic.lower().replace(" ", "_")
        if key not in self.entries:
            return f"No help found for '{topic}'. Use 'help()' to list available topics."

        return self.entries[key].format(level)

    def _list_topics(self, level: HelpLevel, category: HelpCategory | None = None) -> str:
        """List all available help topics."""
        lines = ["\nVRChat MCP Help System", "=" * 40]

        if category:
            entries = [e for e in self.entries.values() if e.category == category]
            lines.append(f"\nCategory: {category.value}\n")
        else:
            entries = list(self.entries.values())
            lines.append("\nAvailable help categories:\n")

            # Group by category if not filtered
            if not category:
                categories = {}
                for entry in entries:
                    if entry.category not in categories:
                        categories[entry.category] = []
                    categories[entry.category].append(entry.name)

                for cat, names in categories.items():
                    lines.append(f"{cat.value}:")
                    for name in sorted(names):
                        lines.append(f"  {name}")
                    lines.append("")

                lines.append("\nUse 'help(category=HelpCategory.CATEGORY)' to list topics in a category.")
                return "\n".join(lines)

        # If we have a specific category or topic
        if entries:
            for entry in sorted(entries, key=lambda e: e.name):
                lines.append(f"{entry.name}:")
                desc = textwrap.shorten(entry.description, width=70, placeholder="...")
                lines.append(f"  {desc}")
                if entry.command:
                    lines.append(f"  Command: {entry.command}")
                lines.append("")
        else:
            lines.append("No topics found in this category.")

        return "\n".join(lines)


# Create a default help system instance
help_system = HelpSystem()


def help(
    topic: str | None = None, level: HelpLevel | str = HelpLevel.INTERMEDIATE, category: HelpCategory | None = None
) -> str:
    """Display help for a topic or list available topics.

    Args:
        topic: The topic to get help for, or None to list all topics
        level: The technical level of the help content (BEGINNER, INTERMEDIATE, ADVANCED, DEVELOPER)
        category: Filter topics by category (HelpCategory enum value)

    Returns:
        Formatted help text
    """
    return help_system.get_help(topic, level, category)
