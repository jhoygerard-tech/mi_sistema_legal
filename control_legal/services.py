"""
services.py — Capa de servicios de LexNova Bolivia.
Única fuente de verdad para: modelo IA, prompts, scraping TCP, PDFs.
"""
import io
import json
import re
from datetime import datetime

import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from django.conf import settings
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from .models import PrecedenteJurisprudencial


# ══════════════════════════════════════════════
# CONFIGURACIÓN GEMINI — ÚNICA EN TODO EL PROYECTO
# ══════════════════════════════════════════════

# ⚠️  Cambia aquí el modelo y se actualiza en todo el sistema automáticamente.
# Opciones: 'gemini-1.5-flash' | 'gemini-2.5-flash' | 'gemini-1.5-pro'
GEMINI_MODEL = 'gemini-2.5-flash'


def _configurar_gemini() -> genai.GenerativeModel:
    """Inicializa y retorna el modelo Gemini. Usar siempre esta función."""
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai.GenerativeModel(GEMINI_MODEL)


def _generar_texto(prompt: str) -> tuple[str | None, str | None]:
    """
    Llama a Gemini con un prompt y retorna (texto, error).
    Función base usada por todos los generadores del sistema.
    """
    try:
        modelo   = _configurar_gemini()
        response = modelo.generate_content(prompt)
        texto    = (response.text or '').strip()
        if not texto:
            return None, 'La IA no devolvió contenido.'
        return texto, None
    except Exception as exc:
        return None, f'Error al conectar con Gemini: {exc}'


# ══════════════════════════════════════════════
# PROMPTS DEL SISTEMA — ÚNICA FUENTE DE VERDAD
# ══════════════════════════════════════════════

SYSTEM_PROMPT_CONTRATOS = """
Actúa como un Abogado Senior y Asesor Legal Corporativo en Bolivia, con más de 20 años de experiencia en Derecho Civil, Comercial y Tecnológico. Tu objetivo es redactar contratos jurídicamente inexpugnables, precisos, con visión preventiva de litigios y estrictamente adaptados a la normativa del Estado Plurinacional de Bolivia.

SISTEMA HÍBRIDO (AUTOMATIZACIÓN + EDICIÓN MANUAL)
Para todo dato faltante usa CORCHETES Y MAYÚSCULAS (ej. [NOMBRE COMPLETO DEL COMPRADOR], [NÚMERO DE C.I. Y EXPEDICIÓN], [MONTO EN NÚMEROS] ([MONTO EN LETRAS] 00/100 BOLIVIANOS)). Nunca inventes datos de las partes.

MARCO NORMATIVO
- Derecho Civil (D.L. No 12760): Art. 452 requisitos de validez.
- Derecho Comercial (Código de Comercio) y Corporativo.
- Contratos Tecnológicos: SaaS, IaaS, PaaS, desarrollo de software, SLA, SENAPI, NDA, privacidad de datos.

ESTILO BOLIVIANO
- Terminología notarial: "mayores de edad y hábiles por derecho", "sin que medie dolo, presión, fraude o vicio alguno en el consentimiento", "a su entera satisfacción".
- En transferencias: "alodial y libre de todo gravamen" y "evicción y saneamiento conforme a ley".
- Cláusulas: PRIMERA.- (TITULO), SEGUNDA.- (TITULO), etc.
- Siempre incluir: Resolución de Pleno Derecho (Art. 569 C.C.), penalidades por mora, jurisdicción.
- Contratos civiles: vía ordinaria. Comerciales/tecnológicos: arbitraje (Ley 708), CNC o CAINCO.
- Documentos privados: "al solo reconocimiento de firmas y rúbricas ante autoridad competente, surtirá los efectos de instrumento público".

ESTRUCTURA: Encabezado → PRIMERA (Antecedentes) → SEGUNDA (Objeto) → Cláusulas operativas → Salvaguarda → Incumplimiento → Jurisdicción → Firmas.
Responde SOLO con el texto del contrato, sin explicaciones ni markdown.
"""

SYSTEM_PROMPT_MEMORIALES = """
Actúa como un Abogado Litigante Senior en Bolivia, especializado en redacción de escritos judiciales ante el Órgano Judicial del Estado Plurinacional de Bolivia.

REGLAS
- Encabezado formal al juzgado correspondiente.
- Identificación con matrícula: "bajo patrocinio del Abogado [nombre], con Matrícula del Colegio de Abogados N° [MATRÍCULA]".
- Fórmulas procesales: "A Ud. con el debido respeto me dirijo exponiendo", "POR TANTO", "A USTED SEÑOR JUEZ pido se sirva...".
- Secciones en mayúsculas: ANTECEDENTES, FUNDAMENTOS DE DERECHO, PETITORIO.
- Petitorio: claro, numerado y específico.
- Datos faltantes en CORCHETES: [MATRÍCULA], [NÚMERO DE EXPEDIENTE], [FECHA DE AUDIENCIA].
- Cierre: "Es justicia que espero merecer. [Ciudad], [fecha]."
- Formal, preciso, sin ambigüedades.

Responde SOLO con el texto del memorial, sin explicaciones ni markdown.
"""

