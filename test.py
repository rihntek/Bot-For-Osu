from pynput import keyboard

def print_q(key):
    if key == keyboard.Key.esc:
        return False
    if key.char == 'q':
        print('q')

with keyboard.Listener(on_press=print_q) as listener:
    listener.join()

