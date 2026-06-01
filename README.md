# Robotica Industrial - Proyecto final

Equipo para Yamel:

- Gael Calderon Robles
- Alejandro Apodaca Cordova
- Lailah Soriano Alvarez
- Moises Ochoa

Este entregable organiza el firmware del controlador del brazo robotico, la app MicroPython para PicoCalc/Picoware y las notas tecnicas para cableado, pruebas y puesta en marcha.

## Estructura

- `firmware/robot-arm-platformio/`: firmware C++/Arduino para Raspberry Pi Pico W con PlatformIO.
- `picoware/apps/robot_arm_remote.py`: app MicroPython para controlar el brazo desde PicoCalc/Picoware.
- `tools/`: scripts de instalacion, carga y prueba desde la computadora.
- `docs/INFORME_TECNICO.md`: reporte tecnico detallado.
- `docs/CABLEADO.md`: guia rapida de cableado.

## Flujo recomendado

1. Instala herramientas en la computadora:

   ```sh
   ./tools/install-tools.sh
   ```

2. Copia la plantilla de configuracion y ajusta Wi-Fi:

   ```sh
   cp firmware/robot-arm-platformio/include/config.example.h firmware/robot-arm-platformio/include/config.h
   ```

3. Compila y carga el firmware al Pico W del brazo:

   ```sh
   cd firmware/robot-arm-platformio
   pio run
   pio run -t upload
   pio device monitor -b 115200
   ```

4. Copia la app `picoware/apps/robot_arm_remote.py` a la SD del PicoCalc:

   ```text
   /picoware/apps/robot_arm_remote.py
   ```

   Tambien puedes usar:

   ```sh
   ./tools/upload_picoware_app.sh
   ```

   Para actualizar la app despues sin sacar la SD, conecta el PicoCalc por USB y ejecuta:

   ```sh
   ./tools/update_picoware_app_usb.sh
   ```

   Esto copia la app a `/picoware/apps/robot_arm_remote.py` usando `mpremote`. Si tu instalacion de Picoware solo descubre apps desde la SD y no expone esa ruta por USB, usa la copia en flash interna como launcher o instala Picoware con dashboard/USB file manager.

5. Enciende el controlador del brazo, anota la IP que imprime por serial y pon esa IP en la app del PicoCalc.

## Prueba rapida

Desde la computadora, con el Pico W conectado por USB:

```sh
python3 tools/serial_test.py --port /dev/tty.usbmodemXXXX
```

Desde Wi-Fi:

```sh
python3 tools/wifi_test.py --host 192.168.4.1
```

No montes los horns de los servos hasta confirmar que el comando neutro funciona:

```text
<BUZZ,90,90,90,90,1000,1000,1000,1000>
```
