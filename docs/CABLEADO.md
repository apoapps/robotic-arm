# Cableado

## Componentes

- Raspberry Pi Pico W para el controlador del brazo.
- PicoCalc con Picoware/MicroPython para el control remoto.
- PCA9685 de 16 canales para PWM de servos.
- 4 servos: gripper, base, hombro y codo.
- Fuente externa de 5 V a 6 V para los servos.

## Pico W a PCA9685

| Pico W | PCA9685 |
| --- | --- |
| GP4 | SDA |
| GP5 | SCL |
| 3V3 | VCC |
| GND | GND |

## Alimentacion de servos

- Fuente externa `+5 V` o `+6 V` a `V+` del PCA9685.
- GND de la fuente a GND del PCA9685.
- GND del Pico W, PCA9685 y fuente externa deben estar unidos.
- No alimentes los servos desde USB ni desde el pin `3V3` del Pico W.

## Canales de servo

| Canal PCA9685 | Articulacion |
| --- | --- |
| 0 | Gripper / efector final |
| 1 | q1 base |
| 2 | q2 hombro |
| 3 | q3 codo |

## Arranque seguro

1. Carga el firmware.
2. Conecta solo el PCA9685 sin horns montados.
3. Manda el comando neutro.
4. Monta horns en posicion mecanica de 90 grados.
5. Prueba una articulacion a la vez con movimientos pequenos.
