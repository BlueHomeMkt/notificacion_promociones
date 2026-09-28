# Notificación de promociones Supercomisión

Cada vez que el flujo de Power Automate "Enviar promos diario" publica la tabla de Supercomisión en Teams, también le envía los datos a este repositorio. GitHub Actions genera la imagen con el diseño aprobado, la publica en GitHub Pages y la envía por WhatsApp con la plantilla aprobada en Twilio.

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

**Settings → Secrets and variables → Actions → New repository secret**. Crea estos cinco:

| Nombre | Valor |
|---|---|
| `TWILIO_ACCOUNT_SID` | El Account SID (empieza con `AC`) |
| `TWILIO_AUTH_TOKEN` | Un Auth Token **nuevo** (el anterior quedó escrito en un chat) |
| `TWILIO_WHATSAPP_FROM` | El número de WhatsApp de Twilio, ej. `+56912345678` |
| `TWILIO_CONTENT_SID` | El SID de la plantilla (empieza con `HX`). Si aún no la tienes, deja `pendiente` y lo cambias después |
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

### 6. Prueba de envío

Deja temporalmente solo tu número en `WHATSAPP_DESTINOS` y corre **Run workflow** con "¿Enviar también el WhatsApp?" en **si**. Te debería llegar la imagen con los datos de ejemplo.

### 7. Conectar Power Automate

En el flujo "Enviar promos diario", en la rama de Supercomisión, agrega una **rama paralela** junto a los pasos "Publicar mensaje en chat Supercomisión…". Así, si esta parte falla, los mensajes de Teams siguen llegando.

1. Acción **Redactar** (renómbrala "Datos para GitHub"). En Entradas escribe `{"filas": }` y, después de los dos puntos, inserta desde el contenido dinámico la **Salida** de "Limpiar columnas Supercomisión":

   ```
   {"filas": [Salida de Limpiar columnas Supercomisión]}
   ```

2. Acción de GitHub **Crear un evento de distribución de repositorio**:
   - Propietario: `BlueHomeMkt`
   - Repositorio: `notificacion_promociones`
   - Tipo de evento: `promos_supercomision` (exactamente así)
   - Carga del cliente (client payload): las **Salidas** de "Datos para GitHub"

3. La primera vez te pedirá iniciar sesión en GitHub. En la pantalla de autorización, presiona **Grant** junto a **BlueHomeMkt**. Si no lo haces, GitHub no deja que Power Automate use la organización y la acción falla con "Not Found".

4. Guarda y prueba el flujo. En la pestaña **Actions** del repositorio debería aparecer una ejecución nueva.

## Qué pasa cada lunes y jueves

1. Power Automate publica la tabla en Teams (como siempre) y envía los datos a GitHub.
2. GitHub Actions genera la imagen con la fecha y hora de Chile, la guarda en `publico/img/` y la publica.
3. Espera a que la imagen esté disponible y envía la plantilla de WhatsApp a cada número de `WHATSAPP_DESTINOS`.

Si ese día no hay promociones, no se genera imagen ni se envía nada.

## Si algo falla

- GitHub envía un correo cuando una ejecución falla. En **Actions** se ve el detalle de cada paso.
- Los errores de Twilio aparecen en el paso "Enviar WhatsApp" con su código (por ejemplo, 401 = credenciales incorrectas). En la consola de Twilio, **Monitor → Logs → Messaging** muestra el estado de cada mensaje.

## Mantenimiento

- **Cambiar destinatarios:** edita el Secret `WHATSAPP_DESTINOS`. Cada destinatario debe haber aceptado recibir mensajes de Blue Home por WhatsApp (política de Meta).
- **Cambiar el diseño:** edita `scripts/plantilla.html`.
- **Si cambias de Auth Token en Twilio:** actualiza el Secret `TWILIO_AUTH_TOKEN`.
- **Continuidad:** la organización BlueHomeMkt debe tener al menos dos Owners. Si quien conectó GitHub en Power Automate deja la empresa, otra persona debe volver a conectarlo con su cuenta.

## Importante

El repositorio es público: cualquiera que tenga el link puede ver las imágenes. Nunca pongas tokens ni claves en los archivos; van solo en los Secrets.
