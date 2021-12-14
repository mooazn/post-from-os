import time
from pynput.mouse import Controller
import random

# Useful script to run if get_collection_assets.py is running. You can probably have your laptop on, but I
# couldn't figure out a way to do that for my laptop and I was too lazy find a way to do it so I resulted in doing this.

mouse = Controller()

while True:
    prev = mouse.position
    x = random.randint(1, 256)
    y = random.randint(1, 256)
    mouse.position = (x, y)
    print(f'Moved from {prev} to {mouse.position}')
    time.sleep(60)
