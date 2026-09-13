# 🎯 IG Hunter Pro

> **Una herramienta de escritorio rápida, segura y local para analizar tus conexiones de Instagram.**

IG Hunter Pro procesa los archivos de datos exportados directamente desde tu cuenta de Instagram para ofrecerte un análisis detallado de tu red, permitiéndote gestionar tu perfil de manera eficiente y sin comprometer tu privacidad.

---

## ✨ Características Principales

Compara tus listas de datos en segundos y detecta al instante:

* 🕵️ **Seguimiento asimétrico:** Usuarios que sigues pero no te devuelven el *follow*, y aquellos que te siguen pero tú no.
* 🤝 **Conexiones mutuas:** Perfiles con seguimiento recíproco.
* ⭐️ **Listas especiales:** Mejores amigos y Perfiles favoritos.
* ⏳ **Gestión de solicitudes:** Solicitudes pendientes de aprobación y solicitudes enviadas recientemente.
* 🗑️ **Historial de limpieza:** Perfiles que dejaste de seguir recientemente y sugerencias que eliminaste.

---

## 🚀 Instalación y Ejecución

Asegúrate de tener Python instalado en tu sistema antes de comenzar.

**1. Instalar dependencias:**
```bash
pip install -r requirements.txt
2. Iniciar la aplicación:

Bash
python main.py
📁 Archivos Necesarios
Para utilizar la herramienta, solicita la descarga de tu información desde la configuración de Instagram. La aplicación es altamente flexible y soporta archivos individuales o directorios completos en los siguientes formatos: .html, .htm y .json.

Si seleccionas la carpeta raíz de tu extracción, el sistema autodetectará y procesará inteligentemente los siguientes archivos:

followers_1.html

following.html

close_friends.html

pending_follow_requests.html

profiles_you've_favorited.html

recent_follow_requests.html

recently_unfollowed_profiles.html

removed_suggestions.html

🛠️ Acciones y Exportación
Gestión Individual por Perfil
Cada usuario detectado se presenta en una tarjeta gráfica interactiva que te permite:

🔗 Abrir perfil: Visitar la cuenta directamente en tu navegador.

📋 Copiar link: Obtener la URL directa del usuario.

👤 Copiar usuario: Extraer el username exacto (ideal para búsquedas).

Exportación de Reportes
Guarda los resultados de tu análisis para revisarlos más tarde. Soporta múltiples formatos de salida:

📄 TXT (Texto plano)

📊 CSV (Valores separados por comas)

📗 Excel (Hoja de cálculo)

🔒 Privacidad y Seguridad Total
Tus datos se quedan en tu equipo.

IG Hunter Pro ha sido diseñado con una arquitectura 100% local. La aplicación no solicita tu usuario ni tu contraseña, y ningún archivo o dato analizado es enviado a internet. Eres el único dueño de tu información.

👨‍💻 Desarrollador
Luis Alberto Xicali Díaz

Ingeniería en Desarrollo y Gestión de Software, UTP

Puebla, México


Al visualizarse en GitHub, este formato organizará la información en bloques claros. Las c