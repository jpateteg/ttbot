import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import io
import requests
from requests.exceptions import RequestException, Timeout # Importar excepciones específicas
import shlex
import datetime
import json
import uuid # Importar el módulo UUID para IDs únicos
import re # Importar módulo de expresiones regulares

# --- Configuración del historial ---
DATA_DIR = "data"
HISTORY_FILE = os.path.join(DATA_DIR, "war_history.json")
ID_COUNTER_FILE = os.path.join(DATA_DIR, "id_counter.json") # Nuevo archivo para el contador de ID

def ensure_data_dir():
    """Asegura que el directorio de datos exista."""
    print(f"DEBUG: Verificando/creando directorio: {DATA_DIR}")
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"DEBUG: Directorio {DATA_DIR} creado.")
    else:
        print(f"DEBUG: Directorio {DATA_DIR} ya existe.")

def load_history():
    """Carga el historial de wars desde el archivo JSON."""
    ensure_data_dir()
    print(f"DEBUG: Intentando cargar historial desde: {HISTORY_FILE}")
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
                print(f"DEBUG: Historial cargado exitosamente. {len(history_data)} entradas.")
                return history_data
        except json.JSONDecodeError as e:
            print(f"ERROR: El archivo de historial {HISTORY_FILE} está corrupto o vacío ({e}). Iniciando uno nuevo.")
            return []
        except Exception as e:
            print(f"ERROR: Fallo inesperado al cargar el historial {HISTORY_FILE}: {e}. Iniciando uno nuevo.")
            return []
    print(f"DEBUG: Archivo de historial {HISTORY_FILE} no encontrado. Iniciando historial vacío.")
    return []

def save_history(data):
    """Guarda el historial de wars en el archivo JSON."""
    ensure_data_dir()
    print(f"DEBUG: Intentando guardar historial en: {HISTORY_FILE}")
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"DEBUG: Historial guardado exitosamente. {len(data)} entradas.")
    except Exception as e:
        print(f"ERROR: Fallo al guardar el historial en {HISTORY_FILE}: {e}")

# --- Funciones para el contador de ID ---
def load_id_counter():
    ensure_data_dir()
    if os.path.exists(ID_COUNTER_FILE):
        with open(ID_COUNTER_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return 0
    return 0

def save_id_counter(counter):
    ensure_data_dir()
    with open(ID_COUNTER_FILE, 'w', encoding='utf-8') as f:
        json.dump(counter, f)

def get_next_id():
    counter = load_id_counter()
    counter += 1
    save_id_counter(counter)
    return f"{counter:05d}" # Formato de 5 dígitos con ceros iniciales

# Cargar las variables de entorno desde el archivo .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Define los intents necesarios
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix='/', intents=intents)


# Puntos por carrera según número de DCs en esa carrera
POINTS_PER_DC_COUNT = {
    0: 82,  # 12 jugadores en pista
    1: 67,  # 11 jugadores en pista
    2: 65,  # 10 jugadores en pista
    3: 63,  # 9 jugadores en pista
    4: 60   # 8 jugadores en pista
}
MAX_DC_PER_RACE = 4 # Máximo 4 DCs en una carrera para que no se reabra la sala (8 jugadores mínimo)

# Diccionario para almacenar el estado de las guerras
active_wars = {}

# Puntos para 11 jugadores totales en la carrera (Mantenidos por si acaso, pero la lógica de DC los reemplaza)
POINTS_TOTAL_11_PLAYERS_RACE = {
    1: 15, 2: 12, 3: 10, 4: 9, 5: 8, # Mantengo 12 puntos de carrera para la tabla visual, no afectan los cálculos de war
    6: 7, 7: 6, 8: 5, 9: 4, 10: 3, 11: 2, 12: 1 # Son los puntos base que el usuario proporcionó.
}

# Puntos para 12 jugadores totales en la carrera (Mantenidos por si acaso, pero la lógica de DC los reemplaza)
POINTS_TOTAL_12_PLAYERS_RACE = {
    1: 15, 2: 12, 3: 10, 4: 9, 5: 8,
    6: 7, 7: 6, 8: 5, 9: 4, 10: 3, 11: 2, 12: 1
}

# --- Configuración para la generación de imágenes ---
IMAGE_WIDTH = 1600
IMAGE_HEIGHT = 1000 # Esta altura es para el scoreboard principal, no para la tabla de jugadores
BACKGROUND_COLOR_PRIMARY = (255, 200, 0)
BACKGROUND_COLOR_SECONDARY = (150, 150, 150)
TEXT_COLOR_PRIMARY = (0, 0, 0) # Negro para texto sobre amarillo
TEXT_COLOR_SECONDARY = (255, 255, 255) # Blanco para texto sobre gris

# Colores para la estilización de la tabla de jugadores
PLAYER_RECT_COLOR_LIGHT = (255, 255, 255, 50) # Blanco semitransparente para rectángulos claros
PLAYER_RECT_COLOR_DARK = (0, 0, 0, 50) # Negro semitransparente para rectángulos oscuros

MVP_COLOR = (255, 223, 0) # Color oro para la medalla MVP

# Rutas de fuentes. Asegúrate de que estos archivos estén disponibles
FONT_REGULAR_PATH = "arial.ttf"
FONT_BOLD_PATH = "arialbd.ttf"

LOGO_SIZE = 300 # Tamaño del logo para el scoreboard principal
TABLE_LOGO_SIZE = 200 # Nuevo: Tamaño del logo para la tabla de jugadores

# --- Función para cargar imagen de logo (desde URL o ruta local) ---
async def load_image_from_path_or_url(path_or_url, target_size=LOGO_SIZE):
    if not path_or_url:
        return None
    try:
        if path_or_url.startswith(('http://', 'https://')):
            print(f"DEBUG: Intentando cargar logo desde URL: {path_or_url}")
            response = requests.get(path_or_url, timeout=10) # Añadido timeout de 10 segundos
            response.raise_for_status() # Lanza HTTPError para 4xx/5xx respuestas
            img_data = io.BytesIO(response.content)
            img = Image.open(img_data).convert("RGBA")
        else:
            print(f"DEBUG: Intentando cargar logo desde ruta local: {path_or_url}")
            if not os.path.exists(path_or_url):
                print(f"ERROR: El archivo de logo local NO EXISTE en la ruta: {path_or_url}")
                return None
            img = Image.open(path_or_url).convert("RGBA")
        
        img = img.resize((target_size, target_size), Image.Resampling.LANCZOS) # Usa target_size aquí
        print(f"DEBUG: Logo cargado y redimensionado exitosamente desde {path_or_url}") 
        return img
    except (RequestException, Timeout) as e: # Captura errores de red y timeout
        print(f"ERROR DE RED/SERVIDOR al cargar la imagen desde {path_or_url}: {e}")
        return None
    except Exception as e: # Captura otros errores (ej. formato de imagen inválido)
        print(f"ERROR GENERAL al cargar la imagen desde {path_or_url} (Problema de imagen o Pillow): {e}")
        return None

