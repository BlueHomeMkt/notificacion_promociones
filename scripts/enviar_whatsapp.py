#!/usr/bin/env python3
"""Envía la imagen del día por WhatsApp usando la plantilla aprobada en Twilio.

Variables de entorno (en GitHub van como Secrets):
    TWILIO_ACCOUNT_SID    Account SID (empieza con AC)
    TWILIO_AUTH_TOKEN     Auth Token de Twilio
    TWILIO_WHATSAPP_FROM  Número de WhatsApp de Twilio, ej. +56912345678
                          (o un Messaging Service SID que empiece con MG)
    TWILIO_CONTENT_SID    SID de la plantilla aprobada (empieza con HX)
    WHATSAPP_DESTINOS     Números de destino separados por coma, ej. +56911111111,+56922222222

Las entrega el workflow:
    ARCHIVO               Nombre del PNG, ej. promociones_supercomision_2026-09-28_1315.png
    FECHA                 Fecha para {{1}}, ej. 28-09-2026
    URL_IMAGENES          URL pública de la carpeta de imágenes (termina en /img)

Opcional:
    DRY_RUN=1             Muestra lo que enviaría, sin llamar a Twilio.

La plantilla usa {{1}} = FECHA en el texto y {{2}} = ARCHIVO en la Media URL.
"""
import json
import os
import sys
import time

import requests

API_TWILIO = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


def requerida(nombre):
    valor = os.environ.get(nombre, "").strip()
    if not valor:
        sys.exit(f"Falta la variable {nombre}. Revisa los Secrets del repositorio.")
    return valor


def como_whatsapp(numero):
    numero = numero.strip().replace(" ", "")
    return numero if numero.startswith("whatsapp:") else f"whatsapp:{numero}"


def ocultar(numero):
    """whatsapp:+56912345678 -> whatsapp:+569****5678 (para no dejar números completos en los logs)."""
    return numero[:-8] + "****" + numero[-4:] if len(numero) > 12 else numero


def esperar_imagen(url, intentos=20, pausa=15):
    """Twilio descarga la imagen al enviar, así que primero confirmamos que ya está publicada."""
    for intento in range(1, intentos + 1):
        try:
            r = requests.head(url, timeout=15, allow_redirects=True)
            tipo = r.headers.get("Content-Type", "")
            if r.status_code == 200 and tipo.startswith("image/"):
                print(f"Imagen publicada: {url}")
                return
            print(f"Intento {intento}: la imagen aún no está lista (HTTP {r.status_code}, {tipo or 'sin tipo'})")
        except requests.RequestException as e:
            print(f"Intento {intento}: error al revisar la imagen ({e})")
        time.sleep(pausa)
    sys.exit(f"La imagen no quedó disponible en {url}. No se envió ningún WhatsApp.")


def main():
    dry_run = os.environ.get("DRY_RUN") == "1"
    archivo = requerida("ARCHIVO")
    fecha = requerida("FECHA")
    url_imagen = f"{requerida('URL_IMAGENES').rstrip('/')}/{archivo}"

    sid = requerida("TWILIO_ACCOUNT_SID")
    token = requerida("TWILIO_AUTH_TOKEN")
    remitente = requerida("TWILIO_WHATSAPP_FROM")
    content_sid = requerida("TWILIO_CONTENT_SID")
    destinos = [como_whatsapp(d) for d in requerida("WHATSAPP_DESTINOS").split(",") if d.strip()]

    datos_base = {
        "ContentSid": content_sid,
        "ContentVariables": json.dumps({"1": fecha, "2": archivo}, ensure_ascii=False),
    }
    if remitente.startswith("MG"):
        datos_base["MessagingServiceSid"] = remitente
    else:
        datos_base["From"] = como_whatsapp(remitente)

    if dry_run:
        print("DRY_RUN: no se revisa la imagen ni se llama a Twilio.")
    else:
        esperar_imagen(url_imagen)

    errores = 0
    for destino in destinos:
        datos = {**datos_base, "To": destino}
        if dry_run:
            print(f"[DRY_RUN] Enviaría a {ocultar(destino)}: {datos_base['ContentVariables']}")
            continue
        r = requests.post(API_TWILIO.format(sid=sid), data=datos, auth=(sid, token), timeout=30)
        if r.status_code in (200, 201):
            print(f"Enviado a {ocultar(destino)} (SID {r.json().get('sid')})")
        else:
            errores += 1
            print(f"ERROR enviando a {ocultar(destino)}: HTTP {r.status_code} {r.text}")

    if errores:
        sys.exit(f"{errores} de {len(destinos)} envíos fallaron.")
    print(f"Listo: {len(destinos)} envío(s).")


if __name__ == "__main__":
    main()
