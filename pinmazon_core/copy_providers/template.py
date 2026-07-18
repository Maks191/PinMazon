from __future__ import annotations

import re

from pinmazon_core.schemas import CopyPackage

from .base import PinCopyRequest


ANGLE_COPY = {
    "result": [
        ("Upgrade Your Daily Setup", "Cleaner everyday workflow", "A focused setup refresh"),
        ("A Smarter Setup Upgrade", "Simple workspace refresh", "Made for daily routines"),
        ("Refresh Your Work Zone", "Useful setup inspiration", "Ready for everyday use"),
        ("Small Change Better Setup", "Easy routine refresh", "Built around real use"),
    ],
    "problem_solution": [
        ("Simplify Your Daily Setup", "Less setup friction", "A practical desk addition"),
        ("Make Your Setup Easier", "Keep routines organized", "Useful everyday option"),
        ("A Cleaner Everyday Routine", "Simple setup support", "Practical visual upgrade"),
        ("Tidy Up Your Workflow", "Focus on the essentials", "Designed for daily use"),
    ],
    "audience_use_case": [
        ("Made For Creative Setups", "Creator friendly inspiration", "Fits modern workspaces"),
        ("For Your Everyday Workflow", "Useful setup idea", "Easy to explore later"),
        ("Creator Setup Inspiration", "Built around daily work", "A practical product find"),
        ("A Find For Your Setup", "Useful workspace idea", "Made for real routines"),
    ],
}


def _tags(category: str) -> tuple[list[str], list[str]]:
    words = [word.lower() for word in re.findall(r"[A-Za-z0-9]+", category) if len(word) > 2]
    keywords = ["amazon finds", "workspace ideas", "product inspiration", *words][:8]
    hashtag_words = ["AmazonFinds", "WorkspaceIdeas", "ProductInspiration", "CreatorSetup"]
    hashtag_words.extend(word.title() for word in words)
    hashtag_words.extend(["UsefulFinds", "DeskSetup", "EverydayGear", "SmartSetup", "GiftIdeas"])
    unique = list(dict.fromkeys(hashtag_words))[:12]
    return [f"#{word}" for word in unique], list(dict.fromkeys(keywords))


class TemplateCopyProvider:
    """Deterministic, no-API fallback that never invents product specifications."""

    def generate(self, request: PinCopyRequest) -> CopyPackage:
        options = ANGLE_COPY.get(request.angle, ANGLE_COPY["result"])
        headline, bullet_one, bullet_two = options[request.variant_index % len(options)]
        product_name = str(request.product["product_name"]).strip()
        category = str(request.product.get("category") or "Useful product finds").strip()
        audience = request.audience.strip() or "Pinterest shoppers"
        hashtags, keywords = _tags(category)
        title = f"{product_name} Idea for {category}"[:100].rstrip()
        description = (
            f"Explore {product_name} as visual inspiration for {audience}. "
            "Review the product details and fit for your own needs before choosing. "
            "Affiliate links may earn commission."
        )
        alt_text = f"Product pin showing {product_name} on a graphic background."
        return CopyPackage(
            angle=request.angle,
            headline=headline,
            bullets=[bullet_one, bullet_two],
            title=title,
            description=description[:500],
            alt_text=alt_text[:500],
            short_description=f"A useful {category.lower()} idea."[:75],
            hashtags=hashtags,
            keywords=keywords,
            recommended_board=request.board,
            funnel=request.funnel,
            risk_flags=[],
        )
