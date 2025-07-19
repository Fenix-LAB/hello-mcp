# Hello MCP
This is a simple project to develop a MCP (Modell Context Protocol).

## Getting Started
I develop this project using the following tools:
- Python 3.10.11

### Create a virtual environment
Windows:
```bash
python -m venv venv
```

Linux/macOS:
```bash
python3 -m venv .venv
```

### Activate the virtual environment
Windows:
```bash
.\venv\Scripts\activate
```

Linux/macOS:
```bash
source .venv/bin/activate
```
### Install dependencies
```bash
pip install -r requirements.txt
```
### Run the application
```bash
python main.py
```

Check out the [API documentation](http://localhost:8000/docs) for more details on how to use the application.

### Common messages

{
  "message": "Hola, ¿cómo estás?"
}

{
  "message": "¿Puedes ayudarme con información sobre el tiempo?",
  "conversation_id": "conv_12345"
}

{
  "message": "¿Y qué hay del pronóstico para mañana?",
  "conversation_id": "conv_12345",
  "stream": false,
  "conversation_history": [
    {
      "role": "user",
      "content": "Hola, ¿cómo está el clima hoy?"
    },
    {
      "role": "assistant",
      "content": "Hola! Hoy el clima está soleado con una temperatura de 25°C."
    }
  ]
}