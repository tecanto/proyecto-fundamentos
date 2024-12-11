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
        self.esp_now = espnow.ESPNow()
        self.esp_now.init()
        self.peer_mac = peer_mac
        self.responses = []

        # Configurar el peer si no está ya registrado
        if not self.esp_now.add_peer(peer_mac):
            print(f"Peer {peer_mac.hex()} ya registrado.")

    def send_message(self, message: str):
        """
        Envía un mensaje al peer configurado.

        Args:
            message: El mensaje a enviar como string.

        Returns:
            bool: True si el mensaje fue enviado exitosamente, False en caso contrario.
        """
        try:
            self.esp_now.send(self.peer_mac, message.encode("utf-8"))
            return True
        except OSError as e:
            print(f"Error enviando mensaje: {e}")
            return False

    def get_message(self) -> str | None:
        peer, message = self.esp_now.recv()
        return message.encode() if message else None
