## 🤖 Discord Bot para Mario Kart Time Trials
Este bot de Discord permite a los usuarios registrar y visualizar sus tiempos en pistas específicas de Mario Kart, con la opción de incluir evidencia (URL).

## ✨ Características Principales
Registro de Tiempos: /tt <nombre_pista> <tiempo> [url_evidencia]

Ejemplo: /tt Estadio Wario 01:23.456 url_evidencia:https://link.a.tu.foto/

El campo url_evidencia es opcional.

Visualización de Tiempos por Pista: /tt-show <nombre_pista> [link:True]

Ejemplo: /tt-show Nurburgring (muestra solo piloto y tiempo)

Ejemplo: /tt-show Nurburgring link:True (muestra piloto, tiempo y columna Zelda con evidencia)

Visualización General de Pistas: /tt-tracks

Muestra una tabla con todas las pistas registradas y la cantidad de usuarios que han subido un tiempo para cada una.

Persistencia de Datos: Los tiempos se almacenan en archivos JSON separados para cada servidor, asegurando que los récords de cada equipo sean independientes.

Formato de Tabla Bonito: Las salidas se presentan en tablas formateadas para una mejor legibilidad.

Ordenación: Los tiempos se muestran ordenados de menor a mayor.

## 🚀 Guía de Configuración y Ejecución
Sigue estos pasos para configurar y poner en marcha tu bot en un entorno macOS.

### Parte 1: Preparación y Configuración en Discord
Necesitamos configurar una aplicación de bot en el Portal de Desarrolladores de Discord.

#### Paso 1: Crea una Aplicación de Bot en Discord
Ve al Portal de Desarrolladores de Discord: Abre tu navegador y ve a https://discord.com/developers/applications. Inicia sesión con tu cuenta de Discord si aún no lo has hecho.

Nueva Aplicación: Haz clic en el botón "New Application" (Nueva Aplicación) en la esquina superior derecha.

Nombra tu Aplicación: Dale un nombre a tu aplicación (ej. "RaceTimeBot", "TiempoDePistaBot"). Este será el nombre de tu bot. Luego haz clic en "Create" (Crear).

Información General (Opcional pero Recomendado): Puedes añadir una descripción y una imagen de perfil si lo deseas. Esto es lo que verán los usuarios cuando interactúen con tu bot.

Crea el Bot: En el menú de la izquierda, haz clic en "Bot". Haz clic en "Add Bot" (Añadir Bot) y luego en "Yes, do it!" (Sí, ¡hazlo!).

¡MUY IMPORTANTE! Copia el "TOKEN" de tu bot. Haz clic en "Copy" para copiarlo. Guarda este token en un lugar SEGURO. No lo compartas con nadie, ya que le da control total sobre tu bot. Si crees que se ha comprometido, puedes hacer clic en "Reset Token".

#### Paso 2: Habilita los Privilegios de Intención (Intents)
Discord requiere que especifiques qué tipos de eventos quieres que tu bot "escuche". Para que nuestro bot funcione correctamente, necesitamos activar algunas intenciones.

En la misma sección "Bot" (donde copiaste el token), desplázate hacia abajo hasta "Privileged Gateway Intents".

Activa los siguientes (asegúrate de que los interruptores estén en azul):

MESSAGE CONTENT INTENT: Este es crucial para que el bot pueda leer el contenido de los mensajes (aunque para los comandos de barra no es estrictamente necesario, es buena práctica tenerlo activado para futuras expansiones).

PRESENCE INTENT: Necesario para que tu bot muestre su estado "Online" en Discord.

SERVER MEMBERS INTENT: Necesario para que el bot pueda obtener la lista de miembros del servidor (para la función /tt-show).

¡Haz clic en "Save Changes" (o "Finalizar actualización") en la parte inferior de la página para guardar los cambios!

#### Paso 3: Invita tu Bot a tu Servidor de Discord
URL de OAuth2: En el menú de la izquierda, haz clic en "OAuth2" y luego en "URL Generator".

Define los Scopes (Alcances): En la sección "Scopes", selecciona:

bot

applications.commands (Crucial para que los comandos de barra funcionen).

Define los Permisos del Bot (Bot Permissions): Al seleccionar los scopes anteriores, aparecerá la sección "Bot Permissions". Selecciona los siguientes:

General Permissions:

View Channels (Ver Canales)

Text Permissions:

Send Messages (Enviar Mensajes)

Embed Links (Insertar Enlaces)

Use Slash Commands (Usar Comandos de Barra)

(Opcional) Manage Messages si alguna vez quieres que el bot borre mensajes.

Genera el Enlace: Después de seleccionar los permisos, se generará una URL en la parte inferior bajo "Generated URL". Cópiala.

Invita el Bot: Pega esa URL en tu navegador web. Se te pedirá que selecciones un servidor al que quieras añadir el bot. Selecciona tu servidor y haz clic en "Authorize" (Autorizar). Completa cualquier verificación de seguridad.

Verifica en Discord: Si todo salió bien, verás que tu bot se ha unido a tu servidor y aparecerá en la lista de miembros (inicialmente "Offline" hasta que ejecutes el código).

### Parte 2: Configuración del Entorno de Desarrollo en tu Mac
Necesitamos Python y la biblioteca discord.py para interactuar con Discord.

#### Paso 1: Instalar Python (Si no lo tienes)
Tu Mac probablemente ya tenga Python preinstalado, pero es recomendable usar una versión más reciente y gestionarla con Homebrew.

Verifica Python: Abre la aplicación "Terminal" (puedes buscarla en Spotlight con Cmd + Space y escribiendo "Terminal").
Escribe:

python3 --version

Si ves algo como Python 3.x.x (idealmente 3.9 o superior), ya lo tienes. Si no, o si ves una versión muy antigua (como Python 2.x.x), te recomiendo instalar Python 3.

Instalar Python con Homebrew (Recomendado):

Instala Homebrew (si no lo tienes): Pega el siguiente comando en tu Terminal y presiona Enter:

/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

Sigue las instrucciones en pantalla.

Instala Python 3 con Homebrew:

brew install python

Verifica la instalación:

python3 --version

#### Paso 2: Crear un Entorno Virtual (Recomendado)
Un entorno virtual aísla las dependencias de tu proyecto de otras instalaciones de Python, evitando conflictos.

Crea una Carpeta para tu Proyecto: En tu Terminal, navega a la ubicación donde quieres guardar tu proyecto. Por ejemplo:

mkdir discord_time_bot
cd discord_time_bot

Crea el Entorno Virtual:

python3 -m venv venv

Activa el Entorno Virtual:

source venv/bin/activate

Notarás (venv) al principio de tu línea de comandos, indicando que el entorno virtual está activo.

#### Paso 3: Instalar las Bibliotecas Necesarias
Con tu entorno virtual activado, instala las bibliotecas discord.py y python-dotenv:

pip install discord.py python-dotenv

