# 🎤 WebSocket Voice Agent - Documentación

## Descripción General

Este proyecto implementa un agente de voz que utiliza WebSockets para mantener conversaciones fluidas y naturales en tiempo real. El agente puede ejecutar herramientas de forma asíncrona sin bloquear la conversación, permitiendo una experiencia de usuario más natural.

## ✨ Características Principales

### 🔄 Conversación en Tiempo Real
- **WebSocket persistente**: Mantiene una conexión continua para conversaciones fluidas
- **Streaming de respuestas**: El agente responde en tiempo real, palabra por palabra
- **Estados de conversación**: Maneja diferentes estados (idle, thinking, speaking, processing_tool)

### ⚡ Ejecución Asíncrona de Herramientas
- **Procesamiento no bloqueante**: Las herramientas se ejecutan en hilos separados
- **Notificaciones de progreso**: El usuario recibe actualizaciones sobre el estado de las herramientas
- **Manejo de errores**: Gestión robusta de errores en herramientas lentas o fallidas

### 🎯 Sistema de Sesiones
- **Sesiones persistentes**: Cada conexión WebSocket mantiene su propio contexto
- **Historial de conversación**: Se mantiene el contexto completo de la conversación
- **Gestión automática de limpieza**: Las sesiones se limpian automáticamente al desconectar

## 🏗️ Arquitectura

### Componentes Principales

#### 1. `WebSocketAgentService`
**Archivo**: `app/services/websocket_agent_service.py`

Servicio principal que maneja:
- Gestión de sesiones WebSocket
- Procesamiento de mensajes
- Ejecución asíncrona de herramientas
- Streaming de respuestas de OpenAI

#### 2. `VoiceSession`
Dataclass que representa una sesión de conversación:
```python
@dataclass
class VoiceSession:
    session_id: str
    websocket: WebSocket
    user_id: str
    state: SessionState
    conversation_history: List[Dict[str, str]]
    pending_tools: Dict[str, asyncio.Task]
    created_at: datetime
    last_activity: datetime
```

#### 3. `SessionState`
Estados posibles de una sesión:
- `IDLE`: Esperando input del usuario
- `LISTENING`: Escuchando (para futuro soporte de audio)
- `THINKING`: Procesando la respuesta
- `SPEAKING`: Enviando respuesta al usuario
- `PROCESSING_TOOL`: Ejecutando herramientas

### Rutas WebSocket

#### 4. `WebSocket Router`
**Archivo**: `app/router/routes/websocket_route.py`

- `WebSocket /ws`: Endpoint principal de WebSocket
- `GET /`: Página de prueba HTML
- `GET /sessions`: Lista sesiones activas
- `GET /sessions/{session_id}`: Info de sesión específica

## 🚀 Instalación y Configuración

### Dependencias Adicionales

Agrega estas dependencias a tu `requirements.ini`:

```ini
# Dependencias existentes...
fastapi==0.115.6
uvicorn==0.33.0
websockets>=12.0  # Para soporte de WebSocket
```

### Variables de Entorno

Asegúrate de tener configuradas las variables de Azure OpenAI:

```bash
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

## 🔧 Uso

### 1. Iniciar el Servidor

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Acceder a la Página de Prueba

Visita: `http://localhost:8000/`

### 3. Conectar WebSocket

La página de prueba incluye un cliente JavaScript completo para probar el WebSocket.

### 4. Ejemplo de Conexión Programática

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

// Primer mensaje para crear sesión
const initialMessage = {
    type: 'system',
    user_id: 'user123',
    content: ''
};
ws.send(JSON.stringify(initialMessage));

