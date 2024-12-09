from esp import espnow
import network
import time
import threading


class ESPNow:
    def __init__(self, peer_mac: bytes):
        """
        Inicializa el módulo ESP-NOW y configura un peer.

        Args:
            peer_mac: Dirección MAC del dispositivo peer en formato bytes.
        """
        self.espnow = espnow.ESPNow()
        self.espnow.init()
        self.peer_mac = peer_mac

        # Configurar el peer si no está ya registrado
        if not self.espnow.add_peer(peer_mac):
            print(f"Peer {peer_mac.hex()} ya registrado.")

        self.listener: ESPNowListener = ESPNowListener(self.espnow)

    def send_message(self, message: str):
        """
        Envía un mensaje al peer configurado.

        Args:
            message: El mensaje a enviar como string.

        Returns:
            bool: True si el mensaje fue enviado exitosamente, False en caso contrario.
        """
        try:
            self.espnow.send(self.peer_mac, message.encode("utf-8"))
            return True
        except OSError as e:
            print(f"Error enviando mensaje: {e}")
            return False


class ESPNowListener:
    def __init__(self, espnow_instance: espnow.ESPNow):
        """
        Inicializa la clase para escuchar mensajes en ESP-NOW.

        Args:
            espnow_instance: Instancia de ESPNow inicializada.
        """
        self._espnow = espnow_instance
        self._running = False
        self._response = None
        self._listener_thread = None

    def start_listening(self):
        """
        Inicia la escucha en segundo plano.
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
        while self._running:
            if self._espnow.any():
                try:
                    peer, message = self._espnow.recv()
                    if peer:
                        self._response = message.decode("utf-8")
                        self.stop()
                except Exception as e:
                    print(f"Error recibiendo mensaje: {e}")
            time.sleep(0.01)  # Pausa breve para reducir carga de CPU

    def stop(self):
        """
        Detiene el proceso de escucha.
        """
        self._running = False
        if self._listener_thread:
            self._listener_thread.join()

    def response(self):
        """
        Verifica si hay una respuesta disponible.

        Returns:
            str | None: Mensaje recibido o None si no hay mensajes.
        """
        if self._response is not None:
            response = self._response
            self._response = None
            self.stop()
            return response
