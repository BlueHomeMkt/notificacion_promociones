#!/usr/bin/env python3
"""Genera la imagen "Promociones Supercomisión Vigentes" con el diseño aprobado.

Uso:
    python scripts/generar_imagen.py ruta/a/datos.json

El archivo de datos es lo que envía Power Automate:
    {"filas": [{"Edificio": "...", "Tipología": "...", "Tipo Promoción": "...",
                "Fecha Vigencia": "...", "Estatus": "..."}, ...]}

"filas" también puede venir como texto JSON. Los nombres de columna se
reconocen aunque cambien mayúsculas, tildes o guiones bajos.

Guarda el PNG en publico/img/ y, si corre en GitHub Actions, deja en la salida
del paso: hay_filas, archivo (nombre del PNG) y fecha (DD-MM-AAAA).
"""
import html
import json
import os
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parent.parent
PLANTILLA = RAIZ / "scripts" / "plantilla.html"
CARPETA_IMG = RAIZ / "publico" / "img"
ZONA_CHILE = ZoneInfo("America/Santiago")

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


def leer_filas(ruta):
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    if isinstance(datos, dict):
        if "filas" not in datos:
            raise ValueError(f'Los datos no traen la clave "filas". Claves recibidas: {list(datos)}')
        datos = datos["filas"]
    if isinstance(datos, str):
        datos = json.loads(datos)
    if not isinstance(datos, list):
        raise ValueError(f'"filas" debería ser una lista y llegó: {type(datos).__name__}')

    filas = []
    for item in datos:
        por_clave = {normalizar(k): ("" if v is None else str(v).strip()) for k, v in item.items()}
        faltantes = [nombre for clave, nombre in COLUMNAS if clave not in por_clave]
        if faltantes:
            raise ValueError(f"Faltan las columnas {faltantes} en la fila: {item}")
        filas.append([por_clave[clave] for clave, _ in COLUMNAS])
    return filas


def clase_estatus(texto):
    t = normalizar(texto)
    if "proximo" in t:
        return "b-proximo"
    if "vigente" in t:
        return "b-vigente"
    if "nueva" in t:
        return "b-nueva"
    return "b-otro"


def armar_html(filas, fecha_hora):
    lineas = []
    for edificio, tipologia, tipo, vigencia, estatus in filas:
        celdas = "".join(f"<td>{html.escape(v)}</td>" for v in (edificio, tipologia, tipo, vigencia))
        badge = f'<td><span class="badge {clase_estatus(estatus)}">{html.escape(estatus)}</span></td>'
        lineas.append(f"      <tr>{celdas}{badge}</tr>")
    plantilla = PLANTILLA.read_text(encoding="utf-8")
    return plantilla.replace("__FECHA__", html.escape(fecha_hora)).replace("__FILAS__", "\n".join(lineas))


def renderizar(contenido_html, destino):
    from playwright.sync_api import sync_playwright

    opciones = {}
    if os.environ.get("CHROMIUM_PATH"):
        opciones["executable_path"] = os.environ["CHROMIUM_PATH"]
    with sync_playwright() as p:
        navegador = p.chromium.launch(**opciones)
        pagina = navegador.new_page(device_scale_factor=2)
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

    filas = leer_filas(sys.argv[1])
    if not filas:
        print("No llegaron promociones: no se genera imagen ni se envía WhatsApp.")
        escribir_salida(hay_filas="false")
        return

    ahora = datetime.now(ZONA_CHILE)
    nombre = f"promociones_supercomision_{ahora:%Y-%m-%d_%H%M}.png"
    CARPETA_IMG.mkdir(parents=True, exist_ok=True)
    destino = CARPETA_IMG / nombre

    renderizar(armar_html(filas, ahora.strftime("%d-%m-%Y · %H:%M")), destino)
    print(f"Imagen generada: {destino.relative_to(RAIZ)} ({len(filas)} filas)")
    escribir_salida(hay_filas="true", archivo=nombre, fecha=ahora.strftime("%d-%m-%Y"))


if __name__ == "__main__":
    main()
