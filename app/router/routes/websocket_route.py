"""
WebSocket Router - Maneja las conexiones WebSocket para conversaciones de voz
"""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from typing import Dict, Any

from config.logger_config import logger
from app.services.websocket_agent_service import websocket_agent_service


router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Endpoint principal del WebSocket para conversaciones de voz en tiempo real
    """
    await websocket.accept()
    session_id = None
    
    try:
        logger.info("Nueva conexión WebSocket establecida")
        
        # Esperar primer mensaje para crear sesión
        initial_data = await websocket.receive_text()
        initial_message = json.loads(initial_data)
        
        # Extraer user_id del primer mensaje
        user_id = initial_message.get("user_id", "anonymous")
        
        # Crear sesión
        session_id = await websocket_agent_service.create_session(websocket, user_id)
        
        # Si el primer mensaje tenía contenido, procesarlo
        if initial_message.get("content"):
            await websocket_agent_service.handle_message(session_id, initial_message)
        
        # Loop principal para manejar mensajes
        while True:
            try:
                # Recibir mensaje
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Procesar mensaje
                await websocket_agent_service.handle_message(session_id, message)
                
            except WebSocketDisconnect:
                logger.info(f"Cliente desconectado de sesión: {session_id}")
                break
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "content": "Formato de mensaje inválido. Usa JSON."
                }))
            except Exception as e:
                logger.error(f"Error en WebSocket: {str(e)}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "content": f"Error procesando mensaje: {str(e)}"
                }))
                
    except WebSocketDisconnect:
        logger.info("Cliente desconectado durante el handshake")
    except Exception as e:
        logger.error(f"Error crítico en WebSocket: {str(e)}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "content": "Error crítico en la conexión"
            }))
        except:
            pass
    finally:
        # Limpiar sesión al cerrar
        if session_id:
            await websocket_agent_service.close_session(session_id)


@router.get("/", response_class=HTMLResponse)
async def get_test_page():
    """Página de prueba para el WebSocket"""
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Voice Agent - Test</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            max-width: 800px; 
            margin: 0 auto; 
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container { 
            background: white; 
            padding: 20px; 
            border-radius: 8px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .chat-container { 
            height: 400px; 
            overflow-y: auto; 
            border: 1px solid #ddd; 
            padding: 10px; 
            margin: 10px 0;
            background-color: #fafafa;
        }
        .message { 
            margin: 10px 0; 
            padding: 8px 12px; 
            border-radius: 6px;
        }
        .user-message { 
            background-color: #007bff; 
            color: white; 
            text-align: right; 
        }
        .agent-message { 
            background-color: #e9ecef; 
            color: #333; 
        }
        .system-message { 
            background-color: #ffeaa7; 
            color: #2d3436; 
            font-style: italic;
        }
        .error-message { 
            background-color: #ff6b6b; 
            color: white;
        }
        .input-container { 
            display: flex; 
            gap: 10px; 
        }
        input[type="text"] { 
            flex: 1; 
            padding: 10px; 
            border: 1px solid #ddd; 
            border-radius: 4px;
        }
        button { 
            padding: 10px 20px; 
            background-color: #007bff; 
            color: white; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer;
        }
        button:hover { 
            background-color: #0056b3; 
        }
        button:disabled { 
            background-color: #6c757d; 
            cursor: not-allowed;
        }
        .status { 
            padding: 5px 10px; 
            margin: 10px 0; 
            border-radius: 4px; 
            font-weight: bold;
        }
        .connected { 
            background-color: #d4edda; 
            color: #155724; 
        }
        .disconnected { 
            background-color: #f8d7da; 
            color: #721c24; 
        }
        .stats {
            margin-top: 20px;
            padding: 10px;
            background-color: #e9ecef;
            border-radius: 4px;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎤 AI Voice Agent - Test</h1>
        <p>Prueba el Voice Agent enviando mensajes de texto. En el futuro soportará audio.</p>
        
        <div id="status" class="status disconnected">Desconectado</div>
        
        <div id="chat" class="chat-container"></div>
        
        <div class="input-container">
            <input type="text" id="messageInput" placeholder="Escribe tu mensaje aquí..." disabled>
            <button id="sendButton" disabled>Enviar</button>
            <button id="connectButton">Conectar</button>
        </div>
        
        <div class="stats">
            <strong>Información de sesión:</strong><br>
            <span id="sessionInfo">No conectado</span>
        </div>
        
        <div class="stats">
            <strong>Instrucciones:</strong><br>
            1. Haz clic en "Conectar" para establecer conexión WebSocket<br>
            2. Escribe un mensaje y presiona "Enviar" o Enter<br>
            3. El agente responderá en tiempo real<br>
            4. Puedes enviar múltiples mensajes para mantener una conversación<br>
            5. Las herramientas se ejecutan de forma asíncrona sin bloquear la conversación
        </div>
    </div>

    <script>
        let ws = null;
        let sessionId = null;
        let currentResponse = "";
        let currentMessageElement = null;
        
        const statusDiv = document.getElementById('status');
        const chatDiv = document.getElementById('chat');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const connectButton = document.getElementById('connectButton');
        const sessionInfo = document.getElementById('sessionInfo');
        
        function addMessage(content, type = 'agent') {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}-message`;
            messageDiv.textContent = content;
            chatDiv.appendChild(messageDiv);
            chatDiv.scrollTop = chatDiv.scrollHeight;
            return messageDiv;
        }
        
        function updateStatus(connected) {
            if (connected) {
                statusDiv.textContent = '✅ Conectado';
                statusDiv.className = 'status connected';
                messageInput.disabled = false;
                sendButton.disabled = false;
                connectButton.textContent = 'Desconectar';
            } else {
                statusDiv.textContent = '❌ Desconectado';
                statusDiv.className = 'status disconnected';
                messageInput.disabled = true;
                sendButton.disabled = true;
                connectButton.textContent = 'Conectar';
                sessionInfo.textContent = 'No conectado';
            }
        }
        
        function connect() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.close();
                return;
            }
            
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/api/ws`;
            
            ws = new WebSocket(wsUrl);
            
            ws.onopen = function(event) {
                updateStatus(true);
                addMessage('Conectado al Voice Agent', 'system');
                
                // Enviar mensaje inicial para crear sesión
                const initialMessage = {
                    type: 'system',
                    user_id: 'test-user-' + Date.now(),
                    content: ''
                };
                ws.send(JSON.stringify(initialMessage));
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                
                switch(data.type) {
                    case 'system':
                        addMessage(data.content, 'system');
                        break;
                    case 'session_created':
                        sessionId = data.session_id;
                        sessionInfo.textContent = `Sesión: ${sessionId.substring(0, 8)}...`;
                        addMessage(`Sesión creada: ${sessionId.substring(0, 8)}...`, 'system');
                        break;
                    case 'message_received':
                        // Confirmación de mensaje recibido
                        break;
                    case 'agent_thinking':
                        addMessage(data.content, 'system');
                        currentResponse = "";
                        currentMessageElement = null;
                        break;
                    case 'final_response_start':
                        // Nueva respuesta final - limpiar acumulación anterior
                        currentResponse = "";
                        currentMessageElement = null;
                        break;
                    case 'response_chunk':
                        currentResponse += data.content;
                        // Actualizar el último mensaje del agente o crear uno nuevo
                        if (currentMessageElement) {
                            currentMessageElement.textContent = currentResponse;
                        } else {
                            currentMessageElement = addMessage(currentResponse, 'agent');
                        }
                        break;
                    case 'response_complete':
                        addMessage('✓ Respuesta completada', 'system');
                        currentMessageElement = null;
                        // Limpiar response acumulada para la próxima respuesta
                        currentResponse = "";
                        break;
                    case 'error':
                        addMessage(`Error: ${data.content}`, 'error');
                        break;
                    default:
                        console.log('Mensaje desconocido:', data);
                }
            };
            
            ws.onclose = function(event) {
                updateStatus(false);
                addMessage('Conexión cerrada', 'system');
                ws = null;
                sessionId = null;
                currentMessageElement = null;
            };
            
            ws.onerror = function(error) {
                addMessage('Error de conexión', 'error');
                console.error('WebSocket error:', error);
            };
        }
        
        function sendMessage() {
            const message = messageInput.value.trim();
            if (message && ws && ws.readyState === WebSocket.OPEN) {
                const messageData = {
                    type: 'text',
                    content: message,
                    user_id: 'test-user'
                };
                
                ws.send(JSON.stringify(messageData));
                addMessage(message, 'user');
                messageInput.value = '';
            }
        }
        
        // Event listeners
        connectButton.addEventListener('click', connect);
        sendButton.addEventListener('click', sendMessage);
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
        
        // Inicializar
        updateStatus(false);
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


@router.get("/sessions")
async def list_active_sessions():
    """
    Lista todas las sesiones activas
    """
    try:
        sessions_count = websocket_agent_service.get_active_sessions_count()
        return {
            "active_sessions": sessions_count,
            "message": f"Hay {sessions_count} sesiones activas"
        }
    except Exception as e:
        logger.error(f"Error listando sesiones: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_session_info(session_id: str):
    """
    Obtiene información de una sesión específica
    """
    try:
        session_info = websocket_agent_service.get_session_info(session_id)
        if not session_info:
            raise HTTPException(status_code=404, detail="Sesión no encontrada")
        return session_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo info de sesión: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
