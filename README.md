# ttbot
Discord Bot para Mario Kart Time Trials
Este bot permitirá a los usuarios registrar tiempos en pistas específicas con o sin evidencias.

Comando de registro: tt <nombre_pista> <tiempo> (ejemplo: /tt Estadio Wario 01:23.456)
Comando de visualización: /tt-show <nombre_pista> (ejemplo: /tt-show Nurburgring)
Comando de visualizacion general: /tt-tracks

Los tiempos se almacenarán y se mostrarán ordenados de menor a mayor.

== Parte 1: Preparación y Configuración en Discord
Necesitamos configurar una aplicación de bot en el portal de desarrolladores de Discord.

=== Paso 1: Crea una Aplicación de Bot en Discord
Ve al Portal de Desarrolladores de Discord: Abre el navegador y ve a https://discord.com/developers/applications. Inicia sesión con tu cuenta de Discord si aún no lo has hecho.
Nueva Aplicación: Haz clic en el botón "New Application" (Nueva Aplicación) en la esquina superior derecha.
Nombra tu Aplicación: Dale un nombre a tu aplicación (ej. "RaceTimeBot", "TiempoDePistaBot"). Este será el nombre de tu bot. Luego haz clic en "Create" (Crear).
Información General (Opcional pero Recomendado):
Puedes añadir una descripción y una imagen de perfil si lo deseas. Esto es lo que verán los usuarios cuando interactúen con tu bot.
Crea el Bot:
En el menú de la izquierda, haz clic en "Bot".
Haz clic en "Add Bot" (Añadir Bot) y luego en "Yes, do it!" (Sí, ¡hazlo!).
¡MUY IMPORTANTE! Aquí verás el "TOKEN" de tu bot. Haz clic en "Copy" para copiarlo. Guarda este token en un lugar SEGURO. No lo compartas con nadie, ya que le da control total sobre tu bot. Si crees que se ha comprometido, puedes hacer clic en "Reset Token".
=== Paso 2: Habilita los Privilegios de Intención (Intents)
Discord requiere que especifiques qué tipos de eventos quieres que tu bot "escuche". Para que nuestro bot funcione correctamente, necesitamos activar algunas intenciones.

En la misma sección "Bot" (donde copiaste el token), desplázate hacia abajo hasta "Privileged Gateway Intents".

Activa los siguientes:

MESSAGE CONTENT INTENT: Este es crucial para que el bot pueda leer el contenido de los mensajes (como tt Nurburgring 01:23.456). ¡Si no lo activas, tu bot no podrá leer los comandos!
PRESENCE INTENT (opcional, pero útil si quieres que tu bot vea el estado de los usuarios)
SERVER MEMBERS INTENT (opcional, útil si tu bot necesita información sobre los miembros del servidor)
Asegúrate de que los interruptores estén en azul (activados).

=== Paso 3: Invita al  Bot a tu Servidor de Discord
URL de OAuth2: En el menú de la izquierda, haz clic en "OAuth2" y luego en "URL Generator".
Define los Permisos del Bot:
En la sección "Scopes" (Alcances), selecciona bot.
En la sección "Bot Permissions" (Permisos del Bot), selecciona los siguientes:
Read Messages/View Channels (Leer Mensajes/Ver Canales)
Send Messages (Enviar Mensajes)
Embed Links (Insertar Enlaces) - Útil para mensajes más bonitos.
Use Slash Commands (Usar Comandos de Barra) - Para nuestro comando /tt-show.
(Opcional) Manage Messages si alguna vez quieres que el bot borre mensajes, pero no es necesario para este proyecto inicial.
Genera el Enlace: Después de seleccionar los permisos, se generará una URL en la parte inferior. Cópiala.
Invita el Bot: Pega esa URL en tu navegador web. Se te pedirá que selecciones un servidor al que quieras añadir el bot. Selecciona tu servidor y haz clic en "Authorize" (Autorizar).
Verifica en Discord: Si todo salió bien, verás que tu bot se ha unido a tu servidor. Estará "Offline" por ahora, ya que aún no hemos ejecutado el código.

== Parte 2: Configuración del Entorno de Desarrollo en tu Mac
Necesitamos Python y una biblioteca para interactuar con Discord.

=== Paso 1: Instalar Python (Si no lo tienes)
Tu Mac probablemente ya tenga Python preinstalado, pero es recomendable usar una versión más reciente y gestionarla con pyenv o Homebrew.

Verifica Python: Abre la aplicación "Terminal" (puedes buscarla en Spotlight con Cmd + Space y escribiendo "Terminal").
Escribe:

Bash

python3 --version
Si ves algo como Python 3.x.x, ya lo tienes. Si no, o si ves una versión muy antigua (como Python 2.x.x), te recomiendo instalar Python 3.

Instalar Python con Homebrew (Recomendado):

Instala Homebrew (si no lo tienes): Homebrew es un gestor de paquetes para macOS. Pega el siguiente comando en tu Terminal y presiona Enter:
Bash

/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
Sigue las instrucciones en pantalla. Puede que necesites introducir tu contraseña de administrador.
Instala Python 3 con Homebrew:
Bash

brew install python
Verifica la instalación:
Bash

python3 --version
Paso 2: Crear un Entorno Virtual (Recomendado)
Un entorno virtual aísla las dependencias de tu proyecto de otras instalaciones de Python, evitando conflictos.

Crea una Carpeta para tu Proyecto: En tu Terminal, navega a la ubicación donde quieres guardar tu proyecto. Por ejemplo:
Bash

mkdir discord_time_bot
cd discord_time_bot
Crea el Entorno Virtual:
Bash

python3 -m venv venv
Activa el Entorno Virtual:
Bash

source venv/bin/activate
Notarás (venv) al principio de tu línea de comandos, indicando que el entorno virtual está activo.
Paso 3: Instalar la Biblioteca discord.py
Con tu entorno virtual activado, instala la biblioteca discord.py:
Bash

pip install discord.py
