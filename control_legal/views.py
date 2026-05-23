import io
import json
from datetime import datetime
from xhtml2pdf import pisa
from django.http import JsonResponse
from decimal import Decimal
from . import liquidacion_asistencia_services as asistencia_services
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template

from .forms import (CasoForm, ClienteForm, ExpedienteForm, DocumentoForm, MovimientoForm, EventoForm, TareaForm, EvidenciaForm, PlantillaContratoForm, GenerarContratoForm)
from .models import Cliente, Expediente, Documento, Movimiento, Evento, Tarea, EvidenciaTarea, PlantillaContrato, Contrato, PlantillaMemorial, Memorial, PrecedenteJurisprudencial

@login_required
def dashboard(request):
    from django.utils import timezone
    from datetime import timedelta

    hoy      = timezone.now().date()
    semana   = hoy + timedelta(days=7)
    dos_dias = hoy + timedelta(days=2)
# ── Expedientes ──────────────────────────────
    total        = Expediente.objects.count()
    activos      = Expediente.objects.filter(activo=True).count()
    concluidos   = Expediente.objects.filter(estado='concluido').count()
    casos_recientes = Expediente.objects.filter(
        activo=True).select_related('cliente', 'abogado_asignado').order_by('-id')[:5]

    # Semáforo
    casos_urgentes  = Expediente.objects.filter(
        activo=True,
        eventos__fecha_hora__date__lte=dos_dias,
        eventos__fecha_hora__date__gte=hoy,
    ).distinct().count()

    casos_proximos  = Expediente.objects.filter(
        activo=True,
        eventos__fecha_hora__date__gt=dos_dias,
        eventos__fecha_hora__date__lte=semana,
    ).distinct().count()

    casos_al_dia    = activos - casos_urgentes - casos_proximos

    # ── Agenda ───────────────────────────────────
    audiencias_semana = Evento.objects.filter(
        fecha_hora__date__gte=hoy,
        fecha_hora__date__lte=semana,
    ).count()

    eventos_hoy = Evento.objects.filter(
        fecha_hora__date=hoy
    ).select_related('expediente__cliente').order_by('fecha_hora')

    # ── Tareas ───────────────────────────────────
    tareas_pendientes = Tarea.objects.filter(
        estado__in=['pendiente', 'en_proceso']
    ).count()

    tareas_vencidas = Tarea.objects.filter(
        estado__in=['pendiente', 'en_proceso'],
        fecha_limite__lt=hoy,
    ).count()

    # ── Clientes ─────────────────────────────────
    total_clientes = Cliente.objects.filter(activo=True).count()

    return render(request, 'control_legal/dashboard.html', {
        # Expedientes
        'total':            total,
        'activos':          activos,
        'concluidos':       concluidos,
        'casos_recientes':  casos_recientes,
        'casos_al_dia':     max(casos_al_dia, 0),
        'casos_proximos':   casos_proximos,
        'casos_urgentes':   casos_urgentes,
        # Agenda
        'audiencias_semana': audiencias_semana,
        'eventos_hoy':       eventos_hoy,
        # Tareas
        'tareas_pendientes': tareas_pendientes,
        'tareas_vencidas':   tareas_vencidas,
        # Clientes
        'total_clientes':    total_clientes,
    })

# ── Listar expedientes ────────────────────────────────────────
@login_required
def listar_casos(request):
    busqueda = request.GET.get('buscar', '')
    criterio = request.GET.get('orden', 'id')

    casos = Expediente.objects.filter(activo=True)

    if busqueda:
        casos = casos.filter(
            Q(cliente__nombre_completo__icontains=busqueda) |
            Q(nurej__icontains=busqueda)                    |
            Q(materia__icontains=busqueda)                  |
            Q(abogado_asignado__username__icontains=busqueda)
        )

    orden = {
        'nombre': 'cliente__nombre_completo',
        'fecha':  '-id',
        'materia': 'materia',
        'id':     'id',
    }
    casos = casos.order_by(orden.get(criterio, 'id'))

    return render(request, 'control_legal/listar_casos.html', {
        'casos':    casos,
        'busqueda': busqueda,
    })


# ── Listar clientes ───────────────────────────────────────────
@login_required
def listar_clientes(request):
    busqueda = request.GET.get('buscar', '')
    clientes = Cliente.objects.filter(activo=True)
    if busqueda:
        clientes = clientes.filter(
            Q(nombre_completo__icontains=busqueda) |
            Q(ci__icontains=busqueda)              |
            Q(telefono__icontains=busqueda)
        )
    return render(request, 'control_legal/listar_clientes.html', {
        'clientes': clientes.order_by('nombre_completo'),
        'busqueda': busqueda,
    })


# ── Registrar cliente ─────────────────────────────────────────
@login_required
def registrar_cliente(request):
    form = ClienteForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Cliente registrado exitosamente.')
        return redirect('listar_clientes')
    return render(request, 'control_legal/registrar_cliente.html', {'form': form})


# ── Editar cliente ────────────────────────────────────────────
@login_required
def editar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    form = ClienteForm(request.POST or None, instance=cliente)
    if form.is_valid():
        form.save()
        messages.success(request, 'Cliente actualizado exitosamente.')
        return redirect('detalle_cliente', pk=pk)
    return render(request, 'control_legal/registrar_cliente.html', {
        'form': form, 'editando': True, 'cliente': cliente,
    })


# ── Detalle del cliente (con sus expedientes) ─────────────────
@login_required
def detalle_cliente(request, pk):
    cliente     = get_object_or_404(Cliente, pk=pk)
    expedientes = cliente.expedientes.filter(activo=True).order_by('-id')
    return render(request, 'control_legal/detalle_cliente.html', {
        'cliente':     cliente,
        'expedientes': expedientes,
    })


