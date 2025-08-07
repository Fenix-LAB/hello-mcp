"""
WebSocket Agent Service - Maneja conversaciones en tiempo real con el agente
MEJORADO: Un solo cliente async, sin mensajes fallback, historial limpio
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

from openai import AsyncAzureOpenAI
from openai.types.chat import ChatCompletionMessage, ChatCompletionMessageToolCall
from fastapi import WebSocket

from config.config import config
from config.logger_config import logger
from app.tools.tool_manager import ToolManager


class SessionState(Enum):
    """Estados de la sesión de conversación"""
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    PROCESSING_TOOL = "processing_tool"


@dataclass
class VoiceSession:
    """Representa una sesión de conversación de voz"""
    session_id: str
    websocket: WebSocket
    user_id: str
    state: SessionState = SessionState.IDLE
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    pending_tools: Dict[str, asyncio.Task] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    # Nuevo: historial separado para respuestas durante ejecución de herramientas
    temp_conversation_history: List[Dict[str, str]] = field(default_factory=list)


class WebSocketAgentService:
    """Servicio principal para manejo de WebSocket y conversaciones de voz"""
    
    def __init__(self):
        # Cliente async único para todas las operaciones
        self.client = AsyncAzureOpenAI(
            azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
            api_key=config.AZURE_OPENAI_API_KEY,
            api_version=config.AZURE_OPENAI_API_VERSION,
            timeout=60.0,
            max_retries=3
        )
        self.tool_manager = ToolManager()
        self.active_sessions: Dict[str, VoiceSession] = {}
        
        # Prompt del sistema optimizado para conversación de voz
        self.system_prompt = """
Eres un asistente de voz inteligente y conversacional. Tu objetivo es mantener una conversación natural y fluida con el usuario.

CARACTERÍSTICAS IMPORTANTES:
- Responde de manera concisa pero completa
- Usa un tono amigable y natural, como si fueras un amigo conocedor
- Si necesitas usar una herramienta, explica brevemente qué vas a hacer
- Mantén el contexto de la conversación anterior
- Cuando las herramientas terminan de ejecutarse, presenta los resultados de manera clara y útil

COMPORTAMIENTO EN CONVERSACIÓN:
- Escucha activamente y responde apropiadamente al contexto
- Haz preguntas de seguimiento cuando sea relevante
- Si el usuario parece estar esperando, ofrece actualizaciones sobre el progreso
- Mantén las respuestas conversacionales, no robóticas
- Al presentar resultados de herramientas, sé directo y claro

IMPORTANTE: Si acabas de ejecutar herramientas y tienes sus resultados, presenta la información solicitada de manera directa y útil. No repitas conversaciones previas, enfócate en responder con los datos obtenidos.

