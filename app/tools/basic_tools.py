"""
Basic Tools - Simple utility tools for the assistant
"""
import asyncio
import datetime
import math
from typing import Dict, List, Any, Callable


class BasicTools:
    """Basic utility tools"""
    
    def get_tools(self) -> Dict[str, Callable]:
        """Get all basic tools"""
        return {
            "calculate": self.calculate,
            "get_current_time": self.get_current_time,
            "get_weather_info": self.get_weather_info,
            "text_analysis": self.text_analysis,
            "slow_process": self.slow_process
        }
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get OpenAI function calling schemas for basic tools"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "calculate",
                    "description": "Perform basic mathematical calculations",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {
                                "type": "string",
                                "description": "Mathematical expression to evaluate (e.g., '2 + 2', '10 * 5', 'sqrt(16)')"
                            }
                        },
                        "required": ["expression"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_current_time",
                    "description": "Get the current date and time",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "timezone": {
                                "type": "string",
                                "description": "Timezone (optional, defaults to UTC)",
                                "default": "UTC"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_weather_info",
                    "description": "Get weather information for a location (placeholder tool)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "City or location name"
                            }
                        },
                        "required": ["location"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "text_analysis",
                    "description": "Analyze text for basic metrics like word count, character count",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "Text to analyze"
                            }
                        },
                        "required": ["text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "slow_process",
                    "description": "Simula un proceso lento que toma 10 segundos para completarse",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_name": {
                                "type": "string",
                                "description": "Nombre de la tarea a ejecutar",
                                "default": "Proceso lento"
                            }
                        }
                    }
                }
            }
        ]
    
    def calculate(self, expression: str) -> str:
        """
        Perform basic mathematical calculations
        
        Args:
            expression: Mathematical expression to evaluate
            
        Returns:
            Result of the calculation
        """
        try:
            # Safe mathematical operations
            allowed_names = {
                k: v for k, v in math.__dict__.items() if not k.startswith("__")
            }
            allowed_names.update({"abs": abs, "round": round})
            
            # Evaluate the expression safely
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return f"Result: {result}"
            
        except Exception as e:
            return f"Error calculating '{expression}': {str(e)}"
    
    async def get_current_time(self, timezone: str = "UTC") -> str:
        """
        Get current date and time (now with async simulation)
        
        Args:
            timezone: Timezone (currently only UTC supported)
            
        Returns:
            Current date and time string
        """
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            print("Simulando tiempo de ejecución de forma asíncrona...")
            
            # Usar asyncio.sleep en lugar de time.sleep para no bloquear
            await asyncio.sleep(20)  # Simulate async delay without blocking
            
            return f"Current time (UTC): {now.strftime('%Y-%m-%d %H:%M:%S')}"
        except Exception as e:
            return f"Error getting current time: {str(e)}"
    
    def get_weather_info(self, location: str) -> str:
        """
        Get weather information (placeholder implementation)
        
        Args:
            location: City or location name
            
        Returns:
            Mock weather information
        """
        # TODO: Implement actual weather API integration
        return f"Weather information for {location}: This is a placeholder tool. In the future, this will integrate with a real weather API to provide current weather conditions, temperature, humidity, and forecast."
    
    def text_analysis(self, text: str) -> str:
        """
        Analyze text for basic metrics
        
        Args:
            text: Text to analyze
            
        Returns:
            Text analysis results
        """
        try:
            word_count = len(text.split())
            char_count = len(text)
            char_count_no_spaces = len(text.replace(" ", ""))
            sentence_count = len([s for s in text.split(".") if s.strip()])
            
            return f"""Text Analysis Results:
- Word count: {word_count}
- Character count: {char_count}
- Character count (no spaces): {char_count_no_spaces}
- Estimated sentence count: {sentence_count}
- Average words per sentence: {round(word_count / max(sentence_count, 1), 2)}"""
            
        except Exception as e:
            return f"Error analyzing text: {str(e)}"
    
    async def slow_process(self, task_name: str = "Proceso lento") -> str:
        """
        Simula un proceso lento que toma 10 segundos
        
        Args:
            task_name: Nombre de la tarea a ejecutar
            
        Returns:
            Resultado del proceso lento
        """
        try:
            # Simular proceso lento de 10 segundos
            await asyncio.sleep(10)
            return f"Proceso '{task_name}' completado después de 10 segundos de trabajo intensivo."
            
        except Exception as e:
            return f"Error en proceso lento: {str(e)}"