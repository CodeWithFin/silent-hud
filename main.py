#!/usr/bin/env python3
"""
SilentHUD - Main Entry Point
An accessibility overlay for silent, visual AI assistance.

Usage:
    sudo python main.py

Note: Requires sudo for global keyboard hooks on Linux.

Hotkeys:
    Ctrl+Shift+X   - Toggle overlay visibility
    Ctrl+Shift+S   - Capture screen at cursor + OCR + get AI response
    Ctrl+Shift+W   - Kill Switch (Terminate App)
"""

import sys
import os
import threading
import setproctitle # Process Disguise

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtCore import QTimer, QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication
import keyboard
import mouse

from src.overlay import GhostOverlay
from src.hotkeys import create_hotkey_manager
from src.ocr import capture_and_ocr
from src.llm import answer_captured_text, answer_captured_image, answer_audio_question
from PyQt6.QtGui import QCursor, QImage
from src.audio import get_recorder

class SilentHUD(QObject):
    """
    Main application controller.
    """
    
    # ... (signals) ...
    start_timer_signal = pyqtSignal()
    stop_timer_signal = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        
        # 1. PROCESS DISGUISE (Anti-Snooping)
        # Rename the process so it looks like a system daemon in 'top'
        try:
            setproctitle.setproctitle("system-audio-helper") 
        except Exception as e:
            print(f"Disguise failed: {e}")
            
        self.app = QApplication(sys.argv)
        self.overlay = GhostOverlay()
        # Initialization
        self.hotkey_manager = None
        self._processing = False
        self._is_recording = False # Audio lock flag
        
        # Timer for updating viewfinder position
        self.mouse_timer = QTimer()
        self.mouse_timer.timeout.connect(self._update_mouse_position)
        self.mouse_timer.setInterval(20)  # 50fps update
        
        # Connect signals to timer slots
        self.start_timer_signal.connect(self.mouse_timer.start)
        self.stop_timer_signal.connect(self.mouse_timer.stop)
        
        self._is_sniper_active = False # Track sniper state
        
        # Viewfinder dimensions (default)
        self.viewfinder_width = 400
        self.viewfinder_height = 200
        
        # Selection State (Rubber Band)
        self._is_selecting = False
        self._selection_start = None # (x, y)
        self._selection_rect = None  # (x, y, w, h)
        
        # Global mouse hook
        mouse.hook(self._on_mouse_event)
        
    def _on_mouse_event(self, event):
        """Handle global mouse events (Scrolling & Selection)."""
        # Handle Scroll (Still used for HUD text scrolling)
        if isinstance(event, mouse.WheelEvent):
            delta = int(event.delta * 40)
            is_modifier_pressed = False
            try:
                # Support Alt Key for scrolling (Windows key removed)
                is_modifier_pressed = keyboard.is_pressed('alt') or keyboard.is_pressed('left alt') or keyboard.is_pressed('right alt')
            except ValueError:
                pass # Key not mapped
            except Exception:
                pass # Generic error
                
            if is_modifier_pressed and not self._is_selecting:
                self.overlay.scroll_display.emit(delta)
                
        # Handle Rubber Band Selection (Sniper Mode + Left Click)
        elif self._is_sniper_active:
            if isinstance(event, mouse.ButtonEvent) and event.button == 'left':
                if event.event_type == 'down':
                    # Start Selection
                    self._is_selecting = True
                    self._selection_start = (QCursor.pos().x(), QCursor.pos().y())
                    self._selection_rect = None # Reset
                elif event.event_type == 'up':
                    # Stop Selection (Lock it)
                    self._is_selecting = False
            
            elif isinstance(event, mouse.MoveEvent) and self._is_selecting and self._selection_start:
                # Dragging
                curr_x, curr_y = event.x, event.y
                start_x, start_y = self._selection_start
                
                # Calculate Rect
                x = min(start_x, curr_x)
                y = min(start_y, curr_y)
                w = abs(curr_x - start_x)
                h = abs(curr_y - start_y)
                
                # Minimum size (avoid tiny dots)
                if w > 5 and h > 5:
                    self._selection_rect = (x, y, w, h)
                    self.overlay.update_viewfinder_geometry.emit(x, y, w, h)

    def _on_audio_start(self):
        """Right Ctrl Pressed: Start Recording"""
        if self._processing or self._is_recording: return
        
        self._is_recording = True
        print("[Main] Audio Start")
        # Distinct Visual for Audio
        self.overlay.show_status_signal.emit("🎤 LISTENING...", "rgba(255, 0, 100, 0.8)") # Bright Red/Pink
        self.overlay.display_response.emit("🎤 Listening via Mic...")
        get_recorder().start_recording()

    def _on_audio_end(self):
        """Right Ctrl Released: Stop & Transcribe"""
        if not self._is_recording: return
        
        print("[Main] Audio End")
        result_file = get_recorder().stop_recording()
        self._is_recording = False # Release lock BEFORE processing starts (so we can process)
        
        if result_file:
            self._processing = True
            self.overlay.display_response.emit("🧠 Processing Audio...")
            
            # Start processing thread
            thread = threading.Thread(target=self._process_audio_thread, args=(result_file,), daemon=True)
            thread.start()
            
    def _process_audio_thread(self, audio_path):
        """Async audio processing."""
        try:
            self.overlay.show_status_signal.emit("⚡ Transcribing...", "rgba(40, 167, 69, 0.7)")
            response = answer_audio_question(audio_path)
            self.overlay.display_response.emit(response)
        except Exception as e:
            print(f"Audio Error: {e}")
            self.overlay.show_status_signal.emit("❌ Audio Error", "rgba(220, 53, 69, 0.7)")
        finally:
            self._processing = False

    def _update_mouse_position(self):
        """Update viewfinder position to follow mouse (Only if NOT selecting)."""
        if self._is_selecting:
            return
            
        # If we have a locked selection (user dragged and released), don't move it
        if self._selection_rect and not self._is_selecting:
            return
            
        # Default Spyglass Behavior (Center on cursor)
        pos = QCursor.pos()
        self.overlay.update_viewfinder.emit(pos.x(), pos.y())
        
    def _on_sniper_start(self):
        """Enter Sniper Mode."""
        self._is_sniper_active = True
        self._selection_rect = None # Reset selection
        self.overlay.toggle_viewfinder.emit(True)
        self.start_timer_signal.emit()
        
    def _on_sniper_end(self):
        """Exit Sniper Mode and Capture."""
        self._is_sniper_active = False
        self.stop_timer_signal.emit()
        self.overlay.toggle_viewfinder.emit(False)
        self._on_capture()
        
    def _on_toggle(self):
        """Handle toggle visibility hotkey."""
        self.overlay.toggle_visibility.emit()
        
    def _on_capture_explain(self):
        """Handle Capture + Explain (Ctrl+Shift+E)."""
        self._on_capture(force_explain=True)

    def _on_capture(self, force_explain=False):
        """Handle capture hotkey - main workflow."""
        if self._processing or self._is_recording:
            print("[Main] Capture ignored (Busy or Recording)")
            return
        self._processing = True
        
        self.overlay.show_status_signal.emit("📸 Capturing...", "rgba(0, 123, 255, 0.7)")
        
        def process():
            try:
                # Determine Capture Region
                if self._selection_rect:
                    # Use explicit selection
                    x, y, w, h = self._selection_rect
                    print(f"[DEBUG] Using Selection: {x, y, w, h}")
                else:
                    # User just clicked capture without selecting: Use default center box
                    cursor = QCursor.pos()
                    w, h = self.viewfinder_width, self.viewfinder_height
                    x = cursor.x() - (w // 2)
                    y = cursor.y() - (h // 2)
                    print(f"[DEBUG] Using Default Center: {x, y, w, h}")

                # Capture
                screen = QApplication.primaryScreen()
                if not screen: raise Exception("No screen")
                
                pixmap = screen.grabWindow(0, x, y, w, h)
                if pixmap.isNull(): raise Exception("Capture failed")
                
                # Process Image
                image = pixmap.toImage()
                from PIL import Image
                
                # Convert to PIL
                buffer = image.bits().asstring(image.sizeInBytes())
                if image.format() == QImage.Format.Format_RGB32 or image.format() == QImage.Format.Format_ARGB32:
                    pil_img = Image.frombuffer("RGBA", (image.width(), image.height()), buffer, "raw", "BGRA").convert("RGB")
                else:
                    from PyQt6.QtCore import QBuffer, QIODevice
                    ba = QBuffer()
                    ba.open(QIODevice.OpenModeFlag.ReadWrite)
                    image.save(ba, "PNG")
                    import io
                    pil_img = Image.open(io.BytesIO(ba.data().data()))
                
                # PRIMARY: GROQ (Text)
                self.overlay.show_status_signal.emit("⚡ Analyzing...", "rgba(40, 167, 69, 0.7)")
                
                captured_text = capture_and_ocr(image=pil_img)
                response = None
                
                # HYBRID STRATEGY:
                # User prefers "context awareness" (Vision) over raw text.
                # We will prioritize Vision unless the capture is tiny/empty.
                
                # Check for "Select only one" or similar MCQ markers to FORCE vision
                is_mcq = "select" in captured_text.lower() or "?" in captured_text or "following" in captured_text.lower()
                
                if not is_mcq and captured_text and len(captured_text.strip()) > 100 and "code" in captured_text.lower():
                    # If it's a huge block of code without a question, Text-Only might be cleaner/faster.
                    print(f"[DEBUG] Text Code Block: {captured_text[:50]}...")
                    response = answer_captured_text(captured_text)
                else:
                    print("[DEBUG] Using Vision (Llama 4 Scout) for Context Awareness...")
                    self.overlay.show_status_signal.emit("👁️ Vision Analysis...", "rgba(108, 117, 225, 0.7)")
                    
                    if force_explain:
                        prompt = """
                        **Vision Analyst - EXPLAIN MODE**
                        
                        The user asked for a detailed explanation.
                        - **Break it down:** Explain the reasoning step-by-step.
                        - **Why?** Explain why the answer is correct and why others are wrong.
                        - **Context:** Provide background information.
                        
                        **Style:** Detailed, educational, clear.
                        """
                    else:
                        # Standard "Direct" Prompt
                        prompt = """
                        **General Purpose Vision Analyst**
                        
                        Analyze the image and user's intent:
                        - **Multiple Choice Question?** Output **ONLY** the correct option letter and text. **NO EXPLANATION.** **NO REASONING.** Example: "Option B) 42".
                        - **Question?** Answer it directly and knowledgeably.
                        - **Code/Error?** Fix it or explain it. Use markdown code blocks.
                        - **Translation?** Translate efficiently.
                        - **General Image?** Describe what is shown or answer specific queries about it.
                        
                        **Style:** Strict, concise, direct. No conversational filler.
                        """
                    
                    response = answer_captured_image(pil_img, prompt)

                self.overlay.display_response.emit(response)
                
            except Exception as e:
                print(f"Error: {e}")
                self.overlay.show_status_signal.emit(f"❌ Error: {str(e)[:20]}", "rgba(220, 53, 69, 0.7)")
            finally:
                self._processing = False
                
        thread = threading.Thread(target=process, daemon=True)
        thread.start()
        
    def _on_clear(self):
        """Handle Clear Display (Ctrl+Shift+Z)."""
        print("[Main] Clearing Display")
        self.overlay.clear_display.emit()
        
    def _on_panic(self):
        """
        HANDLE PANIC BUTTON (Ctrl+Shift+W).
        ULTIMATE STEALTH: Kill the process immediately.
        No trace left.
        """
        print("🚨 PANIC INITIATED. TERMINATING PROCESS.")
        # Stop listeners (optional, but good practice before death)
        if self.hotkey_manager:
            self.hotkey_manager.stop()
        mouse.unhook_all()
        
        # KILL SWITCH
        os._exit(0) # Hard exit, no cleanup handlers ran, vanishes instantly.
        
    def run(self):
        """Start the application."""
        print("\n" + "="*50)
        print("  SilentHUD - Accessibility Overlay")
        print("="*50)
        print("\nHotkeys:")
        print("  Ctrl+Shift+X   - Toggle visibility")
        print("  Ctrl+Shift+S   - Capture + OCR + AI (Direct Answer)")
        print("  Ctrl+Shift+E   - Capture + Explain (Detailed)")
        print("  Hold Right Alt - Spyglass Mode (Preview Region)")
        print("  Hold Right Ctrl- Listen to Question (Audio)")
        print("  Alt + Scroll   - Scroll AI Response")
        print("  Ctrl+Shift+Z   - Clear Display (Hide Text)")
        print("  Ctrl+Shift+Q   - Kill Switch (Terminate App)")
        print("\nPress Ctrl+C in terminal to exit.")
        print("="*50 + "\n")
        
        # Create and start hotkey manager
        self.hotkey_manager = create_hotkey_manager(
            on_toggle=self._on_toggle,
            on_capture=self._on_capture,
            on_panic=self._on_panic,
            on_sniper_start=self._on_sniper_start,
            on_sniper_end=self._on_sniper_end,
            on_audio_start=self._on_audio_start,
            on_audio_end=self._on_audio_end,
            on_explain=self._on_capture_explain,
            on_clear=self._on_clear
        )
        self.hotkey_manager.start()
        
        # Show overlay (starts hidden by default, use toggle to show)
        self.overlay.show()
        
        # Run Qt event loop
        try:
            sys.exit(self.app.exec())
        finally:
            if self.hotkey_manager:
                self.hotkey_manager.stop()
            mouse.unhook_all()


def main():
    """Entry point."""
    # Check if running as root (required for global keyboard hooks on Linux)
    if os.name == 'posix' and os.geteuid() != 0:
        print("⚠️  Warning: On Linux, global keyboard hooks require root access.")
        print("   Run with: sudo ./venv/bin/python main.py")
        print()
        
    hud = SilentHUD()
    hud.run()


if __name__ == "__main__":
    main()
