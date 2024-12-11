import _thread


class Thread:
    def __init__(self, target=None, args=()):
        """
        Simula una clase Thread básica.
        :param target: La función que se ejecutará en el hilo.
        :param args: Los argumentos para la función target.
        """
        self.target = target
        self.args = args
        self._is_alive = False
        self._done = _thread.allocate_lock()  # Bloqueo para simular join()
        self._done.acquire()

    def start(self):
        """
        Inicia el hilo y ejecuta la función target.
        """
        if not self.target:
            raise ValueError("No se especificó una función target para ejecutar.")

        def thread_wrapper():
            self._is_alive = True
            try:
                self.target(*self.args)
            finally:
                self._is_alive = False
                self._done.release()  # Liberar el bloqueo al finalizar el hilo

        _thread.start_new_thread(thread_wrapper, ())

    def join(self):
        """
        Espera a que el hilo termine.
        """
        self._done.acquire()
        self._done.release()

    def is_alive(self):
        """
        Retorna True si el hilo sigue activo, False de lo contrario.
        """
        return self._is_alive
