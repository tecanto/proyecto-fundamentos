import espnow
import time
import threading
from network import WLAN, STA_IF

class ESPNow:
    def __init__(self, peer_mac: bytes):
        """
        Inicializa el módulo ESP-NOW y configura un peer.

        Args:
            peer_mac: Dirección MAC del dispositivo peer en formato bytes.
        """
        wlan = WLAN(STA_IF)
        wlan.active(True)  # Activa el modo estación
        self.esp_now = espnow.ESPNow()
        self.esp_now.active(True)
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

    def _esp_now_recv(self, result: list | None = None):
        peer, message = self.esp_now.recv()
        if result:
            result.append(message)
        return message.decode() if message else None

    def get_message(self, timeout: float | None = None) -> str | None:
        if not timeout:
            return self._esp_now_recv()
        result = []
        esp_now_recv_thread = threading.Thread(target=self._esp_now_recv, args=(result,))
        init_t = time.time()
        esp_now_recv_thread.start()
        while time.time() - init_t < timeout:
            if result:
                break
            time.sleep(0.1)
        return result[-1]
