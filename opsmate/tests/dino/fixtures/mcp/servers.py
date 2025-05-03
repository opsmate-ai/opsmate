from mcp.server.fastmcp import FastMCP
from datetime import datetime
import pytz

mcp = FastMCP("Time")


@mcp.tool()
def get_current_time(timezone: str = "UTC") -> str:
    """Get the current time in a specific timezone"""
    tz = pytz.timezone(timezone)
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    mcp.run()