SYSTEM_PROMPT_JURISPRUDENCIA = """
Actúa como un Abogado Litigante Senior y Estratega Procesal en Bolivia, experto en jurisprudencia del TCP y TSJ.

Tu misión: analizar los hechos del caso y proponer una estrategia jurídica sólida.

INSTRUCCIONES
- Identifica el problema jurídico central y la materia procesal.
- Señala artículos constitucionales y legales bolivianos aplicables.
- Si hay precedentes del banco local, úsalos prioritariamente citando número y ratio decidendi.
- Propón: (1) línea argumentativa principal, (2) línea subsidiaria, (3) riesgos procesales, (4) petitorio sugerido.
- Usa terminología boliviana: amparo, tutela, casación, revisión, etc.
- Sé práctico: indica qué alegar, qué probar y qué evitar.
- No inventes números de sentencia que no estén en el contexto.

Responde en español con secciones claras en mayúsculas.
"""
SYSTEM_PROMPT_ANALISIS_TCP = """
Analiza el siguiente texto extraído de una resolución del Tribunal Constitucional Plurinacional de Bolivia.

Extrae y devuelve ÚNICAMENTE un JSON válido (sin markdown) con estas claves:
{
  "numero_sentencia": "ej. 0060/2023 o 0673/2021-S3",
  "tipo_resolucion": "scp|sc|as|ac|dcp|otro",
  "materia": "civil|penal|familia|laboral|constitucional|administrativo|tributario|asistencia_familiar|derechos_humanos|otro",
  "magistrado_relator": "nombre si aparece",
  "sala": "sala o comisión si aparece",
  "accion_origen": "tipo de acción si aparece",
  "fecha_resolucion": "YYYY-MM-DD o null",
  "palabras_clave": "palabra1, palabra2, palabra3",
  "ratio_decidendi": "regla jurídica central en 2-4 oraciones",
  "resumen_ia": "resumen práctico para el abogado en 4-6 oraciones"
}

Si un dato no aparece, usa cadena vacía o null.
"""

PROMPT_RESCATE_WEB_TCP = """
Eres un investigador jurídico del Tribunal Constitucional Plurinacional de Bolivia.
Usa búsqueda web para ubicar la sentencia en fuentes públicas bolivianas (juristeca.com, tcpbolivia.bo).
NO transcribas páginas completas. Elabora síntesis jurídica original.

Responde ÚNICAMENTE con JSON válido (sin markdown):
{
  "numero_sentencia": "",
  "tipo_resolucion": "scp|sc|as|ac|dcp|otro",
  "materia": "laboral|constitucional|...",
  "magistrado_relator": "",
  "sala": "",
  "accion_origen": "",
  "fecha_resolucion": "YYYY-MM-DD o null",
  "palabras_clave": "palabra1, palabra2",
  "ratio_decidendi": "regla jurídica central",
  "resumen_ia": "resumen práctico para el abogado",
  "texto_completo": "síntesis estructurada en prosa",
  "url_fuente": "URL de la fuente consultada"
}
"""

# ── Generadores IA ─────────────────────────────────────────────

def generar_contrato_con_ia(
    *,
    tipo: str,
    partes: str,
    objeto: str,
    precio: str = '',
    plazo: str = '',
    condiciones: str = '',
) -> tuple[str | None, str | None]:
    prompt = f"""{SYSTEM_PROMPT_CONTRATOS}

[DATOS DEL CONTRATO A GENERAR]
Tipo de Contrato: {tipo}
Identificación de las Partes: {partes}
Objeto y Detalles Específicos: {objeto}
Precio / Contraprestación: {precio}
Plazo de vigencia: {plazo}
Condiciones especiales adicionales: {condiciones}

Redacta el contrato completo según las instrucciones anteriores.
"""
    return _generar_texto(prompt)


def generar_memorial_con_ia(
    *,
    plantilla,
    cliente,
    expediente=None,
    hechos: str = '',
    peticion: str = '',
    datos_extra: str = '',
    abogado_nombre: str = '',
    fecha_hoy: str = '',
) -> tuple[str | None, str | None]:
    contexto_variables = f"""
Cliente: {cliente.nombre_completo}
CI del cliente: {cliente.ci}
Dirección: {cliente.direccion or '[DIRECCIÓN]'}
Abogado: {abogado_nombre or '[NOMBRE DEL ABOGADO]'}
Ciudad: La Paz
Fecha: {fecha_hoy}
NUREJ/Expediente: {expediente.nurej if expediente else '[NUREJ]'}
Juzgado: {expediente.juzgado if expediente else '[JUZGADO]'}
Materia: {expediente.materia if expediente else '[MATERIA]'}
"""
    prompt = f"""{SYSTEM_PROMPT_MEMORIALES}

PLANTILLA A USAR — {plantilla.nombre}:
{plantilla.estructura}

NORMAS APLICABLES:
{plantilla.normas_aplicables or 'Aplica las normas que correspondan según la materia.'}

DATOS DEL CASO:
{contexto_variables}

HECHOS DEL CASO (proporcionados por el abogado):
{hechos}

PETICIÓN ESPECÍFICA:
{peticion}

DATOS ADICIONALES:
{datos_extra or 'Ninguno.'}

Redacta el memorial completo siguiendo la plantilla y adaptándola al caso concreto.
"""
    return _generar_texto(prompt)


