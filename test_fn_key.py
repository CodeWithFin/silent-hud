import keyboard
import time

print("Press the 'Fn' key now (you have 5 seconds)...")
start = time.time()
found = False

def on_key(event):
    global found
    print(f"Key detected: {event.name} ({event.scan_code})")
    if event.name.lower() == 'fn' or event.name.lower() == 'unknown':
        found = True

keyboard.hook(on_key)

while time.time() - start < 5:
    time.sleep(0.1)
    
keyboard.unhook_all()

if not found:
    print("\n❌ 'Fn' key NOT detected. It might be handled by hardware.")
    print("Try keys like: Right Alt, Right Ctrl, Menu, PageUp/Down")
else:
    print("\n✅ 'Fn' key detected!")
