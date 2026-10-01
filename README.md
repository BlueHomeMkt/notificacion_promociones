# Notificación de promociones (Supercomisión + Corretaje y Arriendo)

El flujo de Power Automate "Envío de promos freelances" le envía a este repositorio las promociones de Supercomisión y las de Corretaje y Arriendo vigentes. GitHub Actions genera **una imagen por cada tabla** con el diseño aprobado, las publica en GitHub Pages y las envía por WhatsApp en **dos mensajes**: primero Supercomisión y después Corretaje y Arriendo.

```
Power Automate ──► GitHub Actions ──► imagen PNG ──► GitHub Pages ──► Twilio ──► WhatsApp
```

## Qué hay en el repositorio

| Archivo | Para qué sirve |
|---|---|
| `.github/workflows/enviar-promociones.yml` | Los pasos que corre GitHub Actions |
| `scripts/plantilla.html` | El diseño de la imagen (aquí se cambia el diseño) |
| `scripts/generar_imagen.py` | Arma la imagen a partir de los datos |
| `scripts/enviar_whatsapp.py` | Envía la plantilla de WhatsApp por Twilio |
| `datos/ejemplo.json` | Datos de prueba para las ejecuciones manuales |
| `publico/img/` | Las imágenes publicadas (las agrega el workflow) |

## Instalación (una sola vez)

### 1. Subir los archivos

En el repositorio, entra a **Add file → Upload files**, arrastra todo el contenido de esta carpeta (incluida la carpeta `.github`) y presiona **Commit changes**.

### 2. Activar GitHub Pages

**Settings → Pages → Build and deployment → Source: GitHub Actions**.
(Tiene que ser "GitHub Actions", no "Deploy from a branch".)

### 3. Cargar los Secrets

**Settings → Secrets and variables → Actions → New repository secret**. Crea estos seis:

| Nombre | Valor |
|---|---|
| `TWILIO_ACCOUNT_SID` | El Account SID (empieza con `AC`) |
| `TWILIO_AUTH_TOKEN` | Un Auth Token **nuevo** (el anterior quedó escrito en un chat) |
| `TWILIO_WHATSAPP_FROM` | El número de WhatsApp de Twilio, ej. `+56912345678` |
| `TWILIO_CONTENT_SID` | El SID de la plantilla (empieza con `HX`). Si aún no la tienes, deja `pendiente` y lo cambias después |
| `TWILIO_CONTENT_SID_CORRETAJE` | El SID de la plantilla de Corretaje y Arriendo (empieza con `HX`). Mientras no exista, no lo crees: la imagen se publica igual y solo se salta ese WhatsApp |
| `WHATSAPP_DESTINOS` | Los números que reciben el mensaje, separados por coma, ej. `+56911111111,+56922222222` |

Los Secrets no los puede ver nadie, ni siquiera en los registros del workflow.

### 4. Primera ejecución (publica la imagen de ejemplo)

**Actions → Enviar promociones Supercomisión → Run workflow**, con "¿Enviar también el WhatsApp?" en **no**.

Cuando termine (unos 2 minutos), esta URL debería mostrar la imagen:
https://bluehomemkt.github.io/notificacion_promociones/img/promociones_supercomision_2026-09-28.png

### 5. Terminar la plantilla de Twilio y enviarla a aprobación

- **Media URL:** `https://bluehomemkt.github.io/notificacion_promociones/img/{{2}}`
- **Valores de ejemplo:** `{{1}}` = `28-09-2026` · `{{2}}` = `promociones_supercomision_2026-09-28.png`

Cuando Meta la apruebe, copia el Content SID (`HX...`) en el Secret `TWILIO_CONTENT_SID`.

**Segunda plantilla (Corretaje y Arriendo):** crea otra plantilla igual, con un texto propio para estas promociones y la misma Media URL `https://bluehomemkt.github.io/notificacion_promociones/img/{{2}}`.
- **Valores de ejemplo:** `{{1}}` = `28-09-2026` · `{{2}}` = `promociones_corretaje_arriendo_2026-09-28.png`

Cuando Meta la apruebe, copia su Content SID en el Secret `TWILIO_CONTENT_SID_CORRETAJE`.

### 6. Prueba de envío

Deja temporalmente solo tu número en `WHATSAPP_DESTINOS` y corre **Run workflow** con "¿Enviar también el WhatsApp?" en **si**. Te debería llegar la imagen con los datos de ejemplo.

### 7. Conectar Power Automate

En el flujo "Enviar promos diario", en la rama de Supercomisión, agrega una **rama paralela** junto a los pasos "Publicar mensaje en chat Supercomisión…". Así, si esta parte falla, los mensajes de Teams siguen llegando.

1. Acción **Redactar** (renómbrala "Datos para GitHub"). En Entradas arma este JSON, insertando desde el contenido dinámico la **Salida** de cada "Limpiar columnas…":

   ```
   {"filas": [Salida de Limpiar columnas Supercomisión], "filas_corretaje": [Salida de Limpiar columnas Corretaje]}
   ```

   `filas_corretaje` es opcional: si no viene o viene vacía, solo se envía la imagen de Supercomisión (y al revés).

2. Acción de GitHub **Crear un evento de distribución de repositorio**:
   - Propietario: `BlueHomeMkt`
   - Repositorio: `notificacion_promociones`
   - Tipo de evento: `promos_supercomision` (exactamente así)
   - Carga del cliente (client payload): las **Salidas** de "Datos para GitHub"

3. La primera vez te pedirá iniciar sesión en GitHub. En la pantalla de autorización, presiona **Grant** junto a **BlueHomeMkt**. Si no lo haces, GitHub no deja que Power Automate use la organización y la acción falla con "Not Found".

4. Guarda y prueba el flujo. En la pestaña **Actions** del repositorio debería aparecer una ejecución nueva.

## Qué pasa cada lunes y jueves

1. Power Automate envía a GitHub las dos tablas de promociones.
2. GitHub Actions genera una imagen por tabla con la fecha y hora de Chile, las guarda en `publico/img/` y las publica.
3. Envía el WhatsApp de Supercomisión y luego el de Corretaje y Arriendo a cada número de `WHATSAPP_DESTINOS`. Si el primero falla, el segundo se intenta igual.

Si una tabla viene vacía, esa imagen no se genera ni se envía. Si las dos vienen vacías, no se envía nada.

## Si algo falla

- GitHub envía un correo cuando una ejecución falla. En **Actions** se ve el detalle de cada paso.
- Los errores de Twilio aparecen en el paso "Enviar WhatsApp" con su código (por ejemplo, 401 = credenciales incorrectas). En la consola de Twilio, **Monitor → Logs → Messaging** muestra el estado de cada mensaje.

## Mantenimiento

- **Cambiar destinatarios:** edita el Secret `WHATSAPP_DESTINOS`. Cada destinatario debe haber aceptado recibir mensajes de Blue Home por WhatsApp (política de Meta).
- **Cambiar el diseño:** edita `scripts/plantilla.html` (vale para las dos imágenes).
- **Cambiar los títulos de las imágenes:** edita la lista `TABLAS` al inicio de `scripts/generar_imagen.py`.
- **Si cambias de Auth Token en Twilio:** actualiza el Secret `TWILIO_AUTH_TOKEN`.
- **Continuidad:** la organización BlueHomeMkt debe tener al menos dos Owners. Si quien conectó GitHub en Power Automate deja la empresa, otra persona debe volver a conectarlo con su cuenta.

## Importante

El repositorio es público: cualquiera que tenga el link puede ver las imágenes. Nunca pongas tokens ni claves en los archivos; van solo en los Secrets.
