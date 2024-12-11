from machine import I2C, Pin
import time

class LCD:
    # Comandos LCD
    LCD_CLEARDISPLAY = 0x01
    LCD_RETURNHOME = 0x02
    LCD_ENTRYMODESET = 0x04
    LCD_DISPLAYCONTROL = 0x08
    LCD_CURSORSHIFT = 0x10
    LCD_FUNCTIONSET = 0x20
    LCD_SETCGRAMADDR = 0x40
    LCD_SETDDRAMADDR = 0x80

    # Flags para control de display
    LCD_DISPLAYON = 0x04
    LCD_DISPLAYOFF = 0x00
    LCD_CURSORON = 0x02
    LCD_CURSOROFF = 0x00
    LCD_BLINKON = 0x01
    LCD_BLINKOFF = 0x00

    def __init__(self, i2c, address=0x27):
        """
        Inicializa la pantalla LCD con comunicación I2C
        
        :param i2c: Objeto I2C configurado
        :param address: Dirección I2C del módulo adaptador (por defecto 0x27)
        """
        self.i2c = i2c
        self.address = address
        self.backlight = 0x08  # Valor por defecto de la luz de fondo

        # Inicialización de la pantalla
        time.sleep(0.0050)
        self._write_cmd(0x03)
        time.sleep(0.005)
        self._write_cmd(0x03)
        time.sleep(0.005)
        self._write_cmd(0x03)
        time.sleep(0.005)
        self._write_cmd(0x02)  # Modo de 4 bits

        # Configuración inicial
        self._write_cmd(self.LCD_FUNCTIONSET | 0x08)  # 4 bits, 2 líneas, 5x8 puntos
        self._write_cmd(self.LCD_DISPLAYCONTROL | self.LCD_DISPLAYON)
        self.clear()
        self._write_cmd(self.LCD_ENTRYMODESET | 0x02)  # Incremento de cursor, sin desplazamiento

    def _write_cmd(self, cmd):
        """
        Envía un comando al LCD
        
        :param cmd: Comando a enviar
        """
        self._write_i2c(cmd, 0)

    def _write_data(self, data):
        """
        Envía datos al LCD
        
        :param data: Datos a enviar
        """
        self._write_i2c(data, 1)

    def _write_i2c(self, data, mode):
        """
        Escribe datos o comandos a través de I2C
        
        :param data: Datos a enviar
        :param mode: 0 para comando, 1 para datos
        """
        # Separa los 4 bits altos y bajos
        data_high = data & 0xF0
        data_low = (data << 4) & 0xF0

        # Envía los 4 bits altos
        self._send_i2c(data_high | mode | self.backlight)
        self._send_i2c(data_high | mode | self.backlight | 0x04)
        self._send_i2c(data_high | mode | self.backlight)

        # Envía los 4 bits bajos
        self._send_i2c(data_low | mode | self.backlight)
        self._send_i2c(data_low | mode | self.backlight | 0x04)
        self._send_i2c(data_low | mode | self.backlight)

    def _send_i2c(self, data):
        """
        Envía un byte a través de I2C
        
        :param data: Byte a enviar
        """
        self.i2c.writeto(self.address, bytes([data]))
        time.sleep(0.001)

    def clear(self):
        """
        Limpia la pantalla LCD
        """
        self._write_cmd(self.LCD_CLEARDISPLAY)
        time.sleep(0.002)

    def home(self):
        """
        Mueve el cursor a la posición inicial
        """
        self._write_cmd(self.LCD_RETURNHOME)
        time.sleep(0.002)

    def move(self, col, row):
        """
        Mueve el cursor a una posición específica
        
        :param col: Columna (0-15)
        :param row: Fila (0-1)
        """
        # Calcula la dirección base de la fila
        row_offsets = [0x00, 0x40]
        if row > 1:
            row = 1
        if col > 15:
            col = 15
        
        self._write_cmd(self.LCD_SETDDRAMADDR | (col + row_offsets[row]))

    def write(self, text):
        """
        Escribe texto en la pantalla LCD
        
        :param text: Texto a mostrar
        """
        for char in text:
            self._write_data(ord(char))

def init_lcd(scl_pin=22, sda_pin=21, freq=400000):
    """
    Función de inicialización rápida del LCD
    
    :param scl_pin: Pin para SCL (por defecto 22)
    :param sda_pin: Pin para SDA (por defecto 21)
    :param freq: Frecuencia I2C (por defecto 400000)
    :return: Objeto LCD
    """
    i2c = I2C(0, scl=Pin(scl_pin), sda=Pin(sda_pin), freq=freq)
    return LCD(i2c)