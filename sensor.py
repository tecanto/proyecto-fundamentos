from machine import Pin, time_pulse_us
import time

TRIGGER_PIN = 5
ECHO_PIN = 18

trigger = Pin(TRIGGER_PIN, Pin.OUT)
echo = Pin(ECHO_PIN, Pin.IN)

UMBRAL_DETECCION = 20
SIN_RESPUESTA = -1
LECTURAS_MAX = 10

def messure_distance():
    trigger.value(0)
    time.sleep_us(2)

    trigger.value(1)
    time.sleep_us(10)
    trigger.value(0)

    duracion = time_pulse_us(echo, 1, 100000)

    if duracion < 0:
        return SIN_RESPUESTA

    distancia = (duracion / 2) * 0.0343
    return distancia


def wait_person():
    distancias = [SIN_RESPUESTA] * LECTURAS_MAX
    indice = 0

    while True:
        distancia_actual = messure_distance()
        distancias[indice] = distancia_actual
        indice = (indice + 1) % LECTURAS_MAX

        lectura_anterior = distancias[indice - 1]

        if lectura_anterior == SIN_RESPUESTA and distancia_actual != SIN_RESPUESTA:
            return distancia_actual
        elif abs(distancia_actual - lectura_anterior) > UMBRAL_DETECCION:
            return distancia_actual

        time.sleep(0.02)
