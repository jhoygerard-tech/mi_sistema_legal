"""
Motor PDF — Prefiniquito Laboral Boliviano
Genera el reporte con estructura fiel al modelo del usuario.
"""
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)

# ── Paleta LexNova ────────────────────────────────────────────
NAVY   = colors.HexColor('#1a2744')
BLUE   = colors.HexColor('#2d4a8a')
ACCENT = colors.HexColor('#3d6fd4')
GOLD   = colors.HexColor('#c9962a')
LIGHT  = colors.HexColor('#e8ecf4')
WHITE  = colors.white
GREY   = colors.HexColor('#6c757d')
RED    = colors.HexColor('#dc3545')
GREEN  = colors.HexColor('#198754')
BGROW  = colors.HexColor('#f4f7fd')

def _bs(valor):
    """Formatea un número como 'Bs. 1.234,56'"""
    try:
        n = float(valor)
        return f"Bs. {n:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception:
        return 'Bs. 0,00'

def generar_pdf_prefiniquito(datos: dict) -> io.BytesIO:
    """
    datos: diccionario con todos los campos del formulario y cálculos.
    Retorna BytesIO listo para HttpResponse.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.2*cm, bottomMargin=2.2*cm,
        title='Prefiniquito Laboral — LexNova',
        author='LexNova Sistema Jurídico Digital',
    )

    W = A4[0] - 4*cm  # ancho útil

    # ── Estilos ───────────────────────────────────────────────
    def estilo(nombre, **kw):
        defaults = dict(
            fontName='Helvetica', fontSize=9, leading=13,
            textColor=colors.black, alignment=TA_LEFT,
        )
        defaults.update(kw)
        return ParagraphStyle(nombre, **defaults)

    s_titulo     = estilo('titulo',    fontName='Helvetica-Bold', fontSize=16,
                          textColor=WHITE, alignment=TA_CENTER, leading=20)
    s_subtitulo  = estilo('subtitulo', fontName='Helvetica',      fontSize=8,
                          textColor=colors.HexColor('#c8d3ea'),   alignment=TA_CENTER)
    s_seccion    = estilo('seccion',   fontName='Helvetica-Bold', fontSize=8,
                          textColor=NAVY, letterSpacing=1.2, spaceBefore=4)
    s_normal     = estilo('normal',    fontSize=9,  leading=14)
    s_negrita    = estilo('negrita',   fontName='Helvetica-Bold', fontSize=9, leading=14)
    s_legal      = estilo('legal',     fontName='Helvetica-Oblique', fontSize=7.5,
                          textColor=GREY, leading=11)
    s_disclaimer = estilo('disc',      fontName='Helvetica-Oblique', fontSize=7,
                          textColor=colors.HexColor('#78350f'), leading=10,
                          alignment=TA_JUSTIFY)

    historia = []

    # ══════════════════════════════════════════════════════════
    # 1. ENCABEZADO
    # ══════════════════════════════════════════════════════════
    fecha_emision = datetime.now().strftime('%d de %B de %Y').upper()

    t_enc = Table(
        [
            [Paragraph('PREFINIQUITO LABORAL', s_titulo)],
            [Paragraph(
                'LIQUIDACIÓN DE BENEFICIOS SOCIALES Y DERECHOS LABORALES<br/>'
                'Estado Plurinacional de Bolivia',
                s_subtitulo
            )],
        ],
        colWidths=[W],
    )
    t_enc.setStyle(TableStyle([
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [NAVY, BLUE]),
        ('TOPPADDING',    (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING',   (0,0), (-1,-1), 16),
        ('RIGHTPADDING',  (0,0), (-1,-1), 16),
    ]))
    historia.append(t_enc)
    historia.append(Spacer(1, 0.4*cm))

    # Fecha de emisión
    t_ref = Table([[
        Paragraph(f'<b>Fecha de emisión:</b> {fecha_emision}', s_normal),
        Paragraph('<b>Emitido por:</b> LexNova Sistema Jurídico Digital', s_normal),
    ]], colWidths=[W/2, W/2])
    t_ref.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), LIGHT),
        ('TOPPADDING',    (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING',   (0,0), (-1,-1), 10),
        ('RIGHTPADDING',  (0,0), (-1,-1), 10),
        ('BOX',           (0,0), (-1,-1), 0.5, colors.HexColor('#c8d4f0')),
    ]))
    historia.append(t_ref)
    historia.append(Spacer(1, 0.5*cm))

    # ══════════════════════════════════════════════════════════
    # 2. DATOS DE LAS PARTES
    # ══════════════════════════════════════════════════════════
    historia.append(Paragraph('I. DATOS DE LAS PARTES', s_seccion))
    historia.append(Spacer(1, 0.15*cm))

    col_w = [3.2*cm, W/2-3.2*cm, 3.8*cm, W/2-3.8*cm]
    t_partes = Table([[
        Paragraph('<b>TRABAJADOR</b>', s_negrita),
        Paragraph(datos.get('trabajador', '—'), s_normal),
        Paragraph('<b>EMPLEADOR / EMPRESA</b>', s_negrita),
        Paragraph(datos.get('empleador', '—'), s_normal),
    ]], colWidths=col_w)
    t_partes.setStyle(TableStyle([
        ('BOX',           (0,0), (-1,-1), 0.5, colors.HexColor('#c8d4f0')),
        ('INNERGRID',     (0,0), (-1,-1), 0.3, LIGHT),
        ('TOPPADDING',    (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING',   (0,0), (-1,-1), 10),
        ('RIGHTPADDING',  (0,0), (-1,-1), 10),
    ]))
    historia.append(t_partes)
    historia.append(Spacer(1, 0.4*cm))

    # ══════════════════════════════════════════════════════════
    # 3. PERÍODO LABORAL Y SPI
    # ══════════════════════════════════════════════════════════
    historia.append(Paragraph(
        'II. PERÍODO LABORAL Y SUELDO PROMEDIO INDEMNIZABLE', s_seccion
    ))
    historia.append(Spacer(1, 0.15*cm))

    tiempo = datos.get('tiempo', {})
    tiempo_txt = (
        f"{tiempo.get('anios', 0)} año(s), "
        f"{tiempo.get('meses', 0)} mes(es) y "
        f"{tiempo.get('dias', 0)} día(s) "
        f"[{tiempo.get('totalDias', 0)} días totales]"
    )

    periodo_rows = [
        [
            Paragraph('<b>Fecha de Ingreso</b>', s_negrita),
            Paragraph(datos.get('fechaIngreso', '—'), s_normal),
            Paragraph('<b>Fecha de Conclusión</b>', s_negrita),
            Paragraph(datos.get('fechaConclusion', '—'), s_normal),
        ],
        [
            Paragraph('<b>Tiempo de Servicio</b>', s_negrita),
            Paragraph(tiempo_txt, s_normal),
            Paragraph('<b>Causa de Extinción</b>', s_negrita),
            Paragraph(datos.get('causaLabel', '—'), s_normal),
        ],
        [
            Paragraph('<b>Salario Mes 1</b>', s_negrita),
            Paragraph(_bs(datos.get('s1', 0)), s_normal),
            Paragraph('<b>Salario Mes 2</b>', s_negrita),
            Paragraph(_bs(datos.get('s2', 0)), s_normal),
        ],
        [
            Paragraph('<b>Salario Mes 3</b>', s_negrita),
            Paragraph(_bs(datos.get('s3', 0)), s_normal),
            Paragraph('<b>SPI (Promedio 3 meses)</b>', s_negrita),
            Paragraph(
                f'<b>{_bs(datos.get("spi", 0))}</b>',
                estilo('spi_v', fontName='Helvetica-Bold', fontSize=9, textColor=NAVY)
            ),
        ],
    ]
    t_periodo = Table(periodo_rows, colWidths=col_w)
    t_periodo.setStyle(TableStyle([
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [WHITE, BGROW, WHITE, BGROW]),
        ('BOX',            (0,0), (-1,-1), 0.5, colors.HexColor('#c8d4f0')),
        ('INNERGRID',      (0,0), (-1,-1), 0.3, LIGHT),
        ('TOPPADDING',     (0,0), (-1,-1), 7),
        ('BOTTOMPADDING',  (0,0), (-1,-1), 7),
        ('LEFTPADDING',    (0,0), (-1,-1), 10),
        ('RIGHTPADDING',   (0,0), (-1,-1), 10),
        ('BACKGROUND',     (0,3), (-1,3), colors.HexColor('#eef2fb')),
    ]))
    historia.append(t_periodo)
    historia.append(Spacer(1, 0.1*cm))
    historia.append(Paragraph(
        '(*) SPI: promedio aritmético simple de los últimos 3 meses — '
        'LGT Art. 19 · D.S. 110 Art. 2',
        s_legal
    ))
    historia.append(Spacer(1, 0.5*cm))

    # ══════════════════════════════════════════════════════════
    # 4. TABLA DE CONCEPTOS
    # ══════════════════════════════════════════════════════════
    historia.append(Paragraph(
        'III. DETALLE DE CONCEPTOS LIQUIDADOS', s_seccion
    ))
    historia.append(Spacer(1, 0.15*cm))

    filas_tabla = [[
        Paragraph('CONCEPTO', estilo('th',  fontName='Helvetica-Bold', fontSize=8,
                  textColor=WHITE)),
        Paragraph('CÁLCULO',  estilo('th2', fontName='Helvetica-Bold', fontSize=8,
                  textColor=WHITE)),
        Paragraph('FUNDAMENTO LEGAL', estilo('th3', fontName='Helvetica-Bold',
                  fontSize=8, textColor=WHITE)),
        Paragraph('MONTO', estilo('th4', fontName='Helvetica-Bold', fontSize=8,
                  textColor=WHITE, alignment=TA_RIGHT)),
    ]]

    conceptos = datos.get('conceptos', [])
    for i, c in enumerate(conceptos):
        aplica     = c.get('aplica', True)
        monto_val  = float(c.get('monto', 0))
        color_txt  = NAVY if aplica and monto_val > 0 else GREY
        monto_txt  = _bs(monto_val) if aplica and monto_val > 0 else '—'
        filas_tabla.append([
            Paragraph(f'<b>{c.get("concepto","")}</b>',
                estilo(f'cn{i}', fontName='Helvetica-Bold',
                       fontSize=8.5, textColor=color_txt)),
            Paragraph(c.get('calculo', ''),
                estilo(f'cc{i}', fontSize=8,
                       textColor=colors.black if aplica else GREY, leading=11)),
            Paragraph(c.get('fundamento', ''),
                estilo(f'cf{i}', fontName='Helvetica-Oblique',
                       fontSize=7.5, textColor=ACCENT, leading=10)),
            Paragraph(monto_txt,
                estilo(f'cm{i}',
                       fontName='Helvetica-Bold' if monto_val > 0 else 'Helvetica',
                       fontSize=9, textColor=color_txt, alignment=TA_RIGHT)),
        ])

    subtotal = float(datos.get('subtotal', 0))
    multa    = float(datos.get('multa30',  0))
    total    = float(datos.get('total',    0))
    n        = len(filas_tabla)

    # Fila subtotal
    filas_tabla.append([
        Paragraph('SUBTOTAL LIQUIDADO',
            estilo('sub', fontName='Helvetica-Bold', fontSize=9, textColor=NAVY)),
        Paragraph('', s_normal), Paragraph('', s_normal),
        Paragraph(_bs(subtotal),
            estilo('subv', fontName='Helvetica-Bold', fontSize=9.5,
                   textColor=NAVY, alignment=TA_RIGHT)),
    ])

    # Fila multa 30%
    if multa > 0:
        filas_tabla.append([
            Paragraph('Multa 30% por Retardo en el Pago',
                estilo('ml', fontName='Helvetica-Bold', fontSize=8.5, textColor=RED)),
            Paragraph('Subtotal × 30%',
                estilo('mc', fontSize=8, textColor=RED)),
            Paragraph('D.S. 28699 Art. 9 — más de 15 días desde el despido',
                estilo('mf', fontName='Helvetica-Oblique', fontSize=7.5, textColor=RED)),
            Paragraph(_bs(multa),
                estilo('mv', fontName='Helvetica-Bold', fontSize=9,
                       textColor=RED, alignment=TA_RIGHT)),
        ])

    nf = len(filas_tabla)
    col_w_tabla = [4.5*cm, 5.5*cm, 4.5*cm, 2.5*cm]
    t_conceptos = Table(filas_tabla, colWidths=col_w_tabla, repeatRows=1)

    style_cmds = [
        ('BACKGROUND',    (0,0), (-1,0), NAVY),
        ('ROWBACKGROUNDS',(0,1), (-1, n-1), [WHITE, BGROW]),
        ('TOPPADDING',    (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ('RIGHTPADDING',  (0,0), (-1,-1), 8),
        ('BOX',           (0,0), (-1,-1), 0.5, colors.HexColor('#c8d4f0')),
        ('LINEBELOW',     (0,0), (-1,0),  0.5, BLUE),
        ('BACKGROUND',    (0,n),  (-1,n),  LIGHT),
        ('LINEABOVE',     (0,n),  (-1,n),  1.2, NAVY),
        ('FONTNAME',      (0,n),  (-1,n),  'Helvetica-Bold'),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]
    if multa > 0:
        style_cmds += [
            ('BACKGROUND', (0,nf-1), (-1,nf-1), colors.HexColor('#fff5f5')),
            ('LINEABOVE',  (0,nf-1), (-1,nf-1), 0.5, RED),
        ]
    t_conceptos.setStyle(TableStyle(style_cmds))
    historia.append(t_conceptos)
    historia.append(Spacer(1, 0.3*cm))

    # ══════════════════════════════════════════════════════════
    # 5. TOTAL FINAL
    # ══════════════════════════════════════════════════════════
    t_total = Table([[
        Paragraph('TOTAL GENERAL A PAGAR',
            estilo('tgl', fontName='Helvetica-Bold', fontSize=12,
                   textColor=WHITE, alignment=TA_LEFT)),
        Paragraph(_bs(total),
            estilo('tgv', fontName='Helvetica-Bold', fontSize=14,
                   textColor=WHITE, alignment=TA_RIGHT)),
    ]], colWidths=[W*0.6, W*0.4])
    t_total.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), NAVY),
        ('TOPPADDING',    (0,0), (-1,-1), 14),
        ('BOTTOMPADDING', (0,0), (-1,-1), 14),
        ('LEFTPADDING',   (0,0), (0,-1),  16),
        ('RIGHTPADDING',  (-1,0),(-1,-1), 16),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]))
    historia.append(t_total)
    historia.append(Spacer(1, 0.5*cm))

    # ══════════════════════════════════════════════════════════
    # 6. BASE NORMATIVA
    # ══════════════════════════════════════════════════════════
    historia.append(Paragraph('IV. BASE NORMATIVA APLICADA', s_seccion))
    historia.append(Spacer(1, 0.15*cm))

    normas = [
        ('Ley General del Trabajo (LGT)', 'D.S. 08/12/1942 · Ley 18/12/1944',
         'Indemnización (Art. 13), Desahucio (Art. 12), Vacaciones (Art. 44), Salario Devengado (Art. 18)'),
        ('Decreto Supremo N° 110', '01 de mayo de 2009',
         'Reglamenta el pago de beneficios sociales, desahucio e indemnización (Arts. 1-5)'),
        ('Decreto Supremo N° 28699', '01 de mayo de 2006',
         'Multa del 30% por retardo en el pago (Art. 9) — inamovilidad laboral'),
        ('Decreto Supremo N° 522', '26 de junio de 1954',
         'Consolidación de indemnización por quinquenios (Art. 2)'),
        ('Decreto Supremo N° 21060', '29 de agosto de 1985',
         'Escala del Bono de Antigüedad según años de servicio (Art. 60)'),
        ('Decreto Supremo N° 229', '11 de diciembre de 1944',
         'Aguinaldo de Navidad proporcional y multa 100% por pago tardío'),
        ('Decreto Supremo N° 1592', '19 de abril de 1949',
         'Salario devengado proporcional por días trabajados (Art. 2)'),
    ]
    normas_data = [[
        Paragraph('<b>Norma</b>',
            estilo('nh', fontName='Helvetica-Bold', fontSize=7.5, textColor=WHITE)),
        Paragraph('<b>Fecha / Decreto</b>',
            estilo('nh2', fontName='Helvetica-Bold', fontSize=7.5, textColor=WHITE)),
        Paragraph('<b>Conceptos que regula</b>',
            estilo('nh3', fontName='Helvetica-Bold', fontSize=7.5, textColor=WHITE)),
    ]]
    for i, (norma, fecha, concepto) in enumerate(normas):
        normas_data.append([
            Paragraph(norma,
                estilo(f'nn{i}', fontName='Helvetica-Bold', fontSize=7.5, textColor=NAVY)),
            Paragraph(fecha,
                estilo(f'nf{i}', fontSize=7.5, textColor=GREY)),
            Paragraph(concepto,
                estilo(f'nc{i}', fontSize=7.5, leading=10)),
        ])
    t_normas = Table(normas_data, colWidths=[5*cm, 3*cm, W-8*cm])
    t_normas.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), BLUE),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [WHITE, BGROW]),
        ('BOX',           (0,0), (-1,-1), 0.5, colors.HexColor('#c8d4f0')),
        ('INNERGRID',     (0,0), (-1,-1), 0.3, LIGHT),
        ('TOPPADDING',    (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ('RIGHTPADDING',  (0,0), (-1,-1), 8),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]))
    historia.append(t_normas)
    historia.append(Spacer(1, 0.5*cm))

    # ══════════════════════════════════════════════════════════
    # 7. FIRMAS
    # ══════════════════════════════════════════════════════════
    t_firma = Table([
        [Paragraph('_' * 32, s_normal), Paragraph('_' * 32, s_normal)],
        [
            Paragraph('Firma del Trabajador',
                estilo('fl', fontSize=8, textColor=GREY, alignment=TA_CENTER)),
            Paragraph('Firma y Sello del Empleador',
                estilo('fe', fontSize=8, textColor=GREY, alignment=TA_CENTER)),
        ],
        [
            Paragraph(datos.get('trabajador', ''),
                estilo('fln', fontSize=8, fontName='Helvetica-Bold', alignment=TA_CENTER)),
            Paragraph(datos.get('empleador', ''),
                estilo('fen', fontSize=8, fontName='Helvetica-Bold', alignment=TA_CENTER)),
        ],
    ], colWidths=[W/2, W/2])
    t_firma.setStyle(TableStyle([
        ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING',    (0,0), (-1,0),  20),
        ('TOPPADDING',    (0,1), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    historia.append(KeepTogether([
        HRFlowable(width=W, thickness=0.5, color=LIGHT),
        Spacer(1, 0.3*cm),
        t_firma,
        Spacer(1, 0.5*cm),
    ]))

    # ══════════════════════════════════════════════════════════
    # 8. DISCLAIMER
    # ══════════════════════════════════════════════════════════
    t_disclaimer = Table([[
        Paragraph(
            '<b>ADVERTENCIA LEGAL OBLIGATORIA:</b> '
            'El presente documento constituye una ESTIMACIÓN REFERENCIAL del prefiniquito '
            'laboral, elaborado con base en la Ley General del Trabajo y los Decretos Supremos '
            'vigentes en Bolivia. NO constituye asesoría jurídica vinculante ni reemplaza una '
            'resolución judicial o administrativa. Los montos pueden variar según circunstancias '
            'específicas, convenios colectivos o resoluciones del Ministerio de Trabajo. '
            'LexNova no asume responsabilidad por decisiones tomadas exclusivamente en base a '
            'esta estimación. Consulte con un abogado laboralista habilitado.',
            estilo('disc', fontName='Helvetica-Oblique', fontSize=7,
                   textColor=colors.HexColor('#78350f'), leading=10, alignment=TA_JUSTIFY)
        )
    ]], colWidths=[W])
    t_disclaimer.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), colors.HexColor('#fffbeb')),
        ('BOX',           (0,0), (-1,-1), 1, GOLD),
        ('LEFTPADDING',   (0,0), (-1,-1), 12),
        ('RIGHTPADDING',  (0,0), (-1,-1), 12),
        ('TOPPADDING',    (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    historia.append(t_disclaimer)
    historia.append(Spacer(1, 0.3*cm))
    historia.append(Paragraph(
        f'Emitido el {fecha_emision} · LexNova Sistema Jurídico Digital · Bolivia',
        estilo('pie', fontSize=7, textColor=GREY, alignment=TA_CENTER)
    ))

    doc.build(historia)
    buf.seek(0)
    return buf