def sugerir_estrategia_jurisprudencial(
    *,
    hechos_caso: str,
    materia: str = '',
    peticion: str = '',
    precedentes_contexto: str = '',
) -> tuple[str | None, str | None]:
    prompt = f"""{SYSTEM_PROMPT_JURISPRUDENCIA}

MATERIA / ÁREA: {materia or 'No especificada'}

HECHOS DEL CASO:
{hechos_caso}

PETICIÓN O OBJETIVO PROCESAL:
{peticion or 'No especificada'}

PRECEDENTES DEL BANCO LOCAL (si aplica):
{precedentes_contexto or 'Sin precedentes locales cargados.'}

Elabora la estrategia jurídica completa.
"""
    return _generar_texto(prompt)


# ── Bot francotirador TCP ──────────────────────────────────────

TCP_BASE_URL = 'https://tcpbolivia.bo'
TCP_PORTAL_WEB_URL = 'https://web.tcp.gob.bo'
TCP_DOMINIOS_OFICIALES = frozenset({
    'tcpbolivia.bo', 'www.tcpbolivia.bo', 'tribunalconstitucional.bo',
    'www.tribunalconstitucional.bo', 'buscador.tcpbolivia.bo',
    'jurisprudencia.tcpbolivia.bo', 'web.tcp.gob.bo', 'www.web.tcp.gob.bo',
})

_RE_NUMERO_SENTENCIA = re.compile(
    r'(?:SCP|SC|AS|AC|DCP)\s*[\d]{2,4}/[\d]{4}(?:-S\d+)?|'
    r'[\d]{3,4}/[\d]{4}(?:-S\d+)?',
    re.IGNORECASE,
)

_RE_REFERENCIA_CORTA = re.compile(
    r'^(?:(?:SCP|SC|AS|AC|DCP)\s+)?(\d{1,4})/(\d{4})(?:-(S\d+))?\s*$',
    re.IGNORECASE,
)

_HEADERS_TCP = {
    'User-Agent': (
        'Mozilla/5.0 (compatible; LexNovaBot/1.0; '
        '+https://lexnova.local/jurisprudencia)'
    ),
}


def _detectar_tipo_resolucion(texto: str) -> str:
    texto_upper = texto.upper()
    for patron, tipo in (
        ('SCP', PrecedenteJurisprudencial.TIPO_SCP),
        ('DCP', PrecedenteJurisprudencial.TIPO_DCP),
        (' AS ', PrecedenteJurisprudencial.TIPO_AS),
        (' AC ', PrecedenteJurisprudencial.TIPO_AC),
        ('SC', PrecedenteJurisprudencial.TIPO_SC),
    ):
        if patron in texto_upper:
            return tipo
    return PrecedenteJurisprudencial.TIPO_OTRO


def _extraer_numero_sentencia(texto: str) -> str:
    match = _RE_NUMERO_SENTENCIA.search(texto)
    if match:
        return match.group(0).strip().upper()
    return ''


def _parsear_fecha_desde_url(url: str):
    match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
    if match:
        try:
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3))).date()
        except ValueError:
            return None
    return None


def _es_dominio_tcp(netloc: str) -> bool:
    host = (netloc or '').lower().split(':')[0]
    return host in TCP_DOMINIOS_OFICIALES or host.endswith('.tcpbolivia.bo')


def _parsear_referencia_corta(entrada: str) -> tuple[str | None, str | None]:
    """
    Valida y normaliza un número corto (ej. 0432/2020-S2).
    Retorna (referencia_normalizada, error).
    """
    texto = (entrada or '').strip()
    if not texto:
        return None, 'Debes ingresar un número de sentencia o una URL.'

    match = _RE_REFERENCIA_CORTA.match(texto)
    if not match:
        return None, (
            'Formato inválido. Usa el patrón NNNN/AAAA o NNNN/AAAA-S# '
            '(ej. 0432/2020-S2 o SCP 0060/2023).'
        )

    correlativo, anio, sala = match.group(1), match.group(2), match.group(3)
    if not (1990 <= int(anio) <= 2035):
        return None, 'El año de la sentencia no es válido.'

    referencia = f'{correlativo}/{anio}'
    if sala:
        referencia += f'-{sala.upper()}'

    if not re.match(r'^[\d/\-A-Za-z]+$', referencia):
        return None, 'La referencia contiene caracteres no permitidos.'

    return referencia, None


def _construir_url_busqueda_tcp(referencia: str) -> str:
    """URL oficial de búsqueda en el portal WordPress del TCP."""
    if '..' in referencia or referencia.startswith('/'):
        raise ValueError('Referencia de sentencia no válida.')
    return f'{TCP_BASE_URL}/search/{referencia}/'


def _resolver_url_articulo_tcp(referencia: str) -> tuple[str | None, str | None]:
    """
    Localiza la URL del artículo/noticia que publica la sentencia
    a partir del buscador oficial tcpbolivia.bo/search/<referencia>/.
    """
    correlativo = referencia.split('/')[0].lower()
    anio = referencia.split('/')[1].split('-')[0] if '/' in referencia else ''
    slug_hint = referencia.replace('/', '-').lower()

    urls_a_probar = [_construir_url_busqueda_tcp(referencia)]
    from urllib.parse import quote
    urls_a_probar.append(f'{TCP_BASE_URL}/?s={quote(referencia)}')

    for search_url in urls_a_probar:
        try:
            resp = requests.get(search_url, headers=_HEADERS_TCP, timeout=25)
            resp.raise_for_status()
        except requests.RequestException:
            continue

        soup = BeautifulSoup(resp.text, 'html.parser')
        for enlace in soup.find_all('a', href=True):
            href = enlace['href'].split('#')[0].strip()
            if not re.match(r'^https?://(?:www\.)?tcpbolivia\.bo/\d{4}/', href, re.I):
                continue
            if any(x in href.lower() for x in ('/search/', '/tag/', '/category/', '/page/')):
                continue
            href_l = href.lower()
            texto_l = enlace.get_text(' ', strip=True).lower()
            if (
                correlativo in href_l
                or slug_hint in href_l
                or referencia.lower().replace('/', '') in href_l.replace('-', '')
                or (correlativo in texto_l and anio in texto_l)
            ):
                return href, None

    return None, (
        f'No se encontró la sentencia {referencia} en el portal público del TCP. '
        'Verifica el número o pega la URL directa de la noticia en tcpbolivia.bo.'
    )


