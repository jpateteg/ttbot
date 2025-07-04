import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import re
import asyncio
import json
from unidecode import unidecode 

# --- CONFIGURACIÓN DE JSON PARA MÚLTIPLES SERVIDORES ---
DATA_DIR = 'data' 
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Cargar variables de entorno desde .env
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Configurar intents
intents = discord.Intents.default()
intents.members = True 

# Inicializar el bot con los intents
bot = commands.Bot(command_prefix=None, intents=intents) 

# Expresión regular para validar el formato de tiempo (MM:SS.mmm o SS.mmm)
TIME_REGEX = re.compile(r'^(?:(\d{1,2}):)?(\d{1,2})\.(\d{3})$')

# --- Mapeo de Pistas Normalizadas para ALMACENAMIENTO y VISUALIZACIÓN ---
# STORAGE_KEY_MAP: Mapea cualquier input normalizado a su CLAVE DE ALMACENAMIENTO CANÓNICA.
#                  Las claves aquí son unidecode().lower() del input.
#                  Los valores son la clave canónica que usaremos en el JSON.

STORAGE_KEY_MAP = {
    "aldea arborea": "aldea arborea",
    "fortaleza aerea": "fortaleza aerea",
    "fortaleza aérea": "fortaleza aerea", 
    "cine boo": "cine boo",
    "castillo de bowser": "castillo de bowser",
    "cascadas cheep cheep": "cascadas cheep cheep",
    "monte chocolate": "monte chocolate",
    "ciudad corona": "ciudad corona",
    "gruta diente de leon": "gruta diente de leon",
    "desierto sol-sol": "desierto sol-sol",
    "jungla dino dino": "jungla dino dino",
    "dk alpino": "dk alpino",
    "puerto espacial dk": "puerto espacial dk",
    "caverna osea": "caverna osea",
    "sabana salpicante": "sabana salpicante",
    "templo del bloque": "templo del bloque",
    "playa koopa": "playa koopa",
    "circuito mario bros": "circuito mario bros",
    "mario circuit": "mario circuit",
    "pradera mu-mu": "pradera mu-mu",
    "playa peach": "playa peach",
    "estadio peach": "estadio peach",
    "senda arcoiris": "senda arcoiris",
    "ciudad salina": "ciudad salina",
    "bazar shy guy": "bazar shy guy",
    "cielos helados": "cielos helados",
    "mirador estelar": "mirador estelar",
    "fabrica de toad": "fabrica toad", 
    "fabrica toad": "fabrica toad",   
    "estadio wario": "estadio wario",
    "galeon de wario": "galeon de wario",
    "canon ferroviario": "canon ferroviario",
    "aldea arborea": "aldea arborea", 
    "aldea arbórea": "aldea arborea", 
}

