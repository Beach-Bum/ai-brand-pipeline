"""An MCP server that gives an agent a brand system: what it is, and whether work follows it.

The brand comes from a brand pack (see brand.py); the tools come from tools.py. This file only
connects the two to the Model Context Protocol.

Run:  uv run python -m brand_agent.server            (stdio, for a desktop agent)
      uv run python -m brand_agent.server --http     (streamable HTTP, for a hosted agent)
Pick the brand with the BRAND_ID environment variable (default: the example pack).
"""
from __future__ import annotations

import os
import sys

from mcp.server.mcpserver import MCPServer

from . import tools
from .brand import load


def build() -> MCPServer:
    brand = load()
    server = MCPServer(
        f"{brand['id']}-brand",
        title=f"{brand['name']} brand system",
        instructions=(
            f"The {brand['name']} brand guidelines as tools. Before writing or designing anything for "
            f"{brand['name']}, call brand_strategy and the tool for the part you are working on; do not "
            'rely on memory for colours, typefaces or spacing. After producing CSS, copy or a colour '
            'choice, call lint_css, lint_copy or check_contrast and fix what they report before showing the work.'
        ),
    )
    for fn in tools.ALL:
        server.tool()(fn)
    return server


def main() -> None:
    if '--http' in sys.argv:
        # HOST and PORT come from the environment so a container platform can set them.
        build().run('streamable-http', host=os.environ.get('HOST', '127.0.0.1'), port=int(os.environ.get('PORT', '8000')))
    else:
        build().run('stdio')


if __name__ == '__main__':
    main()
