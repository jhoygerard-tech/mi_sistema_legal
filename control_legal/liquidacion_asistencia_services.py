"""
Liquidación de Asistencia Familiar — Ley 603 (Bolivia).
Lógica forense de cómputo, extracción IA y PDF judicial.
"""
from __future__ import annotations

import io
import json
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from dateutil.relativedelta import relativedelta
from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import legal
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

# ── Importar desde services.py — única fuente de verdad ──────
from .services import _generar_texto as _generar_texto_gemini

# El resto del archivo permanece igual desde DISTRITOS_JUDICIALES en adelante.
# Solo elimina la función _generar_texto_gemini que estaba definida aquí.

GEMINI_MODEL = 'gemini-2.5-flash'


def _generar_texto_gemini(prompt: str) -> tuple[str | None, str | None]:
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        modelo = genai.GenerativeModel(GEMINI_MODEL)
        response = modelo.generate_content(prompt)
        texto = (response.text or '').strip()
        if not texto:
            return None, 'La IA no devolvió contenido.'
        return texto, None
    except Exception as exc:
        return None, f'Error al conectar con Gemini: {exc}'

DISTRITOS_JUDICIALES = [
    'La Paz', 'Cochabamba', 'Santa Cruz', 'Oruro', 'Potosí',
    'Chuquisaca', 'Tarija', 'Beni', 'Pando',
]

PALABRAS_PROCESO_FAMILIA = (
    'asistencia familiar', 'asistencia', 'divorcio', 'guarda',
    'menores', 'alimentos', 'régimen de visitas', 'regimen de visitas',
    'patria potestad', 'filiación',
)


def es_expediente_familia_liquidacion(expediente) -> bool:
    """Casos de Familia: Asistencia Familiar, Divorcios o Guarda con menores."""
    if (expediente.materia or '').strip() == 'Familia':
        return True
    texto = f'{(expediente.tipo_proceso or "")} {(expediente.descripcion or "")}'.lower()
    return any(p in texto for p in PALABRAS_PROCESO_FAMILIA)


