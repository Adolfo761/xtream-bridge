from flask import Flask, request, jsonify
import requests
import re

app = Flask(__name__)

# --- CONFIGURACIÓN ---
# Tu lista M3U definitiva (Usamos githack para evitar bloqueos)
M3U_URL = "https://raw.githack.com/Adolfo761/lista-iptv-permanente/main/LISTA_DEFINITIVA_PERMANENTE.m3u"
# Credenciales Falsas (Tus clientes usarán estas)
USER_VALIDO = "adolfo"
PASS_VALIDO = "vip2026"

def parse_m3u(m3u_content):
    streams = []
    categories = set()
    lines = m3u_content.splitlines()
    current_cat = "General"
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        if line.startswith("#EXTINF"):
            # Intentar extraer categoria
            cat_match = re.search(r'group-title="([^"]+)"', line)
            if cat_match:
                current_cat = cat_match.group(1)
            categories.add(current_cat)
            
            # Extraer nombre (todo después de la última coma)
            name = line.split(",")[-1].strip()
            
            # Extraer logo
            logo_match = re.search(r'tvg-logo="([^"]+)"', line)
            logo = logo_match.group(1) if logo_match else ""
            
        elif line.startswith("http"):
            # Crear un ID único basado en la URL
            stream_id = abs(hash(line)) % 1000000
            
            streams.append({
                "num": stream_id,
                "name": name,
                "stream_type": "live",
                "stream_id": stream_id,
                "stream_icon": logo,
                "epg_channel_id": "",
                "added": "1644400000",
                "category_id": abs(hash(current_cat)) % 1000,
                "container_extension": "ts",
                "custom_sid": "",
                "direct_source": line
            })
    return streams, list(categories)

@app.route('/player_api.php')
def xtream_api():
    user = request.args.get('username')
    password = request.args.get('password')
    action = request.args.get('action', 'login')

    # 1. Seguridad
    if user != USER_VALIDO or password != PASS_VALIDO:
        return jsonify({"user_info": {"auth": 0}, "server_info": {}})

    # 2. Login
    if action == 'login':
        return jsonify({
            "user_info": {
                "username": user,
                "password": password,
                "message": "Bienvenido a Adolfo TV",
                "auth": 1,
                "status": "Active",
                "exp_date": "1799999999",
                "is_trial": "0",
                "active_cons": "0",
                "created_at": "1644400000",
                "max_connections": "1",
                "allowed_output_formats": ["m3u8", "ts", "rtmp"]
            },
            "server_info": {
                "url": request.host_url,
                "port": "80",
                "https_port": "443",
                "server_protocol": "http",
                "rtmp_port": "8880",
                "timezone": "America/Santo_Domingo",
                "timestamp_now": 1644400000,
                "time_now": "2026-02-01 12:00:00"
            }
        })

    # 3. Descargar lista real (solo si pide streams)
    if action in ['get_live_streams', 'get_live_categories']:
        try:
            r = requests.get(M3U_URL)
            r.encoding = 'utf-8' # Forzar UTF-8 para tildes
            streams, cats = parse_m3u(r.text)
        except Exception as e:
            return jsonify([])

        if action == 'get_live_categories':
            json_cats = [{"category_id": abs(hash(c)) % 1000, "category_name": c, "parent_id": 0} for c in cats]
            return jsonify(json_cats)
            
        elif action == 'get_live_streams':
            return jsonify(streams)

    # 4. VOD (Películas) - Retornamos vacío por ahora para no saturar
    if action == 'get_vod_streams' or action == 'get_vod_categories':
        return jsonify([])

    return jsonify([])

# Vercel necesita esto
if __name__ == '__main__':
    app.run(debug=True)
