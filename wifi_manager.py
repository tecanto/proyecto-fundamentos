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
        self.listener = NRFListener(self.nrf)

    def send_message(self, message):
        """
        Enviar un mensaje utilizando NRF24L01
        """
        self.listener.stop()
        self.nrf.stop_listening()  # Cambiar a modo de transmisión
        try:
            self.nrf.send(message)
            return True
        except OSError:
            return False
        finally:
            self.nrf.start_listening()  # Regresar al modo de recepción

    def transmitter_get_distance(self) -> float | None:
        """
        Calcula la distancia al receptor enviando un 'ping' y midiendo el tiempo de ida y vuelta.

        Returns:
            Distancia estimada en metros, o None si falla.
        """
        self.nrf.stop_listening()
        start_time = time.ticks_us()

        # Enviar mensaje 'ping'
        if not self.send_message(b'ping'):
            print("Error al enviar el mensaje")
            return None

        # Escuchar la respuesta 'pong'
        self.listener.start_listening()
        while True:
            response = self.listener.response()
            if response is not None:
                if response == b'pong':
                    end_time = time.ticks_us()
                    round_trip_time = time.ticks_diff(end_time, start_time)
                    distance = (round_trip_time / 2) * 3e-4  # Tiempo a distancia (en metros)
                    self.listener.stop()
                    return distance
            time.sleep(0.01)

    def receiver_get_distance(self) -> None:
        """
        Responde a las solicitudes 'ping' enviando un 'pong'.
        """
        self.listener.start_listening()
        while True:
            message = self.listener.response()
            if message is not None:
                if message == b'ping':
                    self.send_message(b'pong')


class NRFListener:
    def __init__(self, nrf: NRF24L01):
        """
        Inicializa la clase con el módulo NRF.

        Args:
            nrf: Objeto NRF configurado para comunicación.
        """
        self._nrf = nrf
        self._running = False
        self._response = None
        self._listener_thread = None

    def start_listening(self):
        """
        Inicia el proceso de escucha en segundo plano.
        """
        if self._running:
            print("El listener ya está corriendo.")
            return
        self._running = True
        self._response = None
        self._listener_thread = threading.Thread(target=self._listen)
        self._listener_thread.daemon = True
        self._listener_thread.start()

    def _listen(self):
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
            time.sleep(0.01)  # Pausa breve para reducir carga de CPU

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
            response = self._response
            try:
                self._response = None
                self.stop()
            finally:
                return response
