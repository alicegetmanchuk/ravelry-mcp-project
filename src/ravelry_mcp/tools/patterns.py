from typing import Literal
from ravelry_mcp.server import mcp
import ravelry_mcp.deps as deps


@mcp.tool()
async def search_patterns(
    query: str,
    craft: Literal["knitting", "crochet"],
    category: str | None = None,
    yarn_weight: str | None = None,
    difficulty_min: float | None = None,
    difficulty_max: float | None = None,
    free_only: bool = False,
    page_size: int = 10,
) -> dict:
    """Search Ravelry for knitting or crochet patterns.

    Use this tool when the user wants to find patterns by keyword, craft type,
    yarn weight, difficulty level, or price. Returns a list of matching patterns
    with titles, authors, difficulty ratings, and links.

    Args:
        query: Search terms, e.g. "cable knit sweater" or "granny square"
        craft: Either "knitting" or "crochet"
        category: Optional pattern category, e.g. "Pullover" or "Hat"
        yarn_weight: Optional yarn weight, e.g. "worsted", "fingering", "bulky"
        difficulty_min: Optional minimum difficulty rating (0.0 to 5.0)
        difficulty_max: Optional maximum difficulty rating (0.0 to 5.0)
        free_only: If True, only return free patterns
        page_size: Number of results to return (default 10, max 100)
    """
    params = {
        "query": query,
        "craft": craft,
        "page_size": page_size,
    }

    if category is not None:
        params["pc"] = category
    if yarn_weight is not None:
        params["weight"] = yarn_weight
    if difficulty_min is not None:
        params["difficulty_floor"] = difficulty_min
    if difficulty_max is not None:
        params["difficulty_ceiling"] = difficulty_max
    if free_only:
        params["availability"] = "free"

    data = await deps.client.get("/patterns/search.json", params=params)

    patterns = [
        {
            "id": p["id"],
            "name": p["name"],
            "permalink": p["permalink"],
            "free": p.get("free", False),
            "designer_name": p.get("designer", {}).get("name"),
            "photo_url": p.get("first_photo", {}).get("square_url") if p.get("first_photo") else None,
        }
        for p in data.get("patterns", [])
    ]

    paginator = data.get("paginator", {})

    return {
        "meta": {
            "total_results": paginator.get("results"),
            "page": paginator.get("page"),
        },
        "patterns": patterns,
    }


@mcp.tool()
async def get_pattern_details(pattern_id: int) -> dict:
    """Get full details for a specific Ravelry pattern by its ID.

    Use this tool after search_patterns to get in-depth information about a
    pattern the user is interested in — yardage requirements, gauge, available
    sizes, difficulty, and a direct link to the pattern page on Ravelry.

    Args:
        pattern_id: The numeric Ravelry pattern ID, returned by search_patterns
    """
    data = await deps.client.get(f"/patterns/{pattern_id}.json")
    p = data.get("pattern", {})

    permalink = p.get("permalink")

    return {
        "id": p.get("id"),
        "name": p.get("name"),
        "permalink": permalink,
        "free": p.get("free", False),
        "designer_name": p.get("pattern_author", {}).get("name"),
        "difficulty_average": round(p.get("difficulty_average", 0), 2),
        "rating_average": p.get("rating_average"),
        "yardage": p.get("yardage"),
        "yardage_max": p.get("yardage_max"),
        "yardage_description": p.get("yardage_description"),
        "yarn_weight_description": p.get("yarn_weight_description"),
        "gauge_description": p.get("gauge_description"),
        "sizes_available": p.get("sizes_available"),
        "pattern_attributes": [a["permalink"] for a in p.get("pattern_attributes", [])],
        "packs": p.get("packs"),
        "ravelry_url": f"https://www.ravelry.com/patterns/library/{permalink}" if permalink else None,
    }
