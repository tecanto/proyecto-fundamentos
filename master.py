import time
from threading import Thread

import esp_now_manager
import wifi_manager
from sensor import UltrasonicSensor

sensor = UltrasonicSensor(26, 14)
wifi = wifi_manager.Wifi(send_address=b"1NODE", receive_address=b"2NODE")  # Diceccion de recepcion y emision
cono_mac = '34:5F:45:A9:4C:CC'
peer_mac = bytes(int(x, 16) for x in cono_mac.split(':'))
esp_now = esp_now_manager.ESPNow(peer_mac)  # Direccion mac del control
running = False


def esp_now_listener():
    global running
    while True:
        time.sleep(0.1)
        response = esp_now.get_message()
        if response == 'start':
            time.sleep(0.2)
            esp_now.send_message('ok')
            running = True
            break

        if response == 'distance':
            if not wifi.send_message('distance'):
                esp_now.send_message("1")  # si el segundo cono no esta encendido mandar una distancia falsa

            response = listen_wifi_timeout(0.7)
            if response != 'ok':
                continue

            distance = wifi.get_distance.transmitter()

            if distance is None:
                esp_now.send_message("1")  # si no hubo respuesta mandar una distancia falsa

            esp_now.send_message(str(distance))

        if response == 'stop':
            running = False


def listen_wifi_timeout(timeout: float) -> str:
    response = None
    wifi.listener.start_listening()
    init_t = time.process_time()
    while time.process_time() - init_t < timeout:
        response = wifi.listener.response()
    if response:
        return response


def wait_for_sensor():
    sensor_wait_thread = Thread(target=sensor.wait_for_detection)
    sensor_wait_thread.start()
    while sensor_wait_thread.is_alive():
        if not running:
            sensor.stop()
            break
        time.sleep(0.1)
    sensor_wait_thread.join()


def main():
    while not running:
        time.sleep(0.1)

    wait_for_sensor()

    wifi.send_message('start')
    response = listen_wifi_timeout(0.7)
    if response != 'ok' and running:
        esp_now.send_message("1")  # si no esta encendido el segundo cono, mandar un dato falso al control

    if not running:
        return

    stages_init_time: float = time.process_time()
    wifi.listener.start_listening()
    while True:
        if wifi.listener.response():
            break

        time.sleep(0.1)

    stage_one_end_time = time.process_time()
    if not running:
        return
    esp_now.send_message(str((stages_init_time - stage_one_end_time) // 1))  # mandar el tiempo de la etapa 1

    if not running:
        return

    wait_for_sensor()
    second_stage_end_time = time.process_time()

    if not running:
        return

    esp_now.send_message(str((stages_init_time - second_stage_end_time) // 1))


if __name__ == "__main__":
    listener_thread = Thread(target=esp_now_listener)
    listener_thread.start()
    while True:
        print("a")
        try:
            main()
        finally:
            wifi.send_message('stop')
            running = False
            wifi.listener.stop()
