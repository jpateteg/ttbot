import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import re
import asyncio
import json

# --- CONFIGURACIÓN DE JSON PARA MÚLTIPLES SERVIDORES ---
# Define el directorio donde se guardarán los archivos JSON de cada servidor
DATA_DIR = 'data' 
# Crea el directorio si no existe (importante al inicio del script)
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Cargar variables de entorno desde .env
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Configurar intents
intents = discord.Intents.default()
intents.members = True # Necesario para obtener todos los miembros del servidor y para el guild install

# Inicializar el bot con los intents
bot = commands.Bot(command_prefix=None, intents=intents) 

# track_times ya NO será una variable global que contiene todos los datos de todos los servidores.
# Ahora las funciones cargarán y guardarán los datos del servidor específico al que pertenecen.
# La variable track_times global se puede eliminar o comentar si aún existe de versiones anteriores.
# track_times = {} # ELIMINAR O COMENTAR ESTA LÍNEA SI ESTÁ PRESENTE

# Expresión regular para validar el formato de tiempo (MM:SS.mmm o SS.mmm)
TIME_REGEX = re.compile(r'^(?:(\d{1,2}):)?(\d{1,2})\.(\d{3})$')

# --- FUNCIONES DE UTILIDAD PARA SOPORTE MULTI-SERVIDOR ---

# Cargar datos desde JSON para un GUILD específico
def load_guild_data(guild_id):
    file_path = os.path.join(DATA_DIR, f"{guild_id}.json")
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            try:
                guild_data = json.load(f)
                # Asegurarse de que track_name_key sea string para consistencia
                # (JSON guarda keys como strings, pero solo por si acaso)
                return {k: v for k, v in guild_data.items()}
            except json.JSONDecodeError:
                print(f"Error al decodificar JSON para guild {guild_id}. Inicializando con datos vacíos.")
                return {}
    else:
        print(f"Archivo de datos no encontrado para guild {guild_id}. Inicializando con datos vacíos.")
        return {}

# Guardar datos a JSON para un GUILD específico
def save_guild_data(guild_id, guild_data):
    file_path = os.path.join(DATA_DIR, f"{guild_id}.json")
    with open(file_path, 'w') as f:
        json.dump(guild_data, f, indent=4)
    print(f"Datos guardados para guild {guild_id} en {file_path}")

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

# --- Eventos del Bot ---

@bot.event
async def on_ready():
    """Se ejecuta cuando el bot se conecta a Discord."""
    print(f'Bot conectado como {bot.user}!')
    print(f'ID del bot: {bot.user.id}')
    await bot.change_presence(activity=discord.Game(name="registrando tiempos"))

    # DEBUGGING
    #print(f"DEBUG: bot.intents.message_content (desde intents object): {bot.intents.message_content}")
    #print(f"DEBUG: bot.intents.members (desde intents object): {bot.intents.members}") # Asegurarse de que este sea True

    try:
        await bot.tree.sync()
        print("Comandos de barra sincronizados en on_ready.")
    except Exception as e:
        print(f"Error al sincronizar comandos de barra en on_ready: {e}")

