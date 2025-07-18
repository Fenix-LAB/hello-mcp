"""
API Tools - Tools for making external API calls
"""
import httpx
import json
from typing import Dict, List, Any, Callable
from config.logger_config import logger


class APITools:
    """Tools for external API interactions"""
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    def get_tools(self) -> Dict[str, Callable]:
        """Get all API tools"""
        return {
            "make_http_request": self.make_http_request,
            "get_public_ip": self.get_public_ip,
            "placeholder_api_call": self.placeholder_api_call
        }
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get OpenAI function calling schemas for API tools"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "make_http_request",
                    "description": "Make HTTP requests to external APIs",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "URL to make the request to"
                            },
                            "method": {
                                "type": "string",
                                "description": "HTTP method (GET, POST, PUT, DELETE)",
                                "enum": ["GET", "POST", "PUT", "DELETE"],
                                "default": "GET"
                            },
                            "headers": {
                                "type": "object",
                                "description": "HTTP headers (optional)"
                            },
                            "params": {
                                "type": "object",
                                "description": "Query parameters (optional)"
                            }
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_public_ip",
                    "description": "Get the current public IP address",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "placeholder_api_call",
                    "description": "Placeholder for future API integrations",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "service_name": {
                                "type": "string",
                                "description": "Name of the service to call"
                            },
                            "action": {
                                "type": "string",
                                "description": "Action to perform"
                            },
                            "parameters": {
                                "type": "object",
                                "description": "Parameters for the API call"
                            }
                        },
                        "required": ["service_name", "action"]
                    }
                }
            }
        ]
    
    async def make_http_request(
        self, 
        url: str, 
        method: str = "GET", 
        headers: Dict[str, str] = None, 
        params: Dict[str, Any] = None
    ) -> str:
        """
        Make HTTP requests to external APIs
        
        Args:
            url: URL to make the request to
            method: HTTP method
            headers: Optional headers
            params: Optional query parameters
            
        Returns:
            Response from the API
        """
        try:
            # Basic URL validation
            if not url.startswith(('http://', 'https://')):
                return "Error: URL must start with http:// or https://"
            
            response = await self.http_client.request(
                method=method.upper(),
                url=url,
                headers=headers or {},
                params=params or {}
            )
            
            # Try to parse as JSON, fallback to text
            try:
                result = response.json()
                return f"Status: {response.status_code}\nResponse: {json.dumps(result, indent=2)}"
            except:
                return f"Status: {response.status_code}\nResponse: {response.text[:1000]}..."
                
        except Exception as e:
            logger.error(f"Error making HTTP request: {str(e)}")
            return f"Error making HTTP request: {str(e)}"
    
    async def get_public_ip(self) -> str:
        """
        Get the current public IP address
        
        Returns:
            Public IP address
        """
        try:
            response = await self.http_client.get("https://httpbin.org/ip")
            data = response.json()
            return f"Public IP: {data.get('origin', 'Unknown')}"
        except Exception as e:
            logger.error(f"Error getting public IP: {str(e)}")
            return f"Error getting public IP: {str(e)}"
    
    async def placeholder_api_call(
        self, 
        service_name: str, 
        action: str, 
        parameters: Dict[str, Any] = None
    ) -> str:
        """
        Placeholder for future API integrations
        
        Args:
            service_name: Name of the service
            action: Action to perform
            parameters: Parameters for the call
            
        Returns:
            Placeholder response
        """
        return f"""Placeholder API Call:
Service: {service_name}
Action: {action}
Parameters: {json.dumps(parameters or {}, indent=2)}

This is a placeholder tool for future API integrations. 
You can implement specific API calls here such as:
- Database queries
- Third-party service integrations
- Custom business logic APIs
- External data sources

Each service would have its own implementation based on requirements."""
    
    async def __del__(self):
        """Cleanup HTTP client"""
        try:
            await self.http_client.aclose()
        except:
            pass