def _analizar_entrada_tcp(entrada: str) -> tuple[str | None, str | None, str | None]:
    """
    Normaliza la entrada híbrida.
    Retorna (referencia, url_directa, error).
    """
    from urllib.parse import urlparse

    texto = (entrada or '').strip()
    if not texto:
        return None, None, 'Debes proporcionar la URL o el número de la sentencia.'

    if texto.lower().startswith('http://') or texto.lower().startswith('https://'):
        parsed = urlparse(texto)
        if not _es_dominio_tcp(parsed.netloc):
            return None, None, (
                'La URL debe pertenecer al sitio oficial del TCP '
                '(tcpbolivia.bo o web.tcp.gob.bo).'
            )
        referencia = _extraer_numero_sentencia(texto) or _extraer_numero_sentencia(parsed.path)
        return referencia, texto, None

    referencia, error = _parsear_referencia_corta(texto)
    return referencia, None, error


def construir_url_portal_tcp_oficial(entrada: str) -> str:
    """
    Construye el enlace al portal web oficial del TCP (acceso directo del abogado).
    """
    from urllib.parse import quote

    referencia, url_directa, _ = _analizar_entrada_tcp(entrada)
    if url_directa:
        return url_directa
    if referencia:
        return f'{TCP_PORTAL_WEB_URL}/buscador?sentencia={quote(referencia)}'
    texto = (entrada or '').strip()
    if texto:
        return f'{TCP_PORTAL_WEB_URL}/buscador?sentencia={quote(texto)}'
    return f'{TCP_PORTAL_WEB_URL}/'


def _resolver_url_entrada(entrada: str) -> tuple[str | None, str | None]:
    """Acepta URL completa o número corto y devuelve la URL final a raspar."""
    referencia, url_directa, error = _analizar_entrada_tcp(entrada)
    if error:
        return None, error
    if url_directa:
        return url_directa, None
    if referencia:
        try:
            return _resolver_url_articulo_tcp(referencia)
        except ValueError as exc:
            return None, str(exc)
    return None, 'No se pudo interpretar la referencia de la sentencia.'


def _raspar_contenido_sentencia(url: str) -> tuple[str, str, str | None]:
    """
    Descarga y extrae título + texto de una página del TCP.
    Retorna (titulo, texto_completo, error).
    """
    try:
        resp = requests.get(url, headers=_HEADERS_TCP, timeout=25)
        resp.raise_for_status()
    except requests.Timeout:
        return '', '', 'El sitio del TCP tardó demasiado en responder. Intenta de nuevo.'
    except requests.RequestException as exc:
        return '', '', f'No se pudo acceder al sitio del TCP: {exc}'

    soup = BeautifulSoup(resp.text, 'html.parser')
    titulo_tag = soup.find('h1') or soup.find('title')
    titulo = titulo_tag.get_text(' ', strip=True) if titulo_tag else ''

    contenido = (
        soup.find('article')
        or soup.find(class_=re.compile(r'entry-content|post-content|content', re.I))
        or soup.find('main')
    )
    parrafos = []
    if contenido:
        for p in contenido.find_all(['p', 'li', 'h2', 'h3']):
            texto_p = p.get_text(' ', strip=True)
            if len(texto_p) > 30:
                parrafos.append(texto_p)
    if not parrafos:
        parrafos = [
            p.get_text(' ', strip=True)
            for p in soup.find_all('p')
            if len(p.get_text(strip=True)) > 40
        ]

    texto_completo = '\n\n'.join(parrafos[:80])
    if not texto_completo:
        return titulo, '', 'No se encontró el texto de la sentencia en la página.'

    return titulo, texto_completo, None


def _enriquecer_con_ia(texto: str, titulo: str) -> dict:
    fragmento = texto[:12000]
    prompt = f"""{SYSTEM_PROMPT_ANALISIS_TCP}

TÍTULO: {titulo}

TEXTO:
{fragmento}
"""
    resultado, error = _generar_texto(prompt)
    if error or not resultado:
        return {}
    try:
        limpio = resultado.strip()
        if limpio.startswith('```'):
            limpio = re.sub(r'^```(?:json)?\s*', '', limpio)
            limpio = re.sub(r'\s*```$', '', limpio)
        return json.loads(limpio)
    except (ValueError, TypeError):
        return {}


