"""
Test script to verify MCP Agent implementation
"""
import asyncio
import httpx
import json


async def test_traditional_endpoints():
    """Test traditional tool-based endpoints"""
    print("=" * 50)
    print("Testing Traditional Tool-based Endpoints")
    print("=" * 50)
    
    base_url = "http://localhost:8080/api/agent"
    
    async with httpx.AsyncClient() as client:
        # Test health endpoint
        try:
            response = await client.get(f"{base_url}/health")
            print(f"Health Check: {response.status_code}")
            if response.status_code == 200:
                print(f"Response: {response.json()}")
        except Exception as e:
            print(f"Health Check Error: {e}")
        
        # Test diagnose endpoint
        try:
            response = await client.get(f"{base_url}/diagnose")
            print(f"\nDiagnose: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Status: {result.get('status')}")
                print(f"Connection Test: {result.get('connection_test')}")
        except Exception as e:
            print(f"Diagnose Error: {e}")
        
        # Test tools list
        try:
            response = await client.get(f"{base_url}/tools")
            print(f"\nTools List: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Tools Count: {result.get('count')}")
                print(f"Tools: {result.get('tools')}")
        except Exception as e:
            print(f"Tools List Error: {e}")
        
        # Test chat endpoint
        try:
            chat_data = {
                "message": "Hello, can you calculate 5 + 3?"
            }
            response = await client.post(f"{base_url}/chat", json=chat_data)
            print(f"\nChat Test: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Response: {result.get('response')[:100]}...")
                print(f"Tool Calls: {result.get('tool_calls')}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Chat Test Error: {e}")


async def test_mcp_endpoints():
    """Test MCP-based endpoints"""
    print("\n" + "=" * 50)
    print("Testing MCP Agent Endpoints")
    print("=" * 50)
    
    base_url = "http://localhost:8080/api/agent/mcp"
    
    async with httpx.AsyncClient() as client:
        # Test MCP diagnose endpoint
        try:
            response = await client.get(f"{base_url}/diagnose")
            print(f"MCP Diagnose: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Status: {result.get('status')}")
                print(f"Connection Test: {result.get('connection_test')}")
                print(f"MCP Servers Count: {result.get('mcp_servers_count')}")
        except Exception as e:
            print(f"MCP Diagnose Error: {e}")
        
        # Test MCP servers list
        try:
            response = await client.get(f"{base_url}/servers")
            print(f"\nMCP Servers List: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"MCP Servers Count: {result.get('count')}")
                print(f"MCP Servers: {result.get('mcp_servers')}")
        except Exception as e:
            print(f"MCP Servers List Error: {e}")
        
        # Test adding MCP server (example)
        try:
            server_data = {
                "name": "test_mcp",
                "url": "http://localhost:3001",
                "description": "Test MCP server"
            }
            response = await client.post(f"{base_url}/servers", json=server_data)
            print(f"\nAdd MCP Server: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Status: {result.get('status')}")
                print(f"Message: {result.get('message')}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Add MCP Server Error: {e}")
        
        # Test MCP chat endpoint
        try:
            chat_data = {
                "message": "Hello, can you help me with MCP capabilities?",
                "user_id": "test_user",
                "session_id": "test_session"
            }
            response = await client.post(f"{base_url}/chat", json=chat_data)
            print(f"\nMCP Chat Test: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Response: {result.get('response')[:100]}...")
                print(f"MCP Servers Used: {result.get('mcp_servers_used')}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"MCP Chat Test Error: {e}")


async def test_api_documentation():
    """Test API documentation endpoints"""
    print("\n" + "=" * 50)
    print("Testing API Documentation")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        # Test OpenAPI docs
        try:
            response = await client.get("http://localhost:8080/docs")
            print(f"API Docs: {response.status_code}")
        except Exception as e:
            print(f"API Docs Error: {e}")
        
        # Test OpenAPI schema
        try:
            response = await client.get("http://localhost:8080/openapi.json")
            print(f"OpenAPI Schema: {response.status_code}")
            if response.status_code == 200:
                schema = response.json()
                paths = list(schema.get("paths", {}).keys())
                print(f"Available endpoints: {len(paths)}")
                mcp_endpoints = [p for p in paths if "/mcp/" in p]
                print(f"MCP endpoints: {len(mcp_endpoints)}")
        except Exception as e:
            print(f"OpenAPI Schema Error: {e}")


async def main():
    """Main test function"""
    print("MCP Agent API Test Suite")
    print("Make sure the server is running on http://localhost:8080")
    print()
    
    # Test if server is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8080/api/agent/health")
            if response.status_code != 200:
                print("❌ Server is not responding correctly")
                return
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("Make sure to run: python main.py --env local")
        return
    
    print("✅ Server is running")
    print()
    
    # Run all tests
    await test_traditional_endpoints()
    await test_mcp_endpoints()
    await test_api_documentation()
    
    print("\n" + "=" * 50)
    print("Test Suite Completed")
    print("=" * 50)
    print("\nNext steps:")
    print("1. Install missing dependencies: pip install -r requirements.txt")
    print("2. Set up your .env file with Azure OpenAI credentials")
    print("3. Start MCP servers if you want to test MCP functionality")
    print("4. Use the API documentation: http://localhost:8080/docs")


if __name__ == "__main__":
    asyncio.run(main())