Recuerda que esta es una conversación de voz, así que sé natural y expresivo en tus respuestas.
"""
    


    async def create_session(self, websocket: WebSocket, user_id: str) -> str:
        """Crea una nueva sesión de conversación"""
        session_id = str(uuid.uuid4())
        session = VoiceSession(
            session_id=session_id,
            websocket=websocket,
            user_id=user_id
        )
        
        self.active_sessions[session_id] = session
        logger.info(f"Nueva sesión creada: {session_id} para usuario: {user_id}")
        
        # Enviar confirmación de sesión creada
        await self._send_message(websocket, {
            "type": "session_created",
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Mensaje de bienvenida
        await self._send_message(websocket, {
            "type": "system",
            "content": "¡Hola! Soy tu asistente de voz. Estoy aquí para ayudarte con lo que necesites. ¿En qué puedo asistirte hoy?"
        })
        
        return session_id

    async def handle_message(self, session_id: str, message_data: Dict[str, Any]):
        """Maneja mensajes entrantes del usuario"""
        session = self.active_sessions.get(session_id)
        if not session:
            logger.error(f"Sesión no encontrada: {session_id}")
            return
        
        session.last_activity = datetime.now(timezone.utc)
        
        try:
            message_type = message_data.get("type")
            content = message_data.get("content", "")
            
            if message_type == "text":
                await self._handle_text_message(session, content)
            elif message_type == "audio":
                # TODO: Implementar manejo de audio en el futuro
                await self._send_message(session.websocket, {
                    "type": "error",
                    "content": "Audio no soportado aún. Usa texto por ahora."
                })
            else:
                await self._send_message(session.websocket, {
                    "type": "error",
                    "content": f"Tipo de mensaje no soportado: {message_type}"
                })
                
        except Exception as e:
            logger.error(f"Error manejando mensaje en sesión {session_id}: {str(e)}")
            await self._send_message(session.websocket, {
                "type": "error",
                "content": "Error procesando tu mensaje. Por favor, intenta de nuevo."
            })

    async def _handle_text_message(self, session: VoiceSession, content: str):
        """Maneja mensajes de texto del usuario"""
        # Confirmar recepción del mensaje
        await self._send_message(session.websocket, {
            "type": "message_received",
            "content": "Mensaje recibido"
        })
        
        # Verificar si hay herramientas pendientes
        if session.pending_tools:
            # Manejar conversación paralela mientras se ejecutan herramientas
            await self._handle_message_during_tool_execution(session, content)
            return
        
        # Cambiar estado a pensando
        session.state = SessionState.THINKING
        await self._send_message(session.websocket, {
            "type": "agent_thinking",
            "content": "Pensando en tu respuesta..."
        })
        
        # Agregar mensaje del usuario al historial
        session.conversation_history.append({
            "role": "user",
            "content": content
        })
        
        # Procesar con OpenAI
        await self._process_with_openai(session)

    async def _handle_message_during_tool_execution(self, session: VoiceSession, content: str):
        """Maneja mensajes del usuario mientras se ejecutan herramientas - MEJORADO con mejor contexto"""
        try:
            # Generar respuesta dinámica con cliente async existente y contexto mejorado
            response = await self._generate_dynamic_response_during_tools(session, content)
            
            # Enviar respuesta generada dinámicamente
            session.state = SessionState.SPEAKING
            await self._send_response_chunks(session, response)
            session.state = SessionState.IDLE
            
            # IMPORTANTE: Guardamos en historial temporal con timestamp para ordenar
            session.temp_conversation_history.append({
                "role": "user",
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            session.temp_conversation_history.append({
                "role": "assistant", 
                "content": response,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            # Limitar historial temporal para no sobrecargar (máximo 8 mensajes = 4 intercambios)
            if len(session.temp_conversation_history) > 8:
                session.temp_conversation_history = session.temp_conversation_history[-8:]
            
        except Exception as e:
            logger.error(f"Error generando respuesta dinámica durante ejecución de herramientas: {str(e)}")
            # Último recurso: respuesta de emergencia usando IA
            await self._send_emergency_response_during_tools(session, content)
    
    async def _generate_dynamic_response_during_tools(self, session: VoiceSession, content: str) -> str:
        """Genera respuesta dinámica usando el cliente async mientras las herramientas corren - MEJORADO con mejor contexto"""
        
        pending_tools_count = len(session.pending_tools)
        
        # Prompt específico para respuestas durante ejecución de herramientas
        dynamic_prompt = f"""
Eres un asistente de voz que está ejecutando {pending_tools_count} herramienta(s) en segundo plano para una solicitud anterior.

CONTEXTO IMPORTANTE:
- Estás procesando herramientas en segundo plano para una solicitud anterior
- Esta es una conversación paralela que NO debe interferir con el resultado principal
- Tu respuesta es solo para mantener la interacción fluida mientras espera
- Tienes acceso al contexto de la conversación para responder apropiadamente
- NO respondas a la solicitud original, solo mantén la conversación

El usuario acaba de escribir: "{content}"

