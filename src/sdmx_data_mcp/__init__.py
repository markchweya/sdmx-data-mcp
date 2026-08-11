"""An MCP server for discovering and retrieving SDMX statistics.

Wraps :class:`pysdmx.api.dc.pd.PandasConnector` so that AI assistants
can find official statistical datasets and retrieve the observations
themselves, rather than being handed a query URL to fetch.

Run it over STDIO, which is what MCP clients launch::

    sdmx-data-mcp

Or serve it over Streamable HTTP::

    sdmx-data-mcp --transport http --port 8000
"""

from sdmx_data_mcp.server import (
    get_data,
    inspect_dataflow,
    list_services,
    mcp,
    search_dataflows,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "get_data",
    "inspect_dataflow",
    "list_services",
    "mcp",
    "search_dataflows",
]
