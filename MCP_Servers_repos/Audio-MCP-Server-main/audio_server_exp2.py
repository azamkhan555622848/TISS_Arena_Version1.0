#!/usr/bin/env python3
import asyncio
import base64
import io
import json
import os
import sounddevice as sd
import soundfile as sf
import numpy as np
import tempfile
import wave
import queue
import threading
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Import new Google GenAI SDK for Gemini integration
from google import genai
from google.genai.types import (
    LiveConnectConfig,
    GenerationConfig,
    Content,
    Part,
    SpeechConfig,
    VoiceConfig,
    PrebuiltVoiceConfig,
    Modality,
    HttpOptions  # Add this import
)
GENAI_AVAILABLE = True


# Initialize FastMCP server
mcp = FastMCP("audio-interface")

load_dotenv()
# Constants
DEFAULT_SAMPLE_RATE = 44100
DEFAULT_CHANNELS = 1
DEFAULT_DURATION = 5  # seconds
AUDIO_BUFFER_THRESHOLD = 5120  # Similar to TEN-Agent's threshold

# Global variables for real-time conversation
audio_queue = queue.Queue()
conversation_active = False
audio_stream = None
session = None

async def get_audio_devices():
    """Get a list of all available audio devices."""
    devices = sd.query_devices()
    input_devices = [d for d in devices if d['max_input_channels'] > 0]
    output_devices = [d for d in devices if d['max_output_channels'] > 0]
    
    return {
        "input_devices": input_devices,
        "output_devices": output_devices
    }

@mcp.tool()
async def list_audio_devices() -> str:
    """List all available audio input and output devices on the system."""
    devices = await get_audio_devices()
    
    result = "Audio devices available on your system:\n\n"
    
    result += "INPUT DEVICES (MICROPHONES):\n"
    for i, device in enumerate(devices["input_devices"]):
        result += f"{i}: {device['name']} (Channels: {device['max_input_channels']})\n"
    
    result += "\nOUTPUT DEVICES (SPEAKERS):\n"
    for i, device in enumerate(devices["output_devices"]):
        result += f"{i}: {device['name']} (Channels: {device['max_output_channels']})\n"
    
    return result

@mcp.tool()
async def record_audio(duration: float = DEFAULT_DURATION, 
                       sample_rate: int = DEFAULT_SAMPLE_RATE,
                       channels: int = DEFAULT_CHANNELS,
                       device_index: int = None) -> str:
    """Record audio from the microphone.
    
    Args:
        duration: Recording duration in seconds (default: 5)
        sample_rate: Sample rate in Hz (default: 44100)
        channels: Number of audio channels (default: 1)
        device_index: Specific input device index to use (default: system default)
    
    Returns:
        A message confirming the recording was captured
    """
    try:
        # Check if the specified device exists and is an input device
        if device_index is not None:
            devices = await get_audio_devices()
            input_devices = devices["input_devices"]
            if device_index < 0 or device_index >= len(input_devices):
                return f"Error: Invalid device index {device_index}. Use list_audio_devices tool to see available devices."
        
        # Record audio
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=channels,
            device=device_index
        )
        
        # Wait for the recording to complete
        sd.wait()
        
        # Generate a temp file for storage
        fd, temp_path = tempfile.mkstemp(suffix='.wav')
        try:
            with wave.open(temp_path, 'wb') as wf:
                wf.setnchannels(channels)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(sample_rate)
                wf.writeframes((recording * 32767).astype(np.int16).tobytes())
            
            # Encode the file for storage
            with open(temp_path, 'rb') as f:
                encoded_audio = base64.b64encode(f.read()).decode('utf-8')
                
            # Store the audio in a global variable for later playback
            global latest_recording
            latest_recording = {
                'audio_data': encoded_audio,
                'sample_rate': sample_rate,
                'channels': channels
            }
            
            return f"Successfully recorded {duration} seconds of audio. Use play_latest_recording tool to play it back."
        finally:
            os.close(fd)
            os.unlink(temp_path)
            
    except Exception as e:
        return f"Error recording audio: {str(e)}"

# Global variable to store the latest recording
latest_recording = None

@mcp.tool()
async def play_latest_recording() -> str:
    """Play the latest recorded audio through the speakers."""
    global latest_recording
    
    if latest_recording is None:
        return "No recording available. Use record_audio tool first."
    
    try:
        # Decode the audio data
        audio_data = base64.b64decode(latest_recording['audio_data'])
        sample_rate = latest_recording['sample_rate']
        channels = latest_recording['channels']
        
        # Create a temporary file
        fd, temp_path = tempfile.mkstemp(suffix='.wav')
        try:
            # Write the audio data to the temp file
            with open(temp_path, 'wb') as f:
                f.write(audio_data)
            
            # Read the audio file
            data, fs = sf.read(temp_path)
            
            # Play the audio
            sd.play(data, fs)
            sd.wait()  # Wait until the audio is done playing
            
            return "Successfully played the latest recording."
        finally:
            os.close(fd)
            os.unlink(temp_path)
    except Exception as e:
        return f"Error playing audio: {str(e)}"