INSTRUCCIONES:
- Responde de manera natural y conversacional al mensaje actual
- Usa el contexto de la conversación para dar respuestas más relevantes
- Máximo 1-2 oraciones
- Sé amigable y mantén la conversación ligera
- Si te preguntan sobre el estado, confirma que sigues trabajando
- Si es una pregunta simple, puedes responder brevemente
- Si hace referencia a algo de la conversación anterior, puedes mencionarlo brevemente
- No menciones detalles técnicos sobre las herramientas

Responde solo el texto de tu respuesta, sin explicaciones adicionales.
"""

        try:
            # Crear historial completo y limpio para mejor contexto
            messages = [{"role": "system", "content": dynamic_prompt}]
            
            # MÉTODO MEJORADO: Crear historial limpio con contexto completo
            clean_history = self._build_clean_conversation_history(session)
            
            # Agregar historial limpio (máximo últimos 6 mensajes para no sobrecargar)
            if clean_history:
                messages.extend(clean_history[-6:])
            
            # Agregar mensaje actual
            messages.append({"role": "user", "content": content})
            
            # Generar respuesta con cliente async único
            response = await self.client.chat.completions.create(
                model=config.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                max_tokens=150,
                temperature=0.7,
                stream=False
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error en generación dinámica: {str(e)}")
            raise e  # Re-lanzar para manejar en el método padre
    
    async def _send_emergency_response_during_tools(self, session: VoiceSession, content: str):
        """Genera respuesta de emergencia usando IA cuando falla la generación principal"""
        try:
            # Prompt mínimo para emergencia
            emergency_prompt = f"Usuario dice: '{content}'. Responde brevemente que estás trabajando en su solicitud anterior pero puedes conversar."
            
            response = await self.client.chat.completions.create(
                model=config.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[{"role": "system", "content": emergency_prompt}],
                max_tokens=50,
                temperature=0.5,
                stream=False
            )
            
            emergency_response = response.choices[0].message.content.strip()
            
            session.state = SessionState.SPEAKING
            await self._send_response_chunks(session, emergency_response)
            session.state = SessionState.IDLE
            
        except Exception as e:
            logger.error(f"Error en respuesta de emergencia: {str(e)}")
            # Último recurso: silencio controlado
            session.state = SessionState.IDLE

    async def _send_response_chunks(self, session: VoiceSession, response: str):
        """Envía respuesta en chunks para simular streaming"""
        words = response.split(" ")
        current_chunk = ""
        
        for word in words:
            current_chunk += word + " "
            
            # Enviar chunk cada 3-5 palabras
            if len(current_chunk.split()) >= 4:
                await self._send_message(session.websocket, {
                    "type": "response_chunk",
                    "content": current_chunk.strip()
                })
                current_chunk = ""
                await asyncio.sleep(0.1)  # Pequeña pausa para simular naturalidad
        
        # Enviar chunk final si queda contenido
        if current_chunk.strip():
            await self._send_message(session.websocket, {
                "type": "response_chunk",
                "content": current_chunk.strip()
            })
        
        # Indicar que la respuesta está completa
        await self._send_message(session.websocket, {
            "type": "response_complete",
            "content": "Respuesta completada"
        })

    async def _process_with_openai(self, session: VoiceSession):
        """Procesa la conversación con OpenAI"""
        try:
            # Preparar mensajes usando SOLO el historial principal
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(session.conversation_history)
            
            # Obtener herramientas disponibles
            tools = self.tool_manager.get_tools_schema()
            
            # Cambiar estado a hablando
            session.state = SessionState.SPEAKING
            
            # Llamada a OpenAI con streaming
            stream = await self.client.chat.completions.create(
                model=config.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                max_tokens=config.MAX_TOKENS,
                temperature=config.TEMPERATURE,
                stream=True,
            )
            
            # Procesar respuesta en streaming
            await self._handle_streaming_response(session, stream)
            
        except Exception as e:
            logger.error(f"Error procesando con OpenAI: {str(e)}")
            await self._send_message(session.websocket, {
                "type": "error",
                "content": f"Error procesando tu solicitud: {str(e)}"
            })
            session.state = SessionState.IDLE

    async def _handle_streaming_response(self, session: VoiceSession, stream):
        """Maneja la respuesta en streaming de OpenAI"""
        current_response = ""
        tool_calls = []
        
        try:
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta:
                    delta = chunk.choices[0].delta
                    
                    # Contenido de texto
                    if delta.content:
                        current_response += delta.content
                        await self._send_message(session.websocket, {
                            "type": "response_chunk",
                            "content": delta.content
                        })
                    
                    # Tool calls
                    if delta.tool_calls:
                        for tool_call in delta.tool_calls:
                            if len(tool_calls) <= tool_call.index:
                                tool_calls.extend([None] * (tool_call.index + 1 - len(tool_calls)))
                            
                            if tool_calls[tool_call.index] is None:
                                tool_calls[tool_call.index] = {
                                    "id": tool_call.id,
                                    "type": tool_call.type,
                                    "function": {"name": "", "arguments": ""}
                                }
                            
                            if tool_call.function:
                                if tool_call.function.name:
                                    tool_calls[tool_call.index]["function"]["name"] += tool_call.function.name
                                if tool_call.function.arguments:
                                    tool_calls[tool_call.index]["function"]["arguments"] += tool_call.function.arguments
            
            # Procesar tool calls si existen
            if tool_calls and any(tc for tc in tool_calls if tc):
                # SI hay tool_calls, generar confirmación inicial ANTES de ejecutar herramientas
                await self._generate_tool_confirmation_and_execute(session, tool_calls, current_response)
            else:
                # NO hay tool_calls, agregar respuesta normal al historial y terminar
                if current_response:
                    session.conversation_history.append({
                        "role": "assistant",
                        "content": current_response
                    })
                
                # Respuesta completada sin tools
                await self._send_message(session.websocket, {
                    "type": "response_complete",
                    "content": "Respuesta completada"
                })
                session.state = SessionState.IDLE
                
        except Exception as e:
            logger.error(f"Error en streaming response: {str(e)}")
            await self._send_message(session.websocket, {
                "type": "error",
                "content": "Error procesando la respuesta"
            })
            session.state = SessionState.IDLE

    async def _handle_tool_calls(self, session: VoiceSession, tool_calls: List[Dict], assistant_message: str):
        """Maneja las llamadas a herramientas de forma completamente asíncrona"""
        # Notificar que se van a ejecutar herramientas
        await self._send_message(session.websocket, {
            "type": "system",
            "content": "Ejecutando herramientas necesarias para tu solicitud..."
        })
        
        # Agregar mensaje del asistente con tool calls al historial PRINCIPAL
        session.conversation_history.append({
            "role": "assistant",
            "content": assistant_message,
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": tc["type"],
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"]
                    }
                } for tc in tool_calls if tc
            ]
        })
        
        # Limpiar historial temporal al iniciar nueva ejecución de herramientas
        session.temp_conversation_history = []
        
        # Cambiar estado a IDLE para permitir nuevos mensajes
        session.state = SessionState.IDLE
        
        # Ejecutar tools en background con asyncio
        for tool_call in tool_calls:
            if tool_call:
                task = asyncio.create_task(
                    self._execute_tool_in_background(session, tool_call, tool_calls)
                )
                session.pending_tools[tool_call["id"]] = task

    async def _execute_tool_in_background(self, session: VoiceSession, tool_call: Dict, all_tool_calls: List[Dict]):
        """Ejecuta una herramienta en background y maneja la respuesta cuando esté lista"""
        tool_name = tool_call["function"]["name"]
        
        try:
            # Notificar inicio de ejecución de tool
            await self._send_message(session.websocket, {
                "type": "system",
                "content": f"Ejecutando: {tool_name}..."
            })
            
            # Parsear argumentos
            arguments = json.loads(tool_call["function"]["arguments"])
            
            # Ejecutar la herramienta
            result = await self.tool_manager.execute_tool(tool_name, arguments)
            
            # Notificar finalización
            await self._send_message(session.websocket, {
                "type": "system",
                "content": f"✓ {tool_name} completado"
            })
            
            # Agregar resultado al historial PRINCIPAL
            session.conversation_history.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": str(result)
            })
            
            # Remover de pending tools
            if tool_call["id"] in session.pending_tools:
                del session.pending_tools[tool_call["id"]]
            
            # Verificar si todas las herramientas han terminado
            remaining_tools = [tc for tc in all_tool_calls if tc and tc["id"] in session.pending_tools]
            
            if not remaining_tools:
                # Todas las herramientas han terminado, generar respuesta final
                await self._generate_final_tool_response(session)
            
        except Exception as e:
            error_msg = f"Error ejecutando {tool_name}: {str(e)}"
            logger.error(error_msg)
            
            await self._send_message(session.websocket, {
                "type": "system",
                "content": f"❌ Error en {tool_name}: {str(e)}"
            })
            
            # Agregar resultado de error al historial PRINCIPAL
            session.conversation_history.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": error_msg
            })
            
            # Remover de pending tools
            if tool_call["id"] in session.pending_tools:
                del session.pending_tools[tool_call["id"]]
    
    async def _generate_final_tool_response(self, session: VoiceSession):
        """Genera respuesta final cuando todas las herramientas han terminado - MEJORADO"""
        try:
            # Notificar que se están procesando los resultados
            await self._send_message(session.websocket, {
                "type": "system",
                "content": "Procesando resultados de herramientas..."
            })
            
            # Enviar mensaje especial para indicar que inicia la respuesta final
            await self._send_message(session.websocket, {
                "type": "final_response_start",
                "content": "Iniciando respuesta final"
            })
            
            # Cambiar estado a pensando
            session.state = SessionState.THINKING
            
            # MEJORADO: Usar SOLO el historial principal, ignorar conversaciones temporales
            final_system_prompt = self.system_prompt + """