# TRACK_DISPLAY_NAMES: Mapea la CLAVE DE ALMACENAMIENTO CANÓNICA a un diccionario de nombres de visualización por idioma.
TRACK_DISPLAY_NAMES = {
    "aldea arborea": {"es": "Aldea Arbórea", "en": "Acorn Heights"},
    "fortaleza aerea": {"es": "Fortaleza Aérea", "en": "Airship Fortress"},
    "cine boo": {"es": "Cine Boo", "en": "Boo Cinema"},
    "castillo de bowser": {"es": "Castillo de Bowser", "en": "Bowser's Castle"},
    "cascadas cheep cheep": {"es": "Cascadas Cheep Cheep", "en": "Cheep Cheep Falls"},
    "monte chocolate": {"es": "Monte Chocolate", "en": "Choco Mountain"},
    "ciudad corona": {"es": "Ciudad Corona", "en": "Crown City"},
    "gruta diente de leon": {"es": "Gruta Diente de León", "en": "Dandelion Depths"},
    "desierto sol-sol": {"es": "Desierto Sol-Sol", "en": "Desert Hills"},
    "jungla dino dino": {"es": "Jungla Dino Dino", "en": "Dino Dino Jungle"},
    "dk alpino": {"es": "DK Alpino", "en": "DK Pass"},
    "puerto espacial dk": {"es": "Puerto Espacial DK", "en": "DK's Spaceport"},
    "caverna osea": {"es": "Caverna Ósea", "en": "Bone-Dry Burnout"},
    "sabana salpicante": {"es": "Sabana Salpicante", "en": "Faraway Oasis"},
    "templo del bloque": {"es": "Templo del Bloque", "en": "Great Block Ruins"},
    "playa koopa": {"es": "Playa Koopa", "en": "Koopa Troopa Beach"},
    "circuito mario bros": {"es": "Circuito Mario Bros", "en": "Mario Circuit"},
    "mario circuit": {"es": "Mario Circuit", "en": "Mario Circuit"}, # Redundante si ya está arriba, pero para claridad
    "pradera mu-mu": {"es": "Pradera Mu-Mu", "en": "Moo Meadows"},
    "playa peach": {"es": "Playa Peach", "en": "Peach Beach"},
    "estadio peach": {"es": "Estadio Peach", "en": "Peach Stadium"},
    "senda arcoiris": {"es": "Senda Arcoíris", "en": "Rainbow Road"},
    "ciudad salina": {"es": "Ciudad Salina", "en": "Salty Salty Speedway"},
    "bazar shy guy": {"es": "Bazar Shy Guy", "en": "Shy Guy Bazaar"},
    "cielos helados": {"es": "Cielos Helados", "en": "Sky-High Sundae"},
    "mirador estelar": {"es": "Mirador Estelar", "en": "Starview Peak"},
    "fabrica toad": {"es": "Fábrica de Toad", "en": "Toad's Factory"}, 
    "estadio wario": {"es": "Estadio Wario", "en": "Wario Stadium"},
    "galeon de wario": {"es": "Galeón de Wario", "en": "Wario's Galleon"},
    "canon ferroviario": {"es": "Cañón Ferroviario", "en": "Whistlestop Summit"},
    "aldea arborea": {"es": "Aldea Arbórea", "en": "Acorn Heights"}, 
}
# --- DATOS DE IDIOMA DEL BOT ---
LANG_DATA = {
    "es": {
        "command_tt_desc": "Registra un tiempo en una pista.",
        "command_tt_track_name_desc": "El nombre de la pista.",
        "command_tt_time_str_desc": "El tiempo en formato MM:SS.mmm o SS.mmm.",
        "command_tt_url_evidence_desc": "URL opcional de la evidencia del tiempo (ej. foto/video).",
        "response_guild_only": "Este comando solo puede usarse en un servidor.",
        "response_time_format_error": "El formato del tiempo es incorrecto. Usa `MM:SS.mmm` o `SS.mmm`.\nEjemplo: `01:23.456` o `59.123`.",
        "response_url_invalid": "La URL de evidencia proporcionada no parece ser válida. Asegúrate de que empiece con `http://` o `https://`.",
        "response_time_updated": "¡Tiempo actualizado para **{user_name}** en **{track_name}** a `{time_str}`! ¡Nuevo Récord Personal!{evidence_text}",
        "response_time_not_better": "Tu tiempo `{time_str}` en **{track_name}** no es mejor que tu récord actual de `{entry_time}`.",
        "response_time_registered": "Tiempo `{time_str}` registrado para **{user_name}** en **{track_name}**.{evidence_text}",
        "evidence_prefix": " Evidencia: {url_evidence}",

        "command_ttshow_desc": "Muestra los tiempos registrados para una pista.",
        "command_ttshow_track_name_desc": "El nombre de la pista para mostrar los tiempos.",
        "command_ttshow_link_desc": "Establece a 'True' para mostrar la columna de evidencia (Zelda).",
        "ttshow_title": "Tiempos para **{track_name}**",
        "ttshow_col_rank": "#",
        "ttshow_col_pilot": "PILOTO",
        "ttshow_col_time": "TIEMPO",
        "ttshow_col_zelda": "ZELDA",
        "ttshow_no_times": "No hay tiempos registrados para esta pista aún.",
        "ttshow_no_members": "No se encontraron miembros válidos en este servidor para mostrar.",
        "ttshow_time_missing": "---",
        "ttshow_link_na": "N/A",
        "ttshow_evidence_section_title": "Evidencia (Zelda):",
        "ttshow_footer": "Ordenado: Mejores tiempos primero, luego sin tiempo (alfabéticamente).",

        "command_tttracks_desc": "Muestra una lista de todas las pistas con tiempos registrados.",
        "tttracks_title": "Pistas con Tiempos Registrados",
        "tttracks_col_track": "PISTA",
        "tttracks_col_subidos": "SUBIDOS",
        "tttracks_no_tracks": "Aún no hay pistas con tiempos registrados en este servidor.",
        "tttracks_footer": "Listado alfabético de pistas.",

        "command_ttuser_desc": "Muestra los mejores tiempos de un usuario en todas las pistas.",
        "command_ttuser_username_desc": "El nombre de usuario del jugador.",
        "ttuser_not_found": "No se encontró al usuario **{username}** en este servidor.",
        "ttuser_no_times": "**{user_display_name}** aún no ha registrado ningún tiempo en este servidor.",
        "ttuser_title": "Mejores Tiempos de **{user_display_name}**",
        "ttuser_col_track": "PISTA",
        "ttuser_col_time": "TIEMPO",
        "ttuser_footer": "Listado alfabético de pistas.",

        "command_ttleaderboard_desc": "Muestra el top 10 de usuarios por medallas (1er, 2do, 3er lugar).",
        "command_ttleaderboard_username_desc": "Opcional: Ver el desglose de medallas de un usuario específico.",
        "ttleaderboard_no_data": "Aún no hay tiempos registrados en este servidor para generar un leaderboard.",
        "ttleaderboard_not_enough_data": "No hay suficientes tiempos registrados para generar un leaderboard (se necesitan al menos 3 tiempos únicos por pista para los puestos de medalla).",
        "ttleaderboard_general_title": "🏆 Top 10 Clasificación General por Medallas 🏆",
        "ttleaderboard_general_footer": "Clasificado por: 1er lugar > 2do lugar > 3er lugar.",
        "ttleaderboard_no_medals": "(Sin medallas)",
        "ttleaderboard_breakdown_title": "🏅 Desglose de Medallas de **{user_name}** 🏅",
        "ttleaderboard_breakdown_1st": "🥇 Primeros Lugares ({count})",
        "ttleaderboard_breakdown_2nd": "🥈 Segundos Lugares ({count})",
        "ttleaderboard_breakdown_3rd": "🥉 Terceros Lugares ({count})",
        "ttleaderboard_breakdown_no_medals": "**{user_name}** aún no ha obtenido ninguna medalla.",
        "ttleaderboard_breakdown_footer": "Pistas listadas: Nombre (Tiempo)",

        "command_sync_help": "Sincroniza los comandos de barra globales (Admin only).",
        "response_sync_success": "Comandos de barra sincronizados globalmente.",
        "bot_status_activity": "registrando tiempos",
        "bot_connected": "Bot conectado como {bot_user}!",
        "bot_id": "ID del bot: {bot_id}",
        "commands_synced_on_ready": "Comandos de barra sincronizados en on_ready.",
        "error_sync_on_ready": "Error al sincronizar comandos de barra en on_ready: {error}",
        "error_token_not_found": "Error: No se encontró el token del bot en el archivo .env.",
        
        "command_language_desc": "Cambia el idioma del bot para este servidor.",
        "command_language_lang_desc": "Elige el idioma (es/en).",
        "language_set_success": "Idioma del bot cambiado a **Español**.",
        "language_invalid": "Idioma no válido. Por favor, elige 'es' para Español o 'en' para Inglés.",
    },
    "en": {
        "command_tt_desc": "Registers a time for a track.",
        "command_tt_track_name_desc": "The name of the track.",
        "command_tt_time_str_desc": "The time in MM:SS.mmm or SS.mmm format.",
        "command_tt_url_evidence_desc": "Optional URL for time evidence (e.g., photo/video).",
        "response_guild_only": "This command can only be used in a server.",
        "response_time_format_error": "Time format is incorrect. Use `MM:SS.mmm` or `SS.mmm`.\nExample: `01:23.456` or `59.123`.",
        "response_url_invalid": "The provided evidence URL does not seem valid. Make sure it starts with `http://` or `https://`.",
        "response_time_updated": "Time updated for **{user_name}** on **{track_name}** to `{time_str}`! New Personal Best!{evidence_text}",
        "response_time_not_better": "Your time `{time_str}` on **{track_name}** is not better than your current record of `{entry_time}`.",
        "response_time_registered": "Time `{time_str}` registered for **{user_name}** on **{track_name}**.{evidence_text}",
        "evidence_prefix": " Evidence: {url_evidence}",

        "command_ttshow_desc": "Shows registered times for a track.",
        "command_ttshow_track_name_desc": "The name of the track to display times for.",
        "command_ttshow_link_desc": "Set to 'True' to show the evidence column (Zelda).",
        "ttshow_title": "Times for **{track_name}**",
        "ttshow_col_rank": "#",
        "ttshow_col_pilot": "PILOT",
        "ttshow_col_time": "TIME",
        "ttshow_col_zelda": "ZELDA",
        "ttshow_no_times": "No times registered for this track yet.",
        "ttshow_no_members": "No valid members found in this server to display.",
        "ttshow_time_missing": "---",
        "ttshow_link_na": "N/A",
        "ttshow_evidence_section_title": "Evidence (Zelda):",
        "ttshow_footer": "Sorted: Best times first, then no time (alphabetically).",

        "command_tttracks_desc": "Shows a list of all registered tracks with times.",
        "tttracks_title": "Tracks with Registered Times",
        "tttracks_col_track": "TRACK",
        "tttracks_col_subidos": "UPLOADS",
        "tttracks_no_tracks": "No tracks with registered times in this server yet.",
        "tttracks_footer": "Alphabetical list of tracks.",

        "command_ttuser_desc": "Shows a user's best times on all tracks.",
        "command_ttuser_username_desc": "The player's username.",
        "ttuser_not_found": "User **{username}** not found in this server.",
        "ttuser_no_times": "**{user_display_name}** has not registered any times on this server yet.",
        "ttuser_title": "Best Times of **{user_display_name}**",
        "ttuser_col_track": "TRACK",
        "ttuser_col_time": "TIME",
        "ttuser_footer": "Alphabetical list of tracks.",

        "command_ttleaderboard_desc": "Shows the top 10 users by medals (1st, 2nd, 3rd place).",
        "command_ttleaderboard_username_desc": "Optional: View a specific user's medal breakdown.",
        "ttleaderboard_no_data": "No times registered in this server to generate a leaderboard yet.",
        "ttleaderboard_not_enough_data": "Not enough times registered to generate a leaderboard (at least 3 unique times per track needed for medal positions).",
        "ttleaderboard_general_title": "🏆 Top 10 Overall Medal Leaderboard 🏆",
        "ttleaderboard_general_footer": "Ranked by: 1st place > 2nd place > 3rd place.",
        "ttleaderboard_no_medals": "(No medals)",
        "ttleaderboard_breakdown_title": "🏅 Medal Breakdown for **{user_name}** 🏅",
        "ttleaderboard_breakdown_1st": "🥇 First Places ({count})",
        "ttleaderboard_breakdown_2nd": "🥈 Second Places ({count})",
        "ttleaderboard_breakdown_3rd": "🥉 Third Places ({count})",
        "ttleaderboard_breakdown_no_medals": "**{user_name}** has not earned any medals yet.",
        "ttleaderboard_breakdown_footer": "Tracks listed: Name (Time)",

        "command_sync_help": "Sync global slash commands (Admin only).",
        "response_sync_success": "Global slash commands synchronized.",
        "bot_status_activity": "registering times",
        "bot_connected": "Bot connected as {bot_user}!",
        "bot_id": "Bot ID: {bot_id}",
        "commands_synced_on_ready": "Slash commands synchronized on_ready.",
        "error_sync_on_ready": "Error synchronizing slash commands on_ready: {error}",
        "error_token_not_found": "Error: Bot token not found in .env file.",

        "command_language_desc": "Changes the bot's language for this server.",
        "command_language_lang_desc": "Choose the language (es/en).",
        "language_set_success": "Bot language set to **English**.",
        "language_invalid": "Invalid language. Please choose 'es' for Spanish or 'en' for English.",
    }
}