SYSTEM_PROMPT_RESCATE_WEB_TCP = """
Eres un investigador jurídico del Tribunal Constitucional Plurinacional de Bolivia.

Usa la búsqueda web para ubicar la sentencia exacta en fuentes públicas bolivianas
(juristeca.com, tcpbolivia.bo u otros repositorios legales).

NO transcribas literalmente páginas completas. Elabora una síntesis jurídica original
con fundamentos, parte resolutiva y reglas aplicables.

Responde ÚNICAMENTE con JSON válido (sin markdown):
{
  "numero_sentencia": "0546/2018-S1",
  "tipo_resolucion": "scp|sc|as|ac|dcp|otro",
  "materia": "laboral|constitucional|...",
  "magistrado_relator": "",
  "sala": "",
  "accion_origen": "",
  "fecha_resolucion": "YYYY-MM-DD o null",
  "palabras_clave": "palabra1, palabra2",
  "ratio_decidendi": "regla jurídica central",
  "resumen_ia": "resumen práctico para el abogado",
  "texto_completo": "síntesis estructurada (hechos, fundamentos, resolutiva) en prosa",
  "url_fuente": "URL de la fuente consultada"
}
"""


def _extraer_texto_respuesta_gemini(data: dict) -> str:
    partes = []
    for candidato in data.get('candidates', []):
        for parte in candidato.get('content', {}).get('parts', []):
            partes.append(parte.get('text', ''))
    return ''.join(partes).strip()


def _generar_con_busqueda_web(prompt: str, *, reintentos: int = 2) -> tuple[str | None, str | None]:
    """Gemini con Google Search (API REST v1beta). Reintenta si la respuesta viene vacía."""
    api_url = (
        f'https://generativelanguage.googleapis.com/v1beta/models/'
        f'{GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}'
    )
    body = {
        'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
        'tools': [{'google_search': {}}],
    }
    ultimo_error = 'La búsqueda web no devolvió contenido utilizable.'

    for intento in range(reintentos + 1):
        try:
            resp = requests.post(api_url, json=body, timeout=120)
            resp.raise_for_status()
            data = resp.json()
        except requests.Timeout:
            return None, 'La búsqueda web con IA excedió el tiempo de espera.'
        except requests.RequestException as exc:
            return None, f'Error al consultar Gemini con búsqueda web: {exc}'

        if 'error' in data:
            mensaje = data['error'].get('message', 'Error desconocido en la API de Gemini.')
            return None, mensaje

        texto = _extraer_texto_respuesta_gemini(data)
        if texto:
            return texto, None

        razones = [
            c.get('finishReason', '')
            for c in data.get('candidates', [])
            if c.get('finishReason')
        ]
        if razones:
            ultimo_error = (
                f'Gemini finalizó sin texto (motivo: {", ".join(razones)}). '
                'Reintente o consulte el portal oficial.'
            )

    return None, ultimo_error


def _parsear_json_desde_ia(texto: str) -> dict:
    limpio = texto.strip()
    if limpio.startswith('```'):
        limpio = re.sub(r'^```(?:json)?\s*', '', limpio)
        limpio = re.sub(r'\s*```$', '', limpio)
    try:
        return json.loads(limpio)
    except (ValueError, TypeError):
        match = re.search(r'\{[\s\S]*\}', limpio)
        if match:
            try:
                return json.loads(match.group(0))
            except (ValueError, TypeError):
                pass
    return {}


def _extraer_sentencia_respaldo_web(
    referencia: str | None,
    entrada_original: str,
) -> tuple[dict | None, str | None]:
    """Respaldo de emergencia: Gemini + búsqueda web en fuentes legales alternativas."""
    etiqueta = referencia or entrada_original.strip()
    prompt = f"""{SYSTEM_PROMPT_RESCATE_WEB_TCP}

SENTENCIA A LOCALIZAR: {etiqueta}

Tribunal Constitucional Plurinacional de Bolivia. Prioriza juristeca.com y sitios oficiales.
"""
    texto, error = _generar_con_busqueda_web(prompt, reintentos=2)
    if error:
        prompt_suave = (
            f'Con búsqueda web, ubica la sentencia TCP {etiqueta} en Bolivia. '
            'Devuelve solo JSON con: numero_sentencia, materia, tipo_resolucion, '
            'ratio_decidendi, resumen_ia, texto_completo (síntesis breve original), url_fuente. '
            'No copies texto literal masivo.'
        )
        texto, error = _generar_con_busqueda_web(prompt_suave, reintentos=1)
    if error:
        return None, error

    meta = _parsear_json_desde_ia(texto)
    if not meta:
        meta = {
            'numero_sentencia': referencia or _extraer_numero_sentencia(texto),
            'texto_completo':   texto[:15000],
            'resumen_ia':       texto[:2000],
            'url_fuente':       '',
        }

    numero = (meta.get('numero_sentencia') or referencia or '').strip()
    if not numero:
        numero = _extraer_numero_sentencia(texto) or etiqueta
    if not numero:
        return None, 'No se pudo identificar el número de sentencia en la búsqueda web.'

    texto_completo = (meta.get('texto_completo') or '').strip()
    if len(texto_completo) < 120:
        piezas = [
            meta.get('ratio_decidendi', ''),
            meta.get('resumen_ia', ''),
            texto,
        ]
        texto_completo = '\n\n'.join(p for p in piezas if p).strip()
    if len(texto_completo) < 80:
        return None, (
            'La búsqueda web no recuperó suficiente contenido jurídico. '
            'Use el botón del portal oficial del TCP y verifique manualmente.'
        )

    tipo_ia = (meta.get('tipo_resolucion') or '').lower()
    tipos_validos = {c[0] for c in PrecedenteJurisprudencial.TIPOS}
    tipo_resolucion = tipo_ia if tipo_ia in tipos_validos else _detectar_tipo_resolucion(etiqueta)

    materia_ia = (meta.get('materia') or '').lower()
    materias_validas = {c[0] for c in PrecedenteJurisprudencial.MATERIAS}
    materia = materia_ia if materia_ia in materias_validas else 'constitucional'

    fecha_parsed = None
    fecha_raw = meta.get('fecha_resolucion')
    if fecha_raw:
        try:
            fecha_parsed = datetime.strptime(str(fecha_raw)[:10], '%Y-%m-%d').date()
        except ValueError:
            pass

    url_fuente = meta.get('url_fuente', '') or ''
    resumen = meta.get('resumen_ia', '') or ''
    if not resumen.startswith('[Fuente alternativa'):
        resumen = (
            '[Fuente alternativa web — verificar exactitud legal] '
            + resumen
        ).strip()

    return {
        'tribunal':           PrecedenteJurisprudencial.TRIBUNAL_TCP,
        'tipo_resolucion':    tipo_resolucion,
        'numero_sentencia':   numero,
        'fecha_resolucion':   fecha_parsed,
        'materia':            materia,
        'magistrado_relator': meta.get('magistrado_relator', ''),
        'sala':               meta.get('sala', ''),
        'accion_origen':      meta.get('accion_origen', ''),
        'palabras_clave':     meta.get('palabras_clave', ''),
        'ratio_decidendi':    meta.get('ratio_decidendi', ''),
        'resumen_ia':         resumen,
        'texto_completo':     texto_completo,
        'url_fuente':         url_fuente,
        'origen':             PrecedenteJurisprudencial.ORIGEN_IA,
        'titulo_fuente':      f'Sentencia {numero} (rescate web)',
        'fuente_alternativa': True,
    }, None


