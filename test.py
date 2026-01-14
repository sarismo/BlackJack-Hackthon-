

import socket
import time

print("Hello, Python!")
print("Hello, Python!")
print("This is a test file.")
# Set up UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

broadcast_address = ('10.38.51.255', 37020)  # Port 37020 can be any number above 1024

while True:
    message = "Hello from PC 1!"
    sock.sendto(message.encode(), broadcast_address)
    print(f"Sent: {message}")
    time.sleep(2)  # Send every 2 seconds