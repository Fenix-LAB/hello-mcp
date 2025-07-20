"""
Example MCP Server for testing
This is a simple MCP server that provides basic tools for demonstration.
"""
import asyncio
import json
from typing import Any, Dict
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp import stdio_server


# Create MCP server instance
mcp_server = Server("example-mcp-server")


@mcp_server.list_tools()
async def list_tools():
    """List available tools in this MCP server"""
    return [
        Tool(
            name="echo_message",
            description="Echo back a message with a timestamp",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Message to echo back"
                    }
                },
                "required": ["message"]
            }
        ),
        Tool(
            name="simple_calculator",
            description="Perform simple mathematical operations",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["add", "subtract", "multiply", "divide"],
                        "description": "Mathematical operation to perform"
                    },
                    "a": {
                        "type": "number",
                        "description": "First number"
                    },
                    "b": {
                        "type": "number", 
                        "description": "Second number"
                    }
                },
                "required": ["operation", "a", "b"]
            }
        ),
        Tool(
            name="get_system_info",
            description="Get basic system information",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        )
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]):
    """Handle tool calls"""
    
    if name == "echo_message":
        message = arguments.get("message", "")
        from datetime import datetime
        timestamp = datetime.now().isoformat()
        response = f"Echo at {timestamp}: {message}"
        return [TextContent(type="text", text=response)]
    
    elif name == "simple_calculator":
        operation = arguments.get("operation")
        a = arguments.get("a", 0)
        b = arguments.get("b", 0)
        
        try:
            if operation == "add":
                result = a + b
            elif operation == "subtract":
                result = a - b
            elif operation == "multiply":
                result = a * b
            elif operation == "divide":
                if b == 0:
                    return [TextContent(type="text", text="Error: Division by zero")]
                result = a / b
            else:
                return [TextContent(type="text", text=f"Error: Unknown operation {operation}")]
            
            response = f"Result of {a} {operation} {b} = {result}"
            return [TextContent(type="text", text=response)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Calculation error: {str(e)}")]
    
    elif name == "get_system_info":
        import platform
        import os
        
        info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "current_directory": os.getcwd(),
            "environment": os.environ.get("ENV", "unknown")
        }
        
        response = f"System Information:\n{json.dumps(info, indent=2)}"
        return [TextContent(type="text", text=response)]
    
    else:
        return [TextContent(type="text", text=f"Error: Unknown tool '{name}'")]


async def main():
    """Main entry point for the MCP server"""
    print("Starting Example MCP Server...")
    print("This server provides basic tools for testing MCP integration.")
    print("Available tools: echo_message, simple_calculator, get_system_info")
    
    try:
        # Run the server using stdio transport
        async with stdio_server() as streams:
            await mcp_server.run(
                streams[0], streams[1],
                mcp_server.create_initialization_options()
            )
    except KeyboardInterrupt:
        print("\nShutting down MCP server...")
    except Exception as e:
        print(f"Error running MCP server: {e}")


if __name__ == "__main__":
    asyncio.run(main())
