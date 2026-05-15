import wave
import struct
import math
import subprocess
import tempfile
import os
import threading

_ENABLED = True


def _which(cmd: str) -> str | None:
    import shutil
    return shutil.which(cmd)


def _write_wav(path: str, freq: int, duration: float, volume: float = 0.5, sample_rate: int = 44100):
    n = int(sample_rate * duration)
    with wave.open(path, "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        for i in range(n):
            t = i / sample_rate
            fade = min(1.0, min(t, duration - t) / 0.01)  # 10ms fade in/out
            sample = int(32767 * volume * fade * math.sin(2 * math.pi * freq * t))
            f.writeframes(struct.pack("<h", sample))


def _play_windows(path: str):
    import winsound
    winsound.PlaySound(path, winsound.SND_FILENAME)
    try:
        os.unlink(path)
    except OSError:
        pass


def _play_async(freq: int, duration: float, volume: float = 0.5):
    global _ENABLED
    if not _ENABLED:
        return

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    try:
        _write_wav(tmp.name, freq, duration, volume)
    except Exception:
        _ENABLED = False
        return

    if os.name == "nt":
        threading.Thread(target=_play_windows, args=(tmp.name,), daemon=True).start()
        return

    player = _which("paplay") or _which("aplay")
    if not player:
        print("\a", end="", flush=True)
        return

    try:
        subprocess.Popen(
            [player, tmp.name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        _ENABLED = False


def play_error():
    """Low buzz — wrong word."""
    _play_async(freq=220, duration=0.18, volume=0.4)


def play_fixed():
    """Pleasant chime — problematic word typed correctly."""
    _play_async(freq=880, duration=0.15, volume=0.35)