# --- FUNCIONES DE UTILIDAD PARA SOPORTE MULTI-SERVIDOR ---

# Cargar datos desde JSON para un GUILD específico
def load_guild_data(guild_id):
    file_path = os.path.join(DATA_DIR, f"{guild_id}.json")
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            try:
                guild_data = json.load(f)
                # Asegurar que el idioma esté presente, si no, establecer español por defecto
                if 'language' not in guild_data:
                    guild_data['language'] = 'es'
                return {k: v for k, v in guild_data.items()}
            except json.JSONDecodeError:
                print(f"Error al decodificar JSON para guild {guild_id}. Inicializando con datos vacíos.")
                return {'language': 'es'} # Default language if file is corrupt
    else:
        print(f"Archivo de datos no encontrado para guild {guild_id}. Inicializando con datos vacíos.")
        return {'language': 'es'} # Default language for new guilds

# Guardar datos a JSON para un GUILD específico
def save_guild_data(guild_id, guild_data):
    file_path = os.path.join(DATA_DIR, f"{guild_id}.json")
    with open(file_path, 'w') as f:
        json.dump(guild_data, f, indent=4)
    print(f"Datos guardados para guild {guild_id} en {file_path}")

# Obtener la cadena de texto localizada
def get_localized_string(guild_id, key, **kwargs):
    guild_data = load_guild_data(guild_id)
    lang = guild_data.get('language', 'es') # Default to Spanish if not set
    
    # Si la clave no existe en el idioma específico, intentar en español como fallback
    text = LANG_DATA.get(lang, LANG_DATA['es']).get(key, LANG_DATA['es'].get(key, f"MISSING_STRING_{key}"))
    return text.format(**kwargs)


# VALIDACIÓN DE URL 
def is_valid_url(url_string):
    regex = re.compile(
        r'^(?:http)s?://' 
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' 
        r'localhost|' 
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' 
        r'(?::\d+)?' 
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url_string) is not None

# Convertir tiempo a milisegundos para comparación
def time_to_ms(time_str):
    match = TIME_REGEX.match(time_str)
    if not match:
        return float('inf') 
    minutes = int(match.group(1)) if match.group(1) else 0
    seconds = int(match.group(2))
    milliseconds = int(match.group(3))
    return (minutes * 60 * 1000) + (seconds * 1000) + milliseconds

