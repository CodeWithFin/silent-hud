"""
SilentHUD - Transparent Overlay Window
A ghost window that sits on top of all applications without stealing focus.
"""

from PyQt6.QtWidgets import QMainWindow, QWidget, QLabel, QVBoxLayout, QApplication
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor, QPainter, QScreen


from PyQt6.QtWidgets import QMainWindow, QWidget, QLabel, QVBoxLayout, QApplication, QTextEdit
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui import QFont, QColor, QPainter, QScreen, QCursor


class HUDDisplay(QTextEdit):
    """Semi-transparent scrollable text display for AI responses (Rich Text)."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFrameStyle(0)
        
        # Base Widget Styling (Container)
        self.setStyleSheet("""
            QTextEdit {
                background-color: rgba(22, 22, 30, 0.96); /* Deep blue-grey */
                color: #c0caf5; /* Soft lavender-white */
                border-radius: 16px;
                padding: 25px;
                border: 1px solid rgba(118, 124, 157, 0.2); /* Subtle highlight */
                selection-background-color: #3d59a1;
            }
        """)
        
        # Modern Font Stack
        font = QFont("Sans Serif", 14)
        if "Roboto" in QFont.substitutions(): font = QFont("Roboto", 14)
        elif "Inter" in QFont.substitutions(): font = QFont("Inter", 14)
        elif "Segoe UI" in QFont.substitutions(): font = QFont("Segoe UI", 14)
        
        self.setFont(font)
        
        # Hide scrollbars but allow scrolling
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Initially hidden
        self.hide()
    
    def display_text(self, text: str):
        """Display text with Markdown rendering."""
        import markdown
        
        # Modern Dark Theme CSS
        css = """
        <style>
            body { 
                font-family: 'Inter', 'Roboto', 'Segoe UI', sans-serif; 
                line-height: 1.6; 
                color: #c0caf5;
                margin: 0;
            }
            h1, h2, h3 { 
                color: #7aa2f7; /* Soft Blue */
                margin-top: 15px;
                margin-bottom: 8px;
                font-weight: 600;
            }
            strong { color: #bb9af7; } /* Soft Purple */
            p { margin-bottom: 12px; }
            a { color: #7dcfff; text-decoration: none; }
            
            /* Modern Code Blocks */
            pre { 
                background-color: #1a1b26; /* Darker bg */
                color: #a9b1d6;
                padding: 15px; 
                border-radius: 8px; 
                margin: 15px 0;
                overflow-x: auto;
                border: 1px solid rgba(255, 255, 255, 0.05);
                font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
                font-size: 13px;
            }
            
            code { 
                font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace; 
                background-color: transparent;
                padding: 0px;
                color: #7dcfff; /* Bright Cyan for contrast without the boxy background */
            }
        </style>
        """
        
        # Convert Markdown to HTML
        html_content = markdown.markdown(
            text, 
            extensions=['fenced_code', 'tables', 'nl2br']
        )
        
        # Combine CSS and HTML
        full_html = f"{css}<body>{html_content}</body>"
        
        self.setHtml(full_html)
        self.show()
        # Scroll to top
        self.verticalScrollBar().setValue(0)
    
    def clear_text(self):
        """Clear and hide the display."""
        self.setPlainText("")
        self.hide()
        
    def scroll_content(self, delta: int):
        """Scroll content vertically."""
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.value() - delta)


class ViewfinderLabel(QLabel):
    """Visual selection box that follows the mouse."""
    
    def __init__(self, parent=None, width=400, height=200):
        super().__init__(parent)
        self.setFixedSize(width, height)
        # Glowing selection box
        self.setStyleSheet("""
            QLabel {
                background-color: rgba(122, 162, 247, 0.08); /* Stealthy but visible (8%) */
                border: 1px solid rgba(122, 162, 247, 0.15);  /* Very faint border */
                border-radius: 8px;
            }
        """)
        self.hide()

    def update_position(self, global_x, global_y):
        """Center the viewfinder on coordinates (handles global to local mapping)."""
        parent = self.parent()
        if parent:
            # Map global cursor coordinates to parent's local coordinate system
            local_pos = parent.mapFromGlobal(QPoint(global_x, global_y))
            x, y = local_pos.x(), local_pos.y()
        else:
            x, y = global_x, global_y
            
        # Adjust so (x,y) is the center of the widget
        new_x = x - (self.width() // 2)
        new_y = y - (self.height() // 2)
        self.move(new_x, new_y)

    def set_geometry(self, x, y, width, height):
        """Set position and size explicitly (Rubber Band)."""
        # Map global to local
        parent = self.parent()
        if parent:
            local_pos = parent.mapFromGlobal(QPoint(x, y))
            local_x, local_y = local_pos.x(), local_pos.y()
        else:
            local_x, local_y = x, y
            
        self.move(local_x, local_y)
        self.setFixedSize(width, height)

    def set_box_size(self, width, height):
        """Legacy resize logic."""
        self.setFixedSize(width, height)
        # We don't verify position here, update_position handles it



class GhostOverlay(QMainWindow):
    """
    Transparent full-screen overlay.
    """
    
    # ... (signals) ...
    display_response = pyqtSignal(str)
    clear_display = pyqtSignal()
    toggle_visibility = pyqtSignal()
    update_viewfinder = pyqtSignal(int, int) # New signal for mouse updates
    toggle_viewfinder = pyqtSignal(bool)     # New signal for show/hide
    scroll_display = pyqtSignal(int)         # New signal for scrolling
    show_status_signal = pyqtSignal(str, str)# Safe status updates
    resize_viewfinder_signal = pyqtSignal(int, int) # w, h
    update_viewfinder_geometry = pyqtSignal(int, int, int, int) # x, y, w, h
    
    def __init__(self):
        super().__init__()
        self._setup_ghost_window()
        self._setup_ui()
        self._connect_signals()
        
    def _setup_ghost_window(self):
        """Configure window flags for ghost behavior."""
        # Combine flags for stealth overlay
        flags = (
            Qt.WindowType.FramelessWindowHint |      # No title bar
            Qt.WindowType.WindowStaysOnTopHint |     # Always on top
            Qt.WindowType.ToolTip |                  # Treat as a tooltip (often ignored by screen shares)
            Qt.WindowType.WindowTransparentForInput  # Click-through on Linux
        )
        self.setWindowFlags(flags)
        
        # Enable transparency
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # Cover entire screen (all monitors)
        screen = QApplication.primaryScreen()
        if screen:
            # virtualGeometry() returns the geometry of the virtual desktop (all screens combined)
            geometry = screen.virtualGeometry()
            self.setGeometry(geometry)
        
        # Transparent background
        self.setStyleSheet("background: transparent;")
        
    def _setup_ui(self):
        """Create the HUD display elements."""
        # Central widget with transparent background
        central = QWidget()
        central.setStyleSheet("background: transparent;")
        self.setCentralWidget(central)
        
        # Viewfinder (direct child of central widget for absolute positioning)
        self.viewfinder = ViewfinderLabel(central)
        
        # Layout for positioning HUD elements
        layout = QVBoxLayout(central)
        layout.setContentsMargins(60, 60, 60, 60)
        
        # Status indicator (Floating Pill)
        self.status_label = QLabel("⚡ SilentHUD Active")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: rgba(26, 27, 38, 0.9);
                color: #7aa2f7;
                padding: 8px 16px;
                border-radius: 20px;
                font-family: 'Segoe UI', sans-serif;
                font-weight: 600;
                font-size: 12px;
                border: 1px solid rgba(118, 124, 157, 0.3);
            }
        """)
        self.status_label.setFixedWidth(180)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.hide()  # Hidden by default
        # User requested "not visible", so we will largely suppress this status pill.
        
        # Main response display (bottom-right corner)
        self.response_label = HUDDisplay()
        self.response_label.setFixedSize(600, 500) # Fixed size for scroll area
        
        # Add to layout
        layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()
        layout.addWidget(self.response_label, alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        
    def _connect_signals(self):
        """Connect signals for thread-safe updates."""
        self.display_response.connect(self._on_display_response)
        self.clear_display.connect(self._on_clear_display)
        self.toggle_visibility.connect(self._on_toggle_visibility)
        self.update_viewfinder.connect(self.viewfinder.update_position)
        self.toggle_viewfinder.connect(self._on_toggle_viewfinder)
        self.scroll_display.connect(self.response_label.scroll_content)
        self.show_status_signal.connect(self.show_status)
        self.resize_viewfinder_signal.connect(self.viewfinder.set_box_size)
        self.update_viewfinder_geometry.connect(self.viewfinder.set_geometry)
        
    def _on_display_response(self, text: str):
        """Handle display response signal."""
        self.response_label.display_text(text)
        self.status_label.show()
        
    def _on_clear_display(self):
        """Handle clear display signal (panic button)."""
        self.response_label.clear_text()
        self.status_label.hide()
        self.viewfinder.hide()
        
    def _on_toggle_visibility(self):
        """Toggle overlay visibility."""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            
    def _on_toggle_viewfinder(self, visible: bool):
        """Show or hide the viewfinder."""
        if visible:
            self.viewfinder.show()
        else:
            self.viewfinder.hide()

    def show_status(self, message: str, color: str = "rgba(40, 167, 69, 0.7)"):
        """Show a status message briefly."""
        self.status_label.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                padding: 5px 10px;
                border-radius: 5px;
                font-size: 11px;
            }}
        """)
        self.status_label.setText(message)
        # User requested "not visible". We log to console instead.
        print(f"[STATUS] {message}")
        # self.status_label.show() # Disabled for stealth
        
        # Auto-hide after 3 seconds if no response displayed
        if not self.response_label.isVisible():
            QTimer.singleShot(3000, lambda: self.status_label.hide() if not self.response_label.isVisible() else None)
