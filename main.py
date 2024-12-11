import time
import random
from threading import Thread
from machine import I2C, Pin
import i2c_lcd
import espnow
from network import WLAN, STA_IF


def pad_text(text: str):
    padding = ' ' * ((16 - len(text)) // 2)
    return padding + text + padding


def separate_text(*text: str):
    total_len = len(''.join(text))
    if total_len >= 16:
        return ''.join(text)

    separation = ' ' * ((16 - total_len) // (len(text) - 1))
    return separation.join(text)


def wait_release():
    while any(button.value() == 0 for button in buttons.values()):
        time.sleep(0.1)


def get_input(*excluded_buttons: int) -> int:
    while True:
        for btn_id, button in buttons.items():
            if button.value() == 0 and btn_id not in excluded_buttons:
                wait_release()
                return btn_id
        time.sleep(0.1)


def home():
    global overwrite_distance
    lcd.clear()

    lcd.move(0, 0)
    lcd.write(pad_text('HOME'))

    lcd.move(0, 1)
    lcd.write(separate_text('start', 'config'))

    button_input = get_input(0, 2)

    if button_input == 1:
        measure()

    if button_input == 3:
        config()


class EspNowListenStages:
    def __init__(self, timer_screen: 'LcdTimer'):
        self.timer_screen = timer_screen
        self.running: bool = False
        self.paused_time: int = 0
        self.second_stage = False
        self.thread = None

    def listen_for_stage_results(self):
        self.running = True

        _, response = esp_now.recv()
        if not self.running:
            return
        self.timer_screen.first_timer_running = False
        if response and response.isdigit():
            self.timer_screen.first_timer = int(response) - self.paused_time

        _, response = esp_now.recv()
        if not self.running:
            return
        self.timer_screen.second_timer_running = False
        if response and response.isdigit():
            self.timer_screen.second_timer = int(response) - self.paused_time

    def start(self):
        Thread(target=self.listen_for_stage_results).start()

    def join(self):
        if self.thread and self.thread.is_alive():
            self.thread.join()


def measure():
    distance: int = get_distance() if not overwrite_distance else overwrite_distance
    distance = max(1, min(distance, 99))

    esp_now.send(peer_mac, 'start'.encode())
    _, response = esp_now.recv()
    if not response == 'ok':
        return

    timer_screen = LcdTimer(lcd)
    timer_screen.distance = str(distance)

    listener = EspNowListenStages(timer_screen)
    listener.start()

    init_paused: int = 0
    paused_time: int = 0
    running: bool = True
    while listener.thread.is_alive():
        button_input = get_input(0, 1)
        if button_input == 2:
            timer_screen.first_timer_running = not running
            timer_screen.second_timer_running = not running
            running = not running
            if running:
                paused_time = paused_time + time.process_time() - init_paused if init_paused else 0
            init_paused = int(time.process_time() // 1)
        if button_input == 3:
            esp_now.send(peer_mac, 'stop'.encode())
            timer_screen.first_timer_running = False
            timer_screen.second_timer_running = False
            break

    get_input(2, 3)
    timer_screen.stop()


def config():
    global overwrite_distance
    time.sleep(0.2)
    lcd.clear()

    lcd.move(0, 0)
    lcd.write('Distance')

    lcd.move(0, 1)
    lcd.write(separate_text('select', 'up', 'down'))

    button_input = get_input()

    if button_input == 0:
        return

    if button_input == 1:
        overwrite_distance = distance_config_menu.start()

    if button_input == 2:
        config()

    if button_input == 3:
        config()


def get_distance():
    esp_now.send(peer_mac, 'distance'.encode())

    _, response = esp_now.recv()
    distance = int(response) if response and response.isdigit() else 1

    distance = max(1, min(distance, 99))
    return distance


class DistanceConfigMenu:
    def __init__(self, lcd_i2c: 'i2c_lcd.LCD'):
        self.lcd = lcd_i2c

        self.selected_type = 0

        self.distance: int = 1
        self.manual_distance: int = self.distance

    def start(self):
        self.distance = get_distance()
        self.auto()
        if self.selected_type == 1:
            return self.manual_distance

    def auto(self):
        self.lcd.clear()

        self.lcd.move(0, 0)
        self.lcd.write(separate_text(f'auto: {self.distance}', '*' if self.selected_type == 0 else ''))
        self.lcd.move(0, 1)
        self.lcd.write(separate_text('Select', 'up', 'down'))

        button_input = get_input(1 if not self.selected_type == 0 else None)

        # if button_input == 1  End the config Menu

        if button_input == 1:
            self.selected_type = 0

        if button_input == 2:
            new_distance = get_distance()
            if new_distance is not None and new_distance != 1:
                self.distance = new_distance

        if button_input == 3:
            self.manual()

    def manual(self):
        self.lcd.clear()

        self.lcd.move(0, 0)
        self.lcd.write(separate_text('manual', '*' if self.selected_type == 1 else ''))
        self.lcd.move(0, 1)
        self.lcd.write(separate_text('Select', 'Edit', '↑'))

        button_input = get_input(1 if not self.selected_type == 1 else None)

        if button_input == 0:
            return

        if button_input == 1:
            self.selected_type = 1

        if button_input == 2:
            self.meter_select()

        if button_input == 3:
            self.auto()

    def meter_select(self):
        meters = self.manual_distance
        while True:
            meters = max(1, min(meters, 99))

            self.lcd.clear()
            self.lcd.move(0, 0)
            self.lcd.write(f'Meters:{meters}')
            self.lcd.move(0, 1)
            self.lcd.write(separate_text('Apply', '+', '-'))

            button_input = get_input()

            if button_input == 0:
                return

            if button_input == 1:
                self.manual_distance = meters
                return

            if button_input == 2:
                meters = meters + 1

            if button_input == 3:
                meters = meters - 1


class LcdTimer:
    def __init__(self, lcd_i2c: 'i2c_lcd.LCD'):
        self.lcd = lcd_i2c
        self.first_timer = 0
        self.second_timer = 0
        self.running = False
        self.first_timer_running = False
        self.second_timer_running = False
        self.speed = "--"
        self.distance = "--"

    def start(self):
        if not self.running:
            self.running = True
            Thread(target=self._update_display).start()
        return self

    def stop(self):
        self.running = False
        return self

    def _update_display(self):
        self.first_timer_running = True
        self.second_timer_running = True
        while self.running:
            if self.first_timer < 99 * 60 and self.first_timer_running:
                self.first_timer += 1
            if self.second_timer < 99 * 60 and self.first_timer_running:
                self.second_timer += 1

            first_time_str = self._format_time(self.first_timer)
            second_time_str = self._format_time(self.second_timer)

            self.lcd.clear()
            self.lcd.write(separate_text(f"{self.speed}M/S", f"T1{first_time_str}"))
            self.lcd.move(0, 1)
            self.lcd.write(separate_text(f"{self.distance}Meters", f"T2{second_time_str}"))

            if self.first_timer >= 99 * 60:
                self.first_timer = 99 * 60
            if self.second_timer >= 99 * 60:
                self.second_timer = 99 * 60

            time.sleep(1)

    @staticmethod
    def _format_time(seconds: int) -> str:
        minutes = seconds // 60
        seconds = seconds % 60
        return f"E{minutes:02}:{seconds:02}"


if __name__ == '__main__':
    buttons = {
    0: Pin(12, Pin.IN, Pin.PULL_UP),  # home_button
    1: Pin(14, Pin.IN, Pin.PULL_UP),  # start_button
    2: Pin(27, Pin.IN, Pin.PULL_UP),  # pause_button
    3: Pin(26, Pin.IN, Pin.PULL_UP),  # stop_button
    }
    # Mensajes de bienvenida
    WELCOME_MESSAGES = ("Bienvenido",)

    # Configuración de Wi-Fi en modo estación
    wlan = WLAN(STA_IF)
    wlan.active(True)  # Activa el modo estación
    if not wlan.active():
        raise RuntimeError("Error al activar el modo estación del Wi-Fi.")

    # Configuración de EspNow
    MASTER_MAC_ADDRESS = 'A0:B7:65:0F:6C:48'
    peer_mac = bytes([int(x, 16) for x in MASTER_MAC_ADDRESS.split(':')])

    esp_now = espnow.ESPNow()
    esp_now.active(True)
    esp_now.add_peer(peer_mac)

    # Configuración del módulo I2C para la pantalla LCD 2x16
    i2c = I2C(0, scl=Pin(23), sda=Pin(22), freq=400000)
    LCD_DIMENSIONS = (2, 16)  # Dimensiones de la pantalla LCD
    lcd = i2c_lcd.init_lcd(23, 22)

    # Parámetros de distancia y tiempo de espera
    overwrite_distance: int | None = None
    RESPONSE_MAX_WAIT_TIME: int = 5

    time.sleep(2)
    distance_config_menu = DistanceConfigMenu(lcd)
    welcome_message = random.choice(WELCOME_MESSAGES)
    lcd.move(2, 0)
    lcd.write(welcome_message)
    time.sleep(4)
    lcd.clear()

    while True:
        time.sleep(0.1)
        home()