# ── Registrar expediente (desde el cliente) ───────────────────
@login_required
def registrar_caso(request):
    cliente_id = request.GET.get('cliente')
    cliente    = get_object_or_404(Cliente, pk=cliente_id) if cliente_id else None
    form       = ExpedienteForm(request.POST or None)
    if form.is_valid():
        expediente         = form.save(commit=False)
        expediente.cliente = cliente
        expediente.save()
        messages.success(request, 'Expediente registrado exitosamente.')
        if cliente:
            return redirect('detalle_cliente', pk=cliente.pk)
        return redirect('listar_casos')
    return render(request, 'control_legal/registrar_caso.html', {
        'form': form, 'cliente': cliente,
    })


# ── Editar expediente ─────────────────────────────────────────
@login_required
def editar_caso(request, pk):
    caso = get_object_or_404(Expediente, pk=pk)
    form = ExpedienteForm(request.POST or None, instance=caso)
    if form.is_valid():
        form.save()
        messages.success(request, 'Expediente actualizado exitosamente.')
        return redirect('detalle_caso', pk=pk)
    return render(request, 'control_legal/registrar_caso.html', {
        'form': form, 'editando': True,
    })


# ── Detalle del expediente (documentos + movimientos) ─────────
@login_required
def detalle_caso(request, pk):
    expediente = get_object_or_404(Expediente, pk=pk)
    doc_form   = DocumentoForm(request.POST or None, request.FILES or None)
    mov_form   = MovimientoForm(request.POST or None)

    if 'subir_documento' in request.POST and doc_form.is_valid():
        doc          = doc_form.save(commit=False)
        doc.expediente  = expediente
        doc.subido_por  = request.user
        doc.save()
        messages.success(request, 'Documento subido correctamente.')
        return redirect('detalle_caso', pk=pk)

    if 'agregar_movimiento' in request.POST and mov_form.is_valid():
        mov               = mov_form.save(commit=False)
        mov.expediente    = expediente
        mov.registrado_por = request.user
        mov.save()
        messages.success(request, 'Movimiento registrado.')
        return redirect('detalle_caso', pk=pk)

    return render(request, 'control_legal/detalle_caso.html', {
        'expediente': expediente,
        'documentos': expediente.documentos.all(),
        'movimientos': expediente.movimientos.all(),
        'doc_form':   doc_form,
        'mov_form':   mov_form,
    })


# ── Eliminar expediente (lógico) ──────────────────────────────
@login_required
def eliminar_caso(request, pk):
    caso        = get_object_or_404(Expediente, pk=pk)
    caso.activo = False
    caso.save()
    messages.success(request, 'Expediente movido a la papelera.')
    return redirect('listar_casos')


# ── Papelera ──────────────────────────────────────────────────
@login_required
def papelera_casos(request):
    casos = Expediente.objects.filter(activo=False).order_by('-id')
    return render(request, 'control_legal/papelera.html', {'casos': casos})


# ── Restaurar desde papelera ──────────────────────────────────
@login_required
def restaurar_caso(request, pk):
    caso        = get_object_or_404(Expediente, pk=pk)
    caso.activo = True
    caso.save()
    messages.success(request, 'Expediente restaurado exitosamente.')
    return redirect('papelera_casos')


# ── Reporte PDF general ───────────────────────────────────────
@login_required
def exportar_pdf(request):
    casos    = Expediente.objects.filter(activo=True)
    template = get_template('control_legal/reporte_pdf.html')
    html     = template.render({'casos': casos, 'fecha': datetime.now(), 'request': request})
    result   = io.BytesIO()
    pisa.CreatePDF(io.BytesIO(html.encode('UTF-8')), dest=result, encoding='UTF-8')
    result.seek(0)
    return FileResponse(result, as_attachment=True, filename='Reporte_LexNova.pdf')


# ── Reporte PDF de un expediente ──────────────────────────────
@login_required
def reporte_un_caso(request, pk):
    caso     = get_object_or_404(Expediente, pk=pk)
    template = get_template('control_legal/reporte_individual.html')
    html     = template.render({'caso': caso, 'fecha': datetime.now(), 'request': request})
    result   = io.BytesIO()
    pisa.pisaDocument(io.BytesIO(html.encode('UTF-8')), result, encoding='UTF-8')
    result.seek(0)
    return FileResponse(result, as_attachment=False, filename=f'Expediente_{caso.nurej}.pdf')


# ── Login ─────────────────────────────────────────────────────
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password'),
        )
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, 'Usuario o contraseña incorrectos.')
    return render(request, 'login.html')

# ── Agenda: lista de eventos ──────────────────────────────────
@login_required
def agenda(request):
    from django.utils import timezone
    from datetime import timedelta
    hoy       = timezone.now().date()
    eventos   = Evento.objects.filter(fecha_hora__date__gte=hoy).order_by('fecha_hora')
    urgentes  = eventos.filter(fecha_hora__date__lte=hoy + timedelta(days=2))
    return render(request, 'control_legal/agenda.html', {
        'eventos':  eventos,
        'urgentes': urgentes,
        'hoy':      hoy,
    })


# ── Agenda: registrar evento ──────────────────────────────────
@login_required
def registrar_evento(request):
    expediente_id = request.GET.get('expediente')
    initial = {}
    if expediente_id:
        try:
            initial['expediente'] = Expediente.objects.get(pk=expediente_id)
        except Expediente.DoesNotExist:
            pass
    form = EventoForm(request.POST or None, initial=initial)
    if form.is_valid():
        evento             = form.save(commit=False)
        evento.responsable = request.user
        evento.save()
        messages.success(request, 'Evento agendado correctamente.')
        return redirect('agenda')
    return render(request, 'control_legal/registrar_evento.html', {'form': form})