# --- FUNCIÓN DE NORMALIZACIÓN DE PISTAS (para clave de almacenamiento) ---
def normalize_track_name(input_name):
    """
    Normaliza el nombre de una pista para usarlo como clave de almacenamiento:
    quita acentos y convierte a minúsculas. Luego, busca en STORAGE_KEY_MAP
    para obtener la clave canónica si existe un mapeo.
    """
    simple_normalized = unidecode(input_name).lower()
    return STORAGE_KEY_MAP.get(simple_normalized, simple_normalized)

# --- FUNCIÓN PARA OBTENER NOMBRE DE PISTA PARA MOSTRAR ---
def get_display_track_name(storage_key, lang_code):
    """
    Dado una clave de almacenamiento normalizada, devuelve el nombre preferido para mostrar
    desde TRACK_DISPLAY_NAMES en el idioma especificado, o capitaliza la clave si no hay un alias específico.
    """
    track_names_by_lang = TRACK_DISPLAY_NAMES.get(storage_key)
    if track_names_by_lang:
        return track_names_by_lang.get(lang_code, track_names_by_lang.get('es', storage_key.capitalize()))
    return storage_key.capitalize() # Fallback si la clave no está en TRACK_DISPLAY_NAMES

# --- FUNCIÓN DE AUTOCOMPLETADO PARA NOMBRES DE PISTAS ---
async def track_name_autocomplete(interaction: discord.Interaction, current: str):
    """
    Proporciona sugerencias de autocompletado para nombres de pistas.
    Las sugerencias se basan en los valores (nombres de visualización) de TRACK_ALIASES.
    """
    suggestions = []
    current_lower = unidecode(current).lower() 

    # Obtener el idioma del servidor para las sugerencias
    guild_id = str(interaction.guild.id) if interaction.guild else None
    lang = load_guild_data(guild_id).get('language', 'es') if guild_id else 'es'

    # Iterar sobre los NOMBRES DE VISUALIZACIÓN (valores) de TRACK_ALIASES
    unique_display_names = sorted(list(set(track_data.get(lang, track_data.get('es')) for track_data in TRACK_DISPLAY_NAMES.values())))

    for display_name in unique_display_names:
        normalized_display_name = unidecode(display_name).lower()
        if current_lower in normalized_display_name:
            suggestions.append(app_commands.Choice(name=display_name, value=display_name))
        
        if len(suggestions) >= 25: 
            break
    return suggestions

# --- FUNCIÓN DE AUTOCOMPLETADO PARA NOMBRES DE USUARIO ---
async def username_autocomplete(interaction: discord.Interaction, current: str):
    """
    Proporciona sugerencias de autocompletado para nombres de usuario del servidor.
    """
    suggestions = []
    if not interaction.guild:
        return suggestions 

    current_lower = current.lower()
    
    for member in interaction.guild.members:
        if member.bot: 
            continue
        
        if current_lower in member.display_name.lower() or \
           (member.name and current_lower in member.name.lower()):
            
            suggestions.append(app_commands.Choice(name=member.display_name, value=str(member.id)))
        
        if len(suggestions) >= 25: 
            break
    return suggestions


# --- Eventos del Bot ---

@bot.event
async def on_ready():
    """Se ejecuta cuando el bot se conecta a Discord."""
    print(get_localized_string(None, "bot_connected", bot_user=bot.user)) # No guild_id yet
    print(get_localized_string(None, "bot_id", bot_id=bot.user.id))
    await bot.change_presence(activity=discord.Game(name=get_localized_string(None, "bot_status_activity")))

    try:
        await bot.tree.sync()
        print(get_localized_string(None, "commands_synced_on_ready"))
    except Exception as e:
        print(get_localized_string(None, "error_sync_on_ready", error=e))

@bot.event
async def on_command_error(ctx, error):
    """Maneja errores en los comandos de texto (si se usara alguno)."""
    guild_id = str(ctx.guild.id) if ctx.guild else None
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(get_localized_string(guild_id, "response_arguments_missing"))
    elif isinstance(error, commands.BadArgument):
        await ctx.send(get_localized_string(guild_id, "response_invalid_argument"))
    elif isinstance(error, commands.CommandNotFound):
        pass 
    else:
        print(f'Error en el comando {ctx.command}: {error}')
        await ctx.send(get_localized_string(guild_id, "response_unexpected_error", error=error))

# --- Comandos de Barra (Slash Commands) ---

@bot.tree.command(name="tt", description=LANG_DATA['es']['command_tt_desc']) # Default ES for command desc
@app_commands.autocomplete(track_name=track_name_autocomplete) 
@discord.app_commands.describe(
    track_name=LANG_DATA['es']['command_tt_track_name_desc'],
    time_str=LANG_DATA['es']['command_tt_time_str_desc'],
    url_evidence=LANG_DATA['es']['command_tt_url_evidence_desc']
)
async def register_time_slash(interaction: discord.Interaction, track_name: str, time_str: str, url_evidence: str = None):
    guild_id = str(interaction.guild.id) if interaction.guild else None
    if not guild_id:
        await interaction.response.send_message(get_localized_string(None, "response_guild_only"), ephemeral=True)
        return
    
    current_guild_data = load_guild_data(guild_id)
    lang = current_guild_data.get('language', 'es')

    # Obtener la clave de almacenamiento normalizada
    storage_track_key = normalize_track_name(track_name) 
    # Obtener el nombre para mostrar
    display_track_name = get_display_track_name(storage_track_key, lang)
    
    # Validar formato del tiempo
    match = TIME_REGEX.match(time_str)
    if not match:
        await interaction.response.send_message(get_localized_string(guild_id, "response_time_format_error"), ephemeral=True)
        return

    # Validar URL si se proporciona
    if url_evidence:
        if not is_valid_url(url_evidence):
            await interaction.response.send_message(get_localized_string(guild_id, "response_url_invalid"), ephemeral=True)
            return

    total_ms = time_to_ms(time_str)

    user_id = str(interaction.user.id)
    user_name = interaction.user.display_name

    # Usar storage_track_key para almacenar y acceder a los datos
    if storage_track_key not in current_guild_data:
        current_guild_data[storage_track_key] = []

    found_existing = False
    for i, entry in enumerate(current_guild_data[storage_track_key]):
        if entry["user_id"] == user_id:
            existing_time_ms = time_to_ms(entry["time"])
            
            if total_ms < existing_time_ms:
                current_guild_data[storage_track_key][i] = {
                    "user_id": user_id,
                    "user_name": user_name,
                    "time": time_str,
                    "url_evidence": url_evidence
                }
                evidence_text = get_localized_string(guild_id, "evidence_prefix", url_evidence=url_evidence) if url_evidence else ""
                await interaction.response.send_message(get_localized_string(guild_id, "response_time_updated", user_name=user_name, track_name=display_track_name, time_str=time_str, evidence_text=evidence_text))
            else:
                await interaction.response.send_message(get_localized_string(guild_id, "response_time_not_better", time_str=time_str, track_name=display_track_name, entry_time=entry['time']))
            found_existing = True
            break
    
    if not found_existing:
        current_guild_data[storage_track_key].append({
            "user_id": user_id,
            "user_name": user_name,
            "time": time_str,
            "url_evidence": url_evidence
        })
        evidence_text = get_localized_string(guild_id, "evidence_prefix", url_evidence=url_evidence) if url_evidence else ""
        await interaction.response.send_message(get_localized_string(guild_id, "response_time_registered", user_name=user_name, track_name=display_track_name, time_str=time_str, evidence_text=evidence_text))

    current_guild_data[storage_track_key].sort(key=lambda x: time_to_ms(x["time"]))
    
    save_guild_data(guild_id, current_guild_data) 