// Enviar mensaje de texto
const textMessage = {
    type: 'text',
    content: 'Hola, ¿puedes calcular 2+2?',
    user_id: 'user123'
};
ws.send(JSON.stringify(textMessage));
```

## 📨 Protocolo de Mensajes

### Mensajes del Cliente al Servidor

#### Mensaje de Texto
```json
{
    "type": "text",
    "content": "Tu mensaje aquí",
    "user_id": "identificador_usuario"
}
```

#### Mensaje de Audio (Futuro)
```json
{
    "type": "audio",
    "content": "base64_audio_data",
    "user_id": "identificador_usuario"
}
```

### Mensajes del Servidor al Cliente

#### Sesión Creada
```json
{
    "type": "session_created",
    "session_id": "uuid-session-id",
    "timestamp": "2025-07-20T10:30:00Z"
}
```

#### Mensaje del Sistema
```json
{
    "type": "system",
    "content": "Pensando en tu respuesta..."
}
```

#### Chunk de Respuesta
```json
{
    "type": "response_chunk",
    "content": "parte de la respuesta"
}
```

#### Respuesta Completa
```json
{
    "type": "response_complete",
    "content": "Respuesta completada"
}
```

#### Error
```json
{
    "type": "error",
    "content": "Descripción del error"
}
```

## 🛠️ Herramientas Disponibles

El sistema incluye varias herramientas que se ejecutan de forma asíncrona:

### Herramientas Básicas
- `calculate`: Cálculos matemáticos
- `get_current_time`: Fecha y hora actual
- `text_analysis`: Análisis de texto
- `get_weather_info`: Información del clima (placeholder)

### Herramientas de API
- `make_http_request`: Solicitudes HTTP a APIs externas
- `get_public_ip`: Obtener IP pública
- `placeholder_api_call`: Placeholder para futuras integraciones

## 🎯 Flujo de Conversación

1. **Conexión**: Cliente se conecta al WebSocket
2. **Creación de Sesión**: Se crea una sesión única con ID
3. **Mensaje del Usuario**: Cliente envía mensaje de texto
4. **Confirmación**: Servidor confirma recepción
5. **Procesamiento**: 
   - Estado cambia a "thinking"
   - Se procesa con Azure OpenAI
   - Si se necesitan herramientas, se ejecutan asíncronamente
6. **Respuesta**: 
   - Estado cambia a "speaking"
   - Respuesta se envía en chunks en tiempo real
7. **Finalización**: Estado vuelve a "idle"

## 🔍 Monitoreo y Debugging

### Endpoints de Información

- `GET /sessions`: Ver sesiones activas
- `GET /sessions/{session_id}`: Detalles de una sesión
- `GET /agent/health`: Estado del servicio

### Logs

El sistema incluye logging detallado en:
- Creación y cierre de sesiones
- Ejecución de herramientas
- Errores de conexión
- Estados de conversación

## 🔮 Futuras Implementaciones

### Soporte de Audio
- Reconocimiento de voz (Speech-to-Text)
- Síntesis de voz (Text-to-Speech)
- Detección de actividad de voz (VAD)

### Mejoras de Conversación
- Interrupción inteligente del agente
- Detección de contexto emocional
- Personalización de respuestas

### Escalabilidad
- Soporte para múltiples usuarios concurrentes
- Persistencia de sesiones en base de datos
- Balanceador de carga para WebSockets

## 🐛 Solución de Problemas

### Problemas Comunes

1. **Error de Conexión a Azure OpenAI**
   - Verificar variables de entorno
   - Usar endpoint `/agent/diagnose`

2. **WebSocket se Desconecta**
   - Verificar estabilidad de red
   - Revisar logs del servidor

3. **Herramientas Lentas**
   - Las herramientas se ejecutan asíncronamente
   - El usuario recibe notificaciones de progreso

### Debug Mode

Para habilitar logs detallados, configura el nivel de logging en `config/logger_config.py`.

## 📚 Referencias

- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [Azure OpenAI Service](https://azure.microsoft.com/en-us/products/ai-services/openai-service)
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)

---

**Nota**: Este es un sistema en desarrollo. Las funcionalidades de audio se implementarán en futuras versiones.
