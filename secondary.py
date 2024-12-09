import time
from threading import Thread

import wifi_manager
import sensor

wifi = wifi_manager.Wifi(b"amongus", b"susimpostor")  # Diceccion de recepcion y emision


def main():
    wifi.listener.start_listening()
    while True:
        if wifi.listener.response() == 'distance':
            wifi.receiver_get_distance()
            wifi.listener.start_listening()

        elif wifi.listener.response() == 'start':
            break
        time.sleep(0.1)

    sensor_thread = Thread(target=sensor.wait_person, daemon=True)
    sensor_thread.start()

    wifi.listener.start_listening()
    while True:
        time.sleep(0.1)
        if not sensor_thread.is_alive():
            break

        elif wifi.listener.response() == 'distance':
            wifi.receiver_get_distance()
            wifi.listener.start_listening()

    sensor_thread.join()
    wifi.send_message('end')


if __name__ == "__main__":
    while True:
        try:
            main()
        finally:
            wifi.listener.stop()
