"""
SilentHUD - Audio Recorder Module
Handles microphone capture and WAV file generation for Whisper ASR.
"""

import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import tempfile
import os
import threading

class AudioRecorder:
    def __init__(self, sample_rate=16000):
        self.fs = sample_rate
        self.recording = False
        self.audio_data = []
        self.stream = None
        self.filename = os.path.join(tempfile.gettempdir(), "silenthud_audio.wav")
        self._lock = threading.Lock()

    def start_recording(self):
        """Start capturing audio from default microphone."""
        with self._lock:
            if self.recording: return
            self.recording = True
            self.audio_data = [] # Reset buffer
            
            # Start stream (blocking=False)
            try:
                self.stream = sd.InputStream(
                    callback=self._callback, 
                    channels=1, 
                    samplerate=self.fs,
                    dtype='float32'
                )
                self.stream.start()
                print("[Audio] Recording started...")
            except Exception as e:
                print(f"[Audio] Error starting stream: {e}")
                self.recording = False

    def _callback(self, indata, frames, time, status):
        """Callback for sounddevice stream."""
        if status:
            print(f"[Audio] Status: {status}")
        with self._lock:
            if self.recording:
                self.audio_data.append(indata.copy())

    def stop_recording(self) -> str:
        """Stop recording and save to WAV. Returns filepath."""
        with self._lock:
            if not self.recording: return None
            self.recording = False
        
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            print("[Audio] Recording stopped.")

        # Save to file
        with self._lock:
            if not self.audio_data:
                print("[Audio] No data captured.")
                return None
            
            recording = np.concatenate(self.audio_data, axis=0)
            
        # Write WAV (scipy expects float32 to be -1.0 to 1.0, sounddevice gives float32)
        wav.write(self.filename, self.fs, recording)
        return self.filename

# Global instance
_recorder = None

def get_recorder():
    global _recorder
    if _recorder is None:
        _recorder = AudioRecorder()
    return _recorder
