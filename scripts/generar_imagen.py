#!/usr/bin/env python3
"""Genera las imágenes de promociones con el diseño aprobado.

Uso:
    python scripts/generar_imagen.py ruta/a/datos.json

El archivo de datos es lo que envía Power Automate:
    {
      "filas":           [ ...promociones Supercomisión... ],
      "filas_corretaje": [ ...promociones Corretaje y Arriendo... ]
    }
Cada fila: {"Edificio": "...", "Tipología": "...", "Tipo Promoción": "...",
            "Fecha Vigencia": "...", "Estatus": "..."}

Cada lista también puede venir como texto JSON, y cualquiera de las dos puede
faltar o venir vacía (esa imagen simplemente no se genera). Los nombres de
columna se reconocen aunque cambien mayúsculas, tildes o guiones bajos.

En la imagen de Corretaje y Arriendo, los textos de arriendo gratis se
reescriben con el mes del envío (hora de Chile). Por ejemplo, en octubre:
    "Arriendo primer mes gratis"       -> "Arriendo Octubre gratis"
    "Arriendo primeros 2 meses gratis" -> "Arriendo Octubre y Noviembre gratis"

Guarda los PNG en publico/img/ y, si corre en GitHub Actions, deja en la salida
del paso:
    hay_filas, archivo                       -> Supercomisión
    hay_filas_corretaje, archivo_corretaje   -> Corretaje y Arriendo
    hay_alguna                               -> true si se generó al menos una imagen
    fecha                                    -> DD-MM-AAAA
"""
import html
import json
import os
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parent.parent
PLANTILLA = RAIZ / "scripts" / "plantilla.html"
CARPETA_IMG = RAIZ / "publico" / "img"
ZONA_CHILE = ZoneInfo("America/Santiago")

# Una entrada por imagen, en el orden en que se generan.
#   clave:  nombre de la lista en los datos que manda Power Automate
#   titulo: título que aparece en la imagen
#   prefijo: inicio del nombre del PNG
#   sufijo: se agrega a las salidas del paso (hay_filas{sufijo}, archivo{sufijo})
#   meses_arriendo: True = reescribe "Arriendo primer mes gratis" con el mes del envío
TABLAS = [
    {
        "clave": "filas",
        "titulo": "Promociones Supercomisión Vigentes",
        "prefijo": "promociones_supercomision",
        "sufijo": "",
        "meses_arriendo": False,
    },
    {
        "clave": "filas_corretaje",
        "titulo": "Promociones Corretaje y Arriendo Vigentes",
        "prefijo": "promociones_corretaje_arriendo",
        "sufijo": "_corretaje",
        "meses_arriendo": True,
    },
]

MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

# Textos de arriendo gratis que se reescriben con el mes del envío.
# No importan mayúsculas ni espacios de más; el resto de la celda se mantiene.
ARRIENDO_DOS_MESES = re.compile(r"\barriendo\s+primeros\s+(?:2|dos)\s+meses\s+gratis\b", re.IGNORECASE)
ARRIENDO_UN_MES = re.compile(r"\barriendo\s+primer\s+mes\s+gratis\b", re.IGNORECASE)

# (clave normalizada, nombre que se muestra) en el orden de la tabla
COLUMNAS = [
    ("edificio", "Edificio"),
    ("tipologia", "Tipología"),
    ("tipo promocion", "Tipo Promoción"),
    ("fecha vigencia", "Fecha Vigencia"),
    ("estatus", "Estatus"),
]


def normalizar(texto):
    """Minúsculas, sin tildes y con espacios simples: 'Tipo_Promoción' -> 'tipo promocion'."""
    sin_tildes = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return " ".join(sin_tildes.replace("_", " ").lower().split())


def leer_datos(ruta):
    """Devuelve un diccionario {clave: lista de filas} con las listas que vengan en el archivo."""
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    if isinstance(datos, list):  # formato antiguo: solo la lista de Supercomisión
        datos = {"filas": datos}
    if not isinstance(datos, dict):
        raise ValueError(f"Los datos deberían ser un objeto JSON y llegó: {type(datos).__name__}")

    claves = [t["clave"] for t in TABLAS]
    if not any(c in datos for c in claves):
        raise ValueError(f"Los datos no traen ninguna de las claves {claves}. Claves recibidas: {list(datos)}")
    return {c: limpiar_filas(datos.get(c), c) for c in claves}


