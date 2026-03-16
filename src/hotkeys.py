"""
SilentHUD - Global Hotkey Manager
Captures global keyboard shortcuts without stealing focus from other windows.
"""

import threading
from typing import Callable, Dict
import keyboard


class HotkeyManager:
    """
    Manages global hotkeys that work even when other applications have focus.
    Uses the 'keyboard' library which hooks at a lower level than Qt.
    """
    
    # Default hotkey bindings
    DEFAULT_BINDINGS = {
        'toggle': 'ctrl+shift+x',      # Toggle overlay visibility
        'capture': 'ctrl+shift+s',     # Capture screen + OCR
        'explain': 'ctrl+shift+e',     # Capture + Explain (Detailed)
        'panic': 'ctrl+shift+q',       # Kill Switch (Terminate App)
    }
    
    def __init__(self):
        self._bindings: Dict[str, str] = self.DEFAULT_BINDINGS.copy()
        self._callbacks: Dict[str, Callable] = {}
        self._running = False
        
        # Sniper Mode state
        self._sniper_timer: Optional[threading.Timer] = None
        self._sniper_mode_active = False
        
    def set_callback(self, action: str, callback: Callable):
        """
        Register a callback for a specific action.
        
        Args:
            action: One of 'toggle', 'capture', 'panic', 'sniper_start', 'sniper_end'
            callback: Function to call
        """
        self._callbacks[action] = callback
        
    def set_hotkey(self, action: str, hotkey: str):
        """Change the hotkey binding for an action."""
        if action not in self._bindings:
            # Allow custom actions for future extensibility
            self._bindings[action] = hotkey
        else:
            self._bindings[action] = hotkey
            
    def _on_shift_press(self, event):
        """Handle Shift key press."""
        if self._sniper_mode_active or (self._sniper_timer and self._sniper_timer.is_alive()):
            return

        # Start timer to trigger "Sniper Mode"
        self._sniper_timer = threading.Timer(0.4, self._enter_sniper_mode)
        self._sniper_timer.start()
        
    def _on_shift_release(self, event):
        """Handle Shift key release."""
        # Check if timer is running (user released before delay)
        if self._sniper_timer and self._sniper_timer.is_alive():
            self._sniper_timer.cancel()
            self._sniper_timer = None
            return

        # If in Sniper Mode, complete the action
        if self._sniper_mode_active:
            self._exit_sniper_mode()
            
    def _enter_sniper_mode(self):
        """Enter Sniper Mode (viewfinder visible)."""
        self._sniper_mode_active = True
        if 'sniper_start' in self._callbacks:
            self._callbacks['sniper_start']()
            
    def _exit_sniper_mode(self):
        """Exit Sniper Mode (capture and hide viewfinder)."""
        self._sniper_mode_active = False
        if 'sniper_end' in self._callbacks:
            self._callbacks['sniper_end']()
        
    def start(self):
        """Start listening for global hotkeys."""
        if self._running:
            return
            
        self._running = True
        
        # Register standard hotkeys
        for action, hotkey in self._bindings.items():
            if action in self._callbacks:
                keyboard.add_hotkey(
                    hotkey, 
                    self._callbacks[action],
                    suppress=False
                )
                
        # Custom binding for alternate panic
        # Custom binding for Clear Display (was alternate panic)
        keyboard.add_hotkey('ctrl+shift+z', self._callbacks.get('clear', lambda: None), suppress=False)
        
        # Register Right Alt monitoring (Spyglass mode)
        # Using 'right alt' avoids conflict with normal typing (Shift/Caps)
        keyboard.on_press_key('right alt', self._on_shift_press, suppress=False)
        keyboard.on_release_key('right alt', self._on_shift_release, suppress=False)
        # Also support Left Alt for user convenience
        keyboard.on_press_key('left alt', self._on_shift_press, suppress=False)
        keyboard.on_release_key('left alt', self._on_shift_release, suppress=False)
        
        # Register Right Ctrl monitoring (Audio mode)
        # DISABLED BY USER REQUEST
        # keyboard.on_press_key('right ctrl', lambda e: self._callbacks.get('audio_start', lambda: None)(), suppress=False)
        # keyboard.on_release_key('right ctrl', lambda e: self._callbacks.get('audio_end', lambda: None)(), suppress=False)
                
        print(f"[HotkeyManager] Hotkeys active:")
        for action, hotkey in self._bindings.items():
            print(f"  {hotkey.upper()} -> {action}")
            print(f"  RIGHT/LEFT ALT -> spyglass mode")
            
    def stop(self):
        """Stop listening for hotkeys."""
        if not self._running:
            return
            
        self._running = False
        keyboard.unhook_all_hotkeys()
        # Ensure we unhook specific key listeners too if needed, 
        # but unhook_all_hotkeys usually covers it. 
        # Explicitly unhooking 'shift' just in case or rely on unhook_all.
        print("[HotkeyManager] Hotkeys disabled")
        
    def is_running(self) -> bool:
        """Check if hotkey listener is active."""
        return self._running


# Convenience function for quick setup
def create_hotkey_manager(
    on_toggle: Callable = None,
    on_capture: Callable = None,
    on_panic: Callable = None,
    on_sniper_start: Callable = None,
    on_sniper_end: Callable = None,
    on_audio_start: Callable = None,


    on_audio_end: Callable = None,
    on_explain: Callable = None,
    on_clear: Callable = None
) -> HotkeyManager:
    """
    Create and configure a HotkeyManager with callbacks.
    """
    manager = HotkeyManager()
    
    if on_toggle: manager.set_callback('toggle', on_toggle)
    if on_capture: manager.set_callback('capture', on_capture)
    if on_panic: manager.set_callback('panic', on_panic)
    if on_sniper_start: manager.set_callback('sniper_start', on_sniper_start)
    if on_sniper_end: manager.set_callback('sniper_end', on_sniper_end)
    if on_audio_start: manager.set_callback('audio_start', on_audio_start)
    if on_audio_end: manager.set_callback('audio_end', on_audio_end)
    if on_explain: manager.set_callback('explain', on_explain)
    if on_clear: manager.set_callback('clear', on_clear)
        
    return manager
