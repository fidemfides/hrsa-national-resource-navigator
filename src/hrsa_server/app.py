from fastmcp import FastMCP

from hrsa_server.tools.search_hrsa import (
    get_hrsa_snapshot_sha256,
    load_hrsa_rows,
    search_city_state,
    search_zip5,
)

mcp = FastMCP("HRSA Feasibility Server")
mcp.tool(description="Search HRSA health center sites by city and state.")(
    search_city_state
)
mcp.tool(description="Search HRSA health center sites by five-digit ZIP code.")(
    search_zip5
)


@mcp.tool()
def check_hrsa_dataset() -> dict:
    """Verify the HRSA dataset and report its record count."""
    rows = load_hrsa_rows()
    return {
        "status": "ok",
        "record_count": len(rows),
        "source": "HRSA Health Center Sites",
        "sha256": get_hrsa_snapshot_sha256(),
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