@mcp.tool()
async def play_audio(text: str, voice: str = "default") -> str:
    """
    Play audio from text using text-to-speech.
    
    Args:
        text: The text to convert to speech
        voice: The voice to use (default: "default")
    
    Returns:
        A message indicating if the audio was played successfully
    """
    try:
        # Note: This is a simplified implementation that would need to be expanded
        # with an actual TTS service like gTTS, pyttsx3, or an external API
        
        # For now, we'll return a message indicating that TTS is not implemented
        return (
            "Text-to-speech functionality requires additional setup. "
            "You would need to install a TTS library like gTTS or pyttsx3, "
            f"which would convert the text '{text}' to audio using voice '{voice}'. "
            "This would then be played through your speakers."
        )
    except Exception as e:
        return f"Error playing audio: {str(e)}"

@mcp.tool()
async def play_audio_file(file_path: str, device_index: int = None) -> str:
    """
    Play an audio file through the speakers.
    
    Args:
        file_path: Path to the audio file
        device_index: Specific output device index to use (default: system default)
    
    Returns:
        A message indicating if the audio was played successfully
    """
    try:
        # Check if the file exists
        if not os.path.exists(file_path):
            return f"Error: File not found at {file_path}"
        
        # Check if the specified device exists and is an output device
        if device_index is not None:
            devices = await get_audio_devices()
            output_devices = devices["output_devices"]
            if device_index < 0 or device_index >= len(output_devices):
                return f"Error: Invalid device index {device_index}. Use list_audio_devices tool to see available devices."
        
        # Read the audio file
        data, fs = sf.read(file_path)
        
        # Play the audio
        sd.play(data, fs, device=device_index)
        sd.wait()  # Wait until the audio is done playing
        
        return f"Successfully played audio file: {file_path}"
    except Exception as e:
        return f"Error playing audio file: {str(e)}"

# Audio callback function for continuous recording
def audio_callback(indata, frames, time, status):
    """This is called for each audio block."""
    if status:
        print(f"Status: {status}")
    
    # Convert to bytes and add to queue
    audio_data = (indata * 32767).astype(np.int16).tobytes()
    
    # Only add to queue if conversation is active
    if conversation_active:
        audio_queue.put(audio_data)

# Function to play audio received from Gemini
async def play_audio_bytes(audio_data, sample_rate=24000):
    """Play audio bytes directly."""
    try:
        # Convert the PCM audio data to numpy array
        audio_np = np.frombuffer(audio_data, dtype=np.int16) / 32767.0
        
        # Play the audio
        sd.play(audio_np, sample_rate)
        await asyncio.sleep(len(audio_np) / sample_rate)  # Non-blocking wait
    except Exception as e:
        print(f"Error playing audio response: {e}")

# Process audio queue and send to Gemini in chunks
async def process_audio_queue(session):
    """Process audio from queue and send to Gemini in chunks."""
    buffer = bytearray()
    
    while conversation_active:
        try:
            # Get audio data from queue with a timeout
            try:
                audio_chunk = audio_queue.get(timeout=0.1)
                buffer.extend(audio_chunk)
            except queue.Empty:
                await asyncio.sleep(0.01)
                continue
            
            # If buffer reaches threshold, send to Gemini
            if len(buffer) >= AUDIO_BUFFER_THRESHOLD:
                # Encode and send
                base64_audio = base64.b64encode(buffer).decode('utf-8')
                media_chunks = [{
                    "data": base64_audio,
                    "mime_type": "audio/pcm"
                }]
                
                try:
                    await session.send(media_chunks)
                    print(f"Sent {len(buffer)} bytes of audio to Gemini")
                    buffer = bytearray()  # Clear buffer after sending
                except Exception as e:
                    print(f"Error sending audio: {e}")
        except Exception as e:
            print(f"Error in audio processing: {e}")
            await asyncio.sleep(0.1)