SITUACIÓN ACTUAL: Acabas de completar la ejecución de herramientas solicitadas por el usuario. Tienes los resultados disponibles en el historial de conversación.

INSTRUCCIÓN ESPECÍFICA: Presenta los resultados de las herramientas de manera clara y directa. Responde a la solicitud original del usuario con la información obtenida. NO incluyas conversaciones que ocurrieron durante la ejecución de herramientas. Sigue el hilo de la conversación y responde de manera natural y conversacional.
"""
            
            messages = [{"role": "system", "content": final_system_prompt}]
            messages.extend(session.conversation_history)  # SOLO historial principal
            
            # Nueva llamada sin tools para respuesta final
            response = await self.client.chat.completions.create(
                model=config.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                max_tokens=config.MAX_TOKENS,
                temperature=config.TEMPERATURE,
                stream=True,
            )
            
            # Acumular toda la respuesta primero (sin streaming directo)
            session.state = SessionState.SPEAKING
            final_response = ""
            
            # Acumular toda la respuesta sin enviar chunks aún
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    final_response += chunk.choices[0].delta.content
            
            # Enviar la respuesta final directamente (sin duplicaciones gracias al frontend)
            if final_response:
                # logger.info(f"Enviando respuesta final: '{final_response[:100]}...'")
                
                # Hacer streaming manual de la respuesta
                await self._send_response_chunks(session, final_response)
                
                # Agregar respuesta al historial
                session.conversation_history.append({
                    "role": "assistant",
                    "content": final_response
                })
            
            # Limpiar historial temporal después de completar
            session.temp_conversation_history = []
            
            # Conversación completada
            await self._send_message(session.websocket, {
                "type": "response_complete",
                "content": "Respuesta completada"
            })
            
            session.state = SessionState.IDLE
            
        except Exception as e:
            logger.error(f"Error generando respuesta final: {str(e)}")
            await self._send_message(session.websocket, {
                "type": "error",
                "content": "Error procesando los resultados de las herramientas"
            })
            session.state = SessionState.IDLE

    async def close_session(self, session_id: str):
        """Cierra una sesión de conversación"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            
            # Cancelar tools pendientes
            for task in session.pending_tools.values():
                if not task.done():
                    task.cancel()
            
            # Remover sesión
            del self.active_sessions[session_id]
            logger.info(f"Sesión cerrada: {session_id}")

    async def _send_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Envía un mensaje por WebSocket"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error enviando mensaje por WebSocket: {str(e)}")

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de una sesión"""
        session = self.active_sessions.get(session_id)
        if not session:
            return None
            
        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "state": session.state.value,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "message_count": len(session.conversation_history),
            "pending_tools": len(session.pending_tools),
            "temp_messages": len(session.temp_conversation_history)
        }

    def get_active_sessions_count(self) -> int:
        """Obtiene el número de sesiones activas"""
        return len(self.active_sessions)
    
    def _build_clean_conversation_history(self, session: VoiceSession) -> List[Dict[str, str]]:
        """Construye un historial limpio para usar durante la ejecución de herramientas"""
        clean_history = []
        
        # Procesar historial principal eliminando tool_calls problemáticos
        for msg in session.conversation_history:
            if msg.get("role") == "user":
                # Mensajes del usuario siempre incluirlos
                clean_msg = {
                    "role": "user",
                    "content": msg.get("content", "")
                }
                clean_history.append(clean_msg)
            elif msg.get("role") == "assistant":
                # Para mensajes del asistente, quitar tool_calls si existen
                clean_msg = {
                    "role": "assistant",
                    "content": msg.get("content", "")
                }
                # Solo agregar si tiene contenido (no solo tool_calls vacíos)
                if clean_msg["content"].strip():
                    clean_history.append(clean_msg)
            # Saltar mensajes de "tool" que están en proceso
        
        # Agregar historial temporal (conversaciones durante herramientas) sin timestamps
        if session.temp_conversation_history:
            for temp_msg in session.temp_conversation_history:
                clean_msg = {
                    "role": temp_msg.get("role"),
                    "content": temp_msg.get("content", "")
                }
                if clean_msg["content"].strip():
                    clean_history.append(clean_msg)
        
        return clean_history

    async def _generate_tool_confirmation_and_execute(self, session: VoiceSession, tool_calls: List[Dict], original_response: str):
        """Genera confirmación inicial cuando se detectan tool_calls y luego ejecuta las herramientas"""
        try:
            # PASO 1: Si el LLM ya dio una respuesta con contenido, usarla como confirmación
            if original_response and original_response.strip():
                # Agregar la respuesta original al historial
                session.conversation_history.append({
                    "role": "assistant",
                    "content": original_response.strip()
                })
                
                # Completar la respuesta inicial
                await self._send_message(session.websocket, {
                    "type": "response_complete",
                    "content": "Respuesta inicial completada"
                })
            else:
                # Si no hay respuesta del LLM, generar confirmación rápida
                confirmation_msg = "¡Por supuesto! Déjame obtener esa información."
                await self._send_response_chunks(session, confirmation_msg)
                
                # Agregar confirmación al historial
                session.conversation_history.append({
                    "role": "assistant",
                    "content": confirmation_msg
                })
            
            # PASO 2: Ejecutar las herramientas
            await self._handle_tool_calls(session, tool_calls, original_response or "")
            
        except Exception as e:
            logger.error(f"Error generando confirmación y ejecutando herramientas: {str(e)}")
            await self._send_message(session.websocket, {
                "type": "error",
                "content": "Error procesando herramientas"
            })
            session.state = SessionState.IDLE


# Instancia global del servicio
websocket_agent_service = WebSocketAgentService()
