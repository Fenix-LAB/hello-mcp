"""
WebSocket Agent Service - Maneja conversaciones en tiempo real con el agente
"""
import asyncio
import json
import uuid
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

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


class WebSocketAgentService:
    """Servicio principal para manejo de WebSocket y conversaciones de voz"""
    
    def __init__(self):
        self.client = AsyncAzureOpenAI(
            azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
            api_key=config.AZURE_OPENAI_API_KEY,
            api_version=config.AZURE_OPENAI_API_VERSION,
            timeout=60.0,
            max_retries=3
        )
        self.tool_manager = ToolManager()
        self.active_sessions: Dict[str, VoiceSession] = {}
        
        # ThreadPoolExecutor para respuestas paralelas durante ejecución de herramientas
        self.thread_pool = ThreadPoolExecutor(max_workers=5)
        
        # Prompt del sistema optimizado para conversación de voz
        self.system_prompt = """
Eres un asistente de voz inteligente y conversacional. Tu objetivo es mantener una conversación natural y fluida con el usuario.

CARACTERÍSTICAS IMPORTANTES:
- Responde de manera concisa pero completa
- Usa un tono amigable y natural, como si fueras un amigo conocedor
- Si necesitas usar una herramienta, explica brevemente qué vas a hacer
- Mantén el contexto de la conversación anterior
- Si una herramienta tarda en ejecutarse, tranquiliza al usuario

COMPORTAMIENTO EN CONVERSACIÓN:
- Escucha activamente y responde apropiadamente al contexto
- Haz preguntas de seguimiento cuando sea relevante
- Si el usuario parece estar esperando, ofrece actualizaciones sobre el progreso
- Mantén las respuestas conversacionales, no robóticas

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
            # Responder inmediatamente sin usar OpenAI si hay tools pendientes
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
        """Maneja mensajes del usuario mientras se ejecutan herramientas usando OpenAI dinámico"""
        try:
            # Ejecutar en un hilo separado para no bloquear la ejecución de herramientas
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.thread_pool,
                self._generate_dynamic_response_during_tools,
                session, content
            )
            
            # Enviar respuesta generada dinámicamente
            session.state = SessionState.SPEAKING
            await self._send_response_chunks(session, response)
            session.state = SessionState.IDLE
            
        except Exception as e:
            logger.error(f"Error generando respuesta dinámica durante ejecución de herramientas: {str(e)}")
            # Fallback a respuesta básica si falla OpenAI
            await self._send_fallback_response_during_tools(session, content)
    
    def _generate_dynamic_response_during_tools(self, session: VoiceSession, content: str) -> str:
        """Genera respuesta dinámica usando OpenAI en un hilo separado"""
        import asyncio
        import nest_asyncio
        
        # Permitir asyncio en hilos
        nest_asyncio.apply()
        
        # Crear un nuevo evento loop para este hilo
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Crear contexto especial para conversación paralela
            pending_tools_info = []
            for tool_id, task in session.pending_tools.items():
                tool_name = "herramienta"  # Podríamos mejorar esto guardando el nombre
                pending_tools_info.append(tool_name)
            
            tools_description = ", ".join(pending_tools_info) if pending_tools_info else "algunas herramientas"
            
            # Prompt específico para respuestas durante ejecución de herramientas
            dynamic_prompt = f"""
Eres un asistente de voz que está ejecutando herramientas en segundo plano. Actualmente tienes {len(session.pending_tools)} herramientas ejecutándose: {tools_description}.

El usuario acaba de escribir: "{content}"

CONTEXTO IMPORTANTE:
- Estás procesando herramientas en segundo plano, pero puedes seguir conversando
- No interrumpas las herramientas que se están ejecutando
- Mantén la conversación fluida y natural
- Si el usuario pregunta sobre el estado, tranquilízalo pero no des detalles técnicos
- Si hace una nueva pregunta, responde pero menciona que las herramientas anteriores siguen ejecutándose

INSTRUCCIONES:
- Responde de manera natural y conversacional
- Máximo 2-3 oraciones
- Sé amigable y tranquilizador
- No menciones detalles técnicos sobre las herramientas
- Si es apropiado, pregunta algo relacionado o ofrece ayuda adicional

