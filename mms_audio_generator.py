import os, gc, torch
import numpy as np
from transformers import pipeline
from pydub import AudioSegment
import soundfile as sf
from accelerate.utils import release_memory   

# Check if CUDA is available and set device accordingly
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
DEVICE_INDEX = 0 if torch.cuda.is_available() else -1

def load_mms_model():
    model_name = "facebook/mms-tts-ben"
    
    return pipeline(
        task="text-to-speech",
        model=model_name,
        device=DEVICE_INDEX
    )

def save_mp3_pydub(audio_f32: np.ndarray, sr: int, dst_path: str,
                   bitrate: str = "128k"):
    """
    audio_f32 : 1‑D float32 array in the range −1…1
    sr        : sample‑rate returned by the pipeline (16 000 for MMS)
    dst_path  : target filename, e.g. 'clip_01.mp3'
    """
    # 1️⃣  Convert −1…1 float to 16‑bit PCM
    pcm_int16 = (audio_f32 * 32767).astype(np.int16)

    # 2️⃣  Wrap in a PyDub segment (no intermediary file)
    seg = AudioSegment(
        pcm_int16.tobytes(),        # raw data
        frame_rate=sr,
        sample_width=2,             # 16‑bit
        channels=1
    )

    # 3️⃣  Encode straight to MP3
    seg.export(dst_path, format="mp3", bitrate=bitrate)


def generate_mms_voice(text, audio_folder, index, tts_pipe):
    if not text or not text.strip():
        print(f"[WARNING] Empty text for index {index}, returning 1s silence.")
        return AudioSegment.silent(duration=1000)

    audio_path = os.path.join(audio_folder, f"mms_{index}.mp3")

    wav_dict = tts_pipe(text)          # MMS pipeline output
    audio = wav_dict["audio"].astype("float32")   # ensure f32
    sr    = wav_dict["sampling_rate"]

    save_mp3_pydub(audio, sr, audio_path)  

    return AudioSegment.from_file(audio_path)


def release_tts(tts_pipe):
    """
    Explicitly free GPU memory after you're done.
    """
    if hasattr(tts_pipe, "model"):
        # 1️⃣  Let Accelerate wipe GPU/CPU shards in a backend‑aware way
        release_memory(tts_pipe.model)        # does gc.collect + empty_cache  :contentReference[oaicite:0]{index=0}

    # 2️⃣  Remove the pipeline wrapper itself
    del tts_pipe
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.ipc_collect()              # cleans CUDA IPC handles
        torch.cuda.empty_cache()              # returns VRAM to the driver