@bot.tree.command(name="tt-show", description=LANG_DATA['es']['command_ttshow_desc'])
@app_commands.autocomplete(track_name=track_name_autocomplete) 
@discord.app_commands.describe(
    track_name=LANG_DATA['es']['command_ttshow_track_name_desc'],
    link=LANG_DATA['es']['command_ttshow_link_desc']
)
async def show_times(interaction: discord.Interaction, track_name: str, link: bool = False):
    await interaction.response.defer() 

    guild_id = str(interaction.guild.id) if interaction.guild else None
    if not guild_id:
        await interaction.followup.send(get_localized_string(None, "response_guild_only"))
        return
    
    current_guild_data = load_guild_data(guild_id)
    lang = current_guild_data.get('language', 'es')

    # Obtener la clave de almacenamiento normalizada del input del usuario
    input_storage_key = normalize_track_name(track_name)
    # Obtener el nombre para mostrar en el título
    display_track_name_title = get_display_track_name(input_storage_key, lang)

    # --- Lógica para CONSOLIDAR tiempos de la pista ---
    track_entries_for_display = []
    for json_track_key, entries in current_guild_data.items():
        if normalize_track_name(json_track_key) == input_storage_key:
            track_entries_for_display.extend(entries) 
    
    if not track_entries_for_display:
        track_times_for_track = {} 
    else:
        track_times_for_track_raw = {}
        for entry in track_entries_for_display:
            user_id = entry["user_id"]
            if user_id not in track_times_for_track_raw or \
               time_to_ms(entry["time"]) < time_to_ms(track_times_for_track_raw[user_id]["time"]):
                track_times_for_track_raw[user_id] = entry
        track_times_for_track = track_times_for_track_raw 

    all_user_data = []
    
    all_members = interaction.guild.members 

    for member in all_members:
        if member.bot:
            continue
        
        user_id_str = str(member.id)
        
        if user_id_str in track_times_for_track:
            entry = track_times_for_track[user_id_str]
            all_user_data.append({
                "user_id": user_id_str,
                "user_name": member.display_name,
                "time": entry["time"],
                "url_evidence": entry.get("url_evidence"),
                "has_time": True
            })
        else:
            all_user_data.append({
                "user_id": user_id_str,
                "user_name": member.display_name,
                "time": get_localized_string(guild_id, "ttshow_time_missing"), 
                "url_evidence": None,
                "has_time": False
            })

    def custom_sort_key(item):
        if item["has_time"]:
            return (0, time_to_ms(item["time"]))
        else:
            return (1, item["user_name"].lower())
            
    all_user_data.sort(key=custom_sort_key)

    description_parts = []
    
    COL_RANK_WIDTH = 3   
    COL_DRIVER_WIDTH = 15 
    COL_TIME_WIDTH = 11  
    COL_ZELDA_WIDTH = 5   

    table_header_cols = [
        f"{get_localized_string(guild_id, 'ttshow_col_rank'):<{COL_RANK_WIDTH}}", 
        f"{get_localized_string(guild_id, 'ttshow_col_pilot'):<{COL_DRIVER_WIDTH}}", 
        f"{get_localized_string(guild_id, 'ttshow_col_time'):<{COL_TIME_WIDTH}}"
    ]
    table_separator_cols = [
        f"{'-'*COL_RANK_WIDTH}", 
        f"{'-'*COL_DRIVER_WIDTH}", 
        f"{'-'*COL_TIME_WIDTH}"
    ]
    
    if link: 
        table_header_cols.append(f"{get_localized_string(guild_id, 'ttshow_col_zelda'):<{COL_ZELDA_WIDTH}}")
        table_separator_cols.append(f"{'-'*COL_ZELDA_WIDTH}")

    table_header = " | ".join(table_header_cols)
    table_separator = "-|-".join(table_separator_cols)
    
    table_rows = [table_header, table_separator]
    
    evidence_urls_list = []
    rank_counter = 0

    for i, entry in enumerate(all_user_data):
        driver_name = entry['user_name']
        time_val = entry['time'] 
        url_link = entry.get('url_evidence')
        
        if len(driver_name) > COL_DRIVER_WIDTH:
            driver_name = driver_name[:COL_DRIVER_WIDTH-3] + "..."

        display_rank = ""
        display_link_ref = get_localized_string(guild_id, "ttshow_link_na") 
        
        row_cols = []

        if entry["has_time"]:
            rank_counter += 1
            display_rank = f"{rank_counter}."
            row_cols.append(f"{display_rank:<{COL_RANK_WIDTH}}") 
            row_cols.append(f"{driver_name:<{COL_DRIVER_WIDTH}}") 
            row_cols.append(f"{time_val:<{COL_TIME_WIDTH}}") 

            if link:
                if url_link:
                    display_link_ref = "+" 
                    evidence_urls_list.append(f"[{rank_counter}] {url_link}")
                row_cols.append(f"{display_link_ref:<{COL_ZELDA_WIDTH}}")

        else: 
            row_cols.append(f"{display_rank:<{COL_RANK_WIDTH}}") 
            row_cols.append(f"{driver_name:<{COL_DRIVER_WIDTH}}") 
            row_cols.append(f"{time_val:<{COL_TIME_WIDTH}}") 

            if link:
                row_cols.append(f"{display_link_ref:<{COL_ZELDA_WIDTH}}")

        table_rows.append(" | ".join(row_cols))
    
    description_parts.append("```ansi\n" + "\n".join(table_rows) + "\n```")

    if link and evidence_urls_list:
        description_parts.append(f"\n**__{get_localized_string(guild_id, 'ttshow_evidence_section_title')}__**")
        description_parts.extend(evidence_urls_list)

    if not all_user_data:
        description_parts.append(get_localized_string(guild_id, "ttshow_no_members"))


    embed = discord.Embed(
        title=get_localized_string(guild_id, "ttshow_title", track_name=display_track_name_title), 
        description="\n".join(description_parts),
        color=discord.Color.blue()
    )
    embed.set_footer(text=get_localized_string(guild_id, "ttshow_footer"))

    await interaction.followup.send(embed=embed)

