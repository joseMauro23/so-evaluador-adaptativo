"""
Evaluador Adaptativo SO - UNSAAC  (v2 con base de datos JSON)
"""
import streamlit as st
import anthropic
import json
import random
import os
import csv
from datetime import datetime
from pathlib import Path

st.set_page_config(page_title="Evaluador SO - UNSAAC", page_icon="🖥️", layout="centered")

st.markdown("""
<style>
.main-title{text-align:center;color:#1a1a2e;font-size:1.8rem;font-weight:700;}
.sub-title{text-align:center;color:#16213e;font-size:1rem;margin-bottom:1.5rem;}
.pregunta-box{background:#f0f4ff;border-left:4px solid #4361ee;padding:1rem 1.2rem;border-radius:6px;margin:1rem 0;}
.correcto-box{background:#d4edda;border-left:4px solid #28a745;padding:.8rem 1rem;border-radius:6px;}
.incorrecto-box{background:#f8d7da;border-left:4px solid #dc3545;padding:.8rem 1rem;border-radius:6px;}
.ia-box{background:#fff3cd;border-left:4px solid #ffc107;padding:.8rem 1rem;border-radius:6px;margin-top:.8rem;}
.tema-header{background:#1a1a2e;color:white;padding:.5rem 1rem;border-radius:6px;font-weight:600;margin:1rem 0 .5rem;}
</style>
""", unsafe_allow_html=True)

# ── API KEY ──
def get_api_key():
    try: return st.secrets["ANTHROPIC_API_KEY"]
    except: return os.environ.get("ANTHROPIC_API_KEY","")

API_KEY = get_api_key()

# ── CARGAR PREGUNTAS DESDE JSON ──
@st.cache_data
def cargar_preguntas():
    db_path = Path("preguntas_db.json")
    if db_path.exists():
        with open(db_path, encoding="utf-8") as f:
            return json.load(f)
    return []

PREGUNTAS = cargar_preguntas()

def get_preguntas_por_tema():
    por_tema = {}
    for p in PREGUNTAS:
        por_tema.setdefault(p["tema"], {}).setdefault(p["nivel"], []).append(p)
    return por_tema

def get_pregunta(tema, nivel, ids_usados):
    por_tema = get_preguntas_por_tema()
    pool = [p for p in por_tema.get(tema,{}).get(nivel,[]) if p["id"] not in ids_usados]
    return random.choice(pool) if pool else None

TEMAS_LISTA = list(dict.fromkeys(p["tema"] for p in PREGUNTAS))

# ── EVALUACIÓN IA ──
def evaluar_con_ia(pregunta, respuesta_alumno):
    try:
        cliente = anthropic.Anthropic(api_key=API_KEY)
        instruccion = f"""Evalúa esta respuesta de Sistemas Operativos.
PREGUNTA: {pregunta['enunciado']}
RESPUESTA: {respuesta_alumno}
CONCEPTOS CLAVE: {', '.join(pregunta.get('clave',[]))}
RESPUESTA MODELO: {pregunta['explicacion']}
Retorna SOLO este JSON:
{{"correcto":true/false,"puntaje":0.0-1.0,"comentario":"2-3 oraciones en español","repregunta":"pregunta socrática de seguimiento","conceptos_faltantes":["lista"]}}"""
        resp = cliente.messages.create(
            model="claude-3-5-haiku-20241022", max_tokens=500,
            system="Eres profesor experto en SO. Responde SOLO con JSON válido, sin backticks.",
            messages=[{"role":"user","content":instruccion}]
        )
        texto = resp.content[0].text.strip()
        if texto.startswith("```"): texto = texto.split("```")[1]; texto = texto[4:] if texto.startswith("json") else texto
        return json.loads(texto)
    except Exception as e:
        return {"correcto":None,"puntaje":0.5,"comentario":f"Revisa: {pregunta['explicacion']}","repregunta":"¿Puedes ampliar?","conceptos_faltantes":pregunta.get("clave",[])}

