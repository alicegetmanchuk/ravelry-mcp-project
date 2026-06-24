import asyncio
import math
from ravelry_mcp.server import mcp
import ravelry_mcp.deps as deps


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

    data = await client.get("/yarns/search.json", params=params)

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
