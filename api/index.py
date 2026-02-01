from flask import Flask, request, jsonify, redirect
import requests
import re
import hashlib

app = Flask(__name__)

# --- CONFIGURACIÓN ---
M3U_URL = "https://raw.githack.com/Adolfo761/lista-iptv-permanente/main/LISTA_DEFINITIVA_PERMANENTE.m3u"
USER_VALIDO = "adolfo"
PASS_VALIDO = "vip2026"

# --- GENERADOR DE IDs NUMÉRICOS ESTABLES ---
def get_numeric_id(url):
    # Crea una huella digital única (MD5) de la URL
    hash_object = hashlib.md5(url.strip().encode())
    # La convierte a un número hexadecimal y luego a entero
    full_int = int(hash_object.hexdigest(), 16)
    # Lo recorta a 8 dígitos para que sea un ID seguro (ej: 48291043)
    return str(full_int % 100000000)

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
            name_parts = line.split(",")
            name = name_parts[-1].strip()
            
            # Extraer logo
            logo_match = re.search(r'tvg-logo="([^"]+)"', line)
            logo = logo_match.group(1) if logo_match else ""
            
        elif line.startswith("http"):
            # GENERAMOS EL ID NUMÉRICO
            stream_id = get_numeric_id(line)
            
            # Detectar tipo
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
                "category_id": str(abs(hash(current_cat)) % 10000), 
                "container_extension": ext,
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

    if action == 'login':
        return jsonify({
            "user_info": {
                "username": user,
                "password": password,
                "message": "Adolfo Bridge V3 (Numeric)",
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

    # Descarga y parseo (común para todas las peticiones de lista)
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
            return jsonify([s for s in streams if s['stream_type'] == 'live'])

        elif action == 'get_vod_categories':
            json_cats = [{"category_id": str(abs(hash(c)) % 10000), "category_name": c, "parent_id": 0} for c in cats]
            return jsonify(json_cats)
            
        elif action == 'get_vod_streams':
            return jsonify([s for s in streams if s['stream_type'] == 'movie'])

    return jsonify([])

# --- REDIRECCIÓN MÁGICA ---
# Cuando la app pide reproducir el ID numérico, buscamos qué URL real le corresponde
@app.route('/live/<user>/<password>/<stream_id>.ts')
@app.route('/live/<user>/<password>/<stream_id>.m3u8')
@app.route('/movie/<user>/<password>/<stream_id>.<ext>')
def universal_play(user, password, stream_id, ext=None):
    # Limpiamos el ID (quitamos extensiones si vienen pegadas)
    clean_id = stream_id.replace('.ts', '').replace('.m3u8', '').replace('.mp4', '').replace('.mkv', '')
    
    try:
        # Tenemos que descargar la lista para saber qué URL corresponde a este ID numérico
        r = requests.get(M3U_URL)
        r.encoding = 'utf-8'
        streams, _ = parse_m3u(r.text)
        
        # Buscar el stream que tenga este ID
        for s in streams:
            if s['stream_id'] == clean_id:
                return redirect(s['direct_source'], code=302)
                
        return "Error: ID no encontrado en la lista actual", 404
    except:
        return "Error interno", 500

if __name__ == '__main__':
    app.run(debug=True)
