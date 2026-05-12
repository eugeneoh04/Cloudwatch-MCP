import asyncio
import json
import time
import boto3
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

load_dotenv()

server = Server("cloudwatch-mcp")


def get_client():
    return boto3.client("logs", region_name="ap-northeast-2")


@server.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="list_log_groups",
            description="List all available CloudWatch log groups",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="query_logs",
            description="Run a CloudWatch Logs Insights query against a log group",
            inputSchema={
                "type": "object",
                "properties": {
                    "log_group": {
                        "type": "string",
                        "description": "The log group name e.g. /aws/lambda/mcp-log-generator",
                    },
                    "query": {
                        "type": "string",
                        "description": "CloudWatch Logs Insights query string",
                    },
                    "hours_back": {
                        "type": "integer",
                        "description": "How many hours back to search (default 1)",
                        "default": 1,
                    },
                },
                "required": ["log_group", "query"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    client = get_client()

    if name == "list_log_groups":
        response = client.describe_log_groups()
        groups = [g["logGroupName"] for g in response["logGroups"]]
        return [types.TextContent(type="text", text=json.dumps(groups, indent=2))]

    elif name == "query_logs":
        log_group = arguments["log_group"]
        query = arguments["query"]
        hours_back = arguments.get("hours_back", 1)

        end_time = int(time.time()) * 1000
        start_time = end_time - (hours_back * 3600 * 1000)

        response = client.start_query(
            logGroupName=log_group,
            startTime=start_time,
            endTime=end_time,
            queryString=query,
        )
        query_id = response["queryId"]

        # Poll until complete (up to 30 seconds)
        for _ in range(30):
            result = client.get_query_results(queryId=query_id)
            if result["status"] == "Complete":
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(result["results"], indent=2),
                    )
                ]
            await asyncio.sleep(1)

        return [types.TextContent(type="text", text="Query timed out after 30 seconds")]

    else:
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
