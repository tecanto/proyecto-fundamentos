import time
from threading import Thread

import esp_now_manager
import wifi_manager
import sensor

wifi = wifi_manager.Wifi(b"amongus", b"susimpostor")  # Diceccion de recepcion y emision
esp_now = esp_now_manager.ESPNow(b"hawktuah")  # Direccion mac del control
stop_code = False


def stop_program_listener():
    def listen_for_stop():
        global stop_code
        esp_now.listener.start_listening()
        while True:
            response = esp_now.listener.response()
            if response == 'stop':
                stop_code = True
            elif response is not None:
                esp_now.listener._response = response
    listener_thread = Thread(target=listen_for_stop, daemon=True)
    listener_thread.start()


def main():
    esp_now.listener.start_listening()
    while True:
        if esp_now.listener.response() == 'start':
            time.sleep(0.2)
            esp_now.send_message('ok')
            break

        if esp_now.listener.response() == 'distance':
            time.sleep(0.2)

            if not wifi.send_message('distance'):
                esp_now.send_message("1")  # si el segundo cono no esta encendido mandar una distancia falsa

            distance = wifi.transmitter_get_distance()

            if distance is None:
                esp_now.send_message("1")  # si no hubo respuesta mandar una distancia falsa

            esp_now.send_message(str(distance))
            esp_now.listener.start_listening()

        if stop_code or esp_now.listener.response() == 'stop':
            return

        time.sleep(0.1)
    sensor.wait_person()

    second_esp_alive: bool = wifi.send_message('start')
    stages_init_time: float = time.process_time()

    if second_esp_alive:
        wifi.listener.start_listening()
        while True:
            if wifi.listener.response():
                break
            if stop_code:
                return
            time.sleep(0.1)

        stage_one_end_time = time.process_time()
        esp_now.send_message(str((stages_init_time - stage_one_end_time) // 1))  # mandar el tiempo de la etapa 1
    else:
        esp_now.send_message("1")  # si no esta encendido el segundo cono, mandar un dato falso al control

    sensor.wait_person()
    second_stage_end_time = time.process_time()
    esp_now.send_message(str((stages_init_time - second_stage_end_time) // 1))


if __name__ == "__main__":
    stop_program_listener()
    while True:
        try:
            main()
        finally:
            stop_code = False
            wifi.listener.stop()
            esp_now.listener.stop()