@bot.tree.command(name="tt-tracks", description=LANG_DATA['es']['command_tttracks_desc'])
async def list_tracks(interaction: discord.Interaction):
    await interaction.response.defer()

    guild_id = str(interaction.guild.id) if interaction.guild else None
    if not guild_id: 
        await interaction.followup.send(get_localized_string(None, "response_guild_only"))
        return
    
    current_guild_data = load_guild_data(guild_id) 
    lang = current_guild_data.get('language', 'es')

    if not current_guild_data:
        await interaction.followup.send(get_localized_string(guild_id, "tttracks_no_tracks"))
        return

    consolidated_tracks = {} 

    for json_track_key, entries in current_guild_data.items(): 
        # Asegurarse de que 'entries' es una lista antes de intentar iterar
        if not isinstance(entries, list):
            continue # Saltar si no es una lista de entradas de pista (ej. la clave 'language')

        storage_key = normalize_track_name(json_track_key)
        display_name = get_display_track_name(storage_key, lang) # Usar idioma
        
        unique_users_for_storage_key = len({entry["user_id"] for entry in entries})
        
        if display_name in consolidated_tracks:
            consolidated_tracks[display_name] += unique_users_for_storage_key
        else:
            consolidated_tracks[display_name] = unique_users_for_storage_key
    
    track_data_list = []
    for track_name_display, count in consolidated_tracks.items():
        track_data_list.append({
            "track_name": track_name_display, 
            "subidos_count": count
        })
    
    track_data_list.sort(key=lambda x: x["track_name"].lower()) 

    description_parts = []

    COL_TRACK_WIDTH = 20 
    COL_SUBIDOS_WIDTH = 8 

    table_header = f"{get_localized_string(guild_id, 'tttracks_col_track'):<{COL_TRACK_WIDTH}} | {get_localized_string(guild_id, 'tttracks_col_subidos'):<{COL_SUBIDOS_WIDTH}}"
    table_separator = f"{'-'*COL_TRACK_WIDTH}-|-{'-'*COL_SUBIDOS_WIDTH}"
    
    table_rows = [table_header, table_separator]

    for track_data in track_data_list:
        track_name_display = track_data["track_name"]
        subidos_count = track_data["subidos_count"]

        if len(track_name_display) > COL_TRACK_WIDTH:
            track_name_display = track_name_display[:COL_TRACK_WIDTH-3] + "..."

        table_rows.append(
            f"{track_name_display:<{COL_TRACK_WIDTH}} | {str(subidos_count):<{COL_SUBIDOS_WIDTH}}"
        )
    
    description_parts.append("```ansi\n" + "\n".join(table_rows) + "\n```")

    embed = discord.Embed(
        title=get_localized_string(guild_id, "tttracks_title"),
        description="\n".join(description_parts),
        color=discord.Color.green()
    )
    embed.set_footer(text=get_localized_string(guild_id, "tttracks_footer"))

    await interaction.followup.send(embed=embed)

# --- NUEVO COMANDO /tt-user ---
@bot.tree.command(name="tt-user", description=LANG_DATA['es']['command_ttuser_desc'])
@app_commands.autocomplete(username=username_autocomplete) 
@discord.app_commands.describe(
    username=LANG_DATA['es']['command_ttuser_username_desc']
)
async def tt_user(interaction: discord.Interaction, username: str):
    await interaction.response.defer()

    guild_id = str(interaction.guild.id) if interaction.guild else None
    if not guild_id:
        await interaction.followup.send(get_localized_string(None, "response_guild_only"))
        return

    current_guild_data = load_guild_data(guild_id)
    lang = current_guild_data.get('language', 'es')

    target_member = None
    if username.isdigit(): 
        target_member = interaction.guild.get_member(int(username))
    else: 
        for member in interaction.guild.members:
            if member.display_name == username:
                target_member = member
                break
    
    if not target_member:
        await interaction.followup.send(get_localized_string(guild_id, "ttuser_not_found", username=username))
        return

    user_id_str = str(target_member.id)
    user_display_name = target_member.display_name

    user_times = []
    for storage_key, entries in current_guild_data.items():
        # Asegurarse de que 'entries' es una lista antes de intentar iterar
        if not isinstance(entries, list):
            continue # Saltar si no es una lista de entradas de pista (ej. la clave 'language')

        best_time_for_user_on_track = None
        for entry in entries:
            if entry["user_id"] == user_id_str:
                if best_time_for_user_on_track is None or \
                   time_to_ms(entry["time"]) < time_to_ms(best_time_for_user_on_track["time"]):
                    best_time_for_user_on_track = entry
        
        if best_time_for_user_on_track:
            user_times.append({
                "track_name": get_display_track_name(storage_key, lang), 
                "time": best_time_for_user_on_track["time"]
            })
    
    if not user_times:
        await interaction.followup.send(get_localized_string(guild_id, "ttuser_no_times", user_display_name=user_display_name))
        return

    user_times.sort(key=lambda x: x["track_name"].lower())

    description_parts = []

    COL_TRACK_WIDTH = 20 
    COL_TIME_WIDTH = 11  

    table_header = f"{get_localized_string(guild_id, 'ttuser_col_track'):<{COL_TRACK_WIDTH}} | {get_localized_string(guild_id, 'ttuser_col_time'):<{COL_TIME_WIDTH}}"
    table_separator = f"{'-'*COL_TRACK_WIDTH}-|-{'-'*COL_TIME_WIDTH}"
    
    table_rows = [table_header, table_separator]

    for entry in user_times:
        track_name_display = entry["track_name"]
        time_val = entry["time"]

        if len(track_name_display) > COL_TRACK_WIDTH:
            track_name_display = track_name_display[:COL_TRACK_WIDTH-3] + "..."

        table_rows.append(
            f"{track_name_display:<{COL_TRACK_WIDTH}} | {time_val:<{COL_TIME_WIDTH}}"
        )
    
    description_parts.append("```ansi\n" + "\n".join(table_rows) + "\n```")

    embed = discord.Embed(
        title=get_localized_string(guild_id, "ttuser_title", user_display_name=user_display_name),
        description="\n".join(description_parts),
        color=discord.Color.purple() 
    )
    embed.set_footer(text=get_localized_string(guild_id, "ttuser_footer"))

    await interaction.followup.send(embed=embed)


