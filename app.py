"""
╔══════════════════════════════════════════════════════════════════════╗
║   EVALUADOR ADAPTATIVO - SISTEMAS OPERATIVOS - UNSAAC               ║
║   Versión Streamlit Web — 22 alumnos simultáneos                    ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import anthropic
import json
import random
import os
import csv
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Evaluador SO - UNSAAC",
    page_icon="🖥️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ─────────────────────────────────────────────────────────────────────
# CSS PERSONALIZADO
# ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-title {
        text-align: center;
        color: #1a1a2e;
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        text-align: center;
        color: #16213e;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }
    .pregunta-box {
        background: #f0f4ff;
        border-left: 4px solid #4361ee;
        padding: 1rem 1.2rem;
        border-radius: 6px;
        margin: 1rem 0;
    }
    .correcto-box {
        background: #d4edda;
        border-left: 4px solid #28a745;
        padding: 0.8rem 1rem;
        border-radius: 6px;
    }
    .incorrecto-box {
        background: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 0.8rem 1rem;
        border-radius: 6px;
    }
    .ia-box {
        background: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 0.8rem 1rem;
        border-radius: 6px;
        margin-top: 0.8rem;
    }
    .nivel-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    .tema-header {
        background: #1a1a2e;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        font-weight: 600;
        margin: 1rem 0 0.5rem 0;
    }
    .resumen-card {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1.5rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────
# API KEY
# ─────────────────────────────────────────────────────────────────────
def get_api_key():
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except:
        return os.environ.get("ANTHROPIC_API_KEY", "")

# ─────────────────────────────────────────────────────────────────────
# BANCO DE PREGUNTAS
# ─────────────────────────────────────────────────────────────────────
PREGUNTAS = [
    # ── LLAMADAS AL SISTEMA ──
    {
        "id": "SC01", "tema": "Llamadas al Sistema", "nivel": 1,
        "tipo": "tf",
        "enunciado": "¿Verdadero o Falso?\nLas llamadas al sistema (syscalls) permiten a un proceso de usuario solicitar servicios del kernel.",
        "correcta": "V",
        "explicacion": "Las syscalls son la interfaz controlada entre el espacio de usuario y el kernel. Sin ellas, los procesos no podrían acceder a recursos del hardware."
    },
    {
        "id": "SC02", "tema": "Llamadas al Sistema", "nivel": 2,
        "tipo": "mc",
        "enunciado": "Cuando un proceso ejecuta la syscall read(), el procesador cambia de modo usuario a modo kernel. ¿Qué mecanismo produce este cambio?",
        "opciones": {
            "A": "Una interrupción de hardware del disco",
            "B": "Una instrucción de trampa (trap/INT) que eleva el nivel de privilegio",
            "C": "El scheduler de procesos detecta la solicitud",
            "D": "El MMU activa el modo kernel automáticamente"
        },
        "correcta": "B",
        "explicacion": "La instrucción TRAP causa una transición controlada al kernel. El procesador guarda el contexto del usuario, cambia el nivel de privilegio y salta al manejador de syscalls en la tabla IDT."
    },
    {
        "id": "SC03", "tema": "Llamadas al Sistema", "nivel": 3,
        "tipo": "abierta",
        "enunciado": "Explica qué ocurre paso a paso cuando un proceso llama a fork() en Linux. Menciona al menos 4 etapas internas del kernel.",
        "clave": ["tabla de páginas", "copy-on-write", "PCB", "pid", "espacio de direcciones", "copia"],
        "explicacion": "fork() crea un proceso hijo copiando el PCB del padre, asignando un nuevo PID, duplicando la tabla de páginas con COW (copy-on-write), y retornando 0 al hijo y el PID del hijo al padre."
    },
    # ── INTERRUPCIONES ──
    {
        "id": "INT01", "tema": "Interrupciones", "nivel": 1,
        "tipo": "mc",
        "enunciado": "¿Cuál es la diferencia principal entre una interrupción de hardware y una excepción (trap)?",
        "opciones": {
            "A": "Las interrupciones son síncronas; las excepciones son asíncronas",
            "B": "Las interrupciones son asíncronas (dispositivos externos); las excepciones son síncronas (generadas por el CPU)",
            "C": "Ambas son lo mismo, solo cambia el nombre según el sistema operativo",
            "D": "Las excepciones solo ocurren en modo kernel"
        },
        "correcta": "B",
        "explicacion": "Las interrupciones de hardware ocurren en cualquier momento (teclado, disco). Las excepciones son síncronas: las genera el CPU al ejecutar una instrucción (división por cero, page fault, syscall)."
    },
    {
        "id": "INT02", "tema": "Interrupciones", "nivel": 2,
        "tipo": "tf",
        "enunciado": "¿Verdadero o Falso?\nAl atender una interrupción, el SO siempre deshabilita TODAS las interrupciones durante toda la rutina de atención (ISR).",
        "correcta": "F",
        "explicacion": "FALSO. Los SO modernos usan interrupciones anidadas con niveles de prioridad. Durante una ISR se deshabilitan solo las de igual o menor prioridad. Las de mayor prioridad pueden interrumpir la ISR en curso."
    },
    {
        "id": "INT03", "tema": "Interrupciones", "nivel": 3,
        "tipo": "abierta",
        "enunciado": "Un proceso está ejecutando un bucle cuando ocurre un page fault. Describe el camino completo desde la excepción hasta que el proceso retoma su ejecución.",
        "clave": ["MMU", "tabla de páginas", "disco", "swap", "marco de página", "TLB", "retoma"],
        "explicacion": "El MMU detecta la página ausente → genera excepción page fault → kernel identifica la página → la carga desde disco/swap → actualiza tabla de páginas y TLB → retorna al proceso que reintenta la instrucción."
    },
    # ── PROCESOS E HILOS ──
    {
        "id": "PH01", "tema": "Procesos e Hilos", "nivel": 1,
        "tipo": "mc",
        "enunciado": "¿Qué comparten los hilos (threads) de un mismo proceso?",
        "opciones": {
            "A": "Stack, registros y contador de programa",
            "B": "Espacio de direcciones, archivos abiertos y variables globales",
            "C": "Solo el PID del proceso padre",
            "D": "Nada; cada hilo es completamente independiente"
        },
        "correcta": "B",
        "explicacion": "Los hilos comparten el espacio de direcciones, heap, código y descriptores de archivo. Cada hilo tiene su propio stack, registros y contador de programa."
    },
    {
        "id": "PH02", "tema": "Procesos e Hilos", "nivel": 2,
        "tipo": "mc",
        "enunciado": "¿Cuál es el estado de un proceso que está esperando una operación de E/S?",
        "opciones": {
            "A": "Running (ejecutándose)",
            "B": "Ready (listo)",
            "C": "Blocked/Waiting (bloqueado)",
            "D": "Zombie"
        },
        "correcta": "C",
        "explicacion": "Un proceso bloqueado espera un evento externo (E/S, señal, semáforo). No consume CPU. El scheduler lo moverá a 'Ready' cuando el evento ocurra."
    },
    {
        "id": "PH03", "tema": "Procesos e Hilos", "nivel": 3,
        "tipo": "abierta",
        "enunciado": "Compara hilos a nivel de kernel (KLT) vs hilos a nivel de usuario (ULT). ¿En qué escenario ULT tiene ventaja y en cuál KLT es superior?",
        "clave": ["context switch", "kernel", "bloqueo", "paralelismo", "planificador", "multicore"],
        "explicacion": "ULT: context switch rápido sin entrar al kernel, pero si uno se bloquea bloquea todo el proceso. KLT: el kernel los planifica en múltiples cores, ideal para paralelismo real, pero el context switch es más costoso."
    },
    # ── MEMORIA FUNDAMENTOS ──
    {
        "id": "MEM01", "tema": "Memoria - Fundamentos", "nivel": 1,
        "tipo": "mc",
        "enunciado": "¿Qué es el espacio de direcciones virtuales de un proceso?",
        "opciones": {
            "A": "La RAM física que el proceso usa actualmente",
            "B": "El conjunto de direcciones que el proceso puede referenciar, independiente de la RAM física disponible",
            "C": "El espacio en disco asignado al proceso",
            "D": "Solo las direcciones del stack y el heap del proceso"
        },
        "correcta": "B",
        "explicacion": "Cada proceso tiene su propio espacio de direcciones virtuales. El MMU traduce estas a físicas. Esto permite aislamiento entre procesos y que un proceso 'crea' tener más memoria de la que existe físicamente."
    },
    {
        "id": "MEM02", "tema": "Memoria - Fundamentos", "nivel": 2,
        "tipo": "tf",
        "enunciado": "¿Verdadero o Falso?\nLa fragmentación interna ocurre cuando un bloque asignado es más grande que lo que el proceso necesita, desperdiciando el espacio sobrante dentro del bloque.",
        "correcta": "V",
        "explicacion": "CORRECTO. Fragmentación INTERNA: espacio desperdiciado DENTRO de un bloque asignado. Fragmentación EXTERNA: hay suficiente memoria libre total pero dispersa en bloques no contiguos."
    },
    {
        "id": "MEM03", "tema": "Memoria - Fundamentos", "nivel": 3,
        "tipo": "abierta",
        "enunciado": "Explica la diferencia entre fragmentación interna y externa. Da un ejemplo concreto de cada una en un sistema con particiones fijas vs. particiones dinámicas.",
        "clave": ["partición", "desperdicio", "contiguo", "compactación", "interno", "externo"],
        "explicacion": "Fija→interna: proceso de 60KB en partición de 100KB desperdicia 40KB. Dinámica→externa: huecos de 20KB+30KB+15KB=65KB libres pero no se puede alojar un proceso de 50KB contiguo."
    },
    # ── PAGINACIÓN ──
    {
        "id": "PAG01", "tema": "Paginación", "nivel": 1,
        "tipo": "mc",
        "enunciado": "En un sistema con paginación, ¿qué tamaño tiene un marco (frame) respecto a una página virtual?",
        "opciones": {
            "A": "El marco es siempre el doble de la página",
            "B": "Son del mismo tamaño",
            "C": "El marco puede ser de cualquier tamaño",
            "D": "La página es siempre más pequeña que el marco"
        },
        "correcta": "B",
        "explicacion": "En paginación, páginas y marcos tienen el mismo tamaño (típicamente 4KB). Una página virtual se mapea a cualquier marco físico disponible gracias a la tabla de páginas."
    },
    {
        "id": "PAG02", "tema": "Paginación", "nivel": 2,
        "tipo": "mc",
        "enunciado": "Un proceso tiene espacio virtual de 32 bits con páginas de 4KB. ¿Cuántas entradas tiene su tabla de páginas de un nivel?",
        "opciones": {
            "A": "4,096 entradas",
            "B": "1,048,576 entradas (2²⁰)",
            "C": "65,536 entradas",
            "D": "8,388,608 entradas"
        },
        "correcta": "B",
        "explicacion": "4KB = 2¹² → offset 12 bits. 32-12 = 20 bits para número de página → 2²⁰ = 1,048,576 entradas. Por eso se usan tablas multinivel o TLB."
    },
    {
        "id": "PAG03", "tema": "Paginación", "nivel": 3,
        "tipo": "analogia",
        "enunciado": "Los algoritmos de REEMPLAZO DE PÁGINAS deciden qué página sacar de RAM cuando está llena.\n\n🔹 FIFO – Reemplaza la página que entró hace más tiempo.\n🔹 LRU – Reemplaza la página que NO se usó hace más tiempo.\n🔹 Óptimo – Reemplaza la que no se usará por más tiempo en el futuro.\n🔹 Segunda oportunidad – Como FIFO pero da una 'segunda chance' si fue referenciada.\n\n📝 Elige UNO de estos algoritmos y explícalo con una analogía del mundo real (biblioteca, cocina, guardarropa, etc.). Sé detallado. La IA evaluará si tu analogía captura el comportamiento correcto.",
        "clave": ["reemplazo", "página", "referencia", "orden", "uso reciente", "futuro"],
        "explicacion": "Las analogías deben capturar el criterio de selección de la víctima, qué información necesita el algoritmo y sus limitaciones."
    },
    # ── SEGMENTACIÓN ──
    {
        "id": "SEG01", "tema": "Segmentación", "nivel": 1,
        "tipo": "tf",
        "enunciado": "¿Verdadero o Falso?\nEn segmentación, todos los segmentos de un proceso tienen el mismo tamaño.",
        "correcta": "F",
        "explicacion": "FALSO. En segmentación los segmentos tienen tamaño VARIABLE según su contenido (código, stack, heap, datos). Esto los hace más naturales programáticamente pero produce fragmentación externa."
    },
    {
        "id": "SEG02", "tema": "Segmentación", "nivel": 2,
        "tipo": "mc",
        "enunciado": "En segmentación, una dirección lógica es un par (segmento, desplazamiento). ¿Qué verifica el hardware al traducir esta dirección?",
        "opciones": {
            "A": "Solo que el número de segmento sea válido",
            "B": "Que el segmento exista en la tabla y que el desplazamiento no exceda el límite del segmento",
            "C": "Que la dirección física resultante sea par",
            "D": "Que el segmento esté en la primera mitad de la RAM"
        },
        "correcta": "B",
        "explicacion": "El hardware verifica que el número de segmento sea válido, que el desplazamiento < límite del segmento (si no → segmentation fault), y calcula dirección física = base + desplazamiento."
    },
    # ── MEMORIA VIRTUAL ──
    {
        "id": "VIRT01", "tema": "Memoria Virtual", "nivel": 1,
        "tipo": "mc",
        "enunciado": "¿Qué permite la memoria virtual que no es posible con memoria física directa?",
        "opciones": {
            "A": "Acceder a la RAM más rápido",
            "B": "Ejecutar procesos cuyo tamaño total supera la RAM física disponible",
            "C": "Eliminar completamente la fragmentación",
            "D": "Compartir el CPU entre múltiples procesos"
        },
        "correcta": "B",
        "explicacion": "La memoria virtual permite ejecutar procesos más grandes que la RAM física, cargando en RAM solo las páginas activamente usadas (working set) y manteniendo el resto en disco (swap)."
    },
    {
        "id": "VIRT02", "tema": "Memoria Virtual", "nivel": 2,
        "tipo": "abierta",
        "enunciado": "Explica el concepto de 'thrashing' en memoria virtual. ¿Cuándo ocurre y cómo lo detecta/previene el SO?",
        "clave": ["working set", "page fault", "swap", "exceso", "multiprogramación", "disco"],
        "explicacion": "Thrashing: el SO pasa más tiempo moviendo páginas entre disco y RAM que ejecutando procesos. Ocurre cuando el working set total supera la RAM. Prevención: reducir multiprogramación, usar modelo working set."
    },
    {
        "id": "VIRT03", "tema": "Memoria Virtual", "nivel": 3,
        "tipo": "analogia",
        "enunciado": "El THRASHING en memoria virtual es uno de los problemas más críticos de rendimiento.\n\n📝 Crea una analogía del mundo real que explique el thrashing capturando:\n  1. Por qué el sistema se vuelve ineficiente\n  2. Qué recurso se satura\n  3. Por qué 'hacer más trabajo' empeora las cosas\n\nLa IA evaluará la profundidad y precisión conceptual de tu analogía.",
        "clave": ["saturación", "overhead", "más trabajo peor resultado", "recurso compartido", "cuello de botella"],
        "explicacion": "Buenas analogías: un mesero con demasiadas mesas (va y viene sin servir ninguna bien), una autopista congestionada donde todos quieren circular pero nadie avanza."
    },
    # ── ALGORITMOS DE REEMPLAZO ──
    {
        "id": "ALG01", "tema": "Algoritmos de Reemplazo", "nivel": 1,
        "tipo": "mc",
        "enunciado": "El algoritmo FIFO de reemplazo de páginas tiene una anomalía conocida. ¿Cuál es?",
        "opciones": {
            "A": "Nunca produce page faults con suficientes marcos",
            "B": "La anomalía de Bélády: más marcos puede producir MÁS page faults",
            "C": "Solo funciona con páginas de tamaño fijo",
            "D": "Requiere conocer el futuro para funcionar"
        },
        "correcta": "B",
        "explicacion": "La anomalía de Bélády: con FIFO, aumentar el número de marcos disponibles puede AUMENTAR los page faults. Esto no ocurre con LRU ni con el algoritmo Óptimo."
    },
    {
        "id": "ALG02", "tema": "Algoritmos de Reemplazo", "nivel": 2,
        "tipo": "mc",
        "enunciado": "¿Por qué el algoritmo ÓPTIMO (OPT) no puede implementarse en un SO real?",
        "opciones": {
            "A": "Es demasiado lento para calcular en tiempo real",
            "B": "Requiere conocer de antemano qué páginas se usarán en el futuro, lo cual es imposible en general",
            "C": "Solo funciona si todas las páginas tienen el mismo tamaño",
            "D": "El hardware no permite implementarlo"
        },
        "correcta": "B",
        "explicacion": "OPT reemplaza la página que no será usada por más tiempo. Para saber eso se necesita conocer el futuro, lo cual solo es posible en simulaciones. Se usa como baseline teórico."
    },
    {
        "id": "ALG04", "tema": "Algoritmos de Reemplazo", "nivel": 3,
        "tipo": "analogia",
        "enunciado": "El algoritmo LRU explota la LOCALIDAD TEMPORAL de referencia.\n\n📝 TAREA DOBLE:\n  1. Crea una analogía que explique LRU en términos cotidianos.\n  2. Modifica tu analogía para mostrar cómo LRU se DIFERENCIA de FIFO.\n\nLa IA evaluará si capturas:\n  ✓ El criterio de 'uso reciente' vs 'antigüedad de llegada'\n  ✓ Por qué LRU suele ser mejor que FIFO\n  ✓ La limitación de LRU (costoso de implementar exactamente)",
        "clave": ["uso reciente", "antigüedad", "localidad", "costoso", "aproximación"],
        "explicacion": "Ejemplo: cajón de ropa (LRU=pones arriba lo que usas, FIFO=primera en entrar primera en salir sin importar si la usas a diario). LRU exacto requiere timestamp por página → overhead."
    },
    # ── ASIGNACIÓN DINÁMICA ──
    {
        "id": "DIN01", "tema": "Asignación Dinámica", "nivel": 1,
        "tipo": "mc",
        "enunciado": "¿Qué estrategia elige el hueco MÁS PEQUEÑO que satisface la solicitud de memoria?",
        "opciones": {
            "A": "First Fit",
            "B": "Best Fit",
            "C": "Worst Fit",
            "D": "Next Fit"
        },
        "correcta": "B",
        "explicacion": "Best Fit busca el hueco más ajustado a la solicitud, minimizando el desperdicio inmediato. Pero genera muchos fragmentos pequeños inutilizables."
    },
    {
        "id": "DIN02", "tema": "Asignación Dinámica", "nivel": 2,
        "tipo": "abierta",
        "enunciado": "Compara First Fit vs Best Fit vs Worst Fit para asignación de memoria dinámica. ¿En qué situación práctica usarías cada uno y por qué?",
        "clave": ["fragmentación", "velocidad", "hueco", "remanente", "lista libre"],
        "explicacion": "First Fit: rápido, fragmentación moderada. Best Fit: mínimo desperdicio inmediato pero crea fragmentos pequeños. Worst Fit: remanentes grandes útiles para futuras solicitudes. En práctica, First Fit es el más usado."
    },
    # ── SISTEMA BUDDY ──
    {
        "id": "BUD01", "tema": "Sistema Buddy", "nivel": 2,
        "tipo": "mc",
        "enunciado": "En el sistema Buddy, ¿qué ocurre cuando se libera un bloque?",
        "opciones": {
            "A": "Se agrega a la lista libre sin verificar nada más",
            "B": "Se fusiona con su 'buddy' si éste también está libre, formando un bloque mayor",
            "C": "Se divide en dos bloques iguales para usos futuros",
            "D": "Se compacta junto con todos los demás bloques libres"
        },
        "correcta": "B",
        "explicacion": "El sistema Buddy asigna bloques en potencias de 2. Al liberar, verifica si su 'buddy' está libre → si sí, se fusionan en un bloque del doble. Esto reduce la fragmentación externa eficientemente."
    },
    {
        "id": "BUD02", "tema": "Sistema Buddy", "nivel": 3,
        "tipo": "analogia",
        "enunciado": "El SISTEMA BUDDY divide y fusiona memoria en potencias de 2, como si cada bloque tuviera un 'hermano gemelo'.\n\n📝 Crea una analogía que explique:\n  1. Por qué los bloques deben ser potencia de 2\n  2. Cómo se divide un bloque grande para una solicitud pequeña\n  3. Cómo la coalescencia (fusión de buddies) reduce la fragmentación",
        "clave": ["potencia de 2", "división", "fusión", "coalescencia", "hermano", "fragmentación"],
        "explicacion": "La potencia de 2 permite identificar al buddy con XOR sobre la dirección. Analogías: billetes (100, 50, 25...), habitaciones de hotel que se fusionan."
    },
]

# ─────────────────────────────────────────────────────────────────────
# FUNCIONES DE APOYO
# ─────────────────────────────────────────────────────────────────────

def get_preguntas_por_tema():
    por_tema = {}
    for p in PREGUNTAS:
        por_tema.setdefault(p["tema"], {}).setdefault(p["nivel"], []).append(p)
    return por_tema

def get_pregunta(tema, nivel, ids_usados):
    por_tema = get_preguntas_por_tema()
    pool = por_tema.get(tema, {}).get(nivel, [])
    disponibles = [p for p in pool if p["id"] not in ids_usados]
    return random.choice(disponibles) if disponibles else None

def evaluar_con_ia(pregunta, respuesta_alumno, api_key):
    try:
        cliente = anthropic.Anthropic(api_key=api_key)
        tipo = pregunta["tipo"]

        if tipo == "analogia":
            instruccion = f"""Evalúa esta analogía de un estudiante universitario sobre: {pregunta['tema']}

