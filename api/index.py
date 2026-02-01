from flask import Flask, request, jsonify, redirect
import requests
import re
import base64

app = Flask(__name__)

# --- CONFIGURACIÓN ---
M3U_URL = "https://raw.githack.com/Adolfo761/lista-iptv-permanente/main/LISTA_DEFINITIVA_PERMANENTE.m3u"
USER_VALIDO = "adolfo"
PASS_VALIDO = "vip2026"

# --- FUNCIONES AUXILIARES ---
def encode_id(url):
    # Convierte la URL real en un ID seguro y único
    return base64.urlsafe_b64encode(url.strip().encode()).decode().rstrip("=")

def decode_id(sid):
    # Recupera la URL real desde el ID
    try:
        padding = 4 - (len(sid) % 4)
        sid += "=" * padding
        return base64.urlsafe_b64decode(sid.encode()).decode()
    except:
        return None

def parse_m3u(m3u_content):
    streams = []
    categories = set()
    lines = m3u_content.splitlines()
    current_cat = "General"
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        if line.startswith("#EXTINF"):
            # Extraer categoria
            cat_match = re.search(r'group-title="([^"]+)"', line)
            if cat_match:
                current_cat = cat_match.group(1)
            categories.add(current_cat)
            
            # Extraer nombre
            name = line.split(",")[-1].strip()
            
            # Extraer logo
            logo_match = re.search(r'tvg-logo="([^"]+)"', line)
            logo = logo_match.group(1) if logo_match else ""
            
        elif line.startswith("http"):
            # USAMOS BASE64 PARA QUE EL ID SEA ESTABLE Y RECUPERABLE
            stream_id = encode_id(line)
            
            # Detectar si es VOD (básico)
            stream_type = "movie" if "/movie/" in line or line.endswith((".mp4", ".mkv")) else "live"
            
            streams.append({
                "num": 0,
                "name": name,
                "stream_type": stream_type,
                "stream_id": stream_id,
                "stream_icon": logo,
                "epg_channel_id": name,
                "added": "1644400000",
                "category_id": str(abs(hash(current_cat)) % 10000), # ID numérico simple para cat
                "container_extension": "ts",
                "custom_sid": "",
                "direct_source": line
            })
    return streams, list(categories)

# --- RUTAS DE LA API ---

@app.route('/player_api.php')
def xtream_api():
    user = request.args.get('username')
    password = request.args.get('password')
    action = request.args.get('action', 'login')

    if user != USER_VALIDO or password != PASS_VALIDO:
        return jsonify({"user_info": {"auth": 0}, "server_info": {}})

    # LOGIN
    if action == 'login':
        return jsonify({
            "user_info": {
                "username": user,
                "password": password,
                "message": "Conectado a Adolfo Bridge V2",
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
                "timestamp_now": 1644400000,
                "time_now": "2026-02-01 12:00:00"
            }
        })

    # DESCARGAR LISTA (Solo si es necesario)
    if action in ['get_live_streams', 'get_live_categories', 'get_vod_streams', 'get_vod_categories']:
        try:
            r = requests.get(M3U_URL)
            r.encoding = 'utf-8'
            streams, cats = parse_m3u(r.text)
        except:
            return jsonify([])

        if action == 'get_live_categories':
            json_cats = [{"category_id": str(abs(hash(c)) % 10000), "category_name": c, "parent_id": 0} for c in cats]
            return jsonify(json_cats)
            
        elif action == 'get_live_streams':
            # Filtrar solo canales en vivo
            return jsonify([s for s in streams if s['stream_type'] == 'live'])

        elif action == 'get_vod_categories':
             # Usamos las mismas categorías por simplicidad, o podrías filtrar
            json_cats = [{"category_id": str(abs(hash(c)) % 10000), "category_name": c, "parent_id": 0} for c in cats]
            return jsonify(json_cats)
            
        elif action == 'get_vod_streams':
            # Filtrar solo peliculas
            return jsonify([s for s in streams if s['stream_type'] == 'movie'])

    return jsonify([])

# --- RUTAS DE REPRODUCCIÓN (MAGIC REDIRECT) ---
# Estas rutas capturan el intento de reproducir y redirigen a la fuente real

@app.route('/live/<user>/<password>/<stream_id>.ts')
@app.route('/live/<user>/<password>/<stream_id>.m3u8')
def live_play(user, password, stream_id):
    # Quitamos la extensión si viene en el ID
    clean_id = stream_id.replace('.ts', '').replace('.m3u8', '')
    real_url = decode_id(clean_id)
    if real_url:
        return redirect(real_url, code=302)
    return "Error: Canal no encontrado", 404

@app.route('/movie/<user>/<password>/<stream_id>.<ext>')
def movie_play(user, password, stream_id, ext):
    real_url = decode_id(stream_id)
    if real_url:
        return redirect(real_url, code=302)
    return "Error: Pelicula no encontrada", 404

if __name__ == '__main__':
    app.run(debug=True)