def limpiar_filas(lista, clave):
    if lista is None or lista == "":
        return []
    if isinstance(lista, str):
        lista = json.loads(lista)
    if not isinstance(lista, list):
        raise ValueError(f'"{clave}" debería ser una lista y llegó: {type(lista).__name__}')

    filas = []
    for item in lista:
        por_clave = {normalizar(k): ("" if v is None else str(v).strip()) for k, v in item.items()}
        faltantes = [nombre for c, nombre in COLUMNAS if c not in por_clave]
        if faltantes:
            raise ValueError(f'Faltan las columnas {faltantes} en una fila de "{clave}": {item}')
        filas.append([por_clave[c] for c, _ in COLUMNAS])
    return filas


def nombre_mes(fecha, meses_despues=0):
    """Nombre del mes de la fecha, o de N meses después (diciembre + 1 -> Enero)."""
    return MESES[(fecha.month - 1 + meses_despues) % 12]


def poner_meses_arriendo(texto, fecha):
    """'Arriendo primer mes gratis' -> 'Arriendo Octubre gratis' (si fecha es de octubre)."""
    actual, siguiente = nombre_mes(fecha), nombre_mes(fecha, 1)
    texto = ARRIENDO_DOS_MESES.sub(f"Arriendo {actual} y {siguiente} gratis", texto)
    return ARRIENDO_UN_MES.sub(f"Arriendo {actual} gratis", texto)


def clase_estatus(texto):
    t = normalizar(texto)
    if "proximo" in t:
        return "b-proximo"
    if "vigente" in t:
        return "b-vigente"
    if "nueva" in t:
        return "b-nueva"
    return "b-otro"


def armar_html(titulo, filas, fecha_hora):
    lineas = []
    for edificio, tipologia, tipo, vigencia, estatus in filas:
        celdas = "".join(f"<td>{html.escape(v)}</td>" for v in (edificio, tipologia, tipo, vigencia))
        badge = f'<td><span class="badge {clase_estatus(estatus)}">{html.escape(estatus)}</span></td>'
        lineas.append(f"      <tr>{celdas}{badge}</tr>")
    plantilla = PLANTILLA.read_text(encoding="utf-8")
    return (
        plantilla.replace("__TITULO__", html.escape(titulo))
        .replace("__FECHA__", html.escape(fecha_hora))
        .replace("__FILAS__", "\n".join(lineas))
    )


def renderizar(paginas):
    """paginas: lista de (contenido_html, destino). Abre el navegador una sola vez."""
    from playwright.sync_api import sync_playwright

    opciones = {}
    if os.environ.get("CHROMIUM_PATH"):
        opciones["executable_path"] = os.environ["CHROMIUM_PATH"]
    with sync_playwright() as p:
        navegador = p.chromium.launch(**opciones)
        pagina = navegador.new_page(device_scale_factor=2)
        for contenido_html, destino in paginas:
            pagina.set_content(contenido_html, wait_until="load")
            pagina.locator("#card").screenshot(path=str(destino))
        navegador.close()


def escribir_salida(**valores):
    salida = os.environ.get("GITHUB_OUTPUT")
    if salida:
        with open(salida, "a", encoding="utf-8") as f:
            for clave, valor in valores.items():
                f.write(f"{clave}={valor}\n")


def main():
    if len(sys.argv) != 2:
        sys.exit("Uso: python scripts/generar_imagen.py ruta/a/datos.json")

    datos = leer_datos(sys.argv[1])
    ahora = datetime.now(ZONA_CHILE)
    fecha_hora = ahora.strftime("%d-%m-%Y · %H:%M")

    salidas = {"fecha": ahora.strftime("%d-%m-%Y")}
    paginas = []
    for tabla in TABLAS:
        filas = datos[tabla["clave"]]
        sufijo = tabla["sufijo"]
        if not filas:
            print(f'{tabla["titulo"]}: no llegaron promociones, no se genera imagen.')
            salidas[f"hay_filas{sufijo}"] = "false"
            continue
        if tabla["meses_arriendo"]:
            filas = [[e, t, poner_meses_arriendo(p, ahora), v, s] for e, t, p, v, s in filas]
        nombre = f'{tabla["prefijo"]}_{ahora:%Y-%m-%d_%H%M}.png'
        paginas.append((armar_html(tabla["titulo"], filas, fecha_hora), CARPETA_IMG / nombre))
        salidas[f"hay_filas{sufijo}"] = "true"
        salidas[f"archivo{sufijo}"] = nombre
        print(f'{tabla["titulo"]}: {len(filas)} filas -> publico/img/{nombre}')

    if paginas:
        CARPETA_IMG.mkdir(parents=True, exist_ok=True)
        renderizar(paginas)
    else:
        print("No llegaron promociones: no se genera imagen ni se envía WhatsApp.")

    salidas["hay_alguna"] = "true" if paginas else "false"
    escribir_salida(**salidas)


if __name__ == "__main__":
    main()