# --- NUEVO COMANDO /tt-leaderboard ---
@bot.tree.command(name="tt-leaderboard", description=LANG_DATA['es']['command_ttleaderboard_desc'])
@app_commands.autocomplete(username=username_autocomplete) 
@discord.app_commands.describe(
    username=LANG_DATA['es']['command_ttleaderboard_username_desc']
)
async def tt_leaderboard(interaction: discord.Interaction, username: str = None): 
    await interaction.response.defer()

    guild_id = str(interaction.guild.id) if interaction.guild else None
    if not guild_id:
        await interaction.followup.send(get_localized_string(None, "response_guild_only"))
        return

    current_guild_data = load_guild_data(guild_id)
    lang = current_guild_data.get('language', 'es')

    if not current_guild_data:
        await interaction.followup.send(get_localized_string(guild_id, "ttleaderboard_no_data"))
        return

    # Emojis para las medallas
    MEDAL_GOLD = "🥇"
    MEDAL_SILVER = "🥈"
    MEDAL_BRONZE = "🥉"

    # --- Lógica para un usuario específico ---
    if username:
        target_member = None
        if username.isdigit(): 
            target_member = interaction.guild.get_member(int(username))
        else:
            for member in interaction.guild.members:
                if member.display_name == username:
                    target_member = member
                    break
        
        if not target_member:
            await interaction.followup.send(get_localized_string(guild_id, "ttuser_not_found", username=username))
            return
        
        user_id_str = str(target_member.id)
        user_display_name = target_member.display_name

        user_medals_breakdown = {
            '1st_places': [], 
            '2nd_places': [],
            '3rd_places': []
        }

        # Consolidar todos los tiempos de todas las pistas bajo sus claves de almacenamiento canónicas
        consolidated_guild_data_for_user_breakdown = {}
        for json_track_key, entries in current_guild_data.items():
            # Asegurarse de que 'entries' es una lista antes de intentar iterar
            if not isinstance(entries, list):
                continue # Saltar si no es una lista de entradas de pista (ej. la clave 'language')

            canonical_storage_key = normalize_track_name(json_track_key)
            if canonical_storage_key not in consolidated_guild_data_for_user_breakdown:
                consolidated_guild_data_for_user_breakdown[canonical_storage_key] = []
            consolidated_guild_data_for_user_breakdown[canonical_storage_key].extend(entries)

        for storage_key, entries in consolidated_guild_data_for_user_breakdown.items(): 
            if not entries:
                continue

            track_best_times = {}
            for entry in entries:
                user_id = entry["user_id"]
                if user_id not in track_best_times or \
                   time_to_ms(entry["time"]) < time_to_ms(track_best_times[user_id]["time"]):
                    track_best_times[user_id] = entry
            
            sorted_track_times = sorted(track_best_times.values(), key=lambda x: time_to_ms(x["time"]))

            if len(sorted_track_times) >= 1 and sorted_track_times[0]["user_id"] == user_id_str:
                user_medals_breakdown['1st_places'].append(f"**{get_display_track_name(storage_key, lang)}** (`{sorted_track_times[0]['time']}`)")
            
            if len(sorted_track_times) >= 2 and sorted_track_times[1]["user_id"] == user_id_str:
                user_medals_breakdown['2nd_places'].append(f"**{get_display_track_name(storage_key, lang)}** (`{sorted_track_times[1]['time']}`)")
            
            if len(sorted_track_times) >= 3 and sorted_track_times[2]["user_id"] == user_id_str:
                user_medals_breakdown['3rd_places'].append(f"**{get_display_track_name(storage_key, lang)}** (`{sorted_track_times[2]['time']}`)")
        
        embed = discord.Embed(
            title=get_localized_string(guild_id, "ttleaderboard_breakdown_title", user_name=user_display_name),
            color=discord.Color.blue()
        )

        if user_medals_breakdown['1st_places']:
            embed.add_field(name=get_localized_string(guild_id, "ttleaderboard_breakdown_1st", count=len(user_medals_breakdown['1st_places'])), 
                            value="\n".join(user_medals_breakdown['1st_places']), inline=False)
        if user_medals_breakdown['2nd_places']:
            embed.add_field(name=get_localized_string(guild_id, "ttleaderboard_breakdown_2nd", count=len(user_medals_breakdown['2nd_places'])), 
                            value="\n".join(user_medals_breakdown['2nd_places']), inline=False)
        if user_medals_breakdown['3rd_places']:
            embed.add_field(name=get_localized_string(guild_id, "ttleaderboard_breakdown_3rd", count=len(user_medals_breakdown['3rd_places'])), 
                            value="\n".join(user_medals_breakdown['3rd_places']), inline=False)
        
        if not (user_medals_breakdown['1st_places'] or user_medals_breakdown['2nd_places'] or user_medals_breakdown['3rd_places']):
            embed.description = get_localized_string(guild_id, "ttleaderboard_breakdown_no_medals", user_name=user_display_name)

        embed.set_footer(text=get_localized_string(guild_id, "ttleaderboard_breakdown_footer"))
        await interaction.followup.send(embed=embed)
        return 

    # --- Lógica para el Leaderboard General (si no se especificó un usuario) ---
    
    leaderboard_data = {}

    consolidated_guild_data_for_leaderboard = {}
    for json_track_key, entries in current_guild_data.items():
        # Asegurarse de que 'entries' es una lista antes de intentar iterar
        if not isinstance(entries, list):
            continue # Saltar si no es una lista de entradas de pista (ej. la clave 'language')

        canonical_storage_key = normalize_track_name(json_track_key)
        if canonical_storage_key not in consolidated_guild_data_for_leaderboard:
            consolidated_guild_data_for_leaderboard[canonical_storage_key] = []
        consolidated_guild_data_for_leaderboard[canonical_storage_key].extend(entries)

    for storage_key, entries in consolidated_guild_data_for_leaderboard.items(): 
        if not entries: 
            continue

        track_best_times = {} 
        for entry in entries:
            user_id = entry["user_id"]
            if user_id not in track_best_times or \
               time_to_ms(entry["time"]) < time_to_ms(track_best_times[user_id]["time"]):
                track_best_times[user_id] = entry
        
        sorted_track_times = sorted(track_best_times.values(), key=lambda x: time_to_ms(x["time"]))

        if len(sorted_track_times) >= 1:
            first_place_user_id = sorted_track_times[0]["user_id"]
            leaderboard_data.setdefault(first_place_user_id, {'1st': 0, '2nd': 0, '3rd': 0, 'display_name': sorted_track_times[0]["user_name"]})
            leaderboard_data[first_place_user_id]['1st'] += 1
        
        if len(sorted_track_times) >= 2:
            second_place_user_id = sorted_track_times[1]["user_id"]
            leaderboard_data.setdefault(second_place_user_id, {'1st': 0, '2nd': 0, '3rd': 0, 'display_name': sorted_track_times[1]["user_name"]})
            leaderboard_data[second_place_user_id]['2nd'] += 1
        
        if len(sorted_track_times) >= 3:
            third_place_user_id = sorted_track_times[2]["user_id"]
            leaderboard_data.setdefault(third_place_user_id, {'1st': 0, '2nd': 0, '3rd': 0, 'display_name': sorted_track_times[2]["user_name"]})
            leaderboard_data[third_place_user_id]['3rd'] += 1

    leaderboard_list = list(leaderboard_data.items())

    leaderboard_list.sort(key=lambda item: (item[1]['1st'], item[1]['2nd'], item[1]['3rd']), reverse=True)

    top_10_leaderboard = leaderboard_list[:10]

    if not top_10_leaderboard:
        await interaction.followup.send(get_localized_string(guild_id, "ttleaderboard_not_enough_data"))
        return

    description_parts = []
    
    for i, (user_id, stats) in enumerate(top_10_leaderboard):
        rank = i + 1
        display_name = stats['display_name'] 
        
        gold_count = stats['1st']
        silver_count = stats['2nd']
        bronze_count = stats['3rd']

        medals_string = (
            f"{MEDAL_GOLD}{gold_count} " if gold_count > 0 else ""
        ) + (
            f"{MEDAL_SILVER}{silver_count} " if silver_count > 0 else ""
        ) + (
            f"{MEDAL_BRONZE}{bronze_count}" if bronze_count > 0 else ""
        )
        
        if not medals_string:
            medals_string = get_localized_string(guild_id, "ttleaderboard_no_medals")

        description_parts.append(
            f"**{rank}. {display_name}** {medals_string.strip()}"
        )

    embed = discord.Embed(
        title=get_localized_string(guild_id, "ttleaderboard_general_title"),
        description="\n".join(description_parts),
        color=discord.Color.gold() 
    )
    embed.set_footer(text=get_localized_string(guild_id, "ttleaderboard_general_footer"))

    await interaction.followup.send(embed=embed)