def _armar_datos_desde_raspado(
    *,
    url: str,
    titulo: str,
    texto_completo: str,
    referencia: str | None,
) -> tuple[dict | None, str | None]:
    numero = (
        _extraer_numero_sentencia(titulo)
        or _extraer_numero_sentencia(texto_completo)
        or referencia
    )
    if not numero:
        return None, 'No se pudo identificar el número de sentencia en el documento.'

    meta_ia = _enriquecer_con_ia(texto_completo, titulo)

    fecha_parsed = None
    fecha = meta_ia.get('fecha_resolucion')
    if fecha:
        try:
            fecha_parsed = datetime.strptime(str(fecha)[:10], '%Y-%m-%d').date()
        except ValueError:
            fecha_parsed = _parsear_fecha_desde_url(url)
    else:
        fecha_parsed = _parsear_fecha_desde_url(url)

    tipo_ia = (meta_ia.get('tipo_resolucion') or '').lower()
    tipos_validos = {c[0] for c in PrecedenteJurisprudencial.TIPOS}
    tipo_resolucion = tipo_ia if tipo_ia in tipos_validos else _detectar_tipo_resolucion(titulo)

    materia_ia = (meta_ia.get('materia') or '').lower()
    materias_validas = {c[0] for c in PrecedenteJurisprudencial.MATERIAS}
    materia = materia_ia if materia_ia in materias_validas else 'constitucional'

    return {
        'tribunal':           PrecedenteJurisprudencial.TRIBUNAL_TCP,
        'tipo_resolucion':    tipo_resolucion,
        'numero_sentencia':   meta_ia.get('numero_sentencia') or numero,
        'fecha_resolucion':   fecha_parsed,
        'materia':            materia,
        'magistrado_relator': meta_ia.get('magistrado_relator', ''),
        'sala':               meta_ia.get('sala', ''),
        'accion_origen':      meta_ia.get('accion_origen', ''),
        'palabras_clave':     meta_ia.get('palabras_clave', ''),
        'ratio_decidendi':    meta_ia.get('ratio_decidendi', ''),
        'resumen_ia':         meta_ia.get('resumen_ia', ''),
        'texto_completo':     texto_completo,
        'url_fuente':         url,
        'origen':             PrecedenteJurisprudencial.ORIGEN_SCRAPER,
        'titulo_fuente':      titulo,
        'fuente_alternativa': False,
    }, None


def _intentar_raspado_tcp(
    entrada: str,
    referencia: str | None,
    url_directa: str | None,
) -> tuple[dict | None, str | None]:
    """Intenta extracción directa del portal TCP (ruta principal)."""
    try:
        if url_directa:
            titulo, texto, err = _raspar_contenido_sentencia(url_directa)
            if err:
                return None, err
            return _armar_datos_desde_raspado(
                url=url_directa,
                titulo=titulo,
                texto_completo=texto,
                referencia=referencia,
            )

        if referencia:
            url, err = _resolver_url_articulo_tcp(referencia)
            if err or not url:
                return None, err or 'No se encontró la sentencia en el portal del TCP.'
            titulo, texto, err = _raspar_contenido_sentencia(url)
            if err:
                return None, err
            return _armar_datos_desde_raspado(
                url=url,
                titulo=titulo,
                texto_completo=texto,
                referencia=referencia,
            )

        return None, 'No se pudo interpretar la entrada para el raspado TCP.'

    except requests.RequestException as exc:
        return None, f'Error de conexión con el TCP: {exc}'
    except ValueError as exc:
        return None, str(exc)


