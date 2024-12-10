import network
import time

# Configura el Wi-Fi en modo estación
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# Obtén la dirección MAC
mac = wlan.config('mac')  # Retorna una tupla en bytes
while True:
    print("MAC Address:", ':'.join(['{:02X}'.format(b) for b in mac]))
    time.sleep(1)

    #A0:B7:65:0F:6C:48
