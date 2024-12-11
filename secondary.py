import time
from threading import Thread

import wifi_manager
from sensor import UltrasonicSensor

wifi = wifi_manager.Wifi(send_address=b"1NODE", receive_address=b"2NODE")  # Diceccion de recepcion y emision
sensor = UltrasonicSensor(26, 14)


def main():
    wifi.listener.start_listening()
    while True:
        if wifi.listener.response() == 'distance':
            wifi.send_message('ok')
            wifi.get_distance.receiver()
            wifi.listener.start_listening()

        elif wifi.listener.response() == 'start':
            wifi.send_message('ok')
            break
        elif wifi.listener.response() == 'stop':
            wifi.listener.start_listening()
        time.sleep(0.1)

    sensor_thread = Thread(target=sensor.wait_for_detection)
    sensor_thread.start()

    wifi.listener.start_listening()
    while True:
        time.sleep(0.1)
        if not sensor_thread.is_alive():
            break

        elif wifi.listener.response() == 'distance':
            wifi.get_distance.receiver()
            wifi.listener.start_listening()

        elif wifi.listener.response() == 'stop':
            sensor.stop()
            return

    sensor_thread.join()
    wifi.send_message('end')


if __name__ == "__main__":
    while True:
        try:
            main()
        finally:
            wifi.listener.stop()
