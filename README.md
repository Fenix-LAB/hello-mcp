# Hello MCP
This is an AI assistant project that integrates Azure OpenAI with Model Context Protocol (MCP) servers using OpenAI Agents.

## Features

- **Dual Architecture**: Supports both traditional tool-based and MCP server-based interactions
- **Azure OpenAI Integration**: Uses Azure OpenAI as the LLM provider
- **OpenAI Agents**: Leverages OpenAI Agents framework for MCP server connectivity
- **REST API**: FastAPI-based REST API for easy integration
- **Real-time Streaming**: Support for streaming responses
- **Dynamic MCP Management**: Add/remove MCP servers at runtime

## Getting Started

### Prerequisites
- Python 3.10.11 or higher
- Azure OpenAI service with API access
- MCP servers (optional, for MCP functionality)

### Installation

#### 1. Create a virtual environment
Windows:
```bash
python -m venv venv
```

Linux/macOS:
```bash
python3 -m venv .venv
```

#### 2. Activate the virtual environment
Windows:
```bash
.\venv\Scripts\activate
```

Linux/macOS:
```bash
source .venv/bin/activate
```

#### 3. Install dependencies
```bash
pip install -r requirements.txt
```

#### 4. Configure environment variables
Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```

Edit `.env` with your Azure OpenAI credentials:
```env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-01
```

#### 5. Run the application
```bash
python main.py --env local
```

The API will be available at: http://localhost:8080
API documentation: http://localhost:8080/docs

## API Endpoints

### Traditional Tool-based Chat
- `POST /api/agent/chat` - Chat with traditional function calling tools
- `POST /api/agent/chat-stream` - Streaming chat with tools
- `GET /api/agent/tools` - List available tools
- `GET /api/agent/diagnose` - Diagnose Azure OpenAI connection

### MCP-based Chat (Recommended)
- `POST /api/agent/mcp/chat` - Chat using MCP servers and OpenAI Agents
- `POST /api/agent/mcp/chat-stream` - Streaming chat with MCP servers
- `GET /api/agent/mcp/servers` - List connected MCP servers
- `POST /api/agent/mcp/servers` - Add new MCP server
- `DELETE /api/agent/mcp/servers/{server_name}` - Remove MCP server
- `GET /api/agent/mcp/diagnose` - Diagnose MCP Agent Service

### Health & Info
- `GET /api/agent/health` - Service health check

## Usage Examples

### Basic Chat (MCP)

My last chat:

```bash
{
  "message": "Podrias ayudarme a obtener el readme de el siguiente repositorio usando deep wiki: openai-python"
}
```

```bash
curl -X POST "http://localhost:8080/api/agent/mcp/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, can you help me with file operations?",
    "user_id": "user123",
    "session_id": "session456"
  }'
```

### Chat with History
```bash
curl -X POST "http://localhost:8080/api/agent/mcp/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What files are in the current directory?",
    "conversation_history": [
      {"role": "user", "content": "Hello"},
      {"role": "assistant", "content": "Hi! How can I help you today?"}
    ],
    "user_id": "user123",
    "session_id": "session456"
  }'
```

### Add MCP Server
```bash
curl -X POST "http://localhost:8080/api/agent/mcp/servers" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "filesystem_mcp",
    "url": "http://localhost:3001",
    "description": "File system operations MCP server"
  }'
```

### Stream Chat
```bash
curl -X POST "http://localhost:8080/api/agent/mcp/chat-stream" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tell me about MCP servers",
    "stream": true
  }'
```

## Architecture

### Traditional Tools Mode
```
Client → FastAPI → Azure OpenAI Service → Azure OpenAI → Function Tools
```

### MCP Mode (Recommended)
```
Client → FastAPI → MCP Agent Service → OpenAI Agents → Azure OpenAI + MCP Servers
```

## MCP Servers

The application can connect to various MCP servers that provide specialized capabilities:

- **File System MCP**: File operations (read, write, list, etc.)
- **Weather MCP**: Weather data and forecasts
- **Database MCP**: Database operations
- **API Integration MCP**: External API calls
- **Custom MCPs**: Your own specialized servers

### Example MCP Server Configuration
```json
{
  "name": "filesystem_mcp",
  "url": "http://localhost:3001",
  "description": "File system operations MCP server"
}
```

## Configuration

### Environment Variables
- `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI endpoint URL
- `AZURE_OPENAI_API_KEY`: Your Azure OpenAI API key
- `AZURE_OPENAI_DEPLOYMENT_NAME`: Deployment name (e.g., "gpt-4")
- `AZURE_OPENAI_API_VERSION`: API version (e.g., "2024-02-01")
- `ENV`: Environment (local, dev, prod)
- `DEBUG`: Debug mode (true/false)

### Application Settings
- **Port**: 8080 (configurable)
- **Host**: 127.0.0.1 for local, 0.0.0.0 for production
- **Max Tokens**: 1500 (configurable)
- **Temperature**: 0.7 (configurable)

## Development

### Project Structure
```
hello-mcp/
├── app/
│   ├── router/
│   │   └── routes/
│   │       └── agent_service.py    # API endpoints
│   ├── services/
│   │   ├── azure_openai_service.py # Traditional tools service
│   │   └── mcp_agent_service.py    # MCP agent service
│   ├── tools/                      # Traditional function tools
│   │   ├── basic_tools.py
│   │   ├── api_tools.py
│   │   └── tool_manager.py
│   └── server.py                   # FastAPI app
├── config/
│   ├── config.py                   # Configuration
│   └── logger_config.py           # Logging
├── main.py                        # Entry point
└── requirements.txt              # Dependencies
```

### Running Different Modes

#### Local Development
```bash
python main.py --env local --debug
```

#### Production
```bash
python main.py --env prod
```

## Troubleshooting

### Common Issues

1. **Azure OpenAI Connection Errors**
   - Check your endpoint URL and API key
   - Verify deployment name is correct
   - Use the `/api/agent/diagnose` endpoint

2. **MCP Server Connection Issues**
   - Ensure MCP servers are running and accessible
   - Check server URLs and network connectivity
   - Use the `/api/agent/mcp/diagnose` endpoint

3. **Import Errors**
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - Check Python version compatibility

### Diagnostic Commands
```bash
# Test Azure OpenAI connection
curl http://localhost:8080/api/agent/diagnose

# Test MCP Agent Service
curl http://localhost:8080/api/agent/mcp/diagnose

# Check health
curl http://localhost:8080/api/agent/health
```

## License

This project is licensed under the MIT License.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions, please create an issue in the repository or contact the development team.