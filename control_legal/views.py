import io
from datetime import datetime # Para que no falle el context {'fecha': datetime.now()}
from django.http import FileResponse
from django.template.loader import get_template
from xhtml2pdf import pisa

from django.shortcuts import render, redirect
from .forms import CasoForm
from .models import Caso

# 1. FUNCIÓN REGISTRAR (Péguenla al borde izquierdo)
def registrar_caso(request):
    if request.method == 'POST':
        form = CasoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('listar_casos')
    else:
        form = CasoForm()
    return render(request, 'control_legal/registrar_caso.html', {'form': form})

# 2. FUNCIÓN LISTAR (Péguenla al borde izquierdo)
def listar_casos(request):
    # Obtenemos el criterio de orden de la URL, por defecto será por ID
    criterio = request.GET.get('orden', 'id')
    
    casos = Caso.objects.filter(activo=True) 
    
    if busqueda:
        casos = casos.filter(
            Q(cliente__icontains=busqueda) | Q(nurej__icontains=busqueda) | Q(materia__icontains=busqueda) | Q(abogado_asignado__icontains=busqueda)    
        )
    
    opciones = {
        'nombre': 'cliente',
        'fecha': '-id', # El signo "-" ordena del más reciente al más antiguo
        'materia': 'materia',
        'id': 'id'
    }
    
    # Aplicamos el ordenamiento
    metodo_orden = opciones.get(criterio, 'id')
    casos = Caso.objects.filter(activo=True).order_by(metodo_orden)
    
    return render(request, 'control_legal/listar_casos.html', {'casos': casos})
# 3. FUNCIÓN DASHBOARD (Péguenla al borde izquierdo)
def dashboard(request):
    total = Caso.objects.count()
    activos = Caso.objects.filter(estado='Activo').count()
    recientes = Caso.objects.all().order_by('-id')[:3]
    return render(request, 'control_legal/dashboard.html', {
        'total': total,
        'activos': activos,
        'recientes': recientes
    })

from django.shortcuts import render, redirect, get_object_or_404  # Asegúrate de importar get_object_or_404

def editar_caso(request, pk):
    # Buscamos el caso por su ID (pk)
    caso = get_object_or_404(Caso, pk=pk)
    
    if request.method == "POST":
        form = CasoForm(request.POST, instance=caso)
        if form.is_valid():
            form.save()
            return redirect('listar_casos')
    else:
        form = CasoForm(instance=caso)
        
    return render(request, 'control_legal/registrar_caso.html', {'form': form, 'editando': True}) 

from django.db.models import Q # Importante: añade esto al inicio del archivo

def listar_casos(request):
    # 1. Obtenemos el texto de búsqueda y el orden
    busqueda = request.GET.get('buscar', '')
    criterio = request.GET.get('orden', 'id')
    
    # 2. Empezamos con todos los casos
    casos = Caso.objects.all()
    
    # 3. SI HAY BÚSQUEDA: Filtramos por Cliente o NUREJ
    if busqueda:
        casos = casos.filter(
            Q(cliente__icontains=busqueda) | 
            Q(nurej__icontains=busqueda) | 
            Q(materia__icontains=busqueda) | 
            Q(abogado_asignado__icontains=busqueda)
        )
    
    # 4. Aplicamos el orden que ya teníamos
    opciones = {'nombre': 'cliente', 'fecha': '-id', 'materia': 'materia', 'id': 'id'}
    metodo = opciones.get(criterio, 'id')
    casos = casos.order_by(metodo)
    
    return render(request, 'control_legal/listar_casos.html', {
        'casos': casos,
        'busqueda': busqueda # Enviamos la búsqueda de vuelta para que se quede escrita
    })   

from django.shortcuts import get_object_or_404, redirect

def eliminar_caso_logico(request, pk):
    caso = get_object_or_404(Caso, pk=pk)
    caso.activo = False # No lo borramos, solo lo desactivamos
    caso.save()
    return redirect('listar_casos')

