import time
from threading import Thread

import esp_now_manager
import wifi_manager
from sensor import UltrasonicSensor

sensor = UltrasonicSensor(26, 14)
wifi = wifi_manager.Wifi(b"amongus", b"susimpostor")  # Diceccion de recepcion y emision
esp_now = esp_now_manager.ESPNow(b"hawktuah")  # Direccion mac del control
running = False


def esp_now_listener():
    global running
    while True:
        response = esp_now.get_message()
        if response == 'start':
            time.sleep(0.2)
            esp_now.send_message('ok')
            running = True
            break

        if response == 'distance':
            time.sleep(0.2)

            if not wifi.send_message('distance'):
                esp_now.send_message("1")  # si el segundo cono no esta encendido mandar una distancia falsa

            distance = wifi.get_distance.transmitter()

            if distance is None:
                esp_now.send_message("1")  # si no hubo respuesta mandar una distancia falsa

            esp_now.send_message(str(distance))

        if response == 'stop':
            running = False


def main():
    while not running:
        time.sleep(0.1)

    sensor.wait_for_detection()

    second_esp_alive: bool = wifi.send_message('start')
    stages_init_time: float = time.process_time()

    if not running:
        return

    if second_esp_alive:
        wifi.listener.start_listening()
        while True:
            if wifi.listener.response():
                break

            time.sleep(0.1)

        stage_one_end_time = time.process_time()
        esp_now.send_message(str((stages_init_time - stage_one_end_time) // 1))  # mandar el tiempo de la etapa 1
    else:
        esp_now.send_message("1")  # si no esta encendido el segundo cono, mandar un dato falso al control

    if not running:
        return

    sensor.wait_for_detection()
    second_stage_end_time = time.process_time()

    if not running:
        return

    esp_now.send_message(str((stages_init_time - second_stage_end_time) // 1))


if __name__ == "__main__":
    listener_thread = Thread(target=esp_now_listener, daemon=True)
    listener_thread.start()
    while True:
        try:
            main()
        finally:
            running = False
            wifi.listener.stop()
