from flask import Flask, request, jsonify, redirect
import requests
import re
import zlib
import time

app = Flask(__name__)

# --- CONFIGURACIÓN ---
M3U_URL = "https://raw.githack.com/Adolfo761/lista-iptv-permanente/main/LISTA_DEFINITIVA_PERMANENTE.m3u"
USER_VALIDO = "adolfo"
PASS_VALIDO = "vip2026"

# --- CACHÉ EN MEMORIA (Para velocidad extrema) ---
CACHE_DATA = {"streams": [], "categories": [], "timestamp": 0}
CACHE_TTL = 300  # Mantener en memoria 5 minutos

# --- GENERADOR DE IDs ULTRA RÁPIDO Y ESTABLE ---
def get_stable_id(text):
    # zlib.adler32 es mucho más rápido que MD5 y siempre devuelve números
    return str(zlib.adler32(text.encode('utf-8')) & 0xffffffff)

def load_data():
    # Si la caché está fresca, úsala
    if time.time() - CACHE_DATA["timestamp"] < CACHE_TTL and CACHE_DATA["streams"]:
        return CACHE_DATA["streams"], CACHE_DATA["categories"]

    try:
        print("Descargando lista fresca de GitHub...")
        r = requests.get(M3U_URL, timeout=10)
        r.encoding = 'utf-8'
        content = r.text
        
        streams = []
        categories = set()
        current_cat = "General"
        
        for line in content.splitlines():
            line = line.strip()
            if not line: continue
            
            if line.startswith("#EXTINF"):
                # Extraer Categoría
                cat_match = re.search(r'group-title="([^"]+)"', line)
                if cat_match:
                    current_cat = cat_match.group(1)
                categories.add(current_cat)
                
                # Extraer Nombre
                name_parts = line.split(",")
                name = name_parts[-1].strip()
                
                # Extraer Logo
                logo_match = re.search(r'tvg-logo="([^"]+)"', line)
                logo = logo_match.group(1) if logo_match else ""
                
            elif line.startswith("http"):
                # ID ÚNICO BASADO EN LA URL (Estable)
                stream_id = get_stable_id(line)
                # ID DE CATEGORÍA ESTABLE (Crucial para XCIPTV)
                cat_id = get_stable_id(current_cat)
                
                is_movie = "/movie/" in line or line.endswith((".mp4", ".mkv", ".avi"))
                stream_type = "movie" if is_movie else "live"
                ext = "mp4" if is_movie else "ts"
                
                streams.append({
                    "num": stream_id,
                    "name": name,
                    "stream_type": stream_type,
                    "stream_id": stream_id,
                    "stream_icon": logo,
                    "epg_channel_id": name,
                    "added": "1644400000",
                    "category_id": cat_id,
                    "container_extension": ext,
                    "custom_sid": "",
                    "direct_source": line
                })
        
        # Guardar en Caché
        CACHE_DATA["streams"] = streams
        CACHE_DATA["categories"] = list(categories)
        CACHE_DATA["timestamp"] = time.time()
        return streams, list(categories)
        
    except Exception as e:
        print(f"Error cargando lista: {e}")
        return [], []

# --- API PRINCIPAL ---
@app.route('/player_api.php')
def xtream_api():
    user = request.args.get('username')
    password = request.args.get('password')
    action = request.args.get('action', 'login')

    if user != USER_VALIDO or password != PASS_VALIDO:
        return jsonify({"user_info": {"auth": 0}, "server_info": {}})

    if action == 'login':
        return jsonify({
            "user_info": {
                "username": user,
                "password": password,
                "message": "Adolfo Turbo V4",
                "auth": 1,
                "status": "Active",
                "exp_date": "1799999999",
                "is_trial": "0",
                "active_cons": "0",
                "created_at": "1644400000",
                "max_connections": "10",
                "allowed_output_formats": ["m3u8", "ts", "rtmp"]
            },
            "server_info": {
                "url": request.host_url,
                "port": "443",
                "https_port": "443",
                "server_protocol": "https",
                "rtmp_port": "8880",
                "timezone": "America/Santo_Domingo",
                "timestamp_now": int(time.time()),
                "time_now": "2026-02-01 12:00:00"
            }
        })

    # Cargar datos (usando caché)
    streams, cats = load_data()
    
    if action == 'get_live_categories':
        # Usamos get_stable_id para que el ID de la categoría coincida con el del stream
        return jsonify([{"category_id": get_stable_id(c), "category_name": c, "parent_id": 0} for c in cats])
    
    elif action == 'get_vod_categories':
        return jsonify([{"category_id": get_stable_id(c), "category_name": c, "parent_id": 0} for c in cats])
        
    elif action == 'get_live_streams':
        return jsonify([s for s in streams if s['stream_type'] == 'live'])
        
    elif action == 'get_vod_streams':
        return jsonify([s for s in streams if s['stream_type'] == 'movie'])

    return jsonify([])

# --- REPRODUCCIÓN ULTRA RÁPIDA ---
@app.route('/live/<user>/<password>/<stream_id>.ts')
@app.route('/live/<user>/<password>/<stream_id>.m3u8')
@app.route('/movie/<user>/<password>/<stream_id>.<ext>')
def universal_play(user, password, stream_id, ext=None):
    clean_id = stream_id.replace('.ts', '').replace('.m3u8', '').replace('.mp4', '').replace('.mkv', '')
    
    streams, _ = load_data()
    
    # Búsqueda optimizada
    for s in streams:
        if s['stream_id'] == clean_id:
            return redirect(s['direct_source'], code=302)
            
    return "Canal no encontrado (Refresca la lista)", 404

if __name__ == '__main__':
    app.run(debug=True)