def papelera_casos(request):
    # Solo traemos los casos que fueron "borrados" lógicamente
    casos_borrados = Caso.objects.filter(activo=False).order_by('-id')
    return render(request, 'control_legal/papelera.html', {'casos': casos_borrados})

def restaurar_caso(request, pk):
    caso = get_object_or_404(Caso, pk=pk)
    caso.activo = True # Lo activamos de nuevo
    caso.save()
    return redirect('papelera_casos')

from django.contrib.auth.decorators import login_required # Importa esto arriba
from django.contrib import messages # Importa esto para mostrar mensajes de error

@login_required
def listar_casos(request):
    busqueda = request.GET.get('buscar', '')
    criterio = request.GET.get('orden', 'id')
    casos = Caso.objects.filter(activo=True)
    if busqueda:
        casos = casos.filter(
            Q(cliente__icontains=busqueda) | Q(nurej__icontains=busqueda)
        )
    opciones = {'nombre': 'cliente', 'fecha': '-id', 'materia': 'materia', 'id': 'id'}
    metodo = opciones.get(criterio, 'id')
    casos = casos.order_by(metodo)
    return render(request, 'control_legal/listar_casos.html', {'casos': casos, 'busqueda': busqueda})

@login_required
def registrar_caso(request):
    if request.method == 'POST':
        form = CasoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Caso registrado exitosamente.')
            return redirect('listar_casos')
    else:
        form = CasoForm()
    return render(request, 'control_legal/registrar_caso.html', {'form': form})

@login_required
def editar_caso(request, pk):
    caso = get_object_or_404(Caso, pk=pk)
    if request.method == 'POST':
        form = CasoForm(request.POST, instance=caso)
        if form.is_valid():
            form.save()
            messages.success(request, 'Caso editado exitosamente.')
            return redirect('listar_casos')
    else:
        form = CasoForm(instance=caso)
    return render(request, 'control_legal/registrar_caso.html', {'form': form})

@login_required
def eliminar_caso_logico(request, pk):
    caso = get_object_or_404(Caso, pk=pk)
    caso.activo = False
    caso.save()
    messages.success(request, 'Caso movido a la papelera exitosamente.')
    return redirect('listar_casos')

@login_required
def exportar_casos_pdf(request):
    casos = Caso.objects.filter(activo=True)
    template = get_template('control_legal/reporte_pdf.html')
    context = {'casos': casos, 'fecha': datetime.now()}
    
    html = template.render(context)
    result = io.BytesIO()
    
    pisa.CreatePDF(io.BytesIO(html.encode("UTF-8")), dest=result, enconding='UTF-8')
    result.seek(0)
    
    return FileResponse(result, as_attachment=True, filename='Reporte_Soli_Legal.pdf')

from django.shortcuts import get_object_or_404 # Importante para buscar por ID

def reporte_un_caso(request, pk):
    # Buscamos el caso exacto o damos error 404 si no existe
    caso = get_object_or_404(Caso, pk=pk)
    
    template = get_template('control_legal/reporte_individual.html')
    context = {'caso': caso, 'fecha': datetime.now()}
    html = template.render(context)
    
    result = io.BytesIO()
    # Forzamos UTF-8 para que no salgan los símbolos de la imagen 5d32308b-cb6a-47b6-813f-4bfff91a1509
    pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result, encoding='UTF-8')
    
    result.seek(0)
    return FileResponse(result, as_attachment=True, filename=f'Expediente_{caso.nurej}.pdf')

from django.contrib import messages
from django.contrib.auth import authenticate, login
def login_view(request):
    if request.method == "POST":
        # Capturamos los datos reales del formulario
        usuario = request.POST.get('username')
        clave = request.POST.get('password')
        
        # Usamos esas variables para autenticar
        user = authenticate(request, username=usuario, password=clave)
        
        if user is not None:
            login(request, user)
            return redirect('listar_casos')
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")
    
    return render(request, "login.html")