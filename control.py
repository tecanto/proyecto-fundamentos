import time
import random
import threading
from machine import I2C, Pin
from lcd.i2c_lcd import I2cLcd
import esp_now_manager

WELCOME_MESSAGES = (
    "Bienvenido",
    "Recuerda, eres un tio chill",
)


# EspNow Configuration
MASTER_MAC_ADDRESS = b'que bonitos ojos tines'
esp_now = esp_now_manager.ESPNow(MASTER_MAC_ADDRESS)

# I2C Module configuration for 2x16 lcd display
i2c = I2C(0, scl=Pin(23), sda=Pin(22), freq=400000)
print(i2c.scan())
I2C_ADDR = 0x27
LCD_DIMENSIONS = 2, 16
lcd = I2cLcd(i2c, I2C_ADDR, *LCD_DIMENSIONS)

overwrite_distance: int | None = None
RESPONSE_MAX_WAIT_TIME: int = 5

buttons = {
    0: Pin(12, Pin.IN, Pin.PULL_UP),  # home_button
    1: Pin(14, Pin.IN, Pin.PULL_UP),  # start_button
    2: Pin(27, Pin.IN, Pin.PULL_UP),  # pause_button
    3: Pin(26, Pin.IN, Pin.PULL_UP),  # stop_button
}


def pad_text(text: str):
    padding = ' ' * ((LCD_DIMENSIONS[1] - len(text)) // 2)
    return padding + text + padding


def separate_text(*text: str):
    total_len = len(''.join(text))

    if total_len >= LCD_DIMENSIONS[1]:
        return ''.join(text)

    separation = ' ' * ((LCD_DIMENSIONS[1] - total_len) // (len(text) - 1))
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


def listen_esp_now_response(limit: int | None = RESPONSE_MAX_WAIT_TIME) -> str | None:
    esp_now.listener.start_listening()

    init_wait_time = time.process_time()
    while True:
        response = esp_now.listener.response()

        if response:
            break
        if limit is not None and time.process_time() - init_wait_time > limit:
            esp_now.listener.stop()
            break

        time.sleep(0.1)
    return response


def home():
    lcd.clear()

    lcd.move_to(0, 0)
    lcd.putstr(pad_text('HOME'))

    lcd.move_to(0, 1)
    lcd.putstr(separate_text('start', 'config'))

    button_input = get_input(0, 2)

    if button_input == 1:
        measure()

    if button_input == 3:
        config()


def measure():
    def listen_input():
        nonlocal paused_time, listening
        running: bool = True
        init_paused = 0
        while listening:
            button_input = get_input(0, 1)
            if button_input == 2:
                timer_screen.first_timer_running = not running
                timer_screen.second_timer_running = not running
                running = not running
                if running:
                    paused_time = paused_time + time.process_time() - init_paused if init_paused else 0
                init_paused = time.process_time()
            if button_input == 3:
                timer_screen.first_timer_running = False
                timer_screen.second_timer_running = False
                break

    distance: int = get_distance() if not overwrite_distance else overwrite_distance
    distance = max(1, min(distance, 99))
    paused_time: int = 0

    esp_now.send_message('start')
    response = listen_esp_now_response()
    if not response == 'ok':
        return

    listening = True
    listen_input_thread = threading.Thread(target=listen_input)
    listen_input_thread.start()
    timer_screen = LcdTimer(lcd)
    timer_screen.distance = str(distance)

    esp_now.listener.start_listening()
    while True:
        response = esp_now.listener.response()
        if response and response.isdigit():
            timer_screen.first_timer_running = False
            timer_screen.first_timer = int(response) - paused_time
            break

        if not listen_input_thread.is_alive():
            break

        time.sleep(0.1)

    esp_now.listener.start_listening()
    while True:
        response = esp_now.listener.response()
        if response and response.isdigit():
            timer_screen.second_timer_running = False
            timer_screen.second_timer = int(response) - paused_time
            break

        if not listen_input_thread.is_alive():
            break
        time.sleep(0.1)

    esp_now.listener.stop()
    listening = False
    listen_input_thread.join()

    get_input(2, 3)


def config():
    global overwrite_distance
    time.sleep(0.2)
    lcd.clear()

    lcd.move_to(0, 0)
    lcd.putstr('Distance')

    lcd.move_to(0, 1)
    lcd.putstr(separate_text('select', '↑', '↓'))

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
    esp_now.send_message('distance')

    response = listen_esp_now_response()
    distance = int(response) if response and response.isdigit() else 1

    distance = max(1, min(distance, 99))
    return distance


class DistanceConfigMenu:
    def __init__(self, lcd_i2c: 'I2cLcd'):
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

        self.lcd.move_to(0, 0)
        self.lcd.putstr(separate_text(f'auto: {self.distance}', '*' if self.selected_type == 0 else ''))
        self.lcd.move_to(0, 1)
        self.lcd.putstr(separate_text('Select', 'Edit', '↓'))

        button_input = get_input(2, 1 if not self.selected_type == 0 else None)

        # if button_input == 1  End the config Menu

        if button_input == 1:
            self.selected_type = 0

        if button_input == 3:
            self.manual()

    def manual(self):
        self.lcd.clear()

        self.lcd.move_to(0, 0)
        self.lcd.putstr(separate_text('manual', '*' if self.selected_type == 1 else ''))
        self.lcd.move_to(0, 1)
        self.lcd.putstr(separate_text('Select', 'Edit', '↑'))

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
            self.lcd.move_to(0, 0)
            self.lcd.putstr(f'Meters:{meters}')
            self.lcd.move_to(0, 1)
            self.lcd.putstr(separate_text('Apply', '+', '-'))

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
    def __init__(self, lcd_i2c: 'I2cLcd'):
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
            threading.Thread(target=self._update_display, daemon=True).start()
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
            self.lcd.putstr(separate_text(f"{self.speed}M/S", f"T1{first_time_str}"))
            self.lcd.move_to(0, 1)
            self.lcd.putstr(separate_text(f"{self.distance}Meters", f"T2{second_time_str}"))

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
    time.sleep(2)
    distance_config_menu = DistanceConfigMenu(lcd)
    welcome_message = random.choice(WELCOME_MESSAGES)
    lcd.move_to(2, 0)
    lcd.putstr(welcome_message)
    time.sleep(4)
    lcd.clear()

    while True:
        time.sleep(0.1)
        home()