def extraer_sentencia_tcp(entrada: str) -> tuple[dict | None, str | None]:
    """
    Enfoque híbrido definitivo:
    1) Número corto (0546/2018-S1) o URL completa del TCP.
    2) Raspado directo del portal oficial.
    3) Si falla, respaldo automático con Gemini + búsqueda web (fuentes alternativas).
    Retorna dict listo para guardar_precedente (incluye fuente_alternativa cuando aplica).
    """
    referencia, url_directa, error_entrada = _analizar_entrada_tcp(entrada)
    if error_entrada and not url_directa and not referencia:
        return None, error_entrada

    datos, error_raspado = _intentar_raspado_tcp(entrada, referencia, url_directa)
    if datos and not error_raspado:
        return datos, None

    # Respaldo automático con búsqueda web
    datos_respaldo, error_respaldo = _extraer_sentencia_respaldo_web(
        referencia=referencia,
        entrada_original=entrada,
    )
    if datos_respaldo:
        return datos_respaldo, None

    mensaje_raspado = error_raspado or 'No se pudo extraer del portal del TCP.'
    mensaje_respaldo = error_respaldo or 'La búsqueda web alternativa no obtuvo resultados.'
    return None, (
        f'{mensaje_raspado} Se activó el respaldo web: {mensaje_respaldo}'
    )


def guardar_precedente(datos: dict, usuario=None) -> tuple[PrecedenteJurisprudencial | None, bool, str | None]:
    """
    Persiste o actualiza un precedente en el banco local (Opción B).
    Retorna (instancia, creado, error).
    """
    numero = (datos.get('numero_sentencia') or '').strip()
    if not numero:
        return None, False, 'El número de sentencia es obligatorio.'

    fuente_alternativa = bool(datos.get('fuente_alternativa'))
    origen = datos.get('origen', PrecedenteJurisprudencial.ORIGEN_SCRAPER)
    if fuente_alternativa:
        origen = PrecedenteJurisprudencial.ORIGEN_IA

    defaults = {
        'tribunal':          datos.get('tribunal', PrecedenteJurisprudencial.TRIBUNAL_TCP),
        'tipo_resolucion':   datos.get('tipo_resolucion', PrecedenteJurisprudencial.TIPO_SCP),
        'fecha_resolucion':  datos.get('fecha_resolucion'),
        'materia':           datos.get('materia', 'constitucional'),
        'magistrado_relator': datos.get('magistrado_relator', ''),
        'sala':              datos.get('sala', ''),
        'accion_origen':     datos.get('accion_origen', ''),
        'palabras_clave':    datos.get('palabras_clave', ''),
        'ratio_decidendi':   datos.get('ratio_decidendi', ''),
        'resumen_ia':        datos.get('resumen_ia', ''),
        'texto_completo':    datos.get('texto_completo', ''),
        'url_fuente':        datos.get('url_fuente', ''),
        'origen':            origen,
        'ingresado_por':     usuario,
        'verificado':        False if fuente_alternativa else datos.get('verificado', False),
    }

    precedente, creado = PrecedenteJurisprudencial.objects.update_or_create(
        numero_sentencia=numero,
        defaults=defaults,
    )
    return precedente, creado, None


def buscar_precedentes_locales(termino: str = '', materia: str = '', limite: int = 15):
    from django.db.models import Q

    qs = PrecedenteJurisprudencial.objects.all()
    if materia:
        qs = qs.filter(materia=materia)
    if termino:
        qs = qs.filter(
            Q(numero_sentencia__icontains=termino) |
            Q(palabras_clave__icontains=termino) |
            Q(ratio_decidendi__icontains=termino) |
            Q(resumen_ia__icontains=termino) |
            Q(magistrado_relator__icontains=termino)
        )
    return qs.order_by('-fecha_resolucion')[:limite]


def precedentes_a_contexto(precedentes) -> str:
    lineas = []
    for p in precedentes:
        lineas.append(
            f"- {p.get_tipo_resolucion_display()} {p.numero_sentencia} "
            f"({p.get_materia_display()}): {p.ratio_decidendi or p.resumen_ia}"
        )
    return '\n'.join(lineas) if lineas else ''


# ── PDFs con ReportLab / xhtml2pdf ─────────────────────────────

def generar_pdf_documento(
    titulo: str,
    contenido: str,
    *,
    header_brand: str = 'LexNova Bolivia',
    firma_izq: str | None = None,
    firma_der: str | None = None,
) -> io.BytesIO:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        topMargin=3 * cm, bottomMargin=2.5 * cm,
        leftMargin=3 * cm, rightMargin=3 * cm,
    )
    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle(
        'titulo', parent=styles['Normal'],
        fontSize=12 if not firma_izq else 13,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER, spaceAfter=16 if not firma_izq else 20,
    )
    cuerpo_style = ParagraphStyle(
        'cuerpo', parent=styles['Normal'],
        fontSize=11, leading=18,
        alignment=TA_JUSTIFY, spaceAfter=10,
    )
    firma_style = ParagraphStyle(
        'firma', parent=styles['Normal'],
        fontSize=10, spaceBefore=40,
    )
    elements = []

    if header_brand:
        elements.append(Paragraph(
            header_brand,
            ParagraphStyle('header', parent=styles['Normal'], fontSize=10,
                           fontName='Helvetica', alignment=TA_CENTER),
        ))
        elements.append(Spacer(1, 0.3 * cm))

    elements.append(Paragraph(titulo.upper(), titulo_style))
    elements.append(Spacer(1, 0.5 * cm))

    for parrafo in contenido.split('\n'):
        if parrafo.strip():
            elements.append(Paragraph(parrafo.strip(), cuerpo_style))
        else:
            elements.append(Spacer(1, 0.25 * cm))

    if firma_izq and firma_der:
        elements.append(Spacer(1, 2 * cm))
        elements.append(Paragraph(
            '________________________________&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'
            '________________________________',
            firma_style,
        ))
        elements.append(Paragraph(
            f'{firma_izq}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'
            f'{firma_der}',
            ParagraphStyle('firma_nombre', parent=styles['Normal'], fontSize=9),
        ))

    doc.build(elements)
    buf.seek(0)
    return buf


