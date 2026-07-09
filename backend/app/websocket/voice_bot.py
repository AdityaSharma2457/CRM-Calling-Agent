import asyncio
import aiohttp
import json
import logging
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.config import settings
from app.rag.rag_service import get_relevant_context

logger = logging.getLogger(__name__)
router = APIRouter()

# Thresholds for VAD / silence detection
SILENCE_TIMEOUT = 1.2  # seconds of silence before we trigger LLM response
AUDIO_MIN_SIZE = 1024  # minimum bytes of audio to process

async def transcribe_audio(audio_data: bytes, content_type: str = "audio/x-raw;codec=pcm") -> str:
    """Sends audio bytes to Deepgram API for rapid transcription."""
    if not settings.DEEPGRAM_API_KEY:
        logger.error("DEEPGRAM_API_KEY not configured.")
        return ""
        
    url = "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true"
    headers = {
        "Authorization": f"Token {settings.DEEPGRAM_API_KEY}",
        "Content-Type": content_type
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=audio_data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    transcript = result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")
                    return transcript.strip()
                else:
                    text = await resp.text()
                    logger.error(f"Deepgram transcription error: {resp.status} - {text}")
                    return ""
    except Exception as e:
        logger.exception("Failed to transcribe audio via Deepgram")
        return ""

async def query_llm(user_input: str, conversation_history: list) -> str:
    """Queries Google Gemini API with RAG context."""
    if not settings.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not configured.")
        return "I am sorry, my artificial intelligence systems are currently offline."

    # Retrieve relevant info from our RAG database
    rag_context = get_relevant_context(user_input)
    
    system_prompt = (
        "You are Alice, the helpful AI Admission Counsellor for Apex University. "
        "Your goal is to answer questions about the university. "
        "Keep your responses friendly, concise (1-3 sentences maximum), and suitable for a voice conversation. "
        "Use ONLY the following factual university information to answer the user's questions. "
        "If you do not know the answer based on the context, politely state that you don't know and offer the admissions hotline number (+1-800-555-0199).\n\n"
        f"--- UNIVERSITY KNOWLEDGE BASE ---\n{rag_context}\n---------------------------------"
    )
    
    # Format contents for Gemini (user / model turns)
    contents = []
    for msg in conversation_history[-6:]:
        # Map assistant role to model role
        role = "model" if msg["role"] in ("assistant", "model") else "user"
        contents.append({
            "role": role,
            "parts": [{"text": msg["content"]}]
        })
    contents.append({
        "role": "user",
        "parts": [{"text": user_input}]
    })
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        },
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 150
        }
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    response_text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    return response_text.strip()
                else:
                    text = await resp.text()
                    logger.error(f"Gemini API error: {resp.status} - {text}")
                    return "I encountered an error processing your query. Please ask again."
    except Exception as e:
        logger.exception("Failed to query Gemini model")
        return "I am unable to answer right now due to a system error."

async def synthesize_speech(text: str) -> bytes:
    """Synthesizes text to speech using ElevenLabs API."""
    if not settings.ELEVENLABS_API_KEY:
        logger.error("ELEVENLABS_API_KEY not configured.")
        return b""
        
    voice_id = settings.ELEVENLABS_VOICE_ID
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    
    headers = {
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "accept": "audio/mpeg"
    }
    
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    return await resp.read()
                else:
                    err_text = await resp.text()
                    logger.error(f"ElevenLabs TTS error: {resp.status} - {err_text}")
                    return b""
    except Exception as e:
        logger.exception("Failed to synthesize speech via ElevenLabs")
        return b""


@router.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint that receives real-time audio streams,
    processes it through the AI pipeline, and streams synthesized response back.
    """
    await websocket.accept()
    logger.info("Call connected to voice WebSocket.")
    
    conversation_history = []
    audio_buffer = bytearray()
    last_audio_time = time.time()
    
    # Send a warm greeting on connection
    greeting = "Hello! I am Alice, the Apex University Admission Counsellor. How can I help you today?"
    conversation_history.append({"role": "assistant", "content": greeting})
    greeting_audio = await synthesize_speech(greeting)
    if greeting_audio:
        await websocket.send_bytes(greeting_audio)
        
    try:
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive(), timeout=0.2)
            except asyncio.TimeoutError:
                time_since_last_audio = time.time() - last_audio_time
                if len(audio_buffer) >= AUDIO_MIN_SIZE and time_since_last_audio >= SILENCE_TIMEOUT:
                    logger.info(f"Silence detected. Processing {len(audio_buffer)} bytes of audio...")
                    
                    current_audio = bytes(audio_buffer)
                    audio_buffer.clear()
                    
                    # 1. Transcribe the audio
                    transcript = await transcribe_audio(current_audio)
                    if transcript:
                        logger.info(f"User Transcribed: {transcript}")
                        conversation_history.append({"role": "user", "content": transcript})
                        
                        # 2. Query Google Gemini API with RAG
                        response_text = await query_llm(transcript, conversation_history)
                        logger.info(f"AI Response: {response_text}")
                        conversation_history.append({"role": "assistant", "content": response_text})
                        
                        # 3. Synthesize response to audio
                        response_audio = await synthesize_speech(response_text)
                        if response_audio:
                            await websocket.send_bytes(response_audio)
                            logger.info("Sent audio response back to caller.")
                    else:
                        logger.info("Could not transcribe audio.")
                continue

            if "bytes" in message:
                audio_buffer.extend(message["bytes"])
                last_audio_time = time.time()
            elif "text" in message:
                try:
                    data = json.loads(message["text"])
                    if data.get("event") == "stop":
                        logger.info("Received stop command from call client.")
                        break
                except ValueError:
                    pass

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected.")
    except Exception as e:
        logger.exception("Error in voice bot WebSocket loop")
    finally:
        logger.info("WebSocket session ended.")
