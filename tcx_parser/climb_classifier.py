"""
Professional climb categorization system based on length, elevation gain, and average gradient.
Uses the 2-out-of-3 rule for determining categories: HC, Cat 1, Cat 2, Cat 3, Cat 4.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Literal


Category = Literal["Cat 4", "Cat 3", "Cat 2", "Cat 1", "HC", "Unclassified"]


@dataclass
class Threshold:
    """Threshold values for climb categorization."""
    gain: float  # elevation gain in meters
    length: float  # length in km
    avg: float  # average gradient in %


# Professional thresholds for each category
THRESHOLDS = {
    "HC": Threshold(gain=1300, length=20.0, avg=8.0),  # Hors Catégorie (beyond category)
    "C1": Threshold(gain=900, length=12.0, avg=7.0),   # Category 1
    "C2": Threshold(gain=600, length=8.0, avg=6.0),    # Category 2
    "C3": Threshold(gain=350, length=5.0, avg=5.0),    # Category 3
    "C4S": Threshold(gain=200, length=2.5, avg=4.0),   # Cat 4 standard
    "C4B": Threshold(gain=100, length=1.2, avg=7.0),   # Cat 4 "stappi" (short and steep)
}

# Category order from easiest to hardest
CATEGORY_ORDER: list[Category] = ["Cat 4", "Cat 3", "Cat 2", "Cat 1", "HC"]


@dataclass
class ClimbClassification:
    """Result of climb classification."""
    category: Category
    avg_pct: float
    base: Category
    bonus_applied: bool


def avg_pct(length_km: float, gain_m: float) -> float:
    """Calculate average gradient percentage."""
    if not (length_km > 0 and gain_m >= 0):
        return 0.0
    return gain_m / (length_km * 10.0)


def pass_2of3(threshold: Threshold, length_km: float, gain_m: float, avg: float) -> bool:
    """Check if climb passes 2 out of 3 threshold criteria."""
    count = 0
    if gain_m >= threshold.gain:
        count += 1
    if length_km >= threshold.length:
        count += 1
    if avg >= threshold.avg:
        count += 1
    return count >= 2


def base_category(length_km: float, gain_m: float) -> Category:
    """Determine base category before any bonuses."""
    avg = avg_pct(length_km, gain_m)

    if pass_2of3(THRESHOLDS["HC"], length_km, gain_m, avg):
        return "HC"
    if pass_2of3(THRESHOLDS["C1"], length_km, gain_m, avg):
        return "Cat 1"
    if pass_2of3(THRESHOLDS["C2"], length_km, gain_m, avg):
        return "Cat 2"
    if pass_2of3(THRESHOLDS["C3"], length_km, gain_m, avg):
        return "Cat 3"
    if pass_2of3(THRESHOLDS["C4S"], length_km, gain_m, avg):
        return "Cat 4"
    if pass_2of3(THRESHOLDS["C4B"], length_km, gain_m, avg):
        return "Cat 4"

    # Ultra-short steep climbs
    if length_km < 1.2 and avg >= 12.0 and gain_m >= 80:
        return "Cat 4"

    return "Unclassified"


def apply_avg_bonus_95(cat: Category, avg: float) -> Category:
    """Apply bonus upgrade for very steep climbs (>=9.5% average)."""
    if cat == "Unclassified":
        return cat
    if cat == "HC":
        return cat
    if avg >= 9.5:
        idx = CATEGORY_ORDER.index(cat)
        return CATEGORY_ORDER[min(idx + 1, len(CATEGORY_ORDER) - 1)]
    return cat


def classify_climb(length_km: float, gain_m: float) -> ClimbClassification:
    """
    Classify a climb based on length and elevation gain.

    Uses the professional 2-out-of-3 rule for categorization and applies
    a bonus upgrade for very steep climbs (>=9.5% average gradient).

    Args:
        length_km: Length of the climb in kilometers
        gain_m: Elevation gain in meters

    Returns:
        ClimbClassification with category, average gradient, and bonus info
    """
    avg = avg_pct(length_km, gain_m)
    base = base_category(length_km, gain_m)
    final = apply_avg_bonus_95(base, avg)

    return ClimbClassification(
        category=final,
        avg_pct=round(avg, 1),
        base=base,
        bonus_applied=(final != base and avg >= 9.5),
    )


def get_category_color(category: Category) -> str:
    """Get the display color for a category."""
    colors = {
        "HC": "#D04972",
        "Cat 1": "#C15A85",
        "Cat 2": "#A16CA3",
        "Cat 3": "#7B80BD",
        "Cat 4": "#5594D7",
        "Unclassified": "#66B6E5",
    }
    return colors.get(category, "#66B6E5")


def get_category_label(category: Category) -> str:
    """Get the display label for a category."""
    if category == "Unclassified":
        return "Non classificata"
    return category


def get_category_description(category: Category) -> str:
    """Get a description for a category."""
    descriptions = {
        "HC": "Hors Catégorie - Legendary climb",
        "Cat 1": "Category 1 - Very difficult climb",
        "Cat 2": "Category 2 - Difficult climb",
        "Cat 3": "Category 3 - Moderate climb",
        "Cat 4": "Category 4 - Easy climb",
        "Unclassified": "Unclassified - Very easy climb",
    }
    return descriptions.get(category, "Unknown category")


def get_category_rank(category: Category) -> int:
    """Get numeric rank for sorting (higher = harder)."""
    ranks = {
        "Unclassified": 0,
        "Cat 4": 1,
        "Cat 3": 2,
        "Cat 2": 3,
        "Cat 1": 4,
        "HC": 5,
    }
    return ranks.get(category, 0)
