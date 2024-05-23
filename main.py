import M5
from M5 import *
import network
from umqtt import *
import time
import utime
import os, sys, io
from machine import Pin

etiquetas = {}
wlan = None
mqtt_cliente = None
ultimo_movimiento_tiempo = 0

def configurarDisplay():
    global etiquetas
    M5.begin()
    posiciones_etiquetas = [(5, 5), (5, 25), (5, 45), (5, 65), (90, 5)]
    nombres_etiquetas = ["etiqueta0", "etiqueta1", "etiqueta2", "etiqueta3", "etiqueta4"]
    for i, (x, y) in enumerate(posiciones_etiquetas):
        etiquetas[nombres_etiquetas[i]] = Widgets.Label(nombres_etiquetas[i], x, y, 1.0, 0xffffff, 0x222222, Widgets.FONTS.DejaVu18)
    Widgets.setBrightness(125)
    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)

def conectarWifi():
    global wlan
    wlan = network.WLAN(network.STA_IF)
    while not wlan.isconnected():
        wlan.active(False)
        wlan.active(True)
        wlan.config(reconnects=5)
        wlan.config(dhcp_hostname='m5stick')
        wlan.connect('asir1', 'asir1')
        time.sleep(3)

def conectarMQTT():
    global mqtt_cliente
    mqtt_cliente = MQTTClient('m5mqtt', '192.168.249.181', port=1883, user='asir1', password='asir1', keepalive=65535)
    mqtt_cliente.connect(clean_session=True)

def buclePrincipal():
    global etiquetas, wlan, mqtt_cliente, ultimo_movimiento_tiempo
    try:
        while True:
            if wlan.isconnected():
                actualizarDisplay()
                publicarMQTT()
                if time.time() - ultimo_movimiento_tiempo >= 60:  # 60 segundos
                    pin.value(0)
                    mqtt_cliente.publish('sedentarismo', 'Usuario parado', qos=0)
                    mqtt_cliente.publish('movdata', '0', qos=0)
                    time.sleep(0.1)
                    pin.value(1)
                else:
                    mqtt_cliente.publish('sedentarismo', 'Usuario en movimiento', qos=0)
                    mqtt_cliente.publish('movdata', '1', qos=0)
                time.sleep(0.5)
            else:
                manejarDesconexionWifi()
    except (Exception, KeyboardInterrupt) as e:
        manejarExcepcion(e)

def actualizarDisplay():
    global etiquetas, ultimo_movimiento_tiempo
    (x, y, z) = Imu.getAccel()
    etiquetas["etiqueta0"].setColor(0xff0000, 0x000000)  # Rojo
    etiquetas["etiqueta1"].setColor(0x00ff00, 0x000000)  # Verde
    etiquetas["etiqueta2"].setColor(0x0000ff, 0x000000)  # Azul
    etiquetas["etiqueta0"].setText(f'X {x:.2f}')
    etiquetas["etiqueta1"].setText(f'Y {y:.2f}')
    etiquetas["etiqueta2"].setText(f'Z {z - 1:.2f}')
    movimiento = movimientoDetectado(x, y, z)
    etiquetas["etiqueta4"].setColor(0x33ff33 if movimiento else 0xDE2121, 0x000000)
    etiquetas["etiqueta4"].setText(str(movimiento))
    hora_actual = utime.localtime(utime.mktime(utime.gmtime()) + 3600 * 2)
    hora_formateada = "{:02d}:{:02d}:{:02d}".format(hora_actual[3], hora_actual[4], hora_actual[5])
    etiquetas["etiqueta3"].setText(hora_formateada)
    if movimiento:
        ultimo_movimiento_tiempo = time.time()

def publicarMQTT():
    global mqtt_cliente
    (x, y, z) = Imu.getAccel()
    mqtt_cliente.publish('stick', str(movimientoDetectado(x, y, z)), qos=0)

def manejarDesconexionWifi():
    global wlan
    etiquetas["etiqueta0"].setColor(0xff0000, 0x000000)
    etiquetas["etiqueta1"].setColor(0xff0000, 0x000000)
    etiquetas["etiqueta0"].setText(str('¿?'))
    etiquetas["etiqueta4"].setColor(0xff0000, 0x000000)
    etiquetas["etiqueta4"].setText("No hay conexión WiFi")
    wlan.active(False)
    wlan.active(True)
    wlan.config(reconnects=5)
    wlan.config(dhcp_hostname='m5stick')
    wlan.connect('S23 Ultra', 'juanmiii')
    time.sleep(1)

def manejarExcepcion(excepcion):
    try:
        from utility import print_error_msg
        print_error_msg(excepcion)
    except ImportError:
        print("Por favor, actualiza al último firmware")

def movimientoDetectado(x, y, z):
    l = [1.12, -1.12]
    if x >= l[0] or x <= l[1]:
        return True
    if y >= l[0] or y <= l[1]:
        return True
    if z >= l[0] or z <= l[1]:
        return True
    return False
    
async def avisoLed():
    global led_pwm
    for _ in range(10):
        for duty_cycle in range(1023):
            led_pwm.duty(duty_cycle)
            await asyncio.sleep(0.001)  # Tiempo de espera más corto

        for duty_cycle in range(1023, -1, -1):
            led_pwm.duty(duty_cycle)
            await asyncio.sleep(0.01)  # Tiempo de espera más largo

if __name__ == '__main__':
    pin = Pin(10, Pin.OUT)
    configurarDisplay()
    conectarWifi()
    conectarMQTT()
    buclePrincipal()