def guardar_resultado(codigo, nombre, tema, pid, nivel, correcto, puntaje):
    with open("resultados.csv","a",newline="",encoding="utf-8") as f:
        w = csv.writer(f)
        if not Path("resultados.csv").exists() or os.path.getsize("resultados.csv")==0:
            w.writerow(["Timestamp","Codigo","Nombre","Tema","ID","Nivel","Correcto","Puntaje"])
        w.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"),codigo,nombre,tema,pid,nivel,"Sí" if correcto else "No",round(puntaje,2)])

def badge(nivel):
    return {1:"🟢 FÁCIL",2:"🟡 MEDIO",3:"🔴 DIFÍCIL"}.get(nivel,"")

# ── SESSION STATE ──
def init():
    d = {"pagina":"login","codigo":"","nombre":"","temas_sel":[],"temas_rest":[],
         "tema_actual":"","preg_actual":None,"ids_usados":[],"historial":[],
         "fase":"nueva","preg_original":None,"ia_resultado":None,
         "resultado_mostrado":False,"etiqueta":""}
    for k,v in d.items():
        if k not in st.session_state: st.session_state[k]=v
init()

# ── LOGIN ──
def pagina_login():
    st.markdown('<div class="main-title">🖥️ Evaluador Adaptativo</div>',unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Sistemas Operativos — UNSAAC</div>',unsafe_allow_html=True)
    st.divider()
    c1,c2,c3=st.columns([1,2,1])
    with c2:
        st.markdown("### 👤 Identificación")
        codigo=st.text_input("Código de alumno",placeholder="Ej: 2024-0001",max_chars=20)
        nombre=st.text_input("Nombre completo",placeholder="Ej: Juan Pérez",max_chars=80)
        if st.button("🚀 Ingresar",use_container_width=True,type="primary"):
            if not codigo.strip(): st.error("⚠️ Ingresa tu código.")
            elif not nombre.strip(): st.error("⚠️ Ingresa tu nombre.")
            else:
                st.session_state.codigo=codigo.strip()
                st.session_state.nombre=nombre.strip()
                st.session_state.pagina="seleccion"
                st.rerun()
        st.caption(f"📚 {len(PREGUNTAS)} preguntas disponibles en {len(TEMAS_LISTA)} temas")

# ── SELECCIÓN ──
def pagina_seleccion():
    st.markdown(f"### 👋 Bienvenido/a, {st.session_state.nombre}")
    st.markdown(f"📋 Código: `{st.session_state.codigo}`")
    st.divider()
    st.markdown("### 📚 Selecciona temas a evaluar")
    marcados=[]
    cols=st.columns(2)
    for i,t in enumerate(TEMAS_LISTA):
        ptemas=get_preguntas_por_tema()
        n=sum(len(v) for v in ptemas.get(t,{}).values())
        with cols[i%2]:
            if st.checkbox(f"{t} ({n} preguntas)",value=True,key=f"t{i}"): marcados.append(t)
    st.divider()
    if st.button("▶️ Iniciar",type="primary",use_container_width=True):
        if not marcados: st.error("⚠️ Selecciona al menos un tema.")
        else:
            random.shuffle(marcados)
            st.session_state.temas_sel=marcados
            st.session_state.temas_rest=marcados.copy()
            st.session_state.pagina="evaluacion"
            _siguiente_tema()
            st.rerun()

def _siguiente_tema():
    if not st.session_state.temas_rest:
        st.session_state.pagina="resumen"; return
    tema=st.session_state.temas_rest.pop(0)
    st.session_state.tema_actual=tema
    ptemas=get_preguntas_por_tema()
    niveles=sorted(ptemas.get(tema,{}).keys())
    nivel=2 if 2 in niveles else (niveles[0] if niveles else 1)
    preg=get_pregunta(tema,nivel,st.session_state.ids_usados)
    if preg:
        st.session_state.preg_actual=preg
        st.session_state.preg_original=preg
        st.session_state.fase="nueva"
        st.session_state.etiqueta=""
        st.session_state.resultado_mostrado=False
        st.session_state.ia_resultado=None
    else:
        _siguiente_tema()

# ── EVALUACIÓN ──
def pagina_evaluacion():
    preg=st.session_state.preg_actual
    if not preg: st.session_state.pagina="resumen"; st.rerun(); return
    total=len(st.session_state.temas_sel)
    hechos=total-len(st.session_state.temas_rest)-1
    st.markdown(f"**👤 {st.session_state.nombre}** | `{st.session_state.codigo}`")
    st.progress(max(0,hechos)/total if total>0 else 0,text=f"Tema {max(1,hechos+1)} de {total}")
    st.markdown(f'<div class="tema-header">📂 {preg["tema"]}</div>',unsafe_allow_html=True)
    lbl=f"{badge(preg['nivel'])}"
    if st.session_state.etiqueta: lbl+=f" — {st.session_state.etiqueta}"
    st.markdown(f"**{lbl}**")
    st.markdown(f'<div class="pregunta-box">{preg["enunciado"].replace(chr(10),"<br>")}</div>',unsafe_allow_html=True)
    if preg.get("analogia"):
        st.caption(f"💡 Analogía de referencia: *{preg['analogia']}*")
    if st.session_state.resultado_mostrado:
        _mostrar_retro(); return
    with st.form(key=f"f_{preg['id']}_{st.session_state.fase}"):
        resp=None
        if preg["tipo"]=="mc":
            ops=preg["opciones"]
            sel=st.radio("Selecciona:",[ f"{k}) {v}" for k,v in ops.items()],index=None)
            if sel: resp=sel[0]
        elif preg["tipo"]=="tf":
            sel=st.radio("Tu respuesta:",["Verdadero (V)","Falso (F)"],index=None)
            if sel: resp="V" if sel.startswith("V") else "F"
        else:
            resp=st.text_area("Escribe tu respuesta:",height=160,placeholder="Desarrolla tu respuesta aquí...")
        env=st.form_submit_button("✅ Enviar",type="primary",use_container_width=True)
    if env:
        if not resp or (isinstance(resp,str) and not resp.strip()): st.warning("⚠️ Escribe una respuesta."); return
        _procesar(preg, resp.strip() if isinstance(resp,str) else resp)
        st.rerun()

def _procesar(preg, resp):
    st.session_state.ids_usados.append(preg["id"])
    ia=None; puntaje=0.0
    if preg["tipo"] in ("mc","tf"):
        correcto = resp.upper()==preg["correcta"].upper()
        puntaje=1.0 if correcto else 0.0
    else:
        with st.spinner("🤖 La IA evalúa tu respuesta..."):
            ia=evaluar_con_ia(preg,resp)
        puntaje=ia.get("puntaje",0.5)
        cr=ia.get("correcto",None)
        correcto=cr if cr is not None else puntaje>=0.6
    st.session_state.historial.append({"tema":preg["tema"],"id":preg["id"],"nivel":preg["nivel"],"correcto":correcto,"puntaje":puntaje,"fase":st.session_state.fase})
    guardar_resultado(st.session_state.codigo,st.session_state.nombre,preg["tema"],preg["id"],preg["nivel"],correcto,puntaje)
    st.session_state.ia_resultado=ia
    st.session_state.resultado_mostrado=True
    fase=st.session_state.fase
    if fase=="nueva": st.session_state.fase="subir" if correcto else "ancla_pendiente"
    elif fase=="ancla": st.session_state.fase="retoma_pendiente" if correcto else "tema_terminado"
    elif fase=="retoma": st.session_state.fase="subir" if correcto else "tema_terminado"
    elif fase=="subida": st.session_state.fase="tema_terminado"

def _mostrar_retro():
    h=st.session_state.historial[-1] if st.session_state.historial else {}
    correcto=h.get("correcto",False); puntaje=h.get("puntaje",0)
    preg=st.session_state.preg_actual; ia=st.session_state.ia_resultado
    if correcto: st.markdown(f'<div class="correcto-box">✅ <b>¡CORRECTO!</b> Puntaje: {puntaje:.1f}</div>',unsafe_allow_html=True)
    else: st.markdown(f'<div class="incorrecto-box">❌ <b>INCORRECTO</b> Puntaje: {puntaje:.1f}</div>',unsafe_allow_html=True)
    with st.expander("📖 Explicación",expanded=True): st.write(preg["explicacion"])
    if ia:
        with st.expander("🤖 Evaluación IA",expanded=True):
            st.write(ia.get("comentario",""))
            f=ia.get("conceptos_faltantes",[])
            if f: st.markdown("**💡 Reforzar:** "+" | ".join(f))
    st.divider()
    fase=st.session_state.fase
    orig=st.session_state.preg_original
    if fase=="subir":
        sig=get_pregunta(orig["tema"],orig["nivel"]+1,st.session_state.ids_usados) if orig["nivel"]<3 else None
        if sig:
            if st.button("🔼 Subir dificultad",type="primary",use_container_width=True):
                st.session_state.preg_actual=sig; st.session_state.fase="subida"; st.session_state.etiqueta="⬆ NIVEL SUPERIOR"; st.session_state.resultado_mostrado=False; st.session_state.ia_resultado=None; st.rerun()
        else: _btn_siguiente()
    elif fase=="ancla_pendiente":
        anc=get_pregunta(orig["tema"],orig["nivel"]-1,st.session_state.ids_usados) if orig["nivel"]>1 else None
        if anc:
            if st.button("🔽 Pregunta de apoyo",type="secondary",use_container_width=True):
                st.session_state.preg_actual=anc; st.session_state.fase="ancla"; st.session_state.etiqueta="🔽 APOYO"; st.session_state.resultado_mostrado=False; st.session_state.ia_resultado=None; st.rerun()
        else: _btn_siguiente()
    elif fase=="retoma_pendiente":
        if st.button("🔄 Retomar pregunta original",type="primary",use_container_width=True):
            st.session_state.preg_actual=orig; st.session_state.fase="retoma"; st.session_state.etiqueta="🔄 SEGUNDA OPORTUNIDAD"; st.session_state.resultado_mostrado=False; st.session_state.ia_resultado=None; st.rerun()
    else: _btn_siguiente()

def _btn_siguiente():
    if st.session_state.temas_rest:
        if st.button("➡️ Siguiente tema",type="primary",use_container_width=True): _siguiente_tema(); st.rerun()
    else:
        if st.button("🏁 Ver resultados",type="primary",use_container_width=True): st.session_state.pagina="resumen"; st.rerun()

# ── RESUMEN ──
def pagina_resumen():
    st.markdown('<div class="main-title">🏁 Resumen Final</div>',unsafe_allow_html=True)
    st.markdown('<div class="sub-title">UNSAAC — Sistemas Operativos</div>',unsafe_allow_html=True)
    st.divider()
    h=st.session_state.historial
    if not h: st.info("Sin resultados."); return
    total=len(h); correctas=sum(1 for x in h if x["correcto"]); puntaje=sum(x["puntaje"] for x in h); pct=round(100*correctas/total,1) if total>0 else 0
    c1,c2,c3=st.columns(3)
    c1.metric("📝 Preguntas",total); c2.metric("✅ Correctas",correctas); c3.metric("📊 Porcentaje",f"{pct}%")
    st.divider()
    if pct>=80: st.success("🏆 ¡Excelente dominio del tema!")
    elif pct>=60: st.warning("👍 Buen trabajo. Refuerza los temas débiles.")
    else: st.error("📚 Necesitas repasar más. Enfócate en los temas donde fallaste.")
    st.markdown("### 📋 Detalle")
    for x in h:
        ic="✅" if x["correcto"] else "❌"
        st.markdown(f"{ic} **{x['tema']}** | Nivel {x['nivel']} | `{x['id']}` | Puntaje: {x['puntaje']:.2f}")
    st.divider()
    if Path("resultados.csv").exists():
        with open("resultados.csv","rb") as f:
            st.download_button("📥 Descargar resultados CSV",f,f"resultados_{st.session_state.codigo}.csv","text/csv")
    if st.button("🔄 Nueva sesión",use_container_width=True):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

# ── ROUTER ──
if not API_KEY:
    st.error("⚠️ Configura ANTHROPIC_API_KEY en Streamlit Secrets.")
    st.code('ANTHROPIC_API_KEY = "sk-ant-xxxx"',language="toml"); st.stop()
if not PREGUNTAS:
    st.error("⚠️ No se encontró preguntas_db.json. Sube el archivo al repositorio.")
    st.stop()

p=st.session_state.pagina
if p=="login": pagina_login()
elif p=="seleccion": pagina_seleccion()
elif p=="evaluacion": pagina_evaluacion()
elif p=="resumen": pagina_resumen()