@bot.event
async def on_command_error(ctx, error):
    """Maneja errores en los comandos de texto (si se usara alguno)."""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("¡Argumentos faltantes! Por favor, verifica el formato.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("¡Argumento inválido! Revisa los valores.")
    elif isinstance(error, commands.CommandNotFound):
        pass 
    else:
        print(f'Error en el comando {ctx.command}: {error}')
        await ctx.send(f"Ha ocurrido un error inesperado: `{error}`")

# --- Comandos de Barra (Slash Commands) ---

@bot.tree.command(name="tt", description="Registra un tiempo en una pista.")
@discord.app_commands.describe(
    track_name="El nombre de la pista.",
    time_str="El tiempo en formato MM:SS.mmm o SS.mmm.",
    url_evidence="URL opcional de la evidencia del tiempo (ej. foto/video)."
)
async def register_time_slash(interaction: discord.Interaction, track_name: str, time_str: str, url_evidence: str = None):
    await interaction.response.defer(ephemeral=False)

    if not interaction.guild:
        await interaction.followup.send("Este comando solo puede usarse en un servidor.")
        return
    
    guild_id = str(interaction.guild.id) # Obtener ID del servidor

    # Cargar los datos específicos de este servidor
    current_guild_data = load_guild_data(guild_id)

    track_name = track_name.lower()

    # Validar formato del tiempo
    match = TIME_REGEX.match(time_str)
    if not match:
        await interaction.followup.send(
            f"El formato del tiempo es incorrecto. Usa `MM:SS.mmm` o `SS.mmm`.\n"
            f"Ejemplo: `01:23.456` o `59.123`."
        )
        return

    # Validar URL si se proporciona
    if url_evidence:
        if not is_valid_url(url_evidence):
            await interaction.followup.send("La URL de evidencia proporcionada no parece ser válida. Asegúrate de que empiece con `http://` o `https://`.")
            return

    total_ms = time_to_ms(time_str)

    user_id = str(interaction.user.id)
    user_name = interaction.user.display_name

    # Usar current_guild_data en lugar de track_times global
    if track_name not in current_guild_data:
        current_guild_data[track_name] = []

    found_existing = False
    for i, entry in enumerate(current_guild_data[track_name]):
        if entry["user_id"] == user_id:
            existing_time_ms = time_to_ms(entry["time"])
            
            if total_ms < existing_time_ms:
                current_guild_data[track_name][i] = {
                    "user_id": user_id,
                    "user_name": user_name,
                    "time": time_str,
                    "url_evidence": url_evidence
                }
                await interaction.followup.send(f"¡Tiempo actualizado para **{user_name}** en **{track_name.capitalize()}** a `{time_str}`! ¡Nuevo Récord Personal!" + (f" Evidencia: {url_evidence}" if url_evidence else ""))
            else:
                await interaction.followup.send(f"Tu tiempo `{time_str}` en **{track_name.capitalize()}** no es mejor que tu récord actual de `{entry['time']}`.")
            found_existing = True
            break
    
    if not found_existing:
        current_guild_data[track_name].append({
            "user_id": user_id,
            "user_name": user_name,
            "time": time_str,
            "url_evidence": url_evidence
        })
        await interaction.followup.send(f"Tiempo `{time_str}` registrado para **{user_name}** en **{track_name.capitalize()}**." + (f" Evidencia: {url_evidence}" if url_evidence else ""))

    # Reordenar los tiempos y guardar
    current_guild_data[track_name].sort(key=lambda x: time_to_ms(x["time"]))
    
    save_guild_data(guild_id, current_guild_data) # Guardar datos del servidor actual


@bot.tree.command(name="tt-show", description="Muestra los tiempos registrados para una pista.")
@discord.app_commands.describe(
    track_name="El nombre de la pista para mostrar los tiempos.",
    link="Establece a 'True' para mostrar la columna de evidencia (Zelda)."
)
async def show_times(interaction: discord.Interaction, track_name: str, link: bool = False):
    await interaction.response.defer() 

    if not interaction.guild:
        await interaction.followup.send("Este comando solo puede usarse en un servidor.")
        return
    
    guild_id = str(interaction.guild.id) # Obtener ID del servidor

    # Cargar los datos específicos de este servidor
    current_guild_data = load_guild_data(guild_id)

    track_name = track_name.lower()

    # Mapear los tiempos existentes por user_id para fácil acceso
    track_times_for_track = {entry["user_id"]: entry for entry in current_guild_data.get(track_name, [])}

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
                "time": "---", 
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
    
    # --- Configuración de columnas para la tabla (más compactas para móvil) ---
    COL_RANK_WIDTH = 3   
    COL_DRIVER_WIDTH = 15 
    COL_TIME_WIDTH = 11  
    COL_ZELDA_WIDTH = 5   

    table_header_cols = [f"{'#':<{COL_RANK_WIDTH}}", f"{'PILOTO':<{COL_DRIVER_WIDTH}}", f"{'TIEMPO':<{COL_TIME_WIDTH}}"]
    table_separator_cols = [f"{'-'*COL_RANK_WIDTH}", f"{'-'*COL_DRIVER_WIDTH}", f"{'-'*COL_TIME_WIDTH}"]
    
    if link: 
        table_header_cols.append(f"{'ZELDA':<{COL_ZELDA_WIDTH}}")
        table_separator_cols.append(f"{'-'*COL_ZELDA_WIDTH}")

    table_header = " | ".join(table_header_cols)
    table_separator = "-|-".join(table_separator_cols)
    
    table_rows = [table_header, table_separator]
    
    evidence_urls_list = []
    missing_times_list = [] # Se mantiene pero no se usa para imprimir la sección
    rank_counter = 0

    for i, entry in enumerate(all_user_data):
        driver_name = entry['user_name']
        time_val = entry['time'] 
        url_link = entry.get('url_evidence')
        
        if len(driver_name) > COL_DRIVER_WIDTH:
            driver_name = driver_name[:COL_DRIVER_WIDTH-3] + "..."

        display_rank = ""
        display_link_ref = "N/A" 
        
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
            missing_times_list.append(driver_name) 
            row_cols.append(f"{display_rank:<{COL_RANK_WIDTH}}") 
            row_cols.append(f"{driver_name:<{COL_DRIVER_WIDTH}}") 
            row_cols.append(f"{time_val:<{COL_TIME_WIDTH}}") 

            if link:
                row_cols.append(f"{display_link_ref:<{COL_ZELDA_WIDTH}}")

        table_rows.append(" | ".join(row_cols))
    
    description_parts.append("```ansi\n" + "\n".join(table_rows) + "\n```")

    if link and evidence_urls_list:
        description_parts.append("\n**__Evidencia (Zelda):__**")
        description_parts.extend(evidence_urls_list)

    if not all_user_data:
        description_parts.append("No se encontraron miembros válidos en este servidor para mostrar.")


    embed = discord.Embed(
        title=f"Tiempos para **{track_name.capitalize()}**",
        description="\n".join(description_parts),
        color=discord.Color.blue()
    )
    embed.set_footer(text="Ordenado: Mejores tiempos primero, luego sin tiempo (alfabéticamente).")

    await interaction.followup.send(embed=embed)

# --- COMANDO /tt-tracks MODIFICADO ---

@bot.tree.command(name="tt-tracks", description="Muestra una lista de todas las pistas con tiempos registrados.")
async def list_tracks(interaction: discord.Interaction):
    await interaction.response.defer()

    if not interaction.guild: # Asegurarse de que el comando se usa en un servidor
        await interaction.followup.send("Este comando solo puede usarse en un servidor.")
        return
    
    guild_id = str(interaction.guild.id) # Obtener ID del servidor

    # Cargar los datos específicos de este servidor
    current_guild_data = load_guild_data(guild_id) # <-- CARGAR DATOS

    # Usar current_guild_data en lugar de track_times
    if not current_guild_data:
        await interaction.followup.send("Aún no hay pistas con tiempos registrados en este servidor.")
        return

    # Preparar datos para la tabla
    track_data_list = []
    # Iterar sobre los elementos de current_guild_data
    for track_name_key, entries in current_guild_data.items(): 
        # Contar el número de usuarios únicos que han subido un tiempo a esta pista
        unique_users_count = len({entry["user_id"] for entry in entries})
        track_data_list.append({
            "track_name": track_name_key.capitalize(), 
            "subidos_count": unique_users_count
        })
    
    # Ordenar las pistas alfabéticamente por nombre
    track_data_list.sort(key=lambda x: x["track_name"].lower())

    description_parts = []

    COL_TRACK_WIDTH = 20 
    COL_SUBIDOS_WIDTH = 8 

    table_header = f"{'PISTA':<{COL_TRACK_WIDTH}} | {'SUBIDOS':<{COL_SUBIDOS_WIDTH}}"
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
        title="Pistas con Tiempos Registrados",
        description="\n".join(description_parts),
        color=discord.Color.green()
    )
    embed.set_footer(text="Listado alfabético de pistas.")

    await interaction.followup.send(embed=embed)

# --- Sincronizar Comandos de Barra ---
# Ahora que tt también es un slash command, este comando es aún más importante.
# Lo mantenemos como un comando de texto para el dueño, pero se sincronizará en on_ready.
@bot.command(name='sync', help='Sincroniza los comandos de barra globales (Admin only).')
@commands.is_owner()
async def sync_commands(ctx):
    await bot.tree.sync()
    await ctx.send("Comandos de barra sincronizados globalmente.")
    print("Comandos de barra sincronizados.")


# Iniciar el bot
if __name__ == "__main__":
    if not TOKEN:
        print("Error: No se encontró el token del bot en el archivo .env.")
    else:
        bot.run(TOKEN)
