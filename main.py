import json
from typing import Any

import httpx
from pydantic import ValidationError
from pydantic_core import PydanticUndefined
from mcp.server import Server

from mcp.types import Tool, TextContent, CallToolResult, ListToolsResult, CallToolRequestParams
from mcp.server.session import ServerSession

from azair.models import SearchParams
from azair.client import search_flights
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
        return CallToolResult(
            content=[TextContent(type="text", text="Missing params")],
            isError=True,
        )
    name = params.name
    arguments = params.arguments or {}

    if name == "search_flights":
        try:
            search_params = SearchParams(**arguments)
            results = await search_flights(search_params)
        except ValidationError as exc:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Invalid search parameters:\n{exc}")],
                isError=True,
            )
        except httpx.HTTPError as exc:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Flight search failed: {exc}")],
                isError=True,
            )
        except Exception as exc:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Flight search failed: {type(exc).__name__}: {exc}")],
                isError=True,
            )
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps([r.model_dump() for r in results], indent=2))]
        )

    if name == "search_airports":
        query = str(arguments.get("query", "")).strip()
        if not query:
            return CallToolResult(
                content=[TextContent(type="text", text="Query must not be empty.")],
                isError=True,
            )
        try:
            airports = await airport_db.search(query)
        except httpx.HTTPError as exc:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Airport lookup failed: {exc}")],
                isError=True,
            )
        except Exception as exc:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Airport lookup failed: {type(exc).__name__}: {exc}")],
                isError=True,
            )
        if not airports:
            return CallToolResult(
                content=[TextContent(type="text", text="No airports found.")]
            )
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps([a.model_dump() for a in airports], indent=2))]
        )

    return CallToolResult(
        content=[TextContent(type="text", text=f"Unknown tool: {name}")],
        isError=True,
    )


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
