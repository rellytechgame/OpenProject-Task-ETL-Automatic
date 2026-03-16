# ==========================================
# DESARROLLO PROPIEDAD DE: Abiel Jesrrel (Relly) Delgado Lee
# Queda prohibida la reproducción total o parcial sin autorización escrita.
# No se permite uso comercial, atribución económica o reconocimiento sin consentimiento.
# ==========================================
#
# © 2026 Abiel Jesrrel (Relly) Delgado Lee - Todos los derechos reservados.
# Developed by Abiel Jesrrel (Relly) Delgado Lee
# ==========================================

import json
import random
import datetime
import pytz
import requests

# ==========================================
# 1. CONFIGURACIÓN E INICIALIZACIÓN
# ==========================================
with open('config.json', 'r') as file:
    config = json.load(file)

op_base_url = config['openproject']['base_url']
op_headers = {
    "Content-Type": "application/json",
    "Authorization": f"Basic {config['openproject']['api_token']}"
}

timezone = pytz.timezone(config['work_schedule']['timezone'])
current_time = datetime.datetime.now(timezone)
current_day_name = current_time.strftime("%A")
today_date = current_time.strftime("%Y-%m-%d")

# ==========================================
# 2. VALIDACIÓN DE HORARIO LABORAL
# ==========================================
today_rule = next((rule for rule in config['work_schedule']['rules'] if current_day_name in rule['days'] and rule.get('enabled', False)), None)

if not today_rule:
    print(f"[{current_time}] Hoy es {current_day_name}. No hay reglas activas. ETL finalizado.")
    exit()

min_h = today_rule['daily_limits']['min_hours']
max_h = today_rule['daily_limits']['max_hours']
total_hours = round(random.uniform(min_h, max_h), 2)
print(f"[{current_time}] Día laborable. Objetivo: {total_hours} horas.")

# ==========================================
# 3. EXTRACT (Obtener Tareas Abiertas)
# ==========================================
print("Extrayendo tareas asignadas y abiertas...")
filters = '[{"assignee":{"operator":"=","values":["me"]}}, {"status":{"operator":"o","values":[]}}]'
response = requests.get(f"{op_base_url}/api/v3/work_packages?filters={filters}", headers=op_headers)

if response.status_code != 200:
    print(f"Error extrayendo tareas: {response.text}")
    exit()

tasks = response.json().get('_embedded', {}).get('elements', [])
if not tasks:
    print("No tienes tareas abiertas hoy para registrar tiempos.")
    exit()

task_list = [{"id": t['id'], "subject": t['subject']} for t in tasks]

# ==========================================
# 4. TRANSFORM (Enrutador Multi-IA)
# ==========================================
print("Generando distribución con IA...")
prompt = f"""
Eres un desarrollador senior registrando sus tiempos del día.
Tienes un total de {total_hours} horas para distribuir hoy.
Tus tareas abiertas son: {json.dumps(task_list)}

Distribuye las {total_hours} horas. 
Genera un comentario técnico y realista sobre lo que hiciste en cada una.
Devuelve ÚNICAMENTE un JSON válido con este formato:
[
  {{"id": 123, "hours": 2.5, "comment": "Refactorización de controlador de usuarios"}}
]
La suma total de "hours" debe ser exactamente {total_hours}. No incluyas markdown ni texto fuera del JSON.
"""

active_ai = config['ai_settings']['active_provider']
ai_config = config['ai_settings']['providers'][active_ai]
ai_content = ""

try:
    print(f"Conectando con proveedor: {active_ai.upper()}...")
    
    if active_ai == "gemini":
        import google.generativeai as genai
        genai.configure(api_key=ai_config['api_key'])
        model = genai.GenerativeModel(ai_config['model'])
        ai_resp = model.generate_content(prompt)
        ai_content = ai_resp.text
        
    else:
        # OpenAI, Grok, Mistral, DeepSeek y OpenCode usan la interfaz de OpenAI
        from openai import OpenAI
        client = OpenAI(
            api_key=ai_config['api_key'], 
            base_url=ai_config.get('base_url') # Si es nulo, usa la default de OpenAI
        )
        ai_resp = client.chat.completions.create(
            model=ai_config['model'],
            messages=[{"role": "user", "content": prompt}]
        )
        ai_content = ai_resp.choices[0].message.content

    # Limpieza de markdown por si la IA es rebelde
    if "```json" in ai_content:
        ai_content = ai_content.split("```json")[1].split("```")[0].strip()
    elif "```" in ai_content:
        ai_content = ai_content.replace("```", "").strip()
        
    time_entries = json.loads(ai_content)

except Exception as e:
    print(f"Error procesando la IA ({active_ai}): {e}")
    exit()

# ==========================================
# 5. LOAD (Registrar en OpenProject)
# ==========================================
print("Registrando tiempos en OpenProject...")
for entry in time_entries:
    hours = float(entry['hours'])
    iso_duration = f"PT{int(hours)}H{int((hours % 1) * 60)}M"

    payload = {
        "hours": iso_duration,
        "comment": {"raw": entry['comment']},
        "spentOn": today_date,
        "_links": {
            "workPackage": {"href": f"/api/v3/work_packages/{entry['id']}"}
        }
    }

    post_resp = requests.post(f"{op_base_url}/api/v3/time_entries", headers=op_headers, json=payload)
    if post_resp.status_code == 201:
        print(f"✅ Tarea {entry['id']} actualizada: {hours}h")
    else:
        print(f"❌ Error en tarea {entry['id']}: {post_resp.text}")

print("✨ Proceso completado con arquitectura Voxel Enterprise. ¡Código limpio, vida feliz!")

# ==========================================
# © 2026 Abiel Jesrrel (Relly) Delgado Lee
# Todos los derechos reservados.
# Queda prohibida la reproducción sin autorización.
# ==========================================