# --- Sincronizar Comandos de Barra ---
@bot.command(name='sync', help=LANG_DATA['es']['command_sync_help'])
@commands.is_owner()
async def sync_commands(ctx):
    await bot.tree.sync()
    guild_id = str(ctx.guild.id) if ctx.guild else None
    await ctx.send(get_localized_string(guild_id, "response_sync_success"))
    print(get_localized_string(guild_id, "response_sync_success"))


# --- NUEVO COMANDO /tt-language ---
@bot.tree.command(name="tt-language", description=LANG_DATA['es']['command_language_desc'])
@discord.app_commands.describe(
    language=LANG_DATA['es']['command_language_lang_desc']
)
@app_commands.choices(language=[
    app_commands.Choice(name="Español", value="es"),
    app_commands.Choice(name="English", value="en"),
])
@commands.has_permissions(manage_guild=True) # Solo administradores del servidor
async def tt_language(interaction: discord.Interaction, language: str):
    await interaction.response.defer(ephemeral=True) # Respuesta solo visible para el usuario

    if not interaction.guild:
        await interaction.followup.send(get_localized_string(None, "response_guild_only"))
        return

    guild_id = str(interaction.guild.id)
    current_guild_data = load_guild_data(guild_id)

    if language not in LANG_DATA:
        await interaction.followup.send(get_localized_string(guild_id, "language_invalid"))
        return

    current_guild_data['language'] = language
    save_guild_data(guild_id, current_guild_data)
    
    # Sincronizar comandos para actualizar descripciones de comandos
    try:
        await bot.tree.sync()
        print(f"Comandos sincronizados para guild {guild_id} después de cambio de idioma.")
    except Exception as e:
        print(f"Error al sincronizar comandos después de cambio de idioma: {e}")

    await interaction.followup.send(get_localized_string(guild_id, "language_set_success"))


# Iniciar el bot
if __name__ == "__main__":
    if not TOKEN:
        print(get_localized_string(None, "error_token_not_found"))
    else:
        bot.run(TOKEN)
