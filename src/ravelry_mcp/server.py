import asyncio
import math
from contextlib import asynccontextmanager
from typing import Literal

from mcp.server.fastmcp import FastMCP
from ravelry_mcp.client import RavelryClient
import ravelry_mcp.deps as deps


@asynccontextmanager
async def lifespan(server: FastMCP):
    async with RavelryClient() as c:
        deps.client = c
        yield


mcp = FastMCP("ravelry", lifespan=lifespan)


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


@mcp.tool()
async def search_yarn(
    query: str,
    weight: str | None = None,
    fiber: str | None = None,
    sort: str = "best",
    page_size: int = 10,
) -> dict:
    """Search Ravelry's yarn database by name, brand, weight, or fiber content.

    Use this tool when the user wants to find a yarn to use for a pattern, or
    is browsing yarn options by weight or fiber. Returns key details per yarn
    including yardage per skein, which is needed for calculate_yarn_needed.

    Args:
        query: Search terms, e.g. "malabrigo worsted" or "merino sock yarn"
        weight: Optional yarn weight, e.g. "worsted", "fingering", "dk", "bulky"
        fiber: Optional fiber content, e.g. "merino", "cotton", "alpaca"
        sort: Sort order — "best" (relevance), "rating", or "projects" (default: "best")
        page_size: Number of results to return (default 10, max 100)
    """
    params = {
        "query": query,
        "sort": sort,
        "page_size": page_size,
    }

    if weight is not None:
        params["weight"] = weight
    if fiber is not None:
        params["fiber"] = fiber

    data = await deps.client.get("/yarns/search.json", params=params)

    yarns = [
        {
            "id": y["id"],
            "name": y["name"],
            "permalink": y["permalink"],
            "brand": y.get("yarn_company_name"),
            "weight": y.get("yarn_weight", {}).get("name"),
            "yardage": y.get("yardage"),
            "gauge_divisor": y.get("gauge_divisor"),
            "rating_average": y.get("rating_average"),
            "ravelry_url": f"https://www.ravelry.com/yarns/library/{y['permalink']}",
        }
        for y in data.get("yarns", [])
    ]

    return {
        "meta": {
            "total_results": data.get("paginator", {}).get("results"),
            "page": data.get("paginator", {}).get("page"),
        },
        "yarns": yarns,
    }


@mcp.tool()
async def calculate_yarn_needed(
    pattern_id: int,
    yarn_id: int,
    size: str | None = None,
) -> dict:
    """Calculate how many skeins of a specific yarn are needed for a pattern.

    Use this tool when the user has chosen both a pattern and a yarn and wants
    to know how much to buy. Fetches pattern and yarn data concurrently, divides
    the pattern's maximum yardage by the yarn's yardage per skein, and adds a
    one-skein buffer for safety. If the user specifies a size, include it in the
    context but note that yardage is currently based on the pattern maximum.

    Args:
        pattern_id: Ravelry pattern ID from search_patterns
        yarn_id: Ravelry yarn ID from search_yarn
        size: Optional size the user intends to knit, e.g. "M" or "Large"
    """
    pattern_data, yarn_data = await asyncio.gather(
        deps.client.get(f"/patterns/{pattern_id}.json"),
        deps.client.get(f"/yarns/{yarn_id}.json"),
    )

    pattern = pattern_data.get("pattern", {})
    yarn = yarn_data.get("yarn", {})

    pattern_yardage = pattern.get("yardage_max") or pattern.get("yardage")
    yarn_yardage = yarn.get("yardage")

    if not pattern_yardage or not yarn_yardage:
        return {
            "error": "Could not calculate — missing yardage data.",
            "pattern_yardage": pattern_yardage,
            "yarn_yardage_per_skein": yarn_yardage,
        }

    skeins_needed = math.ceil(pattern_yardage / yarn_yardage)
    skeins_with_buffer = skeins_needed + 1

    return {
        "pattern_name": pattern.get("name"),
        "yarn_name": yarn.get("name"),
        "size": size,
        "pattern_yardage": pattern_yardage,
        "yarn_yardage_per_skein": yarn_yardage,
        "skeins_needed": skeins_needed,
        "skeins_with_buffer": skeins_with_buffer,
    }


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
