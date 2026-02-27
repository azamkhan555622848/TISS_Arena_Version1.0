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
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Import Google Generative AI for Gemini integration
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

# Initialize FastMCP server
mcp = FastMCP("audio-interface")

load_dotenv()
# Constants
DEFAULT_SAMPLE_RATE = 44100
DEFAULT_CHANNELS = 1
DEFAULT_DURATION = 5  # seconds

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

# Function to initialize Google Generative AI client
def initialize_genai(api_key):
    """Initialize the Google GenAI client with the provided API key."""
    if not GENAI_AVAILABLE:
        return None
    
    try:
        genai.configure(api_key=api_key)
        # Return the module as the client
        return genai
    except Exception as e:
        print(f"Error initializing Gemini: {e}")
        return None

async def record_audio_to_file(duration, sample_rate=DEFAULT_SAMPLE_RATE, channels=DEFAULT_CHANNELS, device_index=None):
    """Record audio and save to a temporary file."""
    try:
        # Record audio
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=channels,
            device=device_index
        )
        
        # Wait for the recording to complete
        sd.wait()
        
        # Generate a temp file
        fd, temp_path = tempfile.mkstemp(suffix='.wav')
        try:
            with wave.open(temp_path, 'wb') as wf:
                wf.setnchannels(channels)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(sample_rate)
                wf.writeframes((recording * 32767).astype(np.int16).tobytes())
            
            return temp_path, fd
        except Exception as e:
            os.close(fd)
            os.unlink(temp_path)
            print(f"Error saving recording: {e}")
            return None, None
    except Exception as e:
        print(f"Error recording audio: {e}")
        return None, None

@mcp.tool()
async def gemini_conversation(duration: float = DEFAULT_DURATION,
                             sample_rate: int = DEFAULT_SAMPLE_RATE,
                             channels: int = DEFAULT_CHANNELS,
                             device_index: int = None) -> str:
    """
    Start a real-time conversation with Gemini using your microphone and speakers.
    
    Args:
        duration: Maximum recording duration in seconds (default: 5)
        sample_rate: Sample rate in Hz (default: 44100)
        channels: Number of audio channels (default: 1)
        device_index: Specific input device index to use (default: system default)
    
    Returns:
        A message indicating the conversation result
    """
    if not GENAI_AVAILABLE:
        return ("Google Generative AI package is not installed. "
                "Please install it with: pip install google-generativeai")
    
    try:
        # Get API key from environment
        actual_api_key = os.environ.get("GOOGLE_API_KEY")
        if not actual_api_key:
            return ("No API key provided. Please provide a valid Google AI API key "
                    "or set the GOOGLE_API_KEY environment variable.")
        print(actual_api_key)
        # Initialize Gemini (Google Generative AI)
        model = initialize_genai(actual_api_key)
        if not model:
            return "Failed to initialize Gemini model. Please check your API key and connection."
        
        # Check if the specified device exists and is an input device
        if device_index is not None:
            devices = await get_audio_devices()
            input_devices = devices["input_devices"]
            if device_index < 0 or device_index >= len(input_devices):
                return (f"Error: Invalid device index {device_index}. "
                        "Use list_audio_devices tool to see available devices.")
        
        # Record audio
        print(f"Recording for {duration} seconds...")
        recording_file, fd = await record_audio_to_file(
            duration, 
            sample_rate=sample_rate, 
            channels=channels, 
            device_index=device_index
        )
        
        if not recording_file:
            return "Failed to record audio."
            
        try:
            # For demonstration, simulate a transcript.
            transcript = "Hello Gemini, can you tell me about yourself?"
            print(f"Simulated transcript: {transcript}")
            
            # Attempt to create a chat session and get a response.
            try:
                chat_session = model.ChatSession(model="models/gemini-2.0-flash")
                response = chat_session.send_message(transcript)
                response_text = response.last
            except Exception as api_error:
                # Fallback to a simulated response if the API call fails.
                print(f"API call failed: {api_error}")
                response_text = ("Simulated Gemini response: I am Gemini, a conversational AI. "
                                 "Due to current integration issues, this is a placeholder response.")
            
            print(f"Gemini response: {response_text}")
            
            return f"""
Real-time conversation with Gemini completed:

User (simulated transcript): "{transcript}"

Gemini's response: 
{response_text}

Note: This is a simplified implementation. A full implementation would:
1. Use Gemini's audio transcription capabilities for accurate speech-to-text.
2. Convert Gemini's response to audio using text-to-speech.
3. Play the response through speakers automatically.

To hear Gemini's response as audio, you would need to implement a TTS solution.
"""
        finally:
            # Clean up the temporary recording file
            if fd:
                os.close(fd)
            if recording_file and os.path.exists(recording_file):
                os.unlink(recording_file)
    
    except Exception as e:
        return (f"Error in Gemini conversation: {str(e)}\n\n"
                "Make sure you have installed the 'google-generativeai' package and provided a valid API key.")


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
