# 🚀 Instrucciones de Prueba del WebSocket

## 📋 Pasos para Probar

### 1. Instalar Dependencias
Primero, asegúrate de que tienes la dependencia de WebSockets:

```bash
pip install websockets>=12.0
```

O si prefieres regenerar requirements.txt:

```bash
pip-compile requirements.ini --output-file requirements.txt
pip install -r requirements.txt
```

### 2. Iniciar el Servidor
```bash
python main.py --env local --debug
```

O alternativamente:
```bash
uvicorn app.api:app --host 0.0.0.0 --port 8080 --reload
```

### 3. Acceder a la Página de Prueba

**URLs disponibles:**
- Raíz: `http://localhost:8080/` (redirige automáticamente)
- Página de prueba: `http://localhost:8080/api/`
- WebSocket: `ws://localhost:8080/api/ws`

### 4. Probar la Conexión

1. Ir a `http://localhost:8080/`
2. Hacer clic en "Conectar"
3. Escribir un mensaje como "Hola, ¿puedes calcular 2+2?"
4. Observar la respuesta en tiempo real

## 🔧 URLs de la API

- **Página de prueba**: `GET /api/`
- **WebSocket**: `WebSocket /api/ws`
- **Sesiones activas**: `GET /api/sessions`
- **Info de sesión**: `GET /api/sessions/{session_id}`
- **Diagnóstico**: `GET /api/agent/diagnose`
- **Chat normal**: `POST /api/agent/chat`

## 🐛 Solución de Problemas

### Error 403 en WebSocket
- **Causa**: URL incorrecta del WebSocket
- **Solución**: Usar `ws://localhost:8080/api/ws` en lugar de `ws://localhost:8080/ws`

### Error de Conexión a Azure OpenAI
- **Verificar**: Variables de entorno en `config/config.py`
- **Diagnóstico**: `GET /api/agent/diagnose`

### Página no se carga
- **Verificar**: Que el servidor esté corriendo en el puerto 8080
- **URL correcta**: `http://localhost:8080/api/`

## 📝 Ejemplo de Prueba Manual

Puedes probar el WebSocket manualmente con JavaScript en la consola del navegador:

```javascript
// Conectar al WebSocket
const ws = new WebSocket('ws://localhost:8080/api/ws');

// Enviar mensaje inicial
ws.onopen = function() {
    ws.send(JSON.stringify({
        type: 'system',
        user_id: 'test-user',
        content: ''
    }));
};

// Escuchar mensajes
ws.onmessage = function(event) {
    console.log('Received:', JSON.parse(event.data));
};

// Enviar mensaje de prueba
function sendTest() {
    ws.send(JSON.stringify({
        type: 'text',
        content: 'Calcula 5 * 8',
        user_id: 'test-user'
    }));
}

// Llamar sendTest() después de que se establezca la sesión
```

## ✅ Indicadores de Funcionamiento Correcto

1. **Conexión exitosa**: Status verde "✅ Conectado"
2. **Sesión creada**: Aparece ID de sesión
3. **Mensaje de bienvenida**: El agente saluda automáticamente
4. **Respuesta a mensajes**: El agente responde en tiempo real
5. **Herramientas funcionando**: Las calculadoras y tools se ejecutan correctamente

¡Listo para probar! 🎯