@mcp.tool()
async def gemini_realtime_conversation(
    duration: float = 60.0,
    sample_rate: int = 24000,
    channels: int = 1,
    device_index: int = None
) -> str:
    """
    Start a real-time conversation with Gemini using your microphone and speakers.
    
    Args:
        duration: Maximum conversation duration in seconds (default: 60)
        sample_rate: Sample rate in Hz (default: 24000)
        channels: Number of audio channels (default: 1)
        device_index: Specific input device index to use (default: system default)
    
    Returns:
        A message indicating the conversation result
    """
    global conversation_active, audio_stream, session
    
    if not GENAI_AVAILABLE:
        return ("Google GenAI package is not installed. "
                "Please install it with: pip install google-genai")
    
    try:
        # Get API key from environment
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return ("No API key provided. Please set the GOOGLE_API_KEY environment variable.")
        
        # Initialize the Gemini client with the new API
        # Explicitly set API version to beta for access to experimental features
        client = genai.Client(
            api_key=api_key,
            http_options=HttpOptions(api_version="v1beta1")  # Specify beta API version
        )
        
        # Set up LiveConnect configuration with the new API structure
        config = LiveConnectConfig(
            response_modalities=[Modality.AUDIO],
            system_instruction=Content(parts=[Part(text="You are a helpful voice assistant who responds concisely.")]),
            speech_config=SpeechConfig(
                voice_config=VoiceConfig(
                    prebuilt_voice_config=PrebuiltVoiceConfig(voice_name="alloy")
                )
            ),
            generation_config=GenerationConfig(
                temperature=0.7,
                max_output_tokens=1024,
            ),
        )
        
        # Set the conversation flag to active
        conversation_active = True
        
        # Start the audio stream for continuous recording
        audio_stream = sd.InputStream(
            samplerate=sample_rate,
            channels=channels,
            device=device_index,
            callback=audio_callback,
            blocksize=int(0.1 * sample_rate)  # 100ms chunks
        )
        
        # Start the stream
        audio_stream.start()
        
        # Use the correct model ID for Gemini 2.0
        model_id = "gemini-2.0-flash-exp"  # Update to the experimental model or another supported model
        
        # Connect to Gemini's LiveConnect API using the new client structure
        async with client.aio.live.connect(model=model_id, config=config) as live_session:
            session = live_session
            print(f"Connected to Gemini LiveConnect API using model {model_id}")
            
            # Create a task to process audio queue
            audio_processor = asyncio.create_task(process_audio_queue(live_session))
            
            # Timeout after specified duration
            start_time = asyncio.get_event_loop().time()
            
            # Send greeting to start the conversation
            await live_session.send(input="Hello Gemini", end_of_turn=True)
            
            # Process responses from Gemini
            try:
                while conversation_active and (asyncio.get_event_loop().time() - start_time < duration):
                    # Receive messages from Gemini
                    async for message in live_session.receive():
                        # Process server content (structure may vary slightly from old API)
                        if hasattr(message, 'server_content') and message.server_content:
                            # Check if response contains audio data
                            if (hasattr(message.server_content, 'model_turn') and 
                                message.server_content.model_turn):
                                
                                model_turn = message.server_content.model_turn
                                
                                # Process each part in the model's turn
                                for part in model_turn.parts:
                                    # Handle text parts
                                    if hasattr(part, 'text') and part.text:
                                        print(f"Gemini says: {part.text}")
                                    
                                    # Handle audio parts
                                    if hasattr(part, 'inline_data') and part.inline_data.data:
                                        print("Received audio response, playing...")
                                        await play_audio_bytes(part.inline_data.data, sample_rate=sample_rate)
                            
                            # Check if turn is complete
                            if hasattr(message.server_content, 'turn_complete') and message.server_content.turn_complete:
                                print("Turn complete")
                        
                        # Handle setup complete
                        elif hasattr(message, 'setup_complete') and message.setup_complete:
                            print("Setup complete")
                        
                        # Check for timeout
                        if asyncio.get_event_loop().time() - start_time >= duration:
                            print("Conversation timeout reached")
                            break
                
            except Exception as e:
                print(f"Error in response processing: {e}")
                pass
            
            # Clean up
            audio_processor.cancel()
            
            # Close the connection
            try:
                await live_session.close()
            except:
                pass
            
            # Return result
            return "Real-time conversation with Gemini completed."
    
    except Exception as e:
        return f"Error in Gemini real-time conversation: {str(e)}"
    
    finally:
        # Clean up resources
        conversation_active = False
        if audio_stream and audio_stream.active:
            audio_stream.stop()
            audio_stream.close()
        audio_stream = None
        session = None

@mcp.tool()
async def stop_gemini_conversation() -> str:
    """Stop the active Gemini real-time conversation."""
    global conversation_active, audio_stream, session
    
    if not conversation_active:
        return "No active conversation to stop."
    
    try:
        # Set flag to stop conversation
        conversation_active = False
        
        # Stop audio stream
        if audio_stream and audio_stream.active:
            audio_stream.stop()
            audio_stream.close()
        
        # Close session if it exists
        if session:
            try:
                await session.close()
            except:
                pass
        
        return "Gemini conversation stopped successfully."
    except Exception as e:
        return f"Error stopping conversation: {str(e)}"

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')