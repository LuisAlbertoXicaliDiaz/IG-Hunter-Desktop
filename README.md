# IgHunter Pro

Aplicación de escritorio para comparar archivos exportados de Instagram y detectar:

- Usuarios que sigues y no te siguen de vuelta.
- Usuarios que te siguen y tú no sigues.
- Usuarios con seguimiento mutuo.
- Mejores amigos.
- Solicitudes pendientes.
- Perfiles favoritos.
- Solicitudes recientes.
- Perfiles que dejaste de seguir recientemente.
- Sugerencias eliminadas.

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecución

```bash
python main.py
```

## Archivos necesarios

Desde la descarga de datos de Instagram, selecciona los archivos de seguidores y seguidos. La app acepta:

- `.html`
- `.htm`
- `.json`
- carpetas que contengan esos archivos

Si cargas la carpeta completa, la app intenta detectar automáticamente:

- `followers_1.html`
- `following.html`
- `close_friends.html`
- `pending_follow_requests.html`
- `profiles_you've_favorited.html`
- `recent_follow_requests.html`
- `recently_unfollowed_profiles.html`
- `removed_suggestions.html`

## Acciones por perfil

Cada usuario se muestra como una tarjeta con:

- Abrir perfil.
- Copiar link.
- Copiar usuario.

## Exportación

El reporte se puede guardar como:

- TXT
- CSV
- Excel

## Privacidad

La app trabaja de forma local. No pide usuario, contraseña ni envía tus archivos a internet.
