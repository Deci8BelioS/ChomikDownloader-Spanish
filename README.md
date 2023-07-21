# Chomyk / ChomikDownloader

Este script, escrito en Python 3.8, te permite descargar archivos desde Chomikuj.pl.

## Requisitos para su uso:
- **Debian/Ubuntu Python3**: sudo apt-get install python3-requests. 
- **Windows**: pip install requests (or pip3 install requests for python3)

## Parámetros disponibles:

- **-u**: Usuario de Chomikuj.
- **-p**: Contraseña de Chomikuj.
- **-i**: URL del archivo o carpeta que deseas descargar.
- **-d**: Ruta de descarga del archivo (por defecto, será el directorio del script).
- **-t**: Número máximo de hilos para la descarga (por defecto, se utilizan 5 hilos).

> Nota: Al pegar la URL de un archivo, asegúrate de quitar el paréntesis al final de la URL, por ejemplo: (video)

## Ejemplo de uso:

Para descargar los archivos que se encuentran en una carpeta de tu cuenta, puedes utilizar el siguiente comando:

```
sudo python3 chomyk.py -t 4 -u TU_USUARIO -p TU_CONTRASEÑA -i https://chomikuj.pl/TU_USUARIO/NOMBRE_CARPETA/ -d Descargas
```

```
sudo python3 chomyk.py -t 4 -u TU_USUARIO -p TU_CONTRASEÑA -i https://chomikuj.pl/TU_USUARIO/NOMBRE_CARPETA/NOMBRE_CARPETA/nombre_del_archivo,numeros_aleatorios.mkv -d Descargas
```

Recuerda reemplazar `TU_USUARIO` y `TU_CONTRASEÑA` con tus credenciales de Chomikuj y ajustar la URL y la ruta de descarga según tus necesidades.

![Screenshot](https://github.com/Deci8BelioS/ChomikDownloader-Spanish/blob/master/image.png)
