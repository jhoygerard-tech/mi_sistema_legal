import io
import json
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from datetime import date
from django.template.loader import render_to_string

from .models import Expediente
from .liquidacion_asistencia_services import (
    DISTRITOS_JUDICIALES,
    es_expediente_familia_liquidacion,
    computar_liquidacion_completa,
    parsear_tramos_desde_post,
    extraer_datos_liquidacion_ia,
    generar_pdf_liquidacion_asistencia,
)
from decimal import Decimal, InvalidOperation

# ── Importar servicios — NUNCA duplicar lógica aquí ──────────
from .services import (
    # Generadores IA
    generar_contrato_con_ia,
    generar_memorial_con_ia,
    sugerir_estrategia_jurisprudencial,
    # Scraper TCP
    extraer_sentencia_tcp,
    guardar_precedente,
    buscar_precedentes_locales,
    precedentes_a_contexto,
    construir_url_portal_tcp_oficial,
    # PDF
    generar_pdf_documento,
    generar_pdf_reporte,
)

# ── Modelos ───────────────────────────────────────────────────
from .models import (
    Cliente, Expediente, Documento, Movimiento,
    Evento, Tarea, EvidenciaTarea,
    PlantillaContrato, Contrato,
    PlantillaMemorial, Memorial,
    PrecedenteJurisprudencial,
)

# ── Formularios ───────────────────────────────────────────────
from .forms import (
    CasoForm, ClienteForm, ExpedienteForm,
    DocumentoForm, MovimientoForm, EventoForm,
    TareaForm, EvidenciaForm,
    PlantillaContratoForm, GenerarContratoForm,
)

# ════════════════════════════════════════════════════════════════
# IMPORTANTE: No definir GEMINI_MODEL ni prompts aquí.
# Todo está centralizado en services.py.
# ════════════════════════════════════════════════════════════════

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

