import gradio as gr
import yaml
import os
from pathlib import Path
import subprocess
import tempfile
import torch
from TTS.api import TTS
import hashlib
import random
import string

# Configuration and hardware file paths
PERSISTENT_FILE = Path("./data/persistent.yaml")
HARDWARE_FILE = Path("./data/hardware_details.txt")
MODEL_DIR = Path("./models")  # Default model directory

def load_persistent_settings():
    if not PERSISTENT_FILE.exists():
        default_settings = {
            "model_path": str(MODEL_DIR),
            "voice_model": "default",
            "speed": 1.0,
            "pitch": 1.0,
            "volume_gain": 0.0,
            "session_history": "",
            "threads_percent": 80
        }
        with open(PERSISTENT_FILE, 'w') as f:
            yaml.dump(default_settings, f)
        return default_settings
    else:
        with open(PERSISTENT_FILE, 'r') as f:
            settings = yaml.safe_load(f)
            if "threads_percent" not in settings:
                settings["threads_percent"] = 80
            if "model_path" not in settings:
                settings["model_path"] = str(MODEL_DIR)
            return settings

def save_persistent_settings(settings):
    with open(PERSISTENT_FILE, 'w') as f:
        yaml.dump(settings, f)

def load_hardware_details():
    lines = []
    if HARDWARE_FILE.exists():
        with open(HARDWARE_FILE, 'r') as f:
            lines = f.readlines()
    return [line.strip() for line in lines[:4]]

def parse_cpu_threads(hardware_lines):
    threads = 8  # default
    for line in hardware_lines:
        if "CPU Threads Total:" in line:
            parts = line.split(":")
            try:
                threads = int(parts[1].strip())
            except ValueError:
                pass
    return threads

def find_and_load_model(model_path):
    model_directory = Path(model_path)
    model_files = list(model_directory.glob('*.pth'))
    if model_files:
        model_path = model_files[0]  # Select the first .pth file found
        model = torch.load(model_path, map_location='cpu')  # Load model to CPU
        print(f"Model loaded from {model_path}")
        return model
    else:
        print(f"No model files found in {model_path}.")
        return None

settings = load_persistent_settings()
hardware_lines = load_hardware_details()
cpu_threads = parse_cpu_threads(hardware_lines)
tts_model = find_and_load_model(settings['model_path'])

def generate_tts_audio(text, speaker_wav, language):
    output_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir='./output').name
    tts.tts_to_file(text=text, speaker_wav=speaker_wav, language=language, file_path=output_path)
    return output_path

def convert_wav_to_mp3(wav_path):
    random_hash = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    mp3_path = f"./output/{random_hash}.mp3"
    subprocess.run(["ffmpeg", "-y", "-i", wav_path, "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k", mp3_path], check=True)
    return mp3_path

with gr.Blocks(title="Gen-Gradio-Voice") as demo:
    with gr.Tab("Narrator"):
        text_input = gr.Textbox(label="Enter Text", lines=3, placeholder="Type your narration here...")
        speaker_input = gr.Textbox(label="Path to Speaker WAV", placeholder="Enter path to speaker WAV file...")
        language_input = gr.Dropdown(label="Language", choices=['en', 'es', 'de', 'fr'], value='en')
        generate_button = gr.Button("Generate Speech")
        play_button = gr.Button("Play Speech")
        save_button = gr.Button("Save as MP3")
        
        audio_output = gr.Audio(label="Output Audio", type="file")
        mp3_download = gr.File(label="Download MP3")

        generate_button.click(
            fn=generate_tts_audio,
            inputs=[text_input, speaker_input, language_input],
            outputs=audio_output
        )

        play_button.click(None, [], [audio_output])
        save_button.click(
            fn=convert_wav_to_mp3,
            inputs=audio_output,
            outputs=mp3_download
        )

    with gr.Tab("Configuration"):
        gr.Markdown("### Hardware Details")
        gr.Textbox(label="System Info", value="\n".join(hardware_lines), lines=4, interactive=False)
        model_path_input = gr.Textbox(label="Model Path", value=settings["model_path"])
        voice_model_input = gr.Textbox(label="Voice Model", value=settings["voice_model"])
        speed_slider = gr.Slider(label="Speed", minimum=0.5, maximum=2.0, step=0.1, value=settings["speed"])
        pitch_slider = gr.Slider(label="Pitch", minimum=0.5, maximum=2.0, step=0.1, value=settings["pitch"])
        volume_slider = gr.Slider(label="Volume Gain (dB)", minimum=-10, maximum=10, step=1, value=settings["volume_gain"])
        threads_percent_slider = gr.Slider(label="Threads Percentage", minimum=1, maximum 100, step=1, value=settings["threads_percent"])
        
        update_button = gr.Button("Update Settings")
        update_status = gr.Textbox(label="Update Status", value="", interactive=False)

        update_button.click(
            fn=save_persistent_settings,
            inputs=[model_path_input, voice_model_input, speed_slider, pitch_slider, volume_slider, threads_percent_slider],
            outputs=update_status
        )

demo.launch(server_name="0.0.0.0", server_port=7860)