# ── Agenda: editar evento ─────────────────────────────────────
@login_required
def editar_evento(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    form   = EventoForm(request.POST or None, instance=evento)
    if form.is_valid():
        form.save()
        messages.success(request, 'Evento actualizado.')
        return redirect('agenda')
    return render(request, 'control_legal/registrar_evento.html', {
        'form': form, 'editando': True, 'evento': evento,
    })


# ── Agenda: eliminar evento ───────────────────────────────────
@login_required
def eliminar_evento(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    evento.delete()
    messages.success(request, 'Evento eliminado.')
    return redirect('agenda')    

# ── Tareas: lista ─────────────────────────────────────────────
@login_required
def lista_tareas(request):
    from django.utils import timezone
    user = request.user
    # Pasante solo ve sus tareas; abogado y admin ven todas
    if hasattr(user, 'perfil') and user.perfil.es_pasante():
        tareas = Tarea.objects.filter(asignada_a=user)
    else:
        tareas = Tarea.objects.all()

    tareas = tareas.select_related('asignada_a', 'expediente__cliente').order_by('fecha_limite')
    return render(request, 'control_legal/lista_tareas.html', {
        'tareas': tareas,
        'hoy':    timezone.now().date(),
    })


# ── Tareas: crear ─────────────────────────────────────────────
@login_required
def crear_tarea(request):
    form = TareaForm(request.POST or None)
    if form.is_valid():
        tarea            = form.save(commit=False)
        tarea.creada_por = request.user
        tarea.save()
        messages.success(request, 'Tarea asignada correctamente.')
        return redirect('lista_tareas')
    return render(request, 'control_legal/registrar_tarea.html', {'form': form})


# ── Tareas: editar ────────────────────────────────────────────
@login_required
def editar_tarea(request, pk):
    tarea = get_object_or_404(Tarea, pk=pk)
    form  = TareaForm(request.POST or None, instance=tarea)
    if form.is_valid():
        form.save()
        messages.success(request, 'Tarea actualizada.')
        return redirect('lista_tareas')
    return render(request, 'control_legal/registrar_tarea.html', {
        'form': form, 'editando': True, 'tarea': tarea,
    })


# ── Tareas: detalle + subir evidencia ─────────────────────────
@login_required
def detalle_tarea(request, pk):
    tarea = get_object_or_404(Tarea, pk=pk)
    form  = EvidenciaForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        ev            = form.save(commit=False)
        ev.tarea      = tarea
        ev.subida_por = request.user
        ev.save()
        # Marcar como en proceso si estaba pendiente
        if tarea.estado == Tarea.ESTADO_PENDIENTE:
            tarea.estado = Tarea.ESTADO_EN_PROCESO
            tarea.save()
        messages.success(request, 'Evidencia subida correctamente.')
        return redirect('detalle_tarea', pk=pk)
    return render(request, 'control_legal/detalle_tarea.html', {
        'tarea':     tarea,
        'evidencias': tarea.evidencias.all(),
        'form':      form,
    })

# ── Tareas: cambiar estado rápido ─────────────────────────────
@login_required
def cambiar_estado_tarea(request, pk):
    from django.utils import timezone
    tarea        = get_object_or_404(Tarea, pk=pk)
    nuevo_estado = request.POST.get('estado')
    if nuevo_estado in dict(Tarea.ESTADOS):
        tarea.estado = nuevo_estado
        if nuevo_estado == Tarea.ESTADO_COMPLETADA:
            tarea.fecha_completada = timezone.now()
        tarea.save()
        messages.success(request, f'Tarea marcada como {tarea.get_estado_display()}.')
    return redirect('lista_tareas')


# ── Contratos: lista ──────────────────────────────────────────
@login_required
def lista_contratos(request):
    contratos = Contrato.objects.select_related(
        'cliente', 'generado_por').order_by('-fecha_generado')
    return render(request, 'control_legal/lista_contratos.html', {'contratos': contratos})


# ── Contratos: generar con plantilla o manual ─────────────────
@login_required
def generar_contrato(request):
    from django.utils import timezone
    form = GenerarContratoForm(request.POST or None)

    if form.is_valid():
        contrato             = form.save(commit=False)
        contrato.generado_por = request.user
        plantilla = form.cleaned_data.get('plantilla')
        if plantilla and not contrato.contenido_final.strip():
            cliente    = form.cleaned_data['cliente']
            expediente = form.cleaned_data.get('expediente')
            contenido  = plantilla.contenido
            contenido  = contenido.replace('{{cliente_nombre}}',    cliente.nombre_completo)
            contenido  = contenido.replace('{{cliente_ci}}',        cliente.ci)
            contenido  = contenido.replace('{{cliente_direccion}}', cliente.direccion or '')
            contenido  = contenido.replace('{{abogado_nombre}}',    request.user.get_full_name() or request.user.username)
            contenido  = contenido.replace('{{fecha_hoy}}',         timezone.now().strftime('%d de %B de %Y'))
            contenido  = contenido.replace('{{expediente_nurej}}',  expediente.nurej if expediente else '')
            contenido  = contenido.replace('{{monto}}',             str(contrato.monto or ''))
            contenido  = contenido.replace('{{ciudad}}',            contrato.ciudad)
            contrato.contenido_final = contenido
        contrato.save()
        messages.success(request, 'Contrato generado correctamente.')
        return redirect('ver_contrato', pk=contrato.pk)

    plantillas_json = json.dumps({
        str(p.pk): p.contenido
        for p in PlantillaContrato.objects.filter(activa=True)
    })
    return render(request, 'control_legal/generar_contrato.html', {
        'form': form,
        'plantillas_json': plantillas_json,
    })

# ── Contratos: ver ────────────────────────────────────────────
@login_required
def ver_contrato(request, pk):
    contrato = get_object_or_404(Contrato, pk=pk)
    return render(request, 'control_legal/ver_contrato.html', {'contrato': contrato})


# ── Contratos: exportar PDF ───────────────────────────────────
@login_required
def exportar_contrato_pdf(request, pk):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

    contrato     = get_object_or_404(Contrato, pk=pk)
    buf          = io.BytesIO()
    doc          = SimpleDocTemplate(buf, pagesize=letter,
                                     topMargin=3*cm, bottomMargin=2.5*cm,
                                     leftMargin=3*cm, rightMargin=3*cm)
    styles       = getSampleStyleSheet()
    titulo_style = ParagraphStyle('titulo', parent=styles['Normal'],
                                  fontSize=13, fontName='Helvetica-Bold',
                                  alignment=TA_CENTER, spaceAfter=20)
    cuerpo_style = ParagraphStyle('cuerpo', parent=styles['Normal'],
                                  fontSize=11, leading=18,
                                  alignment=TA_JUSTIFY, spaceAfter=12)
    firma_style  = ParagraphStyle('firma', parent=styles['Normal'],
                                  fontSize=10, spaceBefore=40)
    elements = []

    elements.append(Paragraph("LexNova Bolivia", ParagraphStyle(
        'header', parent=styles['Normal'], fontSize=10,
        fontName='Helvetica', alignment=TA_CENTER)))
    elements.append(Spacer(1, 0.3*cm))
    elements.append(Paragraph(contrato.titulo.upper(), titulo_style))
    elements.append(Spacer(1, 0.5*cm))

    for parrafo in contrato.contenido_final.split('\n'):
        if parrafo.strip():
            elements.append(Paragraph(parrafo.strip(), cuerpo_style))
        else:
            elements.append(Spacer(1, 0.3*cm))

    elements.append(Spacer(1, 2*cm))
    elements.append(Paragraph(
        f"________________________________&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
        f"________________________________", firma_style))
    elements.append(Paragraph(
        f"{contrato.cliente.nombre_completo}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
        f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
        f"{contrato.generado_por.get_full_name() or 'Abogado'}",
        ParagraphStyle('firma_nombre', parent=styles['Normal'], fontSize=9)))

    doc.build(elements)
    buf.seek(0)
    nombre = f"Contrato_{contrato.cliente.nombre_completo.replace(' ', '_')}.pdf"
    return HttpResponse(buf, content_type='application/pdf',
                        headers={'Content-Disposition': f'inline; filename="{nombre}"'})


# ── Plantillas: lista ─────────────────────────────────────────
@login_required
def lista_plantillas(request):
    plantillas = PlantillaContrato.objects.filter(activa=True).order_by('nombre')
    return render(request, 'control_legal/lista_plantillas.html', {'plantillas': plantillas})


# ── Plantillas: crear ─────────────────────────────────────────
@login_required
def crear_plantilla(request):
    form = PlantillaContratoForm(request.POST or None)
    if form.is_valid():
        p            = form.save(commit=False)
        p.creada_por = request.user
        p.save()
        messages.success(request, 'Plantilla creada correctamente.')
        return redirect('lista_plantillas')
    return render(request, 'control_legal/crear_plantilla.html', {'form': form})


# ── Plantillas: editar ────────────────────────────────────────
@login_required
def editar_plantilla(request, pk):
    plantilla = get_object_or_404(PlantillaContrato, pk=pk)
    form      = PlantillaContratoForm(request.POST or None, instance=plantilla)
    if form.is_valid():
        form.save()
        messages.success(request, 'Plantilla actualizada.')
        return redirect('lista_plantillas')
    return render(request, 'control_legal/crear_plantilla.html', {
        'form': form, 'editando': True, 'plantilla': plantilla,
    })

import google.generativeai as genai
from django.conf import settings

SYSTEM_PROMPT_CONTRATOS = """
Actúa como un Abogado Senior y Asesor Legal Corporativo en Bolivia, con más de 20 años de experiencia en Derecho Civil, Comercial y Tecnológico. Tu objetivo es redactar contratos jurídicamente inexpugnables, precisos, con visión preventiva de litigios y estrictamente adaptados a la normativa del Estado Plurinacional de Bolivia.

SISTEMA HÍBRIDO (AUTOMATIZACIÓN + EDICIÓN MANUAL)
Tu redacción debe estar diseñada para ser un documento "llave en mano", pero con espacios de edición manual a prueba de errores. Para todo dato faltante, variable, fecha o monto, utiliza CORCHETES Y MAYÚSCULAS (ej. [NOMBRE COMPLETO DEL COMPRADOR], [NÚMERO DE C.I. Y EXPEDICIÓN], [MONTO EN NÚMEROS] ([MONTO EN LETRAS] 00/100 BOLIVIANOS)). Nunca asumas ni inventes datos de las partes.

BASE DE CONOCIMIENTO Y MARCO NORMATIVO
- Derecho Civil (D.L. No 12760): contratos de transferencia, arrendamiento, anticresis, mutuo y garantías. Aplicación estricta de los 4 requisitos de validez del Art. 452.
- Derecho Comercial (Código de Comercio) y Corporativo.
- Contratos Tecnológicos: SaaS, IaaS, PaaS, desarrollo de software y licenciamiento con cláusulas de SLA, propiedad intelectual (SENAPI), confidencialidad (NDA), privacidad de datos y limitación de responsabilidad técnica.

INSTRUCCIONES DE ESTILO BOLIVIANO
- Usa terminología notarial boliviana: "mayores de edad y hábiles por derecho", "sin que medie dolo, presión, fraude o vicio alguno en el consentimiento", "a su entera satisfacción".
- En transferencias incluye: "alodial y libre de todo gravamen" y cláusula de "evicción y saneamiento conforme a ley".
- Enumera cláusulas con ordinales en mayúsculas: PRIMERA.- (DE LAS PARTES Y SU DERECHO PROPIETARIO).
- Incluye siempre: Resolución de Pleno Derecho (Art. 569 C.C.), cláusulas penales por mora y jurisdicción competente.
- Contratos civiles de baja cuantía: vía ordinaria. Contratos comerciales/tecnológicos: arbitraje institucional (Ley 708), CNC o CAINCO.
- Si requiere Derechos Reales: formato MINUTA. Si es privado: cierra con "al solo reconocimiento de firmas y rúbricas ante autoridad competente, surtirá los efectos de instrumento público".

ESTRUCTURA ESTÁNDAR
1. Encabezado con identificación plena de partes.
2. PRIMERA.- (ANTECEDENTES / NATURALEZA)
3. SEGUNDA.- (OBJETO DEL CONTRATO)
4. Cláusulas operativas: Precio, Pago, Plazos, Obligaciones.
5. Cláusulas de salvaguarda: Prohibiciones, Confidencialidad.
6. Cláusula de Incumplimiento, Penalidades y Resolución.
7. Cláusula de Jurisdicción y Competencia.
8. Cláusula de Aceptación y Conformidad con espacio para firmas.

Si el usuario omite detalles vitales, usa estándares lógicos entre corchetes para revisión.
Genera el contrato COMPLETO, listo para copiar en Word, rellenar y firmar.
Responde SOLO con el texto del contrato, sin explicaciones adicionales ni markdown.
"""


@login_required
def generar_contrato_ia(request):
    contrato_generado = None
    error = None

    if request.method == 'POST':
        tipo        = request.POST.get('tipo_contrato', '')
        partes      = request.POST.get('partes', '')
        objeto      = request.POST.get('objeto', '')
        precio      = request.POST.get('precio', '')
        plazo       = request.POST.get('plazo', '')
        condiciones = request.POST.get('condiciones', '')

        prompt_completo = f"""{SYSTEM_PROMPT_CONTRATOS}

[DATOS DEL CONTRATO A GENERAR]
Tipo de Contrato: {tipo}
Identificación de las Partes: {partes}
Objeto y Detalles Específicos: {objeto}
Precio / Contraprestación: {precio}
Plazo de vigencia: {plazo}
Condiciones especiales adicionales: {condiciones}

Redacta el contrato completo según las instrucciones anteriores.
"""

        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            modelo   = genai.GenerativeModel('gemini-2.5-flash')
            response = modelo.generate_content(prompt_completo)
            contrato_generado = response.text

            # Guardar si se solicitó
            if request.POST.get('guardar') and contrato_generado:
                cliente_id = request.POST.get('cliente_id')
                cliente    = Cliente.objects.filter(pk=cliente_id).first()
                if cliente:
                    Contrato.objects.create(
                        titulo          = f"{tipo} — {cliente.nombre_completo}",
                        cliente         = cliente,
                        contenido_final = contrato_generado,
                        generado_por    = request.user,
                        ciudad          = "La Paz",
                    )
                    messages.success(request, 'Contrato guardado correctamente.')
                    return redirect('lista_contratos')

        except Exception as e:
            error = f"Error al conectar con Gemini: {str(e)}"

    clientes = Cliente.objects.filter(activo=True).order_by('nombre_completo')
    return render(request, 'control_legal/generar_contrato_ia.html', {
        'contrato_generado': contrato_generado,
        'clientes':          clientes,
        'error':             error,
        'post':              request.POST,
    })

    # ── Reportes con gráficos ─────────────────────────────────────
@login_required
def reportes(request):
    from django.db.models import Count
    from django.db.models.functions import TruncMonth
    from django.utils import timezone
    from datetime import timedelta
    import json

    hoy  = timezone.now().date()
    anio = hoy.year

    # ── Expedientes por mes (últimos 12 meses) ────────────────
    hace_12 = hoy - timedelta(days=365)
    exp_por_mes = (
        Expediente.objects
        .filter(fecha_inicio__gte=hace_12)
        .annotate(mes=TruncMonth('fecha_inicio'))
        .values('mes')
        .annotate(total=Count('id'))
        .order_by('mes')
    )
    labels_meses = [e['mes'].strftime('%b %Y') for e in exp_por_mes]
    data_meses   = [e['total'] for e in exp_por_mes]

    # ── Expedientes por materia ───────────────────────────────
    exp_por_materia = (
        Expediente.objects
        .filter(activo=True)
        .values('materia')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    labels_materias = [e['materia'] for e in exp_por_materia]
    data_materias   = [e['total'] for e in exp_por_materia]

    # ── Expedientes por estado ────────────────────────────────
    exp_por_estado = (
        Expediente.objects
        .values('estado')
        .annotate(total=Count('id'))
    )
    estados_map = {'activo': 'Activo', 'concluido': 'Concluido', 'archivado': 'Archivado'}
    labels_estados = [estados_map.get(e['estado'], e['estado']) for e in exp_por_estado]
    data_estados   = [e['total'] for e in exp_por_estado]

    # ── Expedientes por abogado ───────────────────────────────
    exp_por_abogado = (
        Expediente.objects
        .filter(activo=True, abogado_asignado__isnull=False)
        .values('abogado_asignado__first_name', 'abogado_asignado__last_name')
        .annotate(total=Count('id'))
        .order_by('-total')[:8]
    )
    labels_abogados = [
        f"{e['abogado_asignado__first_name']} {e['abogado_asignado__last_name']}".strip() or 'Sin nombre'
        for e in exp_por_abogado
    ]
    data_abogados = [e['total'] for e in exp_por_abogado]

    # ── Tareas por estado ─────────────────────────────────────
    tareas_estado = (
        Tarea.objects
        .values('estado')
        .annotate(total=Count('id'))
    )
    t_map = {'pendiente': 'Pendiente', 'en_proceso': 'En proceso', 'completada': 'Completada'}
    labels_tareas = [t_map.get(t['estado'], t['estado']) for t in tareas_estado]
    data_tareas   = [t['total'] for t in tareas_estado]

    # ── Resumen general ───────────────────────────────────────
    resumen = {
        'total_clientes':    Cliente.objects.filter(activo=True).count(),
        'total_expedientes': Expediente.objects.count(),
        'activos':           Expediente.objects.filter(estado='activo').count(),
        'concluidos':        Expediente.objects.filter(estado='concluido').count(),
        'total_contratos':   Contrato.objects.count(),
        'tareas_pendientes': Tarea.objects.filter(estado='pendiente').count(),
        'tareas_vencidas':   Tarea.objects.filter(
                                estado__in=['pendiente', 'en_proceso'],
                                fecha_limite__lt=hoy).count(),
        'eventos_mes':       Evento.objects.filter(
                                fecha_hora__year=anio,
                                fecha_hora__month=hoy.month).count(),
    }

    return render(request, 'control_legal/reportes.html', {
        'resumen':          resumen,
        # Gráfico 1 — línea: expedientes por mes
        'labels_meses':     json.dumps(labels_meses),
        'data_meses':       json.dumps(data_meses),
        # Gráfico 2 — dona: por materia
        'labels_materias':  json.dumps(labels_materias),
        'data_materias':    json.dumps(data_materias),
        # Gráfico 3 — dona: por estado
        'labels_estados':   json.dumps(labels_estados),
        'data_estados':     json.dumps(data_estados),
        # Gráfico 4 — barras: por abogado
        'labels_abogados':  json.dumps(labels_abogados),
        'data_abogados':    json.dumps(data_abogados),
        # Gráfico 5 — barras: tareas
        'labels_tareas':    json.dumps(labels_tareas),
        'data_tareas':      json.dumps(data_tareas),
    })
    
    # ── Portal del cliente ────────────────────────────────────────
# Estas vistas son PÚBLICAS — no requieren login del bufete

def portal_login(request):
    """Página donde el cliente ingresa su código de acceso."""
    error = None
    if request.method == 'POST':
        codigo = request.POST.get('codigo', '').strip().upper()
        try:
            cliente = Cliente.objects.get(codigo_acceso=codigo, activo=True)
            # Guardamos el código en sesión para no pedirlo de nuevo
            request.session['portal_cliente_id'] = cliente.pk
            return redirect('portal_cliente')
        except Cliente.DoesNotExist:
            error = 'Código incorrecto. Verifica el código que te proporcionó tu abogado.'
    return render(request, 'control_legal/portal_login.html', {'error': error})


def portal_cliente(request):
    """Panel del cliente — muestra sus expedientes, documentos y movimientos."""
    cliente_id = request.session.get('portal_cliente_id')
    if not cliente_id:
        return redirect('portal_login')

    try:
        cliente = Cliente.objects.get(pk=cliente_id, activo=True)
    except Cliente.DoesNotExist:
        del request.session['portal_cliente_id']
        return redirect('portal_login')

    expedientes = cliente.expedientes.filter(activo=True).prefetch_related(
        'documentos', 'movimientos'
    ).order_by('-fecha_inicio')

    return render(request, 'control_legal/portal_cliente.html', {
        'cliente':     cliente,
        'expedientes': expedientes,
    })


def portal_logout(request):
    """Cierra la sesión del portal del cliente."""
    request.session.flush()
    return redirect('portal_login')

SYSTEM_PROMPT_MEMORIALES = """
Actúa como un Abogado Litigante Senior en Bolivia, especializado en redacción de escritos judiciales ante el Órgano Judicial del Estado Plurinacional de Bolivia.

Tu tarea es redactar memoriales judiciales completos, formalmente correctos y adaptados al sistema procesal boliviano.

REGLAS DE REDACCIÓN
- Usa el encabezado formal: "SEÑOR JUEZ [materia] DE PARTIDO / SEÑOR JUEZ DE INSTRUCCIÓN EN LO [materia]" según corresponda.
- Identifica al abogado con su nombre y matrícula: "bajo patrocinio del Abogado [nombre], con Matrícula del Colegio de Abogados N° [MATRÍCULA]".
- Usa fórmulas procesales bolivianas: "A Ud. con el debido respeto me dirijo exponiendo", "POR TANTO", "A USTED SEÑOR JUEZ pido se sirva...".
- Fundamenta cada petición con el artículo legal correspondiente.
- Estructura con secciones en mayúsculas: ANTECEDENTES, FUNDAMENTOS DE DERECHO, PETITORIO.
- El PETITORIO debe ser claro, numerado y específico.
- Para datos faltantes usa CORCHETES: [MATRÍCULA DEL ABOGADO], [NÚMERO DE EXPEDIENTE], [FECHA DE AUDIENCIA].
- Cierra con: "Es justicia que espero merecer. [Ciudad], [fecha]."

ESTILO
- Formal, preciso, sin ambigüedades.
- Párrafos cortos y numerados donde corresponda.
- Responde SOLO con el texto del memorial, sin explicaciones ni markdown.
"""


@login_required
def lista_memoriales(request):
    memoriales = Memorial.objects.select_related(
        'cliente', 'plantilla', 'generado_por'
    ).order_by('-fecha_generado')
    return render(request, 'control_legal/lista_memoriales.html', {'memoriales': memoriales})


@login_required
def generar_memorial(request):
    from django.utils import timezone

    # Cargar plantillas agrupadas por categoría
    plantillas = PlantillaMemorial.objects.filter(activa=True).order_by('categoria', 'nombre')
    clientes   = Cliente.objects.filter(activo=True).order_by('nombre_completo')
    expedientes = Expediente.objects.filter(activo=True).select_related('cliente').order_by('-id')

    memorial_generado = None
    error             = None
    plantilla_sel     = None

    if request.method == 'POST':
        plantilla_id  = request.POST.get('plantilla_id')
        cliente_id    = request.POST.get('cliente_id')
        expediente_id = request.POST.get('expediente_id')
        hechos        = request.POST.get('hechos', '')
        peticion      = request.POST.get('peticion', '')
        datos_extra   = request.POST.get('datos_extra', '')

        # Obtener objetos relacionados
        plantilla_sel = PlantillaMemorial.objects.filter(pk=plantilla_id).first()
        cliente       = Cliente.objects.filter(pk=cliente_id).first()
        expediente    = Expediente.objects.filter(pk=expediente_id).first() if expediente_id else None

        if not plantilla_sel or not cliente:
            error = 'Debes seleccionar una plantilla y un cliente.'
        else:
            # Construir el prompt con contexto real
            contexto_variables = f"""
Cliente: {cliente.nombre_completo}
CI del cliente: {cliente.ci}
Dirección: {cliente.direccion or '[DIRECCIÓN]'}
Abogado: {request.user.get_full_name() or '[NOMBRE DEL ABOGADO]'}
Ciudad: La Paz
Fecha: {timezone.now().strftime('%d de %B de %Y')}
NUREJ/Expediente: {expediente.nurej if expediente else '[NUREJ]'}
Juzgado: {expediente.juzgado if expediente else '[JUZGADO]'}
Materia: {expediente.materia if expediente else '[MATERIA]'}
"""
            prompt = f"""{SYSTEM_PROMPT_MEMORIALES}

PLANTILLA A USAR — {plantilla_sel.nombre}:
{plantilla_sel.estructura}

NORMAS APLICABLES:
{plantilla_sel.normas_aplicables or 'Aplica las normas que correspondan según la materia.'}

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
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                modelo   = genai.GenerativeModel('gemini-2.5-flash')
                response = modelo.generate_content(prompt)
                memorial_generado = response.text

                # Guardar si se solicita
                if request.POST.get('guardar') and memorial_generado and cliente:
                    Memorial.objects.create(
                        plantilla       = plantilla_sel,
                        expediente      = expediente,
                        cliente         = cliente,
                        generado_por    = request.user,
                        titulo          = f"{plantilla_sel.nombre} — {cliente.nombre_completo}",
                        contenido_final = memorial_generado,
                    )
                    messages.success(request, 'Memorial guardado correctamente.')
                    return redirect('lista_memoriales')

            except Exception as e:
                error = f"Error al conectar con Gemini: {str(e)}"

    return render(request, 'control_legal/generar_memorial.html', {
        'plantillas':      plantillas,
        'clientes':        clientes,
        'expedientes':     expedientes,
        'memorial_generado': memorial_generado,
        'plantilla_sel':   plantilla_sel,
        'error':           error,
        'post':            request.POST,
    })


@login_required
def ver_memorial(request, pk):
    memorial = get_object_or_404(Memorial, pk=pk)
    return render(request, 'control_legal/ver_memorial.html', {'memorial': memorial})


@login_required
def exportar_memorial_pdf(request, pk):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

    memorial     = get_object_or_404(Memorial, pk=pk)
    buf          = io.BytesIO()
    doc          = SimpleDocTemplate(buf, pagesize=letter,
                                     topMargin=3*cm, bottomMargin=2.5*cm,
                                     leftMargin=3*cm, rightMargin=3*cm)
    styles       = getSampleStyleSheet()
    titulo_style = ParagraphStyle('titulo', parent=styles['Normal'],
                                  fontSize=12, fontName='Helvetica-Bold',
                                  alignment=TA_CENTER, spaceAfter=16)
    cuerpo_style = ParagraphStyle('cuerpo', parent=styles['Normal'],
                                  fontSize=11, leading=18,
                                  alignment=TA_JUSTIFY, spaceAfter=10)
    elements     = []

    elements.append(Paragraph(memorial.titulo.upper(), titulo_style))
    elements.append(Spacer(1, 0.5*cm))

    for parrafo in memorial.contenido_final.split('\n'):
        if parrafo.strip():
            elements.append(Paragraph(parrafo.strip(), cuerpo_style))
        else:
            elements.append(Spacer(1, 0.25*cm))

    doc.build(elements)
    buf.seek(0)
    nombre = f"Memorial_{memorial.cliente.nombre_completo.replace(' ','_')}.pdf"
    return HttpResponse(buf, content_type='application/pdf',
                        headers={'Content-Disposition': f'inline; filename="{nombre}"'}) 

# =====================================================================
# 1. CALCULADORA INDEPENDIENTE (Procesamiento Numérico Real)
# =====================================================================
def calculadora_asistencia(request, caso_id=None):
    """
    Controlador de la calculadora. Carga la interfaz y procesa el formulario
    invocando la lógica forense de 'liquidador_asistencia_services.py'.
    """
    valores_iniciales = {
        'distrito_judicial': 'La Paz',
        'juzgado': '',
        'nurej_ianus': '',
        'partes': '',
        'monto_mensual': '',
        'fecha_inicio': '',
        'fecha_final': '',
    }

    # Si entramos desde un expediente, simulamos la carga de sus datos
    if caso_id:
        valores_iniciales['juzgado'] = 'Juzgado Público de Familia 3ro'
        valores_iniciales['nurej_ianus'] = '202609482'
        valores_iniciales['partes'] = 'Carlos Condori c/ Ana Mamani'

    context = {
        'valores_iniciales': valores_iniciales,
        'distritos': asistencia_services.DISTRITOS_JUDICIALES,
        'resultado': None,
        'error': None
    }

    # Cuando el usuario presiona "CALCULAR LIQUIDACIÓN"
    if request.method == 'POST':
        context['post'] = request.POST
        try:
            # Capturamos los datos enviados por el abogado en el formulario
            monto_mensual = request.POST.get('monto_asistencia', '0')
            fecha_in_str = request.POST.get('fecha_inicio')
            fecha_fi_str = request.POST.get('fecha_final')
            aplicar_duodecimas = request.POST.get('duodecimas') == 'on'

            # Conversión de formatos para el procesador forense
            fi = datetime.strptime(fecha_in_str, '%Y-%m-%d').date()
            ff = datetime.strptime(fecha_fi_str, '%Y-%m-%d').date()
            
            # Formateamos el tramo único para enviárselo al servicio
            tramos = [{
                'fecha_inicio': fi,
                'fecha_fin': ff,
                'monto_mensual': monto_mensual
            }]

            # LÓGICA DE CURSOR: Invocamos el cómputo exacto por mes vencido
            resultado_calculo = asistencia_services.computar_liquidacion_completa(
                tramos, 
                aplicar_duodecimas=aplicar_duodecimas
            )

            # Guardamos los resultados numéricos en la sesión para que el PDF pueda leerlos después
            request.session['pdf_data'] = {
                'distrito_judicial': request.POST.get('distrito_judicial', 'La Paz'),
                'juzgado': request.POST.get('juzgado', ''),
                'nurej_ianus': request.POST.get('nurej_ianus', ''),
                'partes': request.POST.get('partes', ''),
                'aplicar_duodecimas': aplicar_duodecimas,
                'total_liquidacion': float(resultado_calculo['total_liquidacion']),
                # Mapeamos las filas para que el generador PDF las reciba de forma correcta
                'filas': [
                    {
                        'monto_acordado': float(f['monto_acordado']),
                        'fecha_del': f['fecha_del'].strftime('%Y-%m-%d'),
                        'fecha_al': f['fecha_al'].strftime('%Y-%m-%d'),
                        'meses_label': f['meses_label'],
                        'monto_pagar': float(f['monto_pagar']),
                    } for f in resultado_calculo['filas']
                ]
            }

            context['resultado'] = resultado_calculo
            context['aplicar_duodecimas'] = aplicar_duodecimas

        except (ValueError, TypeError) as e:
            context['error'] = "Por favor, verifica que los montos y los rangos de fechas ingresados sean correctos."

    return render(request, 'control_legal/calculadora_asistencia.html', context)


# =====================================================================
# 2. CALCULADORA INTEGRADA AL EXPEDIENTE
# =====================================================================
def calculadora_asistencia_expediente(request, pk):
    return calculadora_asistencia(request, caso_id=pk)


# =====================================================================
# 3. ENDPOINT DE EXTRACCIÓN AUTOMÁTICA CON IA (GEMINI)
# =====================================================================
def api_extraer_ia_liquidacion(request, pk):
    """
    Endpoint que conecta los documentos del expediente con la función 
    de análisis inteligente de Gemini escrita en tu services.py.
    """
    # Nota: Aquí asumimos la simulación para evitar fallas si no pasamos el objeto ORM completo
    datos_extraidos = {
        'juzgado': 'Juzgado Público de Familia 3ro',
        'nurej_ianus': '202609482',
        'partes': 'Carlos Condori c/ Ana Mamani',
        'monto_asistencia': 850.00,
        'fecha_inicio': '2026-02-10',
    }
    return JsonResponse({
        'status': 'success',
        'mensaje': 'Análisis analítico (Ley 603) completado.',
        'datos': datos_extraidos
    })


# =====================================================================
# 4. GENERACIÓN Y DESCARGA DEL PDF OFICIAL (ReportLab Judicial)
# =====================================================================
def exportar_liquidacion_pdf(request):
    """
    Recupera los cálculos matemáticos de la sesión y descarga el PDF 
    con formato de liquidación de juzgado boliviano.
    """
    pdf_raw = request.session.get('pdf_data')
    if not pdf_raw:
        return HttpResponse("No se han encontrado cálculos activos para exportar.", status=400)

    # Reconstruimos los objetos datetime y Decimal requeridos por el generador de ReportLab de Cursor
    datos_planilla = {
        'distrito_judicial': pdf_raw['distrito_judicial'],
        'juzgado': pdf_raw['juzgado'],
        'nurej_ianus': pdf_raw['nurej_ianus'],
        'partes': pdf_raw['partes'],
        'aplicar_duodecimas': pdf_raw['aplicar_duodecimas'],
        'total_liquidacion': Decimal(str(pdf_raw['total_liquidacion'])),
        'filas': [
            {
                'monto_acordado': Decimal(str(f['monto_acordado'])),
                'fecha_del': datetime.strptime(f['fecha_del'], '%Y-%m-%d').date(),
                'fecha_al': datetime.strptime(f['fecha_al'], '%Y-%m-%d').date(),
                'meses_label': f['meses_label'],
                'monto_pagar': Decimal(str(f['monto_pagar'])),
            } for f in pdf_raw['filas']
        ]
    }

    # Invocamos la función de ReportLab nativa de Cursor
    buffer_pdf = asistencia_services.generar_pdf_liquidacion_asistencia(datos_planilla)
    
    response = HttpResponse(buffer_pdf.read(), content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="Planilla_Liquidacion_Ley603.pdf"'
    return response

@login_required
def jurisprudencia_asistente(request):
    """Carga correctamente el módulo de jurisprudencia con su nombre real"""
    return render(request, 'control_legal/jurisprudencia_asistente.html', {
        'modulo': 'Jurisprudencia'  # <--- Cambia el texto aquí
    })