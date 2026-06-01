# Informe tecnico - Robotica Industrial Proyecto Final

## Objetivo

Construir un brazo robotico educativo controlado por un Raspberry Pi Pico W y operado de forma remota desde PicoCalc con Picoware/MicroPython. El sistema permite mover cuatro servos: gripper, base, hombro y codo.

## Equipo

- Gael Calderon Robles
- Alejandro Apodaca Cordova
- Lailah Soriano Alvarez
- Moises Ochoa

## Arquitectura

El proyecto se divide en dos dispositivos:

1. Controlador del brazo: Raspberry Pi Pico W con firmware C++/Arduino en PlatformIO. Controla un PCA9685 por I2C y expone un servidor TCP por Wi-Fi.
2. Control remoto: PicoCalc con Picoware/MicroPython. Ejecuta `robot_arm_remote.py`, abre una conexion TCP al Pico W y envia posiciones.

El protocolo de control es texto plano:

```text
<instruccion,ee,q1,q2,q3,timeEE,time1,time2,time3>
```

Ejemplo:

```text
<BUZZ,90,90,90,90,1000,1000,1000,1000>
```

## Firmware del brazo

El firmware esta en `firmware/robot-arm-platformio`. Sus funciones principales son:

- Inicializar I2C en `GP4`/`GP5`.
- Controlar servos con PCA9685 a 50 Hz.
- Suavizar movimientos con easing cubico.
- Recibir comandos por USB serial y por Wi-Fi TCP.
- Iniciar modo AP si no hay credenciales Wi-Fi.

La configuracion local de Wi-Fi va en `include/config.h`, creado desde `include/config.example.h`.

## App PicoCalc/Picoware

La app esta en `picoware/apps/robot_arm_remote.py`. Esta pensada para ejecutarse desde Picoware y usa solo modulos estandar de MicroPython: `socket` y `time`.

Funciones:

- Solicita IP y puerto del controlador.
- Incluye poses predefinidas.
- Permite introducir angulos manuales.
- Envia comandos TCP y muestra la respuesta del controlador.

## Instalacion recomendada

En la computadora:

```sh
./tools/install-tools.sh
```

Este script instala:

- PlatformIO para compilar y subir firmware C++.
- mpremote para copiar archivos y abrir REPL de MicroPython.
- pyserial para pruebas seriales.

## Instalacion de Picoware

Segun la guia actual de Picoware, para PicoCalc se debe actualizar primero el firmware del teclado si aplica, flashear el UF2 correspondiente y copiar la carpeta `apps` de `builds/MicroPython` a `/picoware` en la SD. Para este proyecto, copia tambien:

```text
picoware/apps/robot_arm_remote.py -> SD:/picoware/apps/robot_arm_remote.py
```

## Actualizacion de la app sin sacar la SD

La ruta preferida es USB con `mpremote`:

```sh
./tools/update_picoware_app_usb.sh
```

El script crea `/picoware/apps` si falta y copia `robot_arm_remote.py` al dispositivo. Esto funciona cuando Picoware/MicroPython expone esa ruta en el filesystem del PicoCalc. Si la app se ejecuta exclusivamente desde la SD y esa SD no queda montada en MicroPython, la alternativa practica es mantener una copia lanzadora en flash interna que importe o ejecute la version actualizada, o usar el dashboard/administrador de archivos USB de la distribucion MicroPython instalada.

## Red

Hay dos modos:

- Modo STA: si `WIFI_SSID` no esta vacio, el Pico W se conecta al router configurado.
- Modo AP: si `WIFI_SSID` esta vacio o falla la conexion, el Pico W crea la red `ROBOT_ARM_PICO` con clave `robot12345`.

El puerto TCP por defecto es `7777`.

## Seguridad y calibracion

- No alimentar servos desde USB.
- Usar fuente externa para servos y tierra comun.
- Probar primero sin horns.
- Montar horns con todos los servos en 90 grados.
- Limitar recorridos si hay interferencia mecanica.
- Si un servo vibra, se calienta o se traba, cortar energia y revisar montaje.

## Fuentes consultadas

- Picoware: https://github.com/jblanked/Picoware
- Guia de instalacion Picoware: https://github.com/jblanked/Picoware/blob/main/guides/Installation.md
- mpremote MicroPython: https://docs.micropython.org/en/latest/reference/mpremote.html
- PicoCalc MicroPython por LofiFren: https://github.com/LofiFren/PicoCalc