# --- Helper function para generar la imagen de resultados de la war (scoreboard principal) ---
async def generate_race_image(war_data):
    """Genera la imagen del scoreboard principal (Equipo 1 vs Equipo 2 con puntajes totales)."""
    # Esta función usa IMAGE_WIDTH y IMAGE_HEIGHT definidos globalmente.
    try:
        image = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), (44, 47, 51)) # Fondo general oscuro
        draw = ImageDraw.Draw(image)
        
        draw.rectangle([0, 0, IMAGE_WIDTH, IMAGE_HEIGHT // 2], fill=BACKGROUND_COLOR_PRIMARY)
        draw.rectangle([0, IMAGE_HEIGHT // 2, IMAGE_WIDTH, IMAGE_HEIGHT], fill=BACKGROUND_COLOR_SECONDARY)

        font_team_name = None
        font_score_huge = None
        
        try:
            font_team_name = ImageFont.truetype(FONT_BOLD_PATH, 80)
            font_score_huge = ImageFont.truetype(FONT_BOLD_PATH, 400)
            print("Fuentes Arial Bold cargadas exitosamente desde ruta local.")
        except IOError:
            print(f"ADVERTENCIA: No se encontró el archivo de fuente '{FONT_BOLD_PATH}' en la carpeta del script. Intentando usar fuentes del sistema.")
            try:
                font_team_name = ImageFont.truetype("Arial Bold", 80)
                font_score_huge = ImageFont.truetype("Arial Bold", 400)
                print("Fuentes Arial Bold cargadas exitosamente desde el sistema.")
            except IOError:
                print("ADVERTENCIA CRÍTICA: No se pudo cargar 'Arial Bold' ni desde el archivo ni desde el sistema. Usando la fuente predeterminada de Pillow (muy pequeña).")
                font_team_name = ImageFont.load_default()
                font_score_huge = ImageFont.load_default()


        # --- Sección Superior (Equipo 1) ---
        quad_tl_x_center = IMAGE_WIDTH // 4
        quad_tl_y_center = IMAGE_HEIGHT // 4
        
        bbox_name1 = draw.textbbox((0,0), war_data['team1_name'], font=font_team_name)
        name1_height = bbox_name1[3] - bbox_name1[1]

        combined_height_1 = LOGO_SIZE + 30 + name1_height

        start_y_block_1 = quad_tl_y_center - (combined_height_1 // 2)

        logo1_img = await load_image_from_path_or_url(war_data['logo1_url'], LOGO_SIZE) # Pasa LOGO_SIZE
        if logo1_img:
            logo1_x = quad_tl_x_center - (LOGO_SIZE // 2)
            logo1_y = start_y_block_1
            image.paste(logo1_img, (logo1_x, logo1_y), logo1_img)
        
        name1_x = quad_tl_x_center
        name1_y = start_y_block_1 + LOGO_SIZE + 30
        draw.text((name1_x, name1_y), war_data['team1_name'], fill=TEXT_COLOR_PRIMARY, font=font_team_name, anchor="mm")
        
        score1_x = IMAGE_WIDTH // 4 * 3
        score1_y = IMAGE_HEIGHT // 4
        draw.text((score1_x, score1_y), str(war_data['team1_points']), fill=TEXT_COLOR_PRIMARY, font=font_score_huge, anchor="mm")

        # --- Sección Inferior (Equipo 2) ---
        quad_bl_x_center = IMAGE_WIDTH // 4
        quad_bl_y_center = IMAGE_HEIGHT // 4 * 3

        bbox_name2 = draw.textbbox((0,0), war_data['team2_name'], font=font_team_name)
        name2_height = bbox_name2[3] - bbox_name2[1]
        combined_height_2 = LOGO_SIZE + 30 + name2_height

        start_y_block_2 = quad_bl_y_center - (combined_height_2 // 2)

        logo2_img = await load_image_from_path_or_url(war_data['logo2_url'], LOGO_SIZE) # Pasa LOGO_SIZE
        if logo2_img:
            logo2_x = quad_bl_x_center - (LOGO_SIZE // 2)
            logo2_y = start_y_block_2
            image.paste(logo2_img, (logo2_x, logo2_y), logo2_img)
        
        name2_x = quad_bl_x_center
        name2_y = start_y_block_2 + LOGO_SIZE + 30
        draw.text((name2_x, name2_y), war_data['team2_name'], fill=TEXT_COLOR_SECONDARY, font=font_team_name, anchor="mm")
        
        score2_x = IMAGE_WIDTH // 4 * 3
        score2_y = IMAGE_HEIGHT // 4 * 3
        draw.text((score2_x, score2_y), str(war_data['team2_points']), fill=TEXT_COLOR_SECONDARY, font=font_score_huge, anchor="mm")

        draw.line([(0, IMAGE_HEIGHT // 2), (IMAGE_WIDTH, IMAGE_HEIGHT // 2)], fill=(0,0,0), width=10)
        draw.line([(IMAGE_WIDTH // 2, 0), (IMAGE_WIDTH // 2, IMAGE_HEIGHT)], fill=(0,0,0), width=10)

        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)

        return img_byte_arr

    except Exception as e:
        print(f"Error generando imagen de resultados: {e}")
        return None

# --- FUNCIÓN: Generar imagen de tabla de jugadores (CON CORRECCIONES DE TAMAÑO Y ERROR) ---
async def generate_player_table_image(war_data):
    """Genera la imagen de la tabla de jugadores individuales con puntajes y MVPs."""
    try:
        # --- INICIALIZACIÓN ROBUSTA DE VARIABLES AL PRINCIPIO ---
        mvp_player_name = None
        max_player_score = -1
        # Calcular el espacio necesario para las notas al final de la imagen
        notes_section_height = len(war_data.get('race_notes', [])) * 25 + 80 if war_data.get('race_notes') else 0 
        # --- FIN INICIALIZACIÓN ROBUSTA ---
        
        # Configuración de imagen para la tabla de jugadores
        img_width = 1600 # Ancho total, mantenido constante
        col_width = img_width // 3 # Ancho de cada columna
        
        player_row_height = 60 # Altura de cada fila de jugador
        header_height = 100 # Espacio para el título principal
        middle_line_height = 5 # Altura de la línea divisoria central
        padding_top_bottom = 50 # Padding general en la parte superior e inferior de la imagen

        # Obtener datos de jugadores para calcular altura dinámica
        team1_players = war_data['player_scores_data'].get('team1', [])
        team2_players = war_data['player_scores_data'].get('team2', [])
        
        # Altura de la lista de jugadores para cada equipo
        team1_players_list_height = len(team1_players) * player_row_height
        team2_players_list_height = len(team2_players) * player_row_height

        # La altura dinámica para la lista de jugadores que se mostrará
        players_area_height_per_team_config = war_data['players_per_team'] * player_row_height

        # Altura base para el contenido visual (logo, nombre, suma total grande) en las columnas 1 y 3
        # Usamos TABLE_LOGO_SIZE aquí
        min_visual_content_height_per_section = TABLE_LOGO_SIZE + 40 + 100 # Logo (200) + NombreEquipo (aprox 40) + ScoreSum (100)

        # La altura total de cada "sección de equipo" (arriba o abajo) será la mayor entre:
        # b) El espacio necesario para los visuales grandes (logo, nombre, score total)
        # a) El espacio necesario para la lista de jugadores (basado en players_per_team)
        # Se añade un padding interno a la sección.
        actual_section_height = max(min_visual_content_height_per_section, players_area_height_per_team_config) + 50 # +50 para padding interno

        # Altura total de la imagen final
        # Incluye: padding superior e inferior, altura del título, dos secciones de equipo, línea central, y notas.
        img_height = (padding_top_bottom * 2) + header_height + \
                     (actual_section_height * 2) + middle_line_height + notes_section_height

        image = Image.new("RGB", (img_width, img_height), (44, 47, 51))
        draw = ImageDraw.Draw(image)

        # Cargar fuentes (usando el mismo patrón robusto)
        font_title = None
        font_team_header = None
        font_player_name_score = None
        font_total_score_sum = None
        font_notes = None
        
        try:
            font_title = ImageFont.truetype(FONT_BOLD_PATH, 50)
            font_team_header = ImageFont.truetype(FONT_BOLD_PATH, 40)
            font_player_name_score = ImageFont.truetype(FONT_REGULAR_PATH, 45)
            font_total_score_sum = ImageFont.truetype(FONT_BOLD_PATH, 100)
            font_notes = ImageFont.truetype(FONT_REGULAR_PATH, 25)
            print("Fuentes para tabla de jugadores cargadas exitosamente desde ruta local.")
        except IOError:
            print(f"ADVERTENCIA: No se encontraron archivos de fuente para la tabla de jugadores. Usando fuentes del sistema/por defecto.")
            font_title = ImageFont.load_default()
            font_team_header = ImageFont.load_default()
            font_player_name_score = ImageFont.load_default()
            font_total_score_sum = ImageFont.load_default()
            font_notes = ImageFont.load_default()
            try:
                font_title = ImageFont.truetype("Arial Bold", 50)
                font_team_header = ImageFont.truetype("Arial Bold", 40)
                font_player_name_score = ImageFont.truetype("Arial", 45)
                font_total_score_sum = ImageFont.truetype("Arial Bold", 100)
                font_notes = ImageFont.truetype("Arial", 25)
            except IOError:
                pass

        # --- Título Principal ---
        team1_name = war_data.get('team1_name', 'Equipo 1')
        team2_name = war_data.get('team2_name', 'Equipo 2')
        display_datetime = war_data.get('historical_timestamp_str', war_data.get('timestamp', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        table_title_text = f"{team1_name} vs {team2_name} - {display_datetime}"
        draw.text((img_width / 2, padding_top_bottom + header_height // 2), table_title_text, fill=TEXT_COLOR_SECONDARY, font=font_title, anchor="mm")
        
        current_y_pos = padding_top_bottom + header_height # Inicia debajo del título y padding superior

        # --- Definir Posiciones de Columnas para el Contenido ---
        col1_x_start = 0
        col2_x_start = col_width
        col3_x_start = col_width * 2

        col1_x_center = col1_x_start + (col_width // 2)
        col2_x_center = col2_x_start + (col_width // 2)
        col3_x_center = col3_x_start + (col_width // 2)

        # --- Dibujar Secciones de Equipo ---
        for team_idx, team_key in enumerate(['team1', 'team2']):
            team_name = war_data.get(f'{team_key}_name', 'Equipo Desconocido')
            players_data = sorted(war_data['player_scores_data'].get(team_key, []), key=lambda p: p['score'], reverse=True)
            total_team_player_score = war_data.get(f'{team_key}_player_sum', 0)
            logo_url = war_data.get(f'logo{1 if team_key == "team1" else 2}_url')
            
            section_bg_color = BACKGROUND_COLOR_PRIMARY if team_key == "team1" else BACKGROUND_COLOR_SECONDARY
            section_text_color_main = TEXT_COLOR_PRIMARY if team_key == "team1" else TEXT_COLOR_SECONDARY
            
            player_rect_color_for_section = PLAYER_RECT_COLOR_DARK if team_key == "team1" else PLAYER_RECT_COLOR_LIGHT
            player_text_color_for_section = MVP_COLOR if team_key == "team1" else (0, 0, 0)

            # --- RE-ASIGNACIÓN DE MVP_PLAYER_NAME Y MAX_PLAYER_SCORE PARA CADA EQUIPO ---
            # Se usan las variables locales de la función que se inicializaron al principio
            # Esto asegura que el MVP y su score se calculen por equipo,
            # pero la inicialización global asegura que siempre existan.
            if players_data:
                mvp_player_name = players_data[0]['name']
                max_player_score = players_data[0]['score']
            else: # Si el equipo no tiene jugadores, asegurar que no haya un MVP para ese equipo
                mvp_player_name = None
                max_player_score = -1
            # --- FIN RE-ASIGNACIÓN ---

            # Dibuja el fondo de la sección del equipo
            draw.rectangle([0, current_y_pos, img_width, current_y_pos + actual_section_height], fill=section_bg_color)
            
            # --- Columna 1: Logo y Nombre de Equipo ---
            # Calcular la posición Y para centrar el logo y el nombre del equipo verticalmente
            # dentro del espacio vertical de la sección actual_section_height
            logo_name_block_height = TABLE_LOGO_SIZE + 40 # Logo + espacio para nombre
            logo_name_block_y_offset = (actual_section_height - logo_name_block_height) // 2 

            # Usamos TABLE_LOGO_SIZE aquí para el dibujo del logo
            logo_x = col1_x_center - (TABLE_LOGO_SIZE // 2)
            logo_y = current_y_pos + logo_name_block_y_offset

            logo_img = await load_image_from_path_or_url(logo_url, TABLE_LOGO_SIZE) # Pasa TABLE_LOGO_SIZE
            if logo_img:
                image.paste(logo_img, (logo_x, logo_y), logo_img)
            
            name_x_col1 = col1_x_center
            name_y_col1 = logo_y + TABLE_LOGO_SIZE + 10 # 10px debajo del logo
            draw.text((name_x_col1, name_y_col1), team_name, fill=section_text_color_main, font=font_team_header, anchor="mm")

            # --- Columna 3: Puntaje Total del Equipo ---
            # Centrar el puntaje total verticalmente en su columna
            score_sum_y_offset = (actual_section_height - font_total_score_sum.size) // 2 
            score_x = col3_x_center
            score_y = current_y_pos + score_sum_y_offset
            draw.text((score_x, score_y), str(total_team_player_score), fill=section_text_color_main, font=font_total_score_sum, anchor="mm")

            # --- Columna 2: Jugadores y Puntajes ---
            # Centrar la lista de jugadores dentro de la columna 2
            players_list_display_height = len(players_data) * player_row_height
            players_list_start_y_offset = (actual_section_height - players_list_display_height) // 2
            
            for i, player in enumerate(players_data):
                player_name = player['name']
                player_score = player['score']
                dc_count_player = player.get('dc_count', 0)
                
                player_y_center_in_row = current_y_pos + players_list_start_y_offset + i * player_row_height + (player_row_height // 2)
                
                rect_padding_x = 20
                rect_height = player_row_height - 10
                
                rect_x1 = col2_x_start + rect_padding_x
                rect_x2 = col2_x_start + col_width - rect_padding_x
                rect_y1 = player_y_center_in_row - (rect_height // 2)
                rect_y2 = rect_y1 + rect_height
                
                draw.rectangle([rect_x1, rect_y1, rect_x2, rect_y2], fill=player_rect_color_for_section)

                player_text = f"{player_name}"
                if dc_count_player > 0:
                    player_text += f" ({dc_count_player} DCs)"
                
                name_draw_x = col2_x_start + rect_padding_x + 10
                draw.text((name_draw_x, player_y_center_in_row), player_text, fill=player_text_color_for_section, font=font_player_name_score, anchor="lm")
                
                score_draw_x = col2_x_start + col_width - rect_padding_x - 10
                draw.text((score_draw_x, player_y_center_in_row), str(player_score), fill=player_text_color_for_section, font=font_player_name_score, anchor="rm")


                # --- CAMBIO IMPORTANTE: Verificar que mvp_player_name NO sea None antes de comparar ---
                if mvp_player_name is not None and player_name == mvp_player_name and max_player_score > 0:
                    medal_size = font_player_name_score.size * 0.8
                    bbox_name_for_medal = draw.textbbox((0,0), player_name, font=font_player_name_score)
                    name_width_for_medal = bbox_name_for_medal[2] - bbox_name_for_medal[0]

                    medal_x = name_draw_x + name_width_for_medal + 10
                    medal_y = player_y_center_in_row - (medal_size // 2)
                    
                    star_font = None
                    try:
                        star_font = ImageFont.truetype(FONT_BOLD_PATH, int(medal_size * 0.8))
                    except IOError:
                        star_font = ImageFont.load_default()
                    
                    draw.ellipse([medal_x, medal_y, medal_x + medal_size, medal_y + medal_size], fill=MVP_COLOR, outline=player_text_color_for_section, width=2)
                    star_symbol_color = (0,0,0) if team_key == "team1" else (255,255,255)
                    draw.text((medal_x + medal_size // 2, medal_y + medal_size // 2), "★", fill=star_symbol_color, font=star_font, anchor="mm")

            current_y_pos += actual_section_height # Avanza la posición Y para la siguiente sección

            # Línea divisoria horizontal entre secciones de equipo (solo después del primer equipo)
            if team_idx == 0: 
                draw.line([(0, current_y_pos), (img_width, current_y_pos)], fill=(0,0,0), width=middle_line_height)
                current_y_pos += middle_line_height # Ajusta la posición Y por el grosor de la línea

        # --- Sección de Notas (al final) ---
        # Las notas se dibujan después de ambas secciones de equipo
        if war_data.get('race_notes'):
            notes_y_start = current_y_pos + 30 # 30px de padding antes del título de las notas
            draw.text((50, notes_y_start), "Notas de la War:", fill=(114, 137, 218), font=font_team_header)
            notes_y_start += 40 # Espacio entre el título de notas y la primera nota
            for i, note in enumerate(war_data['race_notes']):
                draw.text((50, notes_y_start + i * 25), note, fill=(255,255,255), font=font_notes)


        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        return img_byte_arr

    except Exception as e:
        print(f"ERROR: Falló la generación de la tabla de jugadores: {e}")
        return None


@bot.event
async def on_ready():
    """Se ejecuta cuando el bot está listo y conectado a Discord."""
    print(f'Bot conectado como {bot.user}')
    print("Sincronizando comandos de aplicación...")
    try:
        synced_commands = await bot.tree.sync()
        print(f"Sincronizados {len(synced_commands)} comandos de aplicación.")
    except Exception as e:
        print(f"Error al sincronizar comandos de aplicación: {e}")


# --- COMANDO PRINCIPAL /WAR (como comando de barra nativo) ---
@bot.tree.command(name='war', description="Gestiona guerras de Mario Kart y sus resultados.")
@app_commands.describe(
    # --- Parámetros para la configuración básica de la war ---
    n_v_n="Tamaño de la war (ej. '6v6'). Por defecto 6v6.",
    new="Marcar 'True' para iniciar una war nueva, borrando progreso anterior.",
    default_score="Si es un forfeit, la puntuación inicial para Equipo 1 (ej. 150).",

    # --- Parámetros para personalizar Equipo 1 ---
    team1_name="Nombre del Equipo 1. Por defecto 'Malaka Racers'.",
    logo1_url="URL o ruta local del logo del Equipo 1. Por defecto, un logo predefinido.",

    # --- Parámetros para personalizar Equipo 2 ---
    team2_name="Nombre del Equipo 2. Por defecto 'Equipo 2'.",
    logo2_url="URL o ruta local del logo del Equipo 2. Opcional con el nombre de Equipo 2.",
)
async def start_war(
    interaction: discord.Interaction,
    n_v_n: str = "6v6",
    new: bool = False,
    default_score: int = None,
    team1_name: str = "Malaka Racers",
    logo1_url: str = "img/wr-logo.png",
    team2_name: str = "Equipo 2",
    logo2_url: str = "img/team2-logo.png"
):
    ctx = await commands.Context.from_interaction(interaction)
    
    force_new = new
    is_forfeit = (default_score is not None)
    forfeit_score_value = default_score if default_score is not None else 150

    actual_n_value = 6
    if n_v_n:
        try:
            val = int(n_v_n.split('v')[0])
            if 1 <= val <= 12:
                actual_n_value = val
            else:
                await ctx.send("El número de jugadores (N) en 'nvn' debe ser un entero entre 1 y 12. Usando 6v6 por defecto.")
        except ValueError:
            await ctx.send("Formato de 'nvn' incorrecto (ej. '6v6'). Usando 6v6 por defecto.")
    
    # Manejar war existente o forzar una nueva
    if ctx.channel.id in active_wars and active_wars[ctx.channel.id]['status'] == 'in_progress':
        if not force_new:
            await ctx.send("¡Ya hay una war en progreso en este canal! Si quieres iniciar una nueva y borrar el progreso actual, usa `/war new` o `/war new NvN`.")
            return
        else:
            del active_wars[ctx.channel.id]
            await ctx.send("Se ha borrado la war anterior. Iniciando una nueva...")

    # Inicializar datos de la war
    active_wars[ctx.channel.id] = {
        'status': 'in_progress',
        'players_per_team': actual_n_value,
        'current_race': 1,
        'team1_points': 0,
        'team2_points': 0,
        'race_notes': [],
        'team1_name': team1_name,
        'team2_name': team2_name,
        'logo1_url': logo1_url,
        'logo2_url': logo2_url,
        'race_points_history': [],
        'player_scores_input_mode': False,
        'player_scores_current_team': None,
        'player_scores_data': {'team1': [], 'team2': []},
        'is_historical_creation': False, # No es una creación histórica por este comando
        'dc_per_race_count': {i: 0 for i in range(1, 13)} # Inicializar DCs por carrera
    }

    # --- Lógica para Forfeit ---
    if is_forfeit:
        war_data = active_wars[ctx.channel.id]
        war_data['team1_points'] = forfeit_score_value
        war_data['team2_points'] = 0
        war_data['current_race'] = 13
        war_data['status'] = 'finalized'

        await ctx.send(f"¡War iniciada como forfeit! **{war_data['team1_name']}** obtiene **{forfeit_score_value}** puntos, y **{war_data['team2_name']}** obtiene **0** puntos.")
        
        forfeit_image_bytes = await generate_race_image(war_data)
        if forfeit_image_bytes:
            await ctx.send(file=discord.File(forfeit_image_bytes, filename=f"forfeit_final_score.png"))
        else:
            await ctx.send("Error al generar la imagen de forfeit.")
        
        final_message = (f"¡War finalizada por forfeit!\n"
                         f"**{war_data['team1_name']}:** {war_data['team1_points']} puntos\n"
                         f"**{war_data['team2_name']}:** {war_data['team2_points']} puntos\n")
        await ctx.send(final_message)
        
        return

    await ctx.send(f"¡War iniciada! Es de **{actual_n_value}v{actual_n_value}**.\n"
                   f"Equipo 1: **{team1_name}** | Equipo 2: **{team2_name}**.\n"
                   f"Por favor, ingresa las posiciones de tu equipo para la carrera 1 (ej. `1 2 5 9 11 12` o `1 2 5 9 11 dc=1`).")


# --- NUEVO COMANDO: /war-help ---
@bot.tree.command(name='war-help', description="Muestra la guía de comandos para las guerras.")
async def war_help_command(interaction: discord.Interaction):
    ctx = await commands.Context.from_interaction(interaction)
    help_message = """
        ✨ **GUÍA BÁSICA DE COMANDOS DE WAR Malaka TT Bot** ✨

        **1. 🚀 Iniciar/Reiniciar una War:**
        Usa `/war` y rellena las opciones en Discord.
        * `n_v_n`: Tamaño de la war (ej. `6v6`).
        * `new`: Marcar si quieres reiniciar una war.
        * `team1_name`, `logo1_url`: Tu equipo y logo.
        * `team2_name`, `logo2_url`: Equipo rival y logo.

        *Ejemplo:* `/war n_v_n:6v6 team1_name:"Malaka Racers" logo1_url:"img/wr-logo.png" team2_name:"Equipo 2" logo2_url:"img/team2-logo.png"`

        **2. ⚡ War Rápida / Forfeit:**
        * Usa `/war` y selecciona `new:True` y `default_score:[puntuacion]`.
        * `default_score` es opcional, por defecto es 150.
        *Ejemplo:* `/war new:True default_score:150 team1_name:"Mi Equipo"`

        **3. 🏁 Ingresar Resultados de Carrera:**
        * Después de iniciar la war, ingresa las posiciones de TU equipo:
            `1 2 3 7 9 10`
        * **Con Desconexiones (DC):**
            `1 2 3 7 9 10 dc=1` (1 DC total en la carrera)

        **4. 📊 Tabla de Jugadores:**
        * Para ingresar y mostrar puntajes individuales después de una war finalizada:
            `/war-table` (Este es un comando separado ahora)
        * Para crear una tabla de una war antigua:
            `/war-table team1_name:"Mi Equipo" team2_name:"Rival" players_per_team:6 war_date:"YYYY-MM-DD"`
            (Logos son opcionales, si no se pone fecha, usa la actual.)
        * Formato de jugador con DC: `Nombre Puntaje [dc=N r=X]` (N: # DCs, X: # Carrera)

        **5. 📜 Historial de Wars:**
        * Resumen Mensual: `/war-history`
        * Detalle de Wars: `/war-results [month_year] [vs:NombreRival]`
          (Ej: `/war-results month_year:2025-07 vs:"Equipo X"`)

        **6. ✨ Normalizar Tabla de Jugadores:**
        * Aplica bonificaciones a una tabla existente (solo `method:bonus` ahora).
        * **Usa:** `/war-table-normalize war_id:[ID_TABLA]`

        ¡Que tengas grandes wars! 🏆
        """
    try:
        print(f"DEBUG: Intentando enviar mensaje de ayuda con longitud: {len(help_message)} caracteres.")

        if len(help_message) > 2000:
            print(f"ERROR: El mensaje de ayuda excede el límite de 2000 caracteres de Discord ({len(help_message)}).")
            await ctx.send("Lo siento, el mensaje de ayuda es demasiado largo para enviar. Por favor, consulta la consola del bot para ver la guía completa (o pide al desarrollador que la condense).")
        else:
            await ctx.send(help_message)
    except discord.errors.HTTPException as e:
        print(f"ERROR al enviar mensaje de ayuda (HTTPException): {e} - Código de error: {e.code}")
        await ctx.send(f"Lo siento, no pude enviar el mensaje de ayuda. Hubo un error de Discord: `{e.code}`. Revisa la consola para más detalles.")
    except Exception as e:
        print(f"ERROR inesperado al enviar mensaje de ayuda: {e}")
        await ctx.send("Lo siento, ocurrió un error inesperado al intentar enviar el mensaje de ayuda. Revisa la consola del bot.")
    return

# --- COMANDO: /war-table (para iniciar la entrada de jugadores o crear tabla histórica) ---
@bot.tree.command(name='war-table', description="Inicia el modo para ingresar y mostrar puntajes individuales de jugadores.")
@app_commands.describe(
    team1_name="Nombre del Equipo 1 (para wars antiguas).",
    team2_name="Nombre del Equipo 2 (para wars antiguas).",
    logo1_url="URL o ruta local del logo del Equipo 1 (para wars antiguas).",
    logo2_url="URL o ruta local del logo del Equipo 2 (para wars antiguas).",
    players_per_team="Número de jugadores por equipo (ej. 6 para 6v6). Por defecto 6.",
    war_date="Fecha de la war antigua (YYYY-MM-DD o Jamboree-MM). Por defecto, fecha actual."
)
async def war_table_command(
    interaction: discord.Interaction,
    team1_name: str = None,
    team2_name: str = None,
    logo1_url: str = None,
    logo2_url: str = None,
    players_per_team: int = 6,
    war_date: str = None
):
    ctx = await commands.Context.from_interaction(interaction)
    channel_id = ctx.channel.id

    is_historical_creation = (team1_name is not None or team2_name is not None)

    if is_historical_creation:
        # Modo de creación de tabla histórica
        if channel_id in active_wars and active_wars[channel_id]['status'] == 'in_progress':
            await ctx.send("¡Ya hay una war en progreso en este canal! No puedes crear una tabla histórica mientras una war está activa. Por favor, termina la war actual o usa `/war new` para borrarla.")
            return

        # Si ya hay una war finalizada, la borramos para la histórica (para evitar conflictos de estado)
        if channel_id in active_wars and active_wars[channel_id]['status'] == 'finalized':
            del active_wars[channel_id]
            await ctx.send("Se ha borrado la war finalizada anterior para crear una tabla histórica.")

        # Establecer valores por defecto para la war histórica si no se proporcionan
        final_team1_name = team1_name if team1_name is not None else "Malaka Racers"
        final_logo1_url = logo1_url if logo1_url is not None else "img/wr-logo.png"
        final_team2_name = team2_name if team2_name is not None else "Equipo 2"
        final_logo2_url = logo2_url if logo2_url is not None else "img/team2-logo.png"

        final_players_per_team = players_per_team if 1 <= players_per_team <= 12 else 6

        # Determinar la fecha y timestamp para la war histórica
        historical_date_str = datetime.datetime.now().strftime("%Y-%m")
        historical_timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if war_date:
            try:
                parsed_date = datetime.datetime.strptime(war_date, "%Y-%m-%d")
                historical_date_str = parsed_date.strftime("%Y-%m")
                historical_timestamp_str = parsed_date.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    parsed_date = datetime.datetime.strptime(war_date, "%Y-%m")
                    historical_date_str = parsed_date.strftime("%Y-%m")
                    historical_timestamp_str = parsed_date.strftime("%Y-%m-01 %H:%M:%S")
                except ValueError:
                    await ctx.send("Formato de fecha inválido. Usa 'YYYY-MM-DD' o 'YYYY-MM'. Usando la fecha actual para el registro.")
            
        active_wars[channel_id] = {
            'status': 'historical_creation',
            'is_historical_creation': True,
            'historical_date_str': historical_date_str,
            'historical_timestamp_str': historical_timestamp_str,
            'players_per_team': final_players_per_team,
            'current_race': 1,
            'team1_points': 0,
            'team2_points': 0,
            'race_notes': [],
            'team1_name': final_team1_name,
            'team2_name': final_team2_name,
            'logo1_url': final_logo1_url,
            'logo2_url': final_logo2_url,
            'race_points_history': [],
            'player_scores_input_mode': True,
            'player_scores_current_team': 'team1',
            'player_scores_data': {'team1': [], 'team2': []},
            'dc_per_race_count': {i: 0 for i in range(1, 13)} # Inicializar DCs por carrera
        }
        await ctx.send(f"📊 **¡Modo de creación de tabla histórica activado!**\n"
                       f"War: **{final_team1_name}** vs **{final_team2_name}** ({final_players_per_team}v{final_players_per_team}) - Fecha: {historical_date_str}\n"
                       f"Por favor, ingresa los jugadores y sus puntajes **una línea a la vez**.\n"
                       f"Comienza con los jugadores de **{final_team1_name}** (Formato: `NombreDelJugador Puntaje [dc=N r=X]`).\n"
                       f"Cuando termines con **{final_team1_name}**, el bot te lo indicará para que ingreses los del siguiente equipo.\n"
                       f"Luego, ingresa los jugadores de **{final_team2_name}**.\n"
                       f"Cuando hayas terminado con **AMBOS** equipos, el bot te indicará que puedes escribir `FIN`.")
        return
    else:
        # Modo normal: buscar war finalizada en el canal
        if ctx.channel.id not in active_wars:
            await ctx.send("No hay una war en progreso o finalizada en este canal para generar la tabla de jugadores. Inicia una war o termina una existente, o proporciona detalles para una tabla histórica.")
            return
        
        war_data = active_wars[channel_id]

        if war_data.get('player_scores_input_mode', False):
            await ctx.send("Ya estás en el modo de ingreso de puntuaciones individuales. Escribe 'FIN' para generar la tabla.")
            return
        
        if war_data['status'] == 'in_progress':
            await ctx.send("Esta war aún está en progreso. Por favor, termina la war primero (completa las 12 carreras o usa un comando de forfeit).")
            return

        war_data['player_scores_input_mode'] = True
        war_data['player_scores_current_team'] = 'team1' # Empezamos esperando jugadores del equipo 1
        war_data['player_scores_data'] = {'team1': [], 'team2': []} # Resetear cualquier data anterior
        war_data['is_historical_creation'] = False # Asegurar que no es histórica
        war_data['dc_per_race_count'] = {i: 0 for i in range(1, 13)} # Inicializar DCs por carrera

        await ctx.send(f"📊 **¡Listo para registrar las puntuaciones individuales de los jugadores!**\n"
                       f"Por favor, ingresa los jugadores y sus puntajes **una línea a la vez**.\n"
                       f"Comienza con los jugadores de **{war_data['team1_name']}** (Formato: `NombreDelJugador Puntaje [dc=N r=X]`).\n"
                       f"Cuando termines con **{war_data['team1_name']}**, el bot te lo indicará para que ingreses los del siguiente equipo.\n"
                       f"Luego, ingresa los jugadores de **{war_data['team2_name']}**.\n"
                       f"Cuando hayas terminado con **AMBOS** equipos, el bot te indicará que puedes escribir `FIN`.")
        return


# --- NUEVO COMANDO: /war-history (resumen) ---
@bot.tree.command(name='war-history', description="Muestra el historial de wars ganadas/perdidas por mes.")
async def war_history_command(interaction: discord.Interaction):
    ctx = await commands.Context.from_interaction(interaction)
    history = load_history()

    if not history:
        await ctx.send("No hay historial de wars para mostrar. ¡Empieza a jugar!")
        return

    monthly_summary = {}
    for record in history:
        month_year = record.get('date', 'Fecha Desconocida')
        if month_year not in monthly_summary:
            monthly_summary[month_year] = {'won': 0, 'lost': 0, 'draw': 0, 'normalized': 0}
        
        status = record.get('status')
        if status == 'won':
            monthly_summary[month_year]['won'] += 1
        elif status == 'lost':
            monthly_summary[month_year]['lost'] += 1
        elif status == 'draw':
            monthly_summary[month_year]['draw'] += 1
        elif status == 'normalized':
            monthly_summary[month_year]['normalized'] += 1


    response = "**Historial de Wars (Ganadas/Perdidas/Empates/Normalizadas por Mes):**\n"
    for month_year in sorted(monthly_summary.keys()):
        summary = monthly_summary[month_year]
        response += (f"📅 **{month_year}**: Ganadas: {summary['won']}, Perdidas: {summary['lost']}"
                     f", Empates: {summary['draw']}, Normalizadas: {summary['normalized']}\n")
    
    if len(response) > 2000:
        await ctx.send("El historial es demasiado largo para un solo mensaje. Por favor, especifica un mes o revisa la consola.")
        print("Historial completo (se imprime en consola porque es demasiado largo para Discord):")
        print(response)
    else:
        await ctx.send(response)

# --- NUEVO COMANDO: /war-results (detalle de wars) ---
@bot.tree.command(name='war-results', description="Muestra el historial detallado de wars por estado y mes.")
@app_commands.describe(
    month_year="Filtra por mes y año (ej. 'YYYY-MM'). Opcional para ver todos.",
    vs="Nombre del Equipo 2 (oponente) para filtrar wars contra él. Opcional."
)
async def war_results_command(interaction: discord.Interaction, month_year: str = None, vs: str = None):
    ctx = await commands.Context.from_interaction(interaction)
    history = load_history()

    if not history:
        await ctx.send("No hay historial de wars para mostrar. ¡Empieza a jugar!")
        return

    # Filtrar por mes y por oponente
    filtered_wars = []
    for record in history:
        record_date = record.get('date')
        record_team2_name = record.get('team2_name', '').lower()

        if month_year and record_date != month_year:
            continue
        
        if vs and record_team2_name != vs.lower():
            continue

        filtered_wars.append(record)
    
    if not filtered_wars:
        filter_info = []
        if month_year: filter_info.append(f"mes {month_year}")
        if vs: filter_info.append(f"equipo '{vs}'")
        
        if filter_info:
            await ctx.send(f"No se encontraron wars para el {' y '.join(filter_info)}.")
        else:
            await ctx.send("No hay wars registradas en el historial (o no hay para los filtros especificados).")
        return

    # Agrupar por estado
    wars_by_status = {'won': [], 'lost': [], 'draw': [], 'normalized': []}
    for record in filtered_wars:
        status = record.get('status')
        if status in wars_by_status:
            wars_by_status[status].append(record)
        else:
            # Si hay un estado desconocido, agrégalo a una categoría "otros" o ignóralo
            print(f"ADVERTENCIA: Estado de war desconocido '{status}' para el registro ID: {record.get('id')}")
            if 'other' not in wars_by_status:
                wars_by_status['other'] = []
            wars_by_status['other'].append(record)

    response_parts = []
    
    filter_description = []
    if month_year: filter_description.append(f"mes {month_year}")
    if vs: filter_info.append(f"vs '{vs}'")
    
    history_title_suffix = f" ({' y '.join(filter_description)})" if filter_description else " (Todo el Historial)"

    response_parts.append(f"📜 **Historial Detallado de Wars{history_title_suffix}:**\n")
    response_parts.append(f"📊 Ganadas: {len(wars_by_status['won'])}, Perdidas: {len(wars_by_status['lost'])}, Empates: {len(wars_by_status['draw'])}, Normalizadas: {len(wars_by_status['normalized'])}\n")
    response_parts.append("---")

    for status_key in ['won', 'lost', 'draw', 'normalized']:
        if wars_by_status[status_key]:
            spanish_status_name = {
                'won': 'Ganadas',
                'lost': 'Perdidas',
                'draw': 'Empatadas',
                'normalized': 'Normalizadas'
            }.get(status_key, status_key.capitalize())
            response_parts.append(f"\n🏆 **Wars {spanish_status_name}:**")
            
            for i, record in enumerate(wars_by_status[status_key]):
                war_data_for_image = {
                    'players_per_team': record.get('players_per_team', 6),
                    'team1_points': record.get('team1_score', 0),
                    'team2_points': record.get('team2_score', 0),
                    'team1_name': record.get('team1_name', 'Malaka Racers'),
                    'team2_name': record.get('team2_name', 'Equipo 2'),
                    'logo1_url': record.get('logo1_url', "img/wr-logo.png"),
                    'logo2_url': record.get('logo2_url', "img/team2-logo.png"),
                    'race_notes': record.get('notes', []),
                    'player_scores_data': record.get('player_scores_data', {'team1':[], 'team2':[]}),
                    'team1_player_sum': record.get('team1_score', 0),
                    'team2_player_sum': record.get('team2_score', 0),
                    'timestamp': record.get('timestamp')
                }

                summary_text_line = (f"- **{record.get('team1_name', 'Malaka Racers')}** vs **{record.get('team2_name', 'Equipo 2')}**: "
                                     f"Score `{record.get('team1_score',0)}-{record.get('team2_score',0)}` "
                                     f"(Fecha: {record.get('timestamp', 'Fecha Desconocida')})")
                
                player_table_image_bytes = await generate_player_table_image(war_data_for_image)

                await ctx.send(summary_text_line)
                if player_table_image_bytes:
                    await ctx.send(file=discord.File(player_table_image_bytes, filename=f"history_player_table_{status_key}_{record.get('id', 'unknown_id')}_{i}.png"))
                else:
                    await ctx.send(f"  (Error al generar la imagen para esta war, ID: {record.get('id', 'N/A')}).")
                    
    if not response_parts:
        filter_info = []
        if month_year: filter_info.append(f"mes {month_year}")
        if vs: filter_info.append(f"equipo '{vs}'")
        
        if filter_info:
            await ctx.send(f"No se encontraron wars para el {' y '.join(filter_info)}.")
        else:
            await ctx.send("No hay wars registradas en el historial (o no hay para los filtros especificados).")


@bot.event
async def on_message(message):
    ctx = await bot.get_context(message)

    await bot.process_commands(message)

    if message.author == bot.user:
        return

    channel_id = message.channel.id

    if channel_id in active_wars and active_wars[channel_id].get('player_scores_input_mode', False):
        war_data = active_wars[channel_id]
        content = message.content.strip()

        print(f"DEBUG (on_message - player_scores_input_mode): Received content: '{content}', length: {len(content)}")
        print(f"DEBUG (on_message - player_scores_input_mode): Current team: {war_data.get('player_scores_current_team')}, Team1 players: {len(war_data['player_scores_data']['team1'])}, Team2 players: {len(war_data['player_scores_data']['team2'])}")


        if content.lower() == 'fin':
            print("DEBUG: 'FIN' command received.")
            war_data['player_scores_input_mode'] = False
            
            if not war_data['player_scores_data']['team1'] or not war_data['player_scores_data']['team2']:
                print("DEBUG: Validation failed: Teams not fully entered.")
                await ctx.send("Error: Debes ingresar puntajes para ambos equipos antes de finalizar. Ingresa más jugadores o verifica el nombre del equipo.")
                war_data['player_scores_input_mode'] = True
                return
            
            expected_players_per_team = war_data['players_per_team']
            if len(war_data['player_scores_data']['team1']) != expected_players_per_team or \
               len(war_data['player_scores_data']['team2']) != expected_players_per_team:
                print(f"DEBUG: Validation failed: Incorrect number of players. Expected {expected_players_per_team}, got T1:{len(war_data['player_scores_data']['team1'])}, T2:{len(war_data['player_scores_data']['team2'])}")
                await ctx.send(f"Error: Debes ingresar exactamente {expected_players_per_team} jugadores para CADA equipo antes de finalizar. Por favor, corrige los puntajes.")
                war_data['player_scores_input_mode'] = True
                return

            # Calcular sumas de puntos de jugadores
            team1_player_sum = sum(p['score'] for p in war_data['player_scores_data']['team1'])
            team2_player_sum = sum(p['score'] for p in war_data['player_scores_data']['team2'])
            total_player_sum_for_all = team1_player_sum + team2_player_sum
            print(f"DEBUG: Calculated team1_player_sum: {team1_player_sum}, team2_player_sum: {team2_player_sum}, total_player_sum_for_all: {total_player_sum_for_all}")

            # --- Calcular la suma total esperada de la war basada en DCs ---
            expected_total_war_points = 0
            dc_summary_for_explanation = {}
            total_individual_dcs_reported = 0

            print(f"DEBUG: dc_per_race_count before calculation: {war_data['dc_per_race_count']}")

            for race_num in range(1, 13): # Siempre 12 carreras en una war
                dc_in_this_race = war_data['dc_per_race_count'].get(race_num, 0)
                
                effective_dc_for_points = min(dc_in_this_race, MAX_DC_PER_RACE)
                
                points_for_this_race = POINTS_PER_DC_COUNT.get(effective_dc_for_points, POINTS_PER_DC_COUNT[MAX_DC_PER_RACE])
                expected_total_war_points += points_for_this_race
                
                if dc_in_this_race > 0:
                    if dc_in_this_race not in dc_summary_for_explanation:
                        dc_summary_for_explanation[dc_in_this_race] = 0
                    dc_summary_for_explanation[dc_in_this_race] += 1
                
            # Calculate total_individual_dcs_reported from player_scores_data
            for team_key in ['team1', 'team2']:
                for player in war_data['player_scores_data'].get(team_key, []):
                    total_individual_dcs_reported += player.get('dc_count', 0)

            dc_explanation_message = ""
            if total_individual_dcs_reported > 0:
                dc_explanation_parts = [f"Se registraron **{total_individual_dcs_reported} desconexión(es) individual(es)** en la war."]
                
                race_type_descriptions = []
                for dc_level_in_race in sorted(dc_summary_for_explanation.keys()):
                    num_races_affected = dc_summary_for_explanation[dc_level_in_race]
                    players_in_race = (war_data['players_per_team'] * 2) - dc_level_in_race
                    
                    if players_in_race < 8:
                        race_type_descriptions.append(f"**{num_races_affected} carrera(s)** con **más de {MAX_DC_PER_RACE} DCs** (puntos calculados como {POINTS_PER_DC_COUNT[MAX_DC_PER_RACE]} cada una)")
                    else:
                        race_type_descriptions.append(f"**{num_races_affected} carrera(s) de {players_in_race} jugadores** (sumando {POINTS_PER_DC_COUNT.get(dc_level_in_race, POINTS_PER_DC_COUNT[0])} puntos cada una)")
                
                if race_type_descriptions:
                    dc_explanation_parts.append("Esto significa que la war incluyó:")
                    dc_explanation_parts.append(", ".join(race_type_descriptions) + ".")

                dc_explanation_parts.append(f"Por lo tanto, el puntaje total esperado de esta war es de **{expected_total_war_points} puntos**.")
                dc_explanation_message = "\n".join(dc_explanation_parts)

            print(f"DEBUG: Expected total war points: {expected_total_war_points}")
            print(f"DEBUG: Total player sum: {total_player_sum_for_all}")
            print(f"DEBUG: DC Explanation Message: '{dc_explanation_message}'")

            if total_player_sum_for_all != expected_total_war_points:
                await ctx.send(f"Nota: La suma total de puntos de jugadores reportados ({total_player_sum_for_all}) no coincide con la suma esperada para esta war ({expected_total_war_points}) basada en los DCs registrados. Esto puede indicar un error de cálculo o reporte.")
            
            if dc_explanation_message:
                await ctx.send(dc_explanation_message)
            # --- FIN CÁLCULO Y NOTA ---

            # Actualizar war_data con las sumas calculadas
            war_data['team1_player_sum'] = team1_player_sum
            war_data['team2_player_sum'] = team2_player_sum

            player_table_image_bytes_io = await generate_player_table_image(war_data)
            if player_table_image_bytes_io:
                war_id = get_next_id()
                war_data['id'] = war_id
                print(f"DEBUG: War ID generado: {war_id}")

                original_channel_file = discord.File(io.BytesIO(player_table_image_bytes_io.getvalue()), filename=f"war_player_scores_table_{war_id}.png")
                sent_message_in_original_channel = await ctx.send(
                    content=f"📊 Tabla de Puntuaciones de Jugadores (ID: {war_id})",
                    file=original_channel_file
                )
                await sent_message_in_original_channel.add_reaction("✅")
                await sent_message_in_original_channel.add_reaction("❌")
                war_data['player_table_message_id'] = sent_message_in_original_channel.id
                war_data['player_table_initiator_id'] = ctx.author.id
                war_data['temp_player_table_image_bytes'] = player_table_image_bytes_io
                print("DEBUG: Player table image sent to original channel and reactions added.")
            else:
                print("DEBUG: generate_player_table_image regresó None, no se generó la imagen.")
                await ctx.send("Error al generar la tabla de puntuaciones de jugadores. Revisa la consola para más detalles.")
            
            return
        
        lines = content.split('\n')
        processed_any_line_in_bulk = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue

            print(f"DEBUG: Processing line in bulk: '{line}'")

            if line.lower() == 'fin':
                continue

            if line.lower() == war_data['team2_name'].lower() or line.lower() == 'equipo 2':
                if war_data['player_scores_current_team'] == 'team1':
                    expected_players_per_team = war_data['players_per_team']
                    if len(war_data['player_scores_data']['team1']) < expected_players_per_team:
                        await ctx.send(f"Error: Debes ingresar **{expected_players_per_team}** jugadores para **{war_data['team1_name']}** antes de pasar al siguiente equipo (llevas {len(war_data['player_scores_data']['team1'])}).")
                        return
                    war_data['player_scores_current_team'] = 'team2'
                    await ctx.send(f"¡Entendido! Ahora ingresa los jugadores de **{war_data['team2_name']}**.")
                    continue
                elif war_data['player_scores_current_team'] == 'team2':
                    await ctx.send(f"Ya estás ingresando jugadores para **{war_data['team2_name']}**.")
                    continue

            match = re.match(r"(.+?)\s+(\d+)(?:\s+dc=(\d+))?(?:\s+r=([\d,]+))?$", line, re.IGNORECASE)
            if match:
                player_name = match.group(1).strip()
                player_score = int(match.group(2))
                dc_count_player_input = int(match.group(3)) if match.group(3) else 0
                dc_races_str = match.group(4)
                
                dc_race_numbers = []
                if dc_races_str:
                    try:
                        dc_race_numbers = [int(r.strip()) for r in dc_races_str.split(',')]
                    except ValueError:
                        await ctx.send(f"Error en '{line}': Formato de números de carrera 'r=' inválido. Usa números separados por comas (ej. `r=1,5`). Esta línea no se registró.")
                        continue

                try:
                    if player_score < 0:
                        await ctx.send(f"Error en '{line}': El puntaje del jugador no puede ser negativo. Esta línea no se registró.")
                        continue
                    
                    if dc_count_player_input > 0:
                        if dc_count_player_input != len(dc_race_numbers):
                            await ctx.send(f"Error en '{line}': El número de DCs ({dc_count_player_input}) no coincide con la cantidad de carreras especificadas en 'r=' ({len(dc_race_numbers)}). Esta línea no se registró.")
                            continue
                        
                        invalid_races = [r for r in dc_race_numbers if not (1 <= r <= 12)]
                        if invalid_races:
                            await ctx.send(f"Error en '{line}': Número(s) de carrera inválido(s) en 'r=': {invalid_races} (debe ser 1-12). Esta línea no se registró.")
                            continue

                        if 'dc_per_race_count' not in war_data:
                            war_data['dc_per_race_count'] = {i: 0 for i in range(1, 13)}
                        
                        for r_num in dc_race_numbers:
                            war_data['dc_per_race_count'][r_num] += 1
                            
                            if war_data['dc_per_race_count'][r_num] > MAX_DC_PER_RACE:
                                await ctx.send(f"Advertencia: La Carrera {r_num} ahora tiene {war_data['dc_per_race_count'][r_num]} DCs reportados. Esto excede el límite de {MAX_DC_PER_RACE} DCs por carrera. Por favor, revisa tus entradas.")

                    current_team_key = war_data['player_scores_current_team']
                    expected_players_per_team = war_data['players_per_team']

                    if len(war_data['player_scores_data'][current_team_key]) >= expected_players_per_team:
                        await ctx.send(f"Advertencia: Ya has ingresado {expected_players_per_team} jugadores para **{war_data[current_team_key + '_name']}**. Este jugador '{player_name}' ha sido añadido EXTRA. Escribe 'FIN' cuando hayas terminado.")
                    
                    war_data['player_scores_data'][current_team_key].append({
                        'name': player_name,
                        'score': player_score,
                        'dc_count': dc_count_player_input,
                        'dc_races': dc_race_numbers
                    })
                    dc_info_display = ""
                    if dc_count_player_input > 0:
                        dc_info_display = f" (DC: {dc_count_player_input} en Carreras {', '.join(map(str, dc_race_numbers))})"
                    await ctx.send(f"Registrado: {player_name} ({player_score} pts) para **{war_data[current_team_key + '_name']}**.{dc_info_display}")
                    processed_any_line_in_bulk = True

                except ValueError:
                    await ctx.send(f"Formato incorrecto en '{line}'. Ingresa `NombreDelJugador Puntaje [dc=N r=X]`. Esta línea no se registró.")
            else:
                await ctx.send(f"Formato incorrecto en '{line}'. Ingresa `NombreDelJugador Puntaje [dc=N r=X]`. Esta línea no se registró.")
        
        if processed_any_line_in_bulk:
            players_entered_for_current_team = len(war_data['player_scores_data'][war_data['player_scores_current_team']])
            expected_players_per_team = war_data['players_per_team']

            if war_data['player_scores_current_team'] == 'team1':
                if players_entered_for_current_team < expected_players_per_team:
                    await ctx.send(f"Ingresa el siguiente jugador para **{war_data['team1_name']}** (Llevas {players_entered_for_current_team}/{expected_players_per_team}).")
                elif players_entered_for_current_team == expected_players_per_team:
                    await ctx.send(f"¡Has ingresado los {expected_players_per_team} jugadores para **{war_data['team1_name']}**!\n"
                                     f"Ahora ingresa los jugadores de **{war_data['team2_name']}** (Formato: `NombreDelJugador Puntaje [dc=N r=X]`).")
                    war_data['player_scores_current_team'] = 'team2'
            elif war_data['player_scores_current_team'] == 'team2':
                if players_entered_for_current_team < expected_players_per_team:
                    await ctx.send(f"Ingresa el siguiente jugador para **{war_data['team2_name']}** (Llevas {players_entered_for_current_team}/{expected_players_per_team}).")
                elif players_entered_for_current_team == expected_players_per_team:
                    await ctx.send(f"¡Has ingresado los {expected_players_per_team} jugadores para **{war_data['team2_name']}**!\n"
                                     f"Puedes escribir `FIN` para generar la tabla.")
        return

    if message.content.startswith(bot.command_prefix):
        return

    if channel_id in active_wars and active_wars[channel_id]['status'] == 'in_progress':
        war_data = active_wars[channel_id]
        current_race = war_data['current_race']

        if current_race <= 12:
            content = message.content.lower().strip()
            raw_positions_str = ""
            dc_count = 0

            if 'dc=' in content:
                parts = content.split('dc=')
                raw_positions_str = parts[0].strip()
                try:
                    dc_count = int(parts[1].strip())
                    if dc_count < 0:
                        await message.channel.send("El número de desconectados (dc) no puede ser negativo.")
                        return
                    
                    max_players_in_race = war_data['players_per_team'] * 2
                    if dc_count >= max_players_in_race:
                        await message.channel.send(f"Error: No puede haber {dc_count} desconectado(s) si solo hay {max_players_in_race} jugadores totales en la pista. La carrera no puede tener 0 o menos jugadores activos.")
                        return
                    
                    if dc_count > 0:
                        plural = "jugador" if dc_count == 1 else "jugadores"
                        await message.channel.send(f"**¡{dc_count} {plural} desconectado(s) reportado(s)! Puntuación basada en carrera de {max_players_in_race} corredores.**")
                    
                except ValueError:
                    await message.channel.send("Formato de `dc=` incorrecto. Usa `dc=X` donde X es un número entero.")
                    return
            else:
                raw_positions_str = content

            try:
                team_positions = [int(p) for p in raw_positions_str.split()]
            except ValueError:
                await message.channel.send("Formato de posiciones incorrecto. Las posiciones deben ser números separados por espacios (ej. `1 2 5 9 11`).")
                return
            
            if len(team_positions) != len(set(team_positions)):
                await message.channel.send("Error: ¡No se pueden repetir posiciones en la misma carrera! Cada posición debe ser única. Por favor, corrige tu entrada.")
                return

            max_players_in_race = war_data['players_per_team'] * 2

            if any(pos <= 0 or pos > max_players_in_race for pos in team_positions):
                await message.channel.send(f"Una de las posiciones ingresadas es inválida. Las posiciones deben ser números enteros entre 1 y {max_players_in_race} (basado en {war_data['players_per_team']}v{war_data['players_per_team']} = {max_players_in_race} jugadores totales en pista).")
                return

            expected_positions_for_full_team = war_data['players_per_team']

            is_valid_count = False
            if dc_count > 0:
                expected_if_our_dc = war_data['players_per_team'] - dc_count
                if expected_if_our_dc < 0:
                    await message.channel.send(f"Error interno: El número de DCs reportados ({dc_count}) es demasiado alto para tu equipo ({war_data['players_per_team']} jugadores).")
                    return

                if len(team_positions) == expected_positions_for_full_team or len(team_positions) == expected_if_our_dc:
                    is_valid_count = True
                
                if not is_valid_count:
                    await message.channel.send(f"Error: Has reportado {len(team_positions)} posiciones. Con {dc_count} DC(s), se esperaban **exactamente** {expected_positions_for_full_team} (equipo completo) O {expected_if_our_dc} (asumiendo DC(s) de tu equipo). Por favor, corrige tu entrada.")
                    return
            else:
                if len(team_positions) != expected_positions_for_full_team:
                    await message.channel.send(f"Error: Has reportado {len(team_positions)} posiciones para tu equipo. Se esperaban **exactamente** {expected_positions_for_full_team} posiciones. Por favor, corrige tu entrada.")
                    return
            
            team_points = 0
            points_map = POINTS_TOTAL_12_PLAYERS_RACE
            total_race_points = 82

            for pos in team_positions:
                if pos in points_map:
                    team_points += points_map[pos]
                else:
                    await message.channel.send(f"La posición {pos} no tiene puntos asignados en la tabla de 12 jugadores. Esto no debería ocurrir con la validación actual.")
                    return
            
            opponent_points = total_race_points - team_points

            war_data['team1_points'] += team_points
            war_data['team2_points'] += opponent_points
            war_data['race_points_history'].append({'team1_points': team_points, 'team2_points': opponent_points})

            registered_race_number = current_race
            war_data['current_race'] += 1

            note = ""
            if dc_count > 0:
                players_who_finished = max_players_in_race - dc_count
                note = f"Nota: En la Carrera {registered_race_number} se corrió con {players_who_finished} jugadores que terminaron ({dc_count} DC reportado(s) en la carrera)."
                war_data['race_notes'].append(note)

            await message.channel.send(f"Carrera {registered_race_number} registrada. Puntos de tu equipo: **{team_points}**. Puntos del oponente: **{opponent_points}**.")
            
            current_difference = war_data['team1_points'] - war_data['team2_points']
            if current_difference > 0:
                await message.channel.send(f"¡Van ganando por **{current_difference}** puntos! 💪")
            elif current_difference < 0:
                await message.channel.send(f"Van perdiendo por **{-current_difference}** puntos. ¡A esforzarse más! 🚀")
            else:
                await message.channel.send("¡El marcador está empatado! 🤝")
            
            race_differential = team_points - opponent_points
            if race_differential > 0:
                await message.channel.send(f"Esta carrera fue de **+{race_differential}** puntos para tu equipo. 🎉")
            elif race_differential < 0:
                await message.channel.send(f"Esta carrera fue de **{race_differential}** puntos para tu equipo. 📉")
            else:
                await message.channel.send("Esta carrera fue un empate en puntos. ↔️")

            # Re-habilitar el envío de la imagen del scoreboard aquí
            score_image_bytes = await generate_race_image(war_data)
            if score_image_bytes:
                await ctx.send(file=discord.File(score_image_bytes, filename=f"war_score_carrera_{registered_race_number}.png"))
            else:
                print("DEBUG: generate_race_image regresó None, no se generó la imagen.")
                await ctx.send("Error al generar la imagen de resultados. Revisa la consola del bot para más detalles (ej. problemas con fuentes o logos).")

            if war_data['current_race'] <= 12:
                await message.channel.send(f"Ingresa las posiciones para la Carrera {war_data['current_race']}.")
            else:
                final_message = (f"¡War finalizada!\n"
                                 f"**{war_data['team1_name']}:** {war_data['team1_points']} puntos\n"
                                 f"**{war_data['team2_name']}:** {war_data['team2_points']} puntos\n\n")

                if war_data['race_notes']:
                    final_message += "--- Notas de la War ---\n"
                    final_message += "\n".join(war_data['race_notes'])

                await ctx.send(final_message)
                
                war_data['status'] = 'finalized'
                await ctx.send("La war ha finalizado. Usa `/war-table` para ingresar y ver las puntuaciones individuales de los jugadores.")

# Manejador de eventos para reacciones (NUEVO)
@bot.event
async def on_reaction_add(reaction, user):
    # Ignorar reacciones del propio bot
    if user == bot.user:
        return

    channel_id = reaction.message.channel.id
    
    # Buscar la war activa por el message_id de la tabla y el usuario que la inició
    found_war_data = None
    for cid, wd in active_wars.items():
        if wd.get('player_table_message_id') == reaction.message.id and wd.get('player_table_initiator_id') == user.id:
            found_war_data = wd
            channel_id = cid
            break
    
    if found_war_data:
        war_data = found_war_data
        print(f"DEBUG: Reacción detectada para war en canal {channel_id} por usuario {user.name}.")

        if str(reaction.emoji) == "✅":
            print("DEBUG: Reacción ✅ recibida. Procesando guardado.")
            
            # Asegurarse de que la war_data tiene un ID antes de guardarla
            if 'id' not in war_data:
                war_data['id'] = get_next_id() # Generar ID si no existe (para wars en vivo)
                print(f"DEBUG: ID generado para war en vivo: {war_data['id']}")
            
            history = load_history()
            
            # Usar la fecha/timestamp de la war si es histórica, si no, la actual
            record_date = war_data.get('historical_date_str', datetime.datetime.now().strftime("%Y-%m"))
            record_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            status = "draw"
            if war_data['team1_player_sum'] > war_data['team2_player_sum']:
                status = "won"
            elif war_data['team1_player_sum'] < war_data['team2_player_sum']:
                status = "lost"

            new_history_entry = {
                "id": war_data['id'], # Usar el ID que ya está en war_data
                "date": record_date,
                "timestamp": record_timestamp,
                "team1_name": war_data['team1_name'],
                "team2_name": war_data['team2_name'],
                "team1_score": war_data['team1_player_sum'],
                "team2_score": war_data['team2_player_sum'],
                "status": status,
                "notes": war_data['race_notes'],
                "logo1_url": war_data['logo1_url'],
                "logo2_url": war_data['logo2_url'],
                "players_per_team": war_data['players_per_team'],
                "player_scores_data": war_data['player_scores_data'],
                "dc_per_race_count": war_data.get('dc_per_race_count', {i: 0 for i in range(1, 13)}), # Asegura que se guarda el conteo de DCs por carrera
            }
            history.append(new_history_entry)
            save_history(history)
            print(f"DEBUG: War con ID {new_history_entry['id']} guardada en el historial.")

            # --- NUEVO: Mensaje de confirmación con hipervínculo ---
            # Enviar la tabla al canal 📋 resultados
            war_results_channel = discord.utils.get(reaction.message.guild.text_channels, name='⌊📋⌉resultados') # CANAL CON EMOJI
            if war_results_channel:
                # Rebobinar el BytesIO de la imagen para enviarla a 📋 resultados
                player_table_image_bytes_io = found_war_data.get('temp_player_table_image_bytes')
                if player_table_image_bytes_io:
                    player_table_image_bytes_io.seek(0) # Rebobinar
                    sent_to_results_channel_message = await war_results_channel.send(
                        content=f"📊 Tabla de Puntuaciones de Jugadores (ID: {war_data['id']})",
                        file=discord.File(player_table_image_bytes_io, filename=f"war_player_scores_table_{war_data['id']}.png")
                    )
                    permalink = sent_to_results_channel_message.jump_url
                    # Mensaje en el canal original con el hipervínculo que es solo el ID
                    await reaction.message.channel.send(f"✅ Tabla confirmada y war cerrada. ID: [{war_data['id']}]({permalink})")
                else:
                    await reaction.message.channel.send(f"✅ Tabla confirmada y war cerrada. ID: {war_data['id']} (Error al generar la imagen para ⌊📋⌉resultados).")
            else:
                await reaction.message.channel.send(f"✅ Tabla confirmada y war cerrada. ID: {war_data['id']} (No se encontró el canal ⌊📋⌉resultados).")
            # --- FIN NUEVO ---

            del active_wars[channel_id]
            await reaction.message.clear_reactions()
            return
        elif str(reaction.emoji) == "❌":
            print("DEBUG: Reacción ❌ recibida. Reiniciando entrada de puntajes.")
            await reaction.message.channel.send("❌ Volviendo a ingresar puntajes. Por favor, ingresa nuevamente los jugadores y sus puntajes desde el principio.")
            war_data['player_scores_input_mode'] = True
            war_data['player_scores_current_team'] = 'team1'
            war_data['player_scores_data'] = {'team1': [], 'team2': []} # Borrar datos previos
            
            await reaction.message.clear_reactions()
            await ctx.send(f"📊 **¡Re-ingresando puntuaciones individuales!**\n"
                                                 f"Comienza con los jugadores de **{war_data['team1_name']}** (Formato: `NombreDelJugador Puntaje [dc=N r=X]`).\n"
                                                 f"Cuando termines con **{war_data['team1_name']}**, el bot te lo indicará para que ingreses los del siguiente equipo.\n"
                                                 f"Luego, ingresa los jugadores de **{war_data['team2_name']}**.\n"
                                                 f"Cuando hayas terminado con **AMBOS** equipos, el bot te indicará que puedes escribir `FIN`.")
            return
        else:
            print(f"DEBUG: Reacción '{reaction.emoji}' no reconocida. Removiendo.")
            await reaction.remove(user)
            return

# --- Comando /war-table-normalize ---
@bot.tree.command(name='war-table-normalize', description="Normaliza los puntos de una war guardada por ID.")
@app_commands.describe(
    war_id="El ID de la war a normalizar (ej. '00001')."
)
async def war_table_normalize_command(interaction: discord.Interaction, war_id: str):
    ctx = await commands.Context.from_interaction(interaction)
    history = load_history()

    target_war = None
    for record in history:
        if record.get('id') == war_id:
            target_war = record
            break

    if not target_war:
        await ctx.send(f"No se encontró una war con el ID '{war_id}' en el historial.")
        return

    # Crear una copia profunda para no modificar el historial original directamente
    normalized_war_data = target_war.copy()
    normalized_war_data['player_scores_data'] = {
        'team1': [p.copy() for p in target_war['player_scores_data']['team1']],
        'team2': [p.copy() for p in target_war['player_scores_data']['team2']]
    }
    normalized_war_data['is_historical_creation'] = True # Marcar como creación histórica
    normalized_war_data['timestamp'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    normalized_war_data['historical_timestamp_str'] = normalized_war_data['timestamp']
    normalized_war_data['id'] = get_next_id() # Nuevo ID para la tabla normalizada

    original_team1_sum = sum(p['score'] for p in target_war['player_scores_data']['team1'])
    original_team2_sum = sum(p['score'] for p in target_war['player_scores_data']['team2'])
    original_total_sum = original_team1_sum + original_team2_sum

    response_message = ""
    normalization_notes = [] # Para añadir al campo 'notes' de la war normalizada

    # --- Lógica simplificada: SOLO el método 'bonus' ---
    num_1dc_races = 0
    # Contar cuántas carreras tuvieron exactamente 1 DC
    if 'dc_per_race_count' in target_war and target_war['dc_per_race_count']:
        for race_num, dc_count in target_war['dc_per_race_count'].items():
            if dc_count == 1: # Si exactamente 1 jugador se desconectó en la carrera
                num_1dc_races += 1
    else:
        # Si no hay 'dc_per_race_count' en la war guardada, no se puede aplicar el bonus.
        await ctx.send(f"La war con ID '{war_id}' no contiene el conteo de DCs por carrera o no está completo. No se puede aplicar la normalización por bonificación.")
        return

    if num_1dc_races == 0:
        await ctx.send(f"La war con ID '{war_id}' no tuvo carreras con exactamente 1 DC. No se aplicarán bonificaciones.")
        response_message = f"War ID: {war_id} sin cambios (no hubo carreras de 11 jugadores). Nueva tabla ID: **{normalized_war_data['id']}**."
        normalization_notes.append("No se aplicó bonificación: No se registraron carreras con 1 DC.")
    else:
        all_players = []
        for player in normalized_war_data['player_scores_data']['team1']:
            all_players.append({'name': player['name'], 'score': player['score'], 'team': 'team1'})
        for player in normalized_war_data['player_scores_data']['team2']:
            all_players.append({'name': player['name'], 'score': player['score'], 'team': 'team2'})
        
        # Ordenar todos los jugadores por puntaje para aplicar las bonificaciones
        all_players_sorted = sorted(all_players, key=lambda p: p['score'], reverse=True)

        bonus_info = [] # Para las notas

        for i, player_info in enumerate(all_players_sorted):
            player_name = player_info['name']
            bonus_points = 0
            
            if i == 0: # Primer lugar general (MVP)
                bonus_points = 3 * num_1dc_races
                rank_desc = "1er lugar"
            elif i == 1: # Segundo lugar general
                bonus_points = 2 * num_1dc_races
                rank_desc = "2do lugar"
            elif i >= 2 and i < len(all_players_sorted): # Tercer al último lugar general
                bonus_points = 1 * num_1dc_races
                rank_desc = f"{i+1}vo lugar"
            
            # Actualizar el score del jugador en normalized_war_data
            for team_key in ['team1', 'team2']:
                for p in normalized_war_data['player_scores_data'][team_key]:
                    if p['name'] == player_name and player_info['team'] == team_key:
                        p['score'] += bonus_points
                        if bonus_points > 0:
                            bonus_info.append(f"{player_name} ({rank_desc}): +{bonus_points} pts")
                        break
                if bonus_points > 0 and player_name in [p['name'] for p in normalized_war_data['player_scores_data'][team_key] if p['name'] == player_name]:
                    break

        # Recalcular sumas
        normalized_war_data['team1_player_sum'] = sum(p['score'] for p in normalized_war_data['player_scores_data']['team1'])
        normalized_war_data['team2_player_sum'] = sum(p['score'] for p in normalized_war_data['player_scores_data']['team2'])
        total_after_bonus = normalized_war_data['team1_player_sum'] + normalized_war_data['team2_player_sum']

        normalization_notes.append(f"Normalizada por bonificación de posiciones finales (aplicado a {num_1dc_races} carreras con 1 DC).")
        if bonus_info:
            normalization_notes.append("Bonificaciones aplicadas: " + ", ".join(bonus_info))

        response_message = f"War ID: {war_id} normalizada. Nueva suma total: **{total_after_bonus}**. Nueva tabla ID: **{normalized_war_data['id']}**."
        
    # Limpiar las notas de la war original y añadir las de normalización
    if 'notes' not in normalized_war_data or not isinstance(normalized_war_data['notes'], list):
        normalized_war_data['notes'] = []
    normalized_war_data['notes'].extend(normalization_notes)
    
    # Guardar la nueva entrada en el historial
    history.append({
        "id": normalized_war_data['id'],
        "date": normalized_war_data.get('historical_date_str', datetime.datetime.now().strftime("%Y-%m")),
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "team1_name": normalized_war_data['team1_name'],
        "team2_name": normalized_war_data['team2_name'],
        "team1_score": normalized_war_data['team1_player_sum'],
        "team2_score": normalized_war_data['team2_player_sum'],
        "status": "normalized",
        "notes": normalized_war_data['notes'],
        "logo1_url": normalized_war_data['logo1_url'],
        "logo2_url": normalized_war_data['logo2_url'],
        "players_per_team": normalized_war_data['players_per_team'],
        "player_scores_data": normalized_war_data['player_scores_data'],
        "dc_per_race_count": target_war.get('dc_per_race_count', {}),
        "original_war_id": war_id
    })
    save_history(history)
    print(f"DEBUG: War normalizada con ID {normalized_war_data['id']} guardada en el historial.")

    # Generar y enviar la imagen de la tabla normalizada
    player_table_image_bytes_io = await generate_player_table_image(normalized_war_data)
    if player_table_image_bytes_io:
        # Enviar al canal original
        sent_message_in_original_channel = await ctx.send(
            content=response_message,
            file=discord.File(io.BytesIO(player_table_image_bytes_io.getvalue()), filename=f"normalized_war_player_scores_table_{normalized_war_data['id']}.png")
        )

        # Enviar al canal de resultados y añadir hipervínculo
        war_results_channel = discord.utils.get(interaction.guild.text_channels, name='⌊📋⌉resultados')
        if war_results_channel:
            # Rebobinar el BytesIO para poder enviarlo de nuevo
            player_table_image_bytes_io.seek(0)
            sent_to_results_channel_message = await war_results_channel.send(
                content=f"📊 Tabla de Puntuaciones de Jugadores (ID: {normalized_war_data['id']}) [Normalizada]",
                file=discord.File(player_table_image_bytes_io, filename=f"normalized_war_player_scores_table_{normalized_war_data['id']}.png")
            )
            permalink = sent_to_results_channel_message.jump_url
            # Editar el mensaje original para incluir el hipervínculo
            await sent_message_in_original_channel.edit(
                content=f"{response_message}\nTabla también enviada a [{war_results_channel.name}]({permalink})"
            )
        else:
            await ctx.send(f"No se encontró el canal '⌊📋⌉resultados'. La tabla normalizada no fue copiada allí.")
    else:
        await ctx.send(f"Error al generar la imagen de la tabla normalizada. {response_message}")


# --- EJECUTAR EL BOT ---
if TOKEN is None:
    print("Error: El token de Discord no se encontró. Asegúrate de tener un archivo .env con DISCORD_TOKEN=TU_TOKEN")
else:
    bot.run(TOKEN)
