from machine import Pin, SPI
from nrf24l01 import NRF24L01
import threading
import time


class Wifi:
    def __init__(self, send_address: bytes, receive_address: bytes):
        # Configuración de pines
        ce = Pin(22, mode=Pin.OUT)
        cs = Pin(21, mode=Pin.OUT)
        spi_bus = SPI(
            2,
            baudrate=4000000,
            polarity=0,
            phase=0,
            sck=Pin(18),
            mosi=Pin(23),
            miso=Pin(19),
        )

        # Inicializar el módulo NRF24L01
        self.nrf: NRF24L01 = NRF24L01(spi=spi_bus, cs=cs, ce=ce, channel=76, payload_size=16)

        self.nrf.open_tx_pipe(send_address)
        self.nrf.open_rx_pipe(1, receive_address)
        self.get_distance = DistanceMeasurement(self)
        self.listener = NRFListener(self.nrf)

    def send_message(self, message: str):
        """
        Enviar un mensaje utilizando NRF24L01
        """
        self.listener.stop()
        self.nrf.stop_listening()  # Cambiar a modo de transmisión
        try:
            self.nrf.send(message.encode())
            return True
        except OSError:
            return False
        finally:
            self.nrf.start_listening()  # Regresar al modo de recepción


class NRFListener:
    def __init__(self, nrf: NRF24L01):
        """
        Inicializa la clase con el módulo NRF.

        Args:
            nrf: Objeto NRF configurado para comunicación.
        """
        self._nrf = nrf
        self._running = False
        self._response: bytes | None = None
        self._listener_thread = None

    def start_listening(self, sleep_time: float = 0.01):
        """
        Inicia el proceso de escucha en segundo plano.
        """
        if self._running:
            print("El listener ya está corriendo.")
            return
        self._running = True
        self._response = None
        self._listener_thread = threading.Thread(target=self._listen, args=(sleep_time,))
        self._listener_thread.daemon = True
        self._listener_thread.start()

    def _listen(self, sleep_time: float):
        """
        Método privado para escuchar mensajes en un bucle en segundo plano.
        """
        self._nrf.start_listening()
        while self._running:
            if not self._nrf.is_listening:
                break

            if self._nrf.any():
                while self._nrf.any():
                    self._response = self._nrf.recv()
                    self.stop()
            if sleep_time:
                time.sleep(sleep_time)  # Pausa breve para reducir carga de CPU

    def stop(self):
        """
        Detiene el proceso de escucha en segundo plano.
        """
        self._running = False
        self._nrf.stop_listening()
        if self._listener_thread:
            self._listener_thread.join()

    def response(self):
        """
        Verifica si hay una respuesta disponible.

        Returns:
            La respuesta recibida o None si no hay respuesta.
        """
        if self._response is not None:
            response: str = self._response.decode()
            try:
                self._response = None
                self.stop()
            finally:
                return response


class DistanceMeasurement:
    def __init__(self, wifi_instance: Wifi):
        self.wifi = wifi_instance

    def transmitter(self, timeout=1.0, samples: int = 5) -> float | None:
        self.wifi.nrf.stop_listening()
        distances: list[float | None] = []

        for _ in range(samples):
            start_time = time.time()
            if not self.wifi.send_message('ping'):
                print("Error sending ping")
                continue

            self.wifi.nrf.start_listening()
            while time.time() - start_time < timeout:
                response = self.wifi.nrf.recv()
                if response == b'pong':
                    # Speed of radio wave is approximately 3e8 m/s
                    round_trip_time = time.time() - start_time
                    distances.append((round_trip_time * 3e8) / 2)
                    break

            self.wifi.nrf.stop_listening()
            time.sleep(0.1)

        self.wifi.nrf.stop_listening()
        self.wifi.send_message('stop')
        return sum(distances) / len(distances) if distances else None

    def receiver(self, timeout: float = 2.0) -> None:
        self.wifi.nrf.start_listening()
        init_t = time.time()

        while time.time() - init_t < timeout:
            message = self.wifi.nrf.recv()
            if message == b'ping':
                self.wifi.send_message('pong')
                init_t = time.time()
            elif message == b'stop':
                break
        self.wifi.nrf.stop_listening()