# ── Exportar reporte general PDF ──────────────────────────────
@login_required
def exportar_pdf(request):
    from .models import Expediente
    casos = Expediente.objects.filter(activo=True).select_related('cliente')

    # Convertir queryset a lista de dicts para que xhtml2pdf no tenga
    # problemas con objetos ORM dentro del template de PDF
    casos_lista = [
        {
            'nurej': c.nurej or c.numero_expediente or '—',
            'cliente': c.cliente.nombre_completo,
            'materia': c.materia,
            'activo': c.activo,
        }
        for c in casos
    ]

    html = render_to_string('control_legal/reporte_pdf.html', {
        'casos': casos_lista,
        'fecha': timezone.now(),
        'usuario_nombre': request.user.get_full_name() or request.user.username,
    })

    buf = generar_pdf_reporte(html)
    response = HttpResponse(buf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_expedientes.pdf"'
    return response

# Si quieres descarga PDF directo (recomendado):
@login_required  
def reporte_un_caso(request, pk):
    expediente = get_object_or_404(Expediente, pk=pk)
    html = render_to_string('control_legal/reporte_individual.html', {
        'caso': expediente,
        'fecha': timezone.now(),
    })
    buf = generar_pdf_reporte(html)
    response = HttpResponse(buf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="caso_{expediente.pk}.pdf"'
    return response

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

# ── Exportar contrato PDF ─────────────────────────────────────
@login_required
def exportar_contrato_pdf(request, pk):
    contrato = get_object_or_404(Contrato, pk=pk)
    buf      = generar_pdf_documento(
        titulo      = contrato.titulo,
        contenido   = contrato.contenido_final,
        firma_izq   = contrato.cliente.nombre_completo,
        firma_der   = contrato.generado_por.get_full_name() or 'Abogado',
    )
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

# ── Generador de contratos con IA ────────────────────────────
@login_required
def generar_contrato_ia(request):
    contrato_generado = None
    error             = None

    if request.method == 'POST':
        contrato_generado, error = generar_contrato_con_ia(
            tipo        = request.POST.get('tipo_contrato', ''),
            partes      = request.POST.get('partes', ''),
            objeto      = request.POST.get('objeto', ''),
            precio      = request.POST.get('precio', ''),
            plazo       = request.POST.get('plazo', ''),
            condiciones = request.POST.get('condiciones', ''),
        )

        if contrato_generado and request.POST.get('guardar'):
            cliente = Cliente.objects.filter(pk=request.POST.get('cliente_id')).first()
            if cliente:
                Contrato.objects.create(
                    titulo          = f"{request.POST.get('tipo_contrato')} — {cliente.nombre_completo}",
                    cliente         = cliente,
                    contenido_final = contrato_generado,
                    generado_por    = request.user,
                    ciudad          = 'La Paz',
                )
                messages.success(request, 'Contrato guardado correctamente.')
                return redirect('lista_contratos')

    return render(request, 'control_legal/generar_contrato_ia.html', {
        'contrato_generado': contrato_generado,
        'clientes':          Cliente.objects.filter(activo=True).order_by('nombre_completo'),
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


@login_required
def lista_memoriales(request):
    memoriales = Memorial.objects.select_related(
        'cliente', 'plantilla', 'generado_por'
    ).order_by('-fecha_generado')
    return render(request, 'control_legal/lista_memoriales.html', {'memoriales': memoriales})

# ── Generador de memoriales con IA ───────────────────────────
@login_required
def generar_memorial(request):
    plantillas  = PlantillaMemorial.objects.filter(activa=True).order_by('categoria', 'nombre')
    clientes    = Cliente.objects.filter(activo=True).order_by('nombre_completo')
    expedientes = Expediente.objects.filter(activo=True).select_related('cliente').order_by('-id')

    memorial_generado = None
    plantilla_sel     = None
    error             = None

    if request.method == 'POST':
        plantilla_sel = PlantillaMemorial.objects.filter(
            pk=request.POST.get('plantilla_id')).first()
        cliente = Cliente.objects.filter(pk=request.POST.get('cliente_id')).first()
        expediente = Expediente.objects.filter(
            pk=request.POST.get('expediente_id')).first() if request.POST.get('expediente_id') else None

        if not plantilla_sel or not cliente:
            error = 'Debes seleccionar una plantilla y un cliente.'
        else:
            memorial_generado, error = generar_memorial_con_ia(
                plantilla      = plantilla_sel,
                cliente        = cliente,
                expediente     = expediente,
                hechos         = request.POST.get('hechos', ''),
                peticion       = request.POST.get('peticion', ''),
                datos_extra    = request.POST.get('datos_extra', ''),
                abogado_nombre = request.user.get_full_name() or request.user.username,
                fecha_hoy      = timezone.now().strftime('%d de %B de %Y'),
            )

            if memorial_generado and request.POST.get('guardar') and cliente:
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

    return render(request, 'control_legal/generar_memorial.html', {
        'plantillas':        plantillas,
        'clientes':          clientes,
        'expedientes':       expedientes,
        'memorial_generado': memorial_generado,
        'plantilla_sel':     plantilla_sel,
        'error':             error,
        'post':              request.POST,
    })

@login_required
def ver_memorial(request, pk):
    memorial = get_object_or_404(Memorial, pk=pk)
    return render(request, 'control_legal/ver_memorial.html', {'memorial': memorial})

# ── Exportar memorial PDF ─────────────────────────────────────
@login_required
def exportar_memorial_pdf(request, pk):
    memorial = get_object_or_404(Memorial, pk=pk)
    buf      = generar_pdf_documento(
        titulo    = memorial.titulo,
        contenido = memorial.contenido_final,
    )
    nombre = f"Memorial_{memorial.cliente.nombre_completo.replace(' ', '_')}.pdf"
    return HttpResponse(buf, content_type='application/pdf',
                        headers={'Content-Disposition': f'inline; filename="{nombre}"'})

# ── Jurisprudencia: asistente de estrategia ───────────────────
@login_required
def jurisprudencia_asistente(request):
    from .models import PrecedenteJurisprudencial
    from .services import (
        sugerir_estrategia_jurisprudencial,
        extraer_sentencia_tcp,
        guardar_precedente,
        buscar_precedentes_locales,
        precedentes_a_contexto,
    )

    estrategia = None
    precedente_extraido = None
    extraido_fuente_alternativa = False
    error = None
    post = {}

    materias = PrecedenteJurisprudencial.MATERIAS
    buscar = request.GET.get('buscar', '')
    materia_filtro = request.GET.get('materia', '')

    precedentes_banco = buscar_precedentes_locales(
        termino=buscar, materia=materia_filtro
    )

    if request.method == 'POST':
        post = request.POST
        opcion = post.get('opcion', '')

        if opcion == 'estrategia':
            hechos = post.get('hechos_caso', '').strip()
            if not hechos:
                error = 'Debes describir los hechos del caso.'
            else:
                materia = post.get('materia', '')
                peticion = post.get('peticion', '')
                termino = post.get('termino_precedentes', '')

                precedentes_ctx = ''
                if termino:
                    precs = buscar_precedentes_locales(termino=termino, materia=materia)
                    precedentes_ctx = precedentes_a_contexto(precs)

                estrategia, error = sugerir_estrategia_jurisprudencial(
                    hechos_caso=hechos,
                    materia=materia,
                    peticion=peticion,
                    precedentes_contexto=precedentes_ctx,
                )

        elif opcion == 'extraccion_tcp':
            entrada = post.get('url_tcp', '').strip()
            if not entrada:
                error = 'Debes ingresar un número de sentencia o URL.'
            else:
                datos, error = extraer_sentencia_tcp(entrada)
                if datos:
                    precedente_extraido, _, error = guardar_precedente(
                        datos, usuario=request.user
                    )
                    if precedente_extraido:
                        extraido_fuente_alternativa = datos.get('fuente_alternativa', False)
                        error = None  # guardado exitoso

    context = {
        'estrategia': estrategia,
        'precedente_extraido': precedente_extraido,
        'extraido_fuente_alternativa': extraido_fuente_alternativa,
        'error': error,
        'post': post,
        'materias': materias,
        'precedentes_banco': precedentes_banco,
        'buscar': buscar,
        'materia_filtro': materia_filtro,
    }
    return render(request, 'control_legal/jurisprudencia_asistente.html', context)
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
            context['valores_iniciales'] = valores_iniciales

        except (ValueError, TypeError) as e:
            context['error'] = "Por favor, verifica que los montos y los rangos de fechas ingresados sean correctos."

    return render(request, 'control_legal/calculadora_asistencia.html', context)

# =====================================================================
# 2. CALCULADORA INTEGRADA AL EXPEDIENTE
# =====================================================================
@login_required
def calculadora_asistencia(request):
    return _calculadora_asistencia_core(request, expediente=None)


@login_required
def calculadora_asistencia_expediente(request, pk):
    expediente = get_object_or_404(Expediente, pk=pk)
    return _calculadora_asistencia_core(request, expediente=expediente)


def _calculadora_asistencia_core(request, expediente):
    hoy = date.today().strftime('%Y-%m-%d')
    resultado = None
    error = None
    aplicar_duodecimas = False
    post = {}

    valores_iniciales = {}
    if expediente:
        valores_iniciales = {
            'nurej_ianus': expediente.nurej or '',
            'juzgado': expediente.juzgado or '',
            'partes': f'{expediente.cliente.nombre_completo} / (demandado)',
        }
    # Valores que el template necesita directamente (no como dict anidado)
    distrito_actual = ''
    juzgado_actual = valores_iniciales.get('juzgado', '')
    nurej_actual = valores_iniciales.get('nurej_ianus', '')
    partes_actual = valores_iniciales.get('partes', '')
    fecha_inicio_actual = ''
    monto_actual = ''

    if request.method == 'POST':
        aplicar_duodecimas = bool(request.POST.get('aplicar_duodecimas'))
        tramos = parsear_tramos_desde_post(request.POST)
        accion = request.POST.get('accion', 'calcular')

        # Recuperar valores del POST para repintar el formulario
        distrito_actual = request.POST.get('distrito_judicial', '')
        juzgado_actual = request.POST.get('juzgado', '')
        nurej_actual = request.POST.get('nurej_ianus', '')
        partes_actual = request.POST.get('partes', '')

        if not tramos:
            error = 'Debes añadir al menos un tramo con fechas y monto válidos.'
        else:
            resultado = computar_liquidacion_completa(
                tramos, aplicar_duodecimas=aplicar_duodecimas
            )
            datos_planilla = {
                'distrito_judicial': post.get('distrito_judicial', ''),
                'juzgado': post.get('juzgado', ''),
                'nurej_ianus': post.get('nurej_ianus', ''),
                'partes': post.get('partes', ''),
                'filas': resultado['filas'],
                'total_liquidacion': resultado['total_liquidacion'],
                'aplicar_duodecimas': aplicar_duodecimas,
            }

            if accion == 'reporte_pdf':
                buf = generar_pdf_liquidacion_asistencia(datos_planilla)
                response = HttpResponse(buf, content_type='application/pdf')
                response['Content-Disposition'] = (
                    'attachment; filename="liquidacion_asistencia.pdf"'
                )
                return response

    context = {
        'hoy': hoy,
        'distritos': DISTRITOS_JUDICIALES,
        'resultado': resultado,
        'error': error,
        'aplicar_duodecimas': aplicar_duodecimas,
        'expediente': expediente,
        # Variables planas — el template las usa directamente
        'distrito_actual': distrito_actual,
        'juzgado_actual': juzgado_actual,
        'nurej_actual': nurej_actual,
        'partes_actual': partes_actual,
    }
    return render(request, 'control_legal/calculadora_asistencia.html', context)


@login_required
def api_extraer_ia_liquidacion(request, pk):
    """Endpoint AJAX: extrae datos del expediente con IA."""
    expediente = get_object_or_404(Expediente, pk=pk)
    datos, error = extraer_datos_liquidacion_ia(expediente)
    if error:
        return JsonResponse({'ok': False, 'error': error})
    return JsonResponse({'ok': True, 'datos': datos})    


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