def _redondear_bs(valor) -> Decimal:
    return Decimal(valor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _formatear_fecha(f: date) -> str:
    return f.strftime('%d/%m/%Y')


def computar_tramo_liquidacion(
    fecha_inicio: date,
    fecha_fin: date,
    monto_mensual: Decimal,
    *,
    aplicar_duodecimas: bool = False,
) -> dict:
    """
    Cómputo fecha a fecha (mes vencido). Del 10/01 al 09/02 = 1 mes cumplido.
    Duodécimas solo sobre días residuales del último tramo si está activado.
    """
    monto_mensual = _redondear_bs(monto_mensual)
    if fecha_fin < fecha_inicio:
        return {
            'filas': [],
            'meses_enteros': 0,
            'monto_tramo': Decimal('0.00'),
            'dias_residuales': 0,
        }

    filas = []
    meses_enteros = 0
    monto_acumulado = Decimal('0.00')
    cursor = fecha_inicio

    while True:
        fin_mes_cumplido = cursor + relativedelta(months=+1, days=-1)
        if fin_mes_cumplido > fecha_fin:
            break
        meses_enteros += 1
        monto_acumulado += monto_mensual
        filas.append({
            'monto_acordado': monto_mensual,
            'fecha_del': cursor,
            'fecha_al': fin_mes_cumplido,
            'meses_label': '1 mes cumplido',
            'meses_numero': 1,
            'monto_pagar': monto_mensual,
            'es_duodecima': False,
        })
        cursor = fin_mes_cumplido + timedelta(days=1)

    dias_residuales = 0
    if cursor <= fecha_fin:
        dias_residuales = (fecha_fin - cursor).days + 1

    if dias_residuales > 0 and aplicar_duodecimas:
        monto_dias = _redondear_bs((monto_mensual / Decimal('30')) * Decimal(dias_residuales))
        monto_acumulado += monto_dias
        filas.append({
            'monto_acordado': monto_mensual,
            'fecha_del': cursor,
            'fecha_al': fecha_fin,
            'meses_label': f'{dias_residuales} día(s) — duodécimas (30 días/mes)',
            'meses_numero': 0,
            'monto_pagar': monto_dias,
            'es_duodecima': True,
        })

    return {
        'filas': filas,
        'meses_enteros': meses_enteros,
        'monto_tramo': _redondear_bs(monto_acumulado),
        'dias_residuales': dias_residuales if aplicar_duodecimas else 0,
    }


def computar_liquidacion_completa(
    tramos: list[dict],
    *,
    aplicar_duodecimas: bool = False,
    pagos: list[dict] | None = None,
) -> dict:
    """
    Calcula la liquidación completa por tramos y descuenta los pagos del obligado.
    - tramos: lista con fecha_inicio, fecha_fin, monto_mensual
    - pagos:  lista con monto, fecha, concepto  (Art. 114 Ley 603)
    """
    todas_filas  = []
    total        = Decimal('0.00')
    total_meses  = 0

    for idx, tramo in enumerate(tramos, start=1):
        fi    = tramo['fecha_inicio']
        ff    = tramo['fecha_fin']
        monto = _redondear_bs(tramo['monto_mensual'])
        res   = computar_tramo_liquidacion(
            fi, ff, monto, aplicar_duodecimas=aplicar_duodecimas,
        )
        for fila in res['filas']:
            fila['tramo_numero'] = idx
            todas_filas.append(fila)
        total       += res['monto_tramo']
        total_meses += res['meses_enteros']

    # ── Pagos del obligado — Art. 114 Ley 603 ────────────────────
    detalle_pagos = []
    total_pagado  = Decimal('0.00')
    for p in (pagos or []):
        try:
            monto_pago = _redondear_bs(str(p.get('monto', '0')).replace(',', '.'))
            if monto_pago <= 0:
                continue
            total_pagado += monto_pago
            detalle_pagos.append({
                'monto':    monto_pago,
                'fecha':    p.get('fecha') or None,
                'concepto': p.get('concepto') or 'Pago parcial Art. 114 Ley 603',
            })
        except Exception:
            continue

    saldo_adeudado = _redondear_bs(total - total_pagado)

    return {
        'filas':               todas_filas,
        'total_liquidacion':   _redondear_bs(total),
        'total_meses_enteros': total_meses,
        'total_pagado':        _redondear_bs(total_pagado),
        'detalle_pagos':       detalle_pagos,
        'saldo_adeudado':      saldo_adeudado,
    }


def _leer_texto_pdf(ruta: str) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(ruta)
        return '\n'.join(
            (page.extract_text() or '') for page in reader.pages[:25]
        )
    except Exception:
        return ''


def _leer_texto_docx(ruta: str) -> str:
    try:
        from docx import Document
        doc = Document(ruta)
        return '\n'.join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception:
        return ''


def _extraer_texto_documento(archivo) -> str:
    if not archivo:
        return ''
    path = Path(archivo.path)
    ext = path.suffix.lower()
    if ext == '.pdf':
        return _leer_texto_pdf(str(path))
    if ext in ('.docx',):
        return _leer_texto_docx(str(path))
    if ext == '.doc':
        return ''
    return ''


PROMPT_EXTRACCION_LIQUIDACION = """
Analiza los siguientes fragmentos de documentos judiciales bolivianos de un proceso de
ASISTENCIA FAMILIAR (Ley 603).

Extrae ÚNICAMENTE un JSON válido (sin markdown):
{
  "fecha_inicio": "YYYY-MM-DD o null (citación o última liquidación fijada)",
  "monto_mensual": "número decimal sin símbolos o null",
  "partes": "demandante y demandado si aparecen",
  "distrito_judicial": "",
  "juzgado": "",
  "nurej_ianus": "",
  "observaciones": "breve nota de la fuente"
}

Si no encuentras un dato, usa null o cadena vacía. No inventes montos.
"""


def extraer_datos_liquidacion_ia(expediente) -> tuple[dict | None, str | None]:
    """Analiza PDF/Word adjuntos al expediente con Gemini."""
    fragmentos = []
    for doc in expediente.documentos.all()[:8]:
        texto = _extraer_texto_documento(doc.archivo)
        if texto and len(texto.strip()) > 80:
            fragmentos.append(
                f"[{doc.get_tipo_display()} — {doc.titulo}]\n{texto[:6000]}"
            )

    if not fragmentos:
        return None, (
            'No hay documentos PDF o Word con texto legible en este expediente. '
            'Suba resoluciones o liquidaciones previas para la extracción automática.'
        )

    contexto_exp = f"""
Expediente: NUREJ {expediente.nurej or 'N/D'}, Juzgado: {expediente.juzgado or 'N/D'},
Materia: {expediente.materia}, Tipo: {expediente.tipo_proceso or 'N/D'},
Cliente: {expediente.cliente.nombre_completo}.
"""
    prompt = f"""{PROMPT_EXTRACCION_LIQUIDACION}

{contexto_exp}

DOCUMENTOS:
{chr(10).join(fragmentos[:5])}
"""
    respuesta, error = _generar_texto_gemini(prompt)
    if error:
        return None, error

    limpio = respuesta.strip()
    if limpio.startswith('```'):
        limpio = re.sub(r'^```(?:json)?\s*', '', limpio)
        limpio = re.sub(r'\s*```$', '', limpio)
    try:
        datos = json.loads(limpio)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', limpio)
        if not match:
            return None, 'La IA no devolvió datos estructurados válidos.'
        datos = json.loads(match.group(0))

    return datos, None


def parsear_tramos_desde_post(post_data) -> list[dict]:
    """
    Lee tramos desde campos HTML indexados:
        tramo_inicio_0, tramo_fin_0, tramo_monto_0
        tramo_inicio_1, tramo_fin_1, tramo_monto_1  ...
    No depende de JSON ni de JS para funcionar.
    """
    tramos = []
    i = 0
    while True:
        fecha_inicio = post_data.get(f'tramo_inicio_{i}', '').strip()
        fecha_fin    = post_data.get(f'tramo_fin_{i}', '').strip()
        monto_raw    = post_data.get(f'tramo_monto_{i}', '').strip()

        # Si no existe el campo, terminamos el loop
        if not fecha_inicio and not fecha_fin and not monto_raw:
            break

        try:
            fi    = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            ff    = datetime.strptime(fecha_fin,    '%Y-%m-%d').date()
            monto = Decimal(monto_raw.replace(',', '.'))
            tramos.append({
                'fecha_inicio':  fi,
                'fecha_fin':     ff,
                'monto_mensual': monto,
            })
        except (ValueError, TypeError):
            pass  # campo mal formado, lo ignoramos

        i += 1
        if i > 50:  # límite de seguridad
            break

    return tramos


def parsear_pagos_desde_post(post_data) -> list[dict]:
    """
    Lee pagos desde campos HTML indexados:
        pago_fecha_0, pago_monto_0, pago_concepto_0
        pago_fecha_1, pago_monto_1, pago_concepto_1  ...
    No depende de JSON ni de JS para funcionar.
    """
    pagos = []
    i = 0
    while True:
        monto_raw = post_data.get(f'pago_monto_{i}', '').strip()

        # Si no existe el campo de monto, terminamos
        if not monto_raw and f'pago_monto_{i}' not in post_data:
            break

        try:
            monto = Decimal(monto_raw.replace(',', '.'))
            if monto > 0:
                pagos.append({
                    'monto':    monto,
                    'fecha':    post_data.get(f'pago_fecha_{i}',    '').strip() or None,
                    'concepto': post_data.get(f'pago_concepto_{i}', '').strip() or '',
                })
        except (ValueError, TypeError):
            pass

        i += 1
        if i > 100:
            break

    return pagos

def generar_pdf_liquidacion_asistencia(datos_planilla: dict) -> io.BytesIO:
    """Planilla judicial boliviana — Ley 603."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=legal,
        topMargin=2 * cm, bottomMargin=2 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    titulo = ParagraphStyle(
        'titulo_liq', parent=styles['Normal'],
        fontSize=13, fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=8,
    )
    subtitulo = ParagraphStyle(
        'sub_liq', parent=styles['Normal'],
        fontSize=10, alignment=TA_CENTER, spaceAfter=14,
    )
    normal = ParagraphStyle(
        'normal_liq', parent=styles['Normal'],
        fontSize=10, leading=14, alignment=TA_JUSTIFY,
    )

    elementos = [
        Paragraph('PLANILLA DE LIQUIDACIÓN DE ASISTENCIA FAMILIAR', titulo),
        Paragraph('Ley N° 603 Codigo de las Familias y del Proceso Familiar', subtitulo),
        Spacer(1, 0.3 * cm),
        Paragraph(
            f'<b>Distrito Judicial:</b> {datos_planilla.get("distrito_judicial", "")}<br/>'
            f'<b>Juzgado de la Causa:</b> {datos_planilla.get("juzgado", "")}<br/>'
            f'<b>NUREJ / IANUS:</b> {datos_planilla.get("nurej_ianus", "")}<br/>'
            f'<b>Partes:</b> {datos_planilla.get("partes", "")}',
            normal,
        ),
        Spacer(1, 0.5 * cm),
    ]

    encabezados = [
        'Monto de Asistencia\nAcordada (Bs.)',
        'Periodo que comprende\nla liquidación (Del — Al)',
        'Meses cumplidos\n(Mes vencido)',
        'Monto a Pagar\n(Bs.)',
    ]
    filas_tabla = [encabezados]

    for fila in datos_planilla.get('filas', []):
        periodo = (
            f'Del {_formatear_fecha(fila["fecha_del"])} al '
            f'{_formatear_fecha(fila["fecha_al"])}'
        )
        filas_tabla.append([
            f'{fila["monto_acordado"]:,.2f}',
            periodo,
            fila['meses_label'],
            f'{fila["monto_pagar"]:,.2f}',
        ])

    filas_tabla.append([
        '', '', 'TOTAL GENERAL',
        f'{datos_planilla.get("total_liquidacion", Decimal("0")):,.2f}',
    ])

    tabla = Table(
        filas_tabla,
        colWidths=[4.2 * cm, 6.5 * cm, 4.5 * cm, 3.8 * cm],
        repeatRows=1,
    )
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a2744')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f4f6fa')]),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8ecf4')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 0.6 * cm))

    nota_duod = ''
    if datos_planilla.get('aplicar_duodecimas'):
        nota_duod = (
            'Se aplicó fraccionamiento por duodécimas (Monto Mensual ÷ 30 × días residuales) '
            'en el mes de corte.'
        )
    else:
        nota_duod = (
            'Sin fraccionamiento duodécimo: los días residuales del último tramo '
            'que no completan un mes entero no se liquidaron.'
        )

    elementos.append(Paragraph(
        f'<i>{nota_duod}</i><br/><br/>'
        f'Fecha de emisión de la planilla: {_formatear_fecha(date.today())}. '
        'Documento generado por LexNova Bolivia.',
        ParagraphStyle('pie', parent=styles['Normal'], fontSize=8, alignment=TA_JUSTIFY),
    ))

    doc.build(elementos)
    buf.seek(0)
    return buf