def generar_pdf_reporte(html: str) -> io.BytesIO:
    result = io.BytesIO()
    pisa.CreatePDF(io.BytesIO(html.encode('UTF-8')), dest=result, encoding='UTF-8')
    result.seek(0)
    return result


# ══════════════════════════════════════════════════════════════
# CONSTANTES — pega en services.py junto a las otras constantes
# ══════════════════════════════════════════════════════════════

IDIOMAS_NATIVOS = {
    'quechua': 'Quechua (Qhichwa)',
    'aymara':  'Aymara (Aymar Aru)',
}

CONTEXTOS_IDIOMA = {
    'expediente':   'el estado y avance de un caso judicial',
    'movimiento':   'una actuación procesal ocurrida en un caso judicial',
    'documento':    'un documento legal adjunto a un expediente judicial',
    'contrato':     'un contrato legal firmado entre las partes',
    'memorial':     'un escrito judicial presentado ante un juez',
    'liquidacion':  'el cálculo de una deuda de asistencia familiar',
    'tarea':        'una tarea o instrucción asignada dentro del caso',
    'evento':       'una audiencia o evento judicial próximo',
    'jurisprudencia': 'una sentencia judicial citada como precedente',
    'general':      'un documento o actuación legal',
}

PROMPT_IDIOMA_NATIVO = """
Eres un traductor e intérprete jurídico especializado en Bolivia, con dominio del {idioma_nombre} y del derecho boliviano.

Tu misión es explicar el siguiente texto legal en {idioma_nombre}, de forma clara, simple y respetuosa, para que una persona que habla ese idioma como lengua materna pueda entender perfectamente qué está pasando con su caso.

CONTEXTO: El texto trata sobre {contexto}.

TEXTO ORIGINAL (en español jurídico):
{texto}

INSTRUCCIONES:
1. Primero escribe la explicación COMPLETA en {idioma_nombre}.
2. Luego escribe la misma explicación en español simple (sin tecnicismos), separada por una línea con "---".
3. Usa un tono cálido, cercano y respetuoso — como hablaría un abogado de confianza.
4. Evita términos legales complejos en ambas versiones. Si debes usarlos, explícalos.
5. Si hay fechas, montos o plazos importantes, destácalos claramente.
6. Incluye al final en {idioma_nombre} qué debe hacer o qué pasará a continuación (si se puede inferir del texto).
7. Máximo 300 palabras por sección.

Formato de respuesta:
[EXPLICACIÓN EN {idioma_nombre_mayus}]
(aquí la explicación en idioma nativo)

---

[EXPLICACIÓN EN ESPAÑOL SIMPLE]
(aquí la explicación en español sin tecnicismos)
"""


# ══════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL — pega en services.py
# ══════════════════════════════════════════════════════════════

def explicar_en_idioma_nativo(
    texto: str,
    idioma: str,
    contexto: str = 'general',
) -> tuple[str | None, str | None]:
    """
    Genera una explicación del texto jurídico en Quechua o Aymara
    acompañada de su versión en español simple.

    Parámetros:
        texto    : Texto jurídico a explicar (memorial, contrato, descripción, etc.)
        idioma   : 'quechua' o 'aymara'
        contexto : Clave del diccionario CONTEXTOS_IDIOMA (ej. 'contrato', 'expediente')

    Retorna:
        (explicacion_str, error_str) — uno de los dos será None.
    """
    idioma = (idioma or '').lower().strip()
    if idioma not in IDIOMAS_NATIVOS:
        return None, f'Idioma no soportado: {idioma}. Usa "quechua" o "aymara".'

    texto = (texto or '').strip()
    if not texto:
        return None, 'No hay texto para explicar.'
    if len(texto) < 20:
        return None, 'El texto es demasiado corto para generar una explicación.'

    # Limitar texto de entrada para no exceder tokens
    texto_recortado = texto[:6000] if len(texto) > 6000 else texto

    idioma_nombre      = IDIOMAS_NATIVOS[idioma]
    idioma_nombre_mayus = idioma_nombre.upper()
    contexto_desc      = CONTEXTOS_IDIOMA.get(contexto, CONTEXTOS_IDIOMA['general'])

    prompt = PROMPT_IDIOMA_NATIVO.format(
        idioma_nombre=idioma_nombre,
        idioma_nombre_mayus=idioma_nombre_mayus,
        contexto=contexto_desc,
        texto=texto_recortado,
    )

    return _generar_texto(prompt)