import json
from typing import Any
from pydantic_core import PydanticUndefined
from mcp.server import Server

from mcp.types import Tool, TextContent, CallToolResult, ListToolsResult, CallToolRequestParams
from mcp.server.session import ServerSession

from azair.models import SearchParams
from azair.client import fetch_search_results
from azair.parser import parse_results
from azair.airports import AirportDB

airport_db = AirportDB()


def _unwrap(annotation):
    origin = getattr(annotation, "__origin__", None)
    if origin is not None and not isinstance(origin, type):
        args = getattr(annotation, "__args__", ())
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return _unwrap(non_none[0])
    return annotation


def _describe_search_params() -> dict:
    fields = SearchParams.model_fields
    props = {}
    for name, field in fields.items():
        annotation = _unwrap(field.annotation)
        origin = getattr(annotation, "__origin__", None)
        if origin in (list, set):
            args = getattr(annotation, "__args__", ())
            inner = args[0] if args else int
            inner_type = "integer" if inner is int else "number" if inner is float else "string"
            prop = {"type": "array", "items": {"type": inner_type}}
        elif annotation is int:
            prop = {"type": "integer"}
        elif annotation is float:
            prop = {"type": "number"}
        elif annotation is bool:
            prop = {"type": "boolean"}
        else:
            prop = {"type": "string"}
        prop["description"] = field.description or name.replace("_", " ")
        if field.default is not PydanticUndefined:
            prop["default"] = field.default
        props[name] = prop
    return {
        "type": "object",
        "properties": props,
        "required": ["src_airport", "dst_airport", "dep_date", "arr_date"],
    }


async def list_tools(_session: ServerSession | None = None, _params: Any = None) -> ListToolsResult:
    return ListToolsResult(
        tools=[
            Tool(
                name="search_flights",
                description="Search for cheap flights on azair.eu across European low-cost airlines. Supports flexible date ranges, multiple airports per side, metro-area codes (e.g. MIL_ALL), anywhere (XXX), one-way or return, and all advanced filters (weekdays, time windows, stopover limits, overnight waits, transfers, Schengen-only).",
                inputSchema=_describe_search_params(),
            ),
            Tool(
                name="search_airports",
                description="Search for airports by IATA code or name. Uses the azair airport database.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Airport IATA code or name to search for",
                        }
                    },
                    "required": ["query"],
                },
            ),
        ]
    )


async def call_tool(_session: ServerSession | None = None, params: CallToolRequestParams | None = None) -> CallToolResult:
    if params is None:
        return CallToolResult(content=[TextContent(type="text", text="Missing params")])
    name = params.name
    arguments = params.arguments or {}

    if name == "search_flights":
        search_params = SearchParams(**arguments)
        html = await fetch_search_results(search_params)
        results = parse_results(html)
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps([r.model_dump() for r in results], indent=2))]
        )

    if name == "search_airports":
        query = arguments.get("query", "")
        airports = await airport_db.search(query)
        if not airports:
            return CallToolResult(
                content=[TextContent(type="text", text="No airports found.")]
            )
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps([a.model_dump() for a in airports], indent=2))]
        )

    raise ValueError(f"Unknown tool: {name}")


server = Server(
    "azair-eu-mcp",
    version="0.1.0",
    on_list_tools=list_tools,
    on_call_tool=call_tool,
)


async def main():
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import anyio
    anyio.run(main)