Responde solo el texto de tu respuesta, sin explicaciones adicionales."""

            # Crear cliente sincrónico para el hilo
            from openai import AzureOpenAI
            sync_client = AzureOpenAI(
                azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
                api_key=config.AZURE_OPENAI_API_KEY,
                api_version=config.AZURE_OPENAI_API_VERSION,
                timeout=30.0
            )
            
            # Generar respuesta
            response = sync_client.chat.completions.create(
                model=config.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[
                    {"role": "system", "content": dynamic_prompt}
                ],
                max_tokens=150,
                temperature=0.7,
            )
            
            generated_response = response.choices[0].message.content.strip()
            
            # Agregar información sobre herramientas si es relevante
            if len(session.pending_tools) > 0:
                generated_response += f" (Tengo {len(session.pending_tools)} herramienta{'s' if len(session.pending_tools) > 1 else ''} trabajando en segundo plano)"
            
            return generated_response
            
        except Exception as e:
            logger.error(f"Error en generación dinámica: {str(e)}")
            # Fallback a respuesta predefinida
            return f"Estoy aquí y sigo trabajando en tu solicitud anterior. {content} - Perfecto, sigamos conversando mientras proceso las herramientas en segundo plano."
            
        finally:
            loop.close()
    
    async def _send_fallback_response_during_tools(self, session: VoiceSession, content: str):
        """Envía respuesta de fallback si falla la generación dinámica"""
        fallback_responses = [
            "Estoy aquí y sigo trabajando en tu solicitud. ¿Hay algo más en lo que pueda ayudarte?",
            "Perfecto. Mientras proceso tu solicitud anterior, podemos seguir conversando.",
            "Entiendo. Estoy multitarea: trabajando en tu tarea anterior y disponible para conversar contigo.",
            "¡Claro! Sigo procesando tu solicitud pero puedo seguir charlando contigo sin problema."
        ]
        
        import random
        response = random.choice(fallback_responses)
        
        # Agregar información sobre herramientas pendientes
        if len(session.pending_tools) > 0:
            response += f" (Tengo {len(session.pending_tools)} herramienta{'s' if len(session.pending_tools) > 1 else ''} ejecutándose)"
        
        session.state = SessionState.SPEAKING
        await self._send_response_chunks(session, response)
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
            # Preparar mensajes
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
            
            # Agregar respuesta al historial
            if current_response:
                session.conversation_history.append({
                    "role": "assistant",
                    "content": current_response
                })
            
            # Procesar tool calls si existen
            if tool_calls and any(tc for tc in tool_calls if tc):
                await self._handle_tool_calls(session, tool_calls, current_response)
            else:
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
        
        # Agregar mensaje del asistente con tool calls al historial
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
        
        # Cambiar estado a IDLE para permitir nuevos mensajes
        session.state = SessionState.IDLE
        
        # Ejecutar tools en background sin bloquear
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
            
            # Agregar resultado al historial
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
            
            # Agregar resultado de error al historial
            session.conversation_history.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": error_msg
            })
            
            # Remover de pending tools
            if tool_call["id"] in session.pending_tools:
                del session.pending_tools[tool_call["id"]]
    
    async def _generate_final_tool_response(self, session: VoiceSession):
        """Genera respuesta final cuando todas las herramientas han terminado"""
        try:
            # Notificar que se están procesando los resultados
            await self._send_message(session.websocket, {
                "type": "system",
                "content": "Procesando resultados de herramientas..."
            })
            
            # Cambiar estado a pensando
            session.state = SessionState.THINKING
            
            # Preparar mensajes con el historial completo
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(session.conversation_history)
            
            # Nueva llamada sin tools para respuesta final
            response = await self.client.chat.completions.create(
                model=config.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages,
                max_tokens=config.MAX_TOKENS,
                temperature=config.TEMPERATURE,
                stream=True,
            )
            
            # Enviar respuesta final en streaming
            session.state = SessionState.SPEAKING
            final_response = ""
            
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    final_response += content
                    await self._send_message(session.websocket, {
                        "type": "response_chunk",
                        "content": content
                    })
            
            # Agregar respuesta final al historial
            if final_response:
                session.conversation_history.append({
                    "role": "assistant",
                    "content": final_response
                })
            
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

    async def _execute_tool_async(self, session: VoiceSession, tool_call: Dict) -> str:
        """Ejecuta una herramienta de forma asíncrona"""
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
            
            return str(result)
            
        except Exception as e:
            error_msg = f"Error ejecutando {tool_name}: {str(e)}"
            logger.error(error_msg)
            
            await self._send_message(session.websocket, {
                "type": "system",
                "content": f"❌ Error en {tool_name}"
            })
            
            return error_msg

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
            "pending_tools": len(session.pending_tools)
        }

    def get_active_sessions_count(self) -> int:
        """Obtiene el número de sesiones activas"""
        return len(self.active_sessions)


# Instancia global del servicio
websocket_agent_service = WebSocketAgentService()
