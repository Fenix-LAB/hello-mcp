"""
Tool Manager - Manages all available tools for the assistant
"""
from typing import Dict, List, Any, Callable
from config.logger_config import logger
from app.tools.basic_tools import BasicTools
from app.tools.api_tools import APITools


class ToolManager:
    """Manages all available tools and their execution"""
    
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.tool_schemas: List[Dict[str, Any]] = []
        self._register_tools()
    
    def _register_tools(self):
        """Register all available tools"""
        # Initialize tool classes
        basic_tools = BasicTools()
        api_tools = APITools()
        
        # Register basic tools
        self.tools.update(basic_tools.get_tools())
        self.tool_schemas.extend(basic_tools.get_tool_schemas())
        
        # Register API tools
        self.tools.update(api_tools.get_tools())
        self.tool_schemas.extend(api_tools.get_tool_schemas())
        
        logger.info(f"Registered {len(self.tools)} tools: {list(self.tools.keys())}")
    
    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """Get OpenAI tools schema format"""
        return self.tool_schemas
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool with given arguments"""
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        try:
            tool_function = self.tools[tool_name]
            
            # Execute tool (handle both sync and async functions)
            if asyncio.iscoroutinefunction(tool_function):
                result = await tool_function(**arguments)
            else:
                result = tool_function(**arguments)
            
            logger.info(f"Tool '{tool_name}' executed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {str(e)}")
            raise
    
    def list_tools(self) -> List[str]:
        """List all available tool names"""
        return list(self.tools.keys())


import asyncio