PREGUNTA: {pregunta['enunciado']}
RESPUESTA: {respuesta_alumno}
CONCEPTOS ESPERADOS: {', '.join(pregunta['clave'])}

Retorna SOLO este JSON (sin texto adicional):
{{
  "correcto": true/false,
  "puntaje": 0.0-1.0,
  "comentario": "retroalimentación de 2-3 oraciones en español",
  "repregunta": "pregunta socrática de seguimiento en español",
  "conceptos_faltantes": ["conceptos que no mencionó"]
}}"""
        else:
            instruccion = f"""Evalúa esta respuesta de Sistemas Operativos.

PREGUNTA: {pregunta['enunciado']}
RESPUESTA: {respuesta_alumno}
CONCEPTOS CLAVE: {', '.join(pregunta['clave'])}
RESPUESTA MODELO: {pregunta['explicacion']}

Retorna SOLO este JSON (sin texto adicional):
{{
  "correcto": true/false,
  "puntaje": 0.0-1.0,
  "comentario": "retroalimentación de 2-3 oraciones en español",
  "repregunta": "pregunta socrática basada en lo que el alumno dijo",
  "conceptos_faltantes": ["conceptos no mencionados"]
}}"""

        resp = cliente.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=500,
            system="Eres un profesor experto en Sistemas Operativos. Evalúa respuestas estudiantiles de forma pedagógica. Responde SOLO con JSON válido, sin backticks ni texto extra.",
            messages=[{"role": "user", "content": instruccion}]
        )
        texto = resp.content[0].text.strip()
        if texto.startswith("```"):
            texto = texto.split("```")[1]
            if texto.startswith("json"):
                texto = texto[4:]
        return json.loads(texto)
    except Exception as e:
        return {
            "correcto": None,
            "puntaje": 0.5,
            "comentario": f"Revisa la respuesta modelo: {pregunta['explicacion']}",
            "repregunta": "¿Puedes ampliar tu explicación?",
            "conceptos_faltantes": pregunta.get("clave", [])
        }

def guardar_resultado(codigo, nombre, tema, pregunta_id, nivel, correcto, puntaje):
    """Guarda resultados en CSV para que el profesor los descargue."""
    archivo = "resultados.csv"
    existe = Path(archivo).exists()
    with open(archivo, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not existe:
            writer.writerow(["Timestamp", "Codigo", "Nombre", "Tema", "PreguntaID", "Nivel", "Correcto", "Puntaje"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            codigo, nombre, tema, pregunta_id, nivel,
            "Sí" if correcto else "No",
            round(puntaje, 2)
        ])

def badge_nivel(nivel):
    colores = {1: "🟢 FÁCIL", 2: "🟡 MEDIO", 3: "🔴 DIFÍCIL"}
    return colores.get(nivel, "")

# ─────────────────────────────────────────────────────────────────────
# INICIALIZAR SESSION STATE
# ─────────────────────────────────────────────────────────────────────

def init_state():
    defaults = {
        "pagina": "login",           # login | seleccion | evaluacion | resumen
        "codigo": "",
        "nombre": "",
        "temas_seleccionados": [],
        "temas_restantes": [],
        "tema_actual": "",
        "pregunta_actual": None,
        "ids_usados": [],
        "historial": [],              # lista de dicts con resultado por pregunta
        "fase": "nueva",              # nueva | ancla | retoma | subida | repregunta_ia
        "pregunta_original": None,
        "ia_resultado": None,
        "mensaje_transicion": "",
        "respuesta_enviada": False,
        "resultado_mostrado": False,
        "etiqueta": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()
TEMAS_LISTA = list(dict.fromkeys(p["tema"] for p in PREGUNTAS))
API_KEY = get_api_key()

# ─────────────────────────────────────────────────────────────────────
# PÁGINA: LOGIN
# ─────────────────────────────────────────────────────────────────────

def pagina_login():
    st.markdown('<div class="main-title">🖥️ Evaluador Adaptativo</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Sistemas Operativos — UNSAAC</div>', unsafe_allow_html=True)
    st.divider()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 👤 Identificación del Alumno")
        codigo = st.text_input("Código de alumno", placeholder="Ej: 200312 o 2024-0001",
                               max_chars=20, key="input_codigo")
        nombre = st.text_input("Nombre completo", placeholder="Ej: Juan Pérez Quispe",
                               max_chars=80, key="input_nombre")

        if st.button("🚀 Ingresar al Evaluador", use_container_width=True, type="primary"):
            if not codigo.strip():
                st.error("⚠️ Ingresa tu código de alumno.")
            elif not nombre.strip():
                st.error("⚠️ Ingresa tu nombre completo.")
            else:
                st.session_state.codigo = codigo.strip()
                st.session_state.nombre = nombre.strip()
                st.session_state.pagina = "seleccion"
                st.rerun()

        st.markdown("---")
        st.caption("💡 Cada alumno tiene su propia sesión independiente.")

# ─────────────────────────────────────────────────────────────────────
# PÁGINA: SELECCIÓN DE TEMAS
# ─────────────────────────────────────────────────────────────────────

def pagina_seleccion():
    st.markdown(f"### 👋 Bienvenido/a, {st.session_state.nombre}")
    st.markdown(f"📋 **Código:** `{st.session_state.codigo}`")
    st.divider()
    st.markdown("### 📚 Selecciona los temas a evaluar")
    st.caption("Puedes seleccionar uno o varios temas. El evaluador adaptará la dificultad automáticamente.")

    temas_marcados = []
    cols = st.columns(2)
    for i, tema in enumerate(TEMAS_LISTA):
        with cols[i % 2]:
            if st.checkbox(tema, value=True, key=f"tema_{i}"):
                temas_marcados.append(tema)

    st.divider()
    if st.button("▶️ Iniciar Evaluación", type="primary", use_container_width=True):
        if not temas_marcados:
            st.error("⚠️ Selecciona al menos un tema.")
        else:
            random.shuffle(temas_marcados)
            st.session_state.temas_seleccionados = temas_marcados
            st.session_state.temas_restantes = temas_marcados.copy()
            st.session_state.pagina = "evaluacion"
            st.session_state.fase = "nueva"
            _cargar_siguiente_tema()
            st.rerun()

def _cargar_siguiente_tema():
    if st.session_state.temas_restantes:
        tema = st.session_state.temas_restantes.pop(0)
        st.session_state.tema_actual = tema
        # Iniciar con nivel 2 si existe, sino el más bajo disponible
        por_tema = get_preguntas_por_tema()
        niveles = sorted(por_tema.get(tema, {}).keys())
        nivel_inicio = 2 if 2 in niveles else (niveles[0] if niveles else 1)
        preg = get_pregunta(tema, nivel_inicio, st.session_state.ids_usados)
        if preg:
            st.session_state.pregunta_actual = preg
            st.session_state.pregunta_original = preg
            st.session_state.fase = "nueva"
            st.session_state.etiqueta = ""
            st.session_state.resultado_mostrado = False
            st.session_state.ia_resultado = None
        else:
            # No hay preguntas disponibles para este tema, pasar al siguiente
            if st.session_state.temas_restantes:
                _cargar_siguiente_tema()
            else:
                st.session_state.pagina = "resumen"
    else:
        st.session_state.pagina = "resumen"

# ─────────────────────────────────────────────────────────────────────
# PÁGINA: EVALUACIÓN ADAPTATIVA
# ─────────────────────────────────────────────────────────────────────

def pagina_evaluacion():
    preg = st.session_state.pregunta_actual
    if not preg:
        st.session_state.pagina = "resumen"
        st.rerun()
        return

    # ── Barra de progreso ──
    total_temas = len(st.session_state.temas_seleccionados)
    temas_hechos = total_temas - len(st.session_state.temas_restantes) - 1
    progreso = max(0, temas_hechos) / total_temas if total_temas > 0 else 0

    st.markdown(f"**👤 {st.session_state.nombre}** | Código: `{st.session_state.codigo}`")
    st.progress(progreso, text=f"Tema {max(1, temas_hechos+1)} de {total_temas}")

    # ── Encabezado del tema ──
    st.markdown(f'<div class="tema-header">📂 {preg["tema"]}</div>', unsafe_allow_html=True)

    etiqueta_extra = ""
    if st.session_state.etiqueta:
        etiqueta_extra = f" — {st.session_state.etiqueta}"

    st.markdown(f"**{badge_nivel(preg['nivel'])}{etiqueta_extra}**")

    # ── Enunciado ──
    st.markdown(f'<div class="pregunta-box">{preg["enunciado"].replace(chr(10), "<br>")}</div>',
                unsafe_allow_html=True)

    # ── Si ya se mostró el resultado, mostrar retroalimentación y botón continuar ──
    if st.session_state.resultado_mostrado:
        _mostrar_retroalimentacion()
        return

    # ── Formulario de respuesta ──
    with st.form(key=f"form_{preg['id']}_{st.session_state.fase}"):
        respuesta = None

        if preg["tipo"] == "mc":
            opciones = preg["opciones"]
            etiquetas = [f"{k}) {v}" for k, v in opciones.items()]
            seleccion = st.radio("Selecciona tu respuesta:", etiquetas, index=None)
            if seleccion:
                respuesta = seleccion[0]  # primera letra

        elif preg["tipo"] == "tf":
            seleccion = st.radio("Tu respuesta:", ["Verdadero (V)", "Falso (F)"], index=None)
            if seleccion:
                respuesta = "V" if seleccion.startswith("V") else "F"

        else:  # abierta / analogia
            respuesta = st.text_area(
                "Escribe tu respuesta:",
                height=180,
                placeholder="Desarrolla tu respuesta aquí..."
            )

        enviado = st.form_submit_button("✅ Enviar respuesta", type="primary", use_container_width=True)

    if enviado:
        if not respuesta or (isinstance(respuesta, str) and not respuesta.strip()):
            st.warning("⚠️ Escribe una respuesta antes de continuar.")
            return
        _procesar_respuesta(preg, respuesta.strip() if isinstance(respuesta, str) else respuesta)
        st.rerun()

def _procesar_respuesta(preg, respuesta):
    """Evalúa la respuesta y actualiza el estado."""
    st.session_state.ids_usados.append(preg["id"])
    ia_resultado = None
    puntaje = 0.0

    if preg["tipo"] in ("mc", "tf"):
        correcto = respuesta.upper() == preg["correcta"].upper()
        puntaje = 1.0 if correcto else 0.0
    else:
        with st.spinner("🤖 La IA está evaluando tu respuesta..."):
            ia_resultado = evaluar_con_ia(preg, respuesta, API_KEY)
        puntaje = ia_resultado.get("puntaje", 0.5)
        correcto_raw = ia_resultado.get("correcto", None)
        correcto = correcto_raw if correcto_raw is not None else puntaje >= 0.6

    # Registrar en historial
    st.session_state.historial.append({
        "tema": preg["tema"],
        "id": preg["id"],
        "nivel": preg["nivel"],
        "correcto": correcto,
        "puntaje": puntaje,
        "fase": st.session_state.fase
    })

    guardar_resultado(
        st.session_state.codigo,
        st.session_state.nombre,
        preg["tema"], preg["id"], preg["nivel"],
        correcto, puntaje
    )

    st.session_state.ia_resultado = ia_resultado
    st.session_state.resultado_mostrado = True

    # Determinar próxima fase
    fase_actual = st.session_state.fase
    preg_original = st.session_state.pregunta_original

    if fase_actual == "nueva":
        if correcto:
            st.session_state.fase = "subir"
        else:
            st.session_state.fase = "ancla_pendiente"
    elif fase_actual == "ancla":
        if correcto:
            st.session_state.fase = "retoma_pendiente"
        else:
            st.session_state.fase = "tema_terminado"
    elif fase_actual == "retoma":
        if correcto:
            st.session_state.fase = "subir"
        else:
            st.session_state.fase = "tema_terminado"
    elif fase_actual == "subida":
        st.session_state.fase = "tema_terminado"

def _mostrar_retroalimentacion():
    """Muestra el resultado y botón para continuar."""
    historial_actual = st.session_state.historial[-1] if st.session_state.historial else {}
    correcto = historial_actual.get("correcto", False)
    puntaje = historial_actual.get("puntaje", 0)
    preg = st.session_state.pregunta_actual
    ia_resultado = st.session_state.ia_resultado

    if correcto:
        st.markdown(f'<div class="correcto-box">✅ <strong>¡CORRECTO!</strong> (Puntaje: {puntaje:.1f})</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="incorrecto-box">❌ <strong>INCORRECTO</strong> (Puntaje: {puntaje:.1f})</div>',
                    unsafe_allow_html=True)

    with st.expander("📖 Ver explicación", expanded=True):
        st.write(preg["explicacion"])

    if ia_resultado:
        with st.expander("🤖 Evaluación de la IA", expanded=True):
            st.write(ia_resultado.get("comentario", ""))
            faltantes = ia_resultado.get("conceptos_faltantes", [])
            if faltantes:
                st.markdown("**💡 Conceptos a reforzar:** " + ", ".join(faltantes))

    st.divider()

    fase = st.session_state.fase
    preg_original = st.session_state.pregunta_original

    if fase == "subir":
        nivel_superior = preg_original["nivel"] + 1
        preg_siguiente = get_pregunta(preg_original["tema"], nivel_superior, st.session_state.ids_usados) if nivel_superior <= 3 else None
        if preg_siguiente:
            if st.button("🔼 ¡Bien! Subir dificultad", type="primary", use_container_width=True):
                st.session_state.pregunta_actual = preg_siguiente
                st.session_state.fase = "subida"
                st.session_state.etiqueta = "⬆ NIVEL SUPERIOR"
                st.session_state.resultado_mostrado = False
                st.session_state.ia_resultado = None
                st.rerun()
        else:
            if st.button("➡️ Siguiente tema", type="primary", use_container_width=True):
                _cargar_siguiente_tema()
                st.rerun()

    elif fase == "ancla_pendiente":
        nivel_ancla = preg_original["nivel"] - 1
        preg_ancla = get_pregunta(preg_original["tema"], nivel_ancla, st.session_state.ids_usados) if nivel_ancla >= 1 else None
        if preg_ancla:
            if st.button("🔽 Repasemos algo más básico primero", type="secondary", use_container_width=True):
                st.session_state.pregunta_actual = preg_ancla
                st.session_state.fase = "ancla"
                st.session_state.etiqueta = "🔽 PREGUNTA DE APOYO"
                st.session_state.resultado_mostrado = False
                st.session_state.ia_resultado = None
                st.rerun()
        else:
            if st.button("➡️ Siguiente tema", type="primary", use_container_width=True):
                _cargar_siguiente_tema()
                st.rerun()

    elif fase == "retoma_pendiente":
        if st.button("🔄 Retomar la pregunta original", type="primary", use_container_width=True):
            st.session_state.pregunta_actual = preg_original
            st.session_state.fase = "retoma"
            st.session_state.etiqueta = "🔄 SEGUNDA OPORTUNIDAD"
            st.session_state.resultado_mostrado = False
            st.session_state.ia_resultado = None
            st.rerun()

    elif fase == "tema_terminado":
        if st.session_state.temas_restantes:
            if st.button("➡️ Siguiente tema", type="primary", use_container_width=True):
                _cargar_siguiente_tema()
                st.rerun()
        else:
            if st.button("🏁 Ver resultados finales", type="primary", use_container_width=True):
                st.session_state.pagina = "resumen"
                st.rerun()

    elif fase == "subida":
        if st.session_state.temas_restantes:
            if st.button("➡️ Siguiente tema", type="primary", use_container_width=True):
                _cargar_siguiente_tema()
                st.rerun()
        else:
            if st.button("🏁 Ver resultados finales", type="primary", use_container_width=True):
                st.session_state.pagina = "resumen"
                st.rerun()

# ─────────────────────────────────────────────────────────────────────
# PÁGINA: RESUMEN FINAL
# ─────────────────────────────────────────────────────────────────────

def pagina_resumen():
    st.markdown('<div class="main-title">🏁 Resumen Final</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-title">UNSAAC — Sistemas Operativos</div>', unsafe_allow_html=True)
    st.divider()

    historial = st.session_state.historial
    if not historial:
        st.info("No hay resultados registrados.")
        return

    total = len(historial)
    correctas = sum(1 for h in historial if h["correcto"])
    puntaje_total = sum(h["puntaje"] for h in historial)
    porcentaje = round(100 * correctas / total, 1) if total > 0 else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📝 Preguntas", total)
    with col2:
        st.metric("✅ Correctas", correctas)
    with col3:
        st.metric("📊 Porcentaje", f"{porcentaje}%")

    st.divider()

    if porcentaje >= 80:
        st.success("🏆 ¡Excelente dominio del tema!")
    elif porcentaje >= 60:
        st.warning("👍 Buen trabajo. Refuerza los conceptos donde fallaste.")
    else:
        st.error("📚 Necesitas repasar más. Revisa Paginación, Algoritmos de Reemplazo y Memoria Virtual.")

    st.divider()
    st.markdown("### 📋 Detalle por pregunta")

    for h in historial:
        icono = "✅" if h["correcto"] else "❌"
        st.markdown(
            f"{icono} **{h['tema']}** | Nivel {h['nivel']} | ID: `{h['id']}` | Puntaje: {h['puntaje']:.2f}"
        )

    st.divider()

    # Descargar resultados CSV
    if Path("resultados.csv").exists():
        with open("resultados.csv", "rb") as f:
            st.download_button(
                label="📥 Descargar mis resultados (CSV)",
                data=f,
                file_name=f"resultados_{st.session_state.codigo}.csv",
                mime="text/csv"
            )

    if st.button("🔄 Nueva sesión", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ─────────────────────────────────────────────────────────────────────
# ROUTER PRINCIPAL
# ─────────────────────────────────────────────────────────────────────

if not API_KEY:
    st.error("⚠️ No se encontró la API Key de Anthropic. Configúrala en Streamlit Secrets.")
    st.code('ANTHROPIC_API_KEY = "sk-ant-xxxxxxxxxxxx"', language="toml")
    st.stop()

pagina = st.session_state.pagina

if pagina == "login":
    pagina_login()
elif pagina == "seleccion":
    pagina_seleccion()
elif pagina == "evaluacion":
    pagina_evaluacion()
elif pagina == "resumen":
    pagina_resumen()
