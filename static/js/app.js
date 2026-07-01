/* ========================================
   BLOQUERA TONKA - APP JS
   ======================================== */

// Global state
let currentUser = null;
let currentSection = 'dashboard';
let chartInstance = null;

// API Base URL - Auto-detect
const API_URL = '';

// ========================================
// INIT
// ========================================

document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    checkSession();
});

function initEventListeners() {
    // Login form
    document.getElementById('login-form').addEventListener('submit', (e) => {
        e.preventDefault();
        login();
    });

    // Menu toggle
    document.getElementById('menu-toggle').addEventListener('click', toggleSidebar);

    // Sidebar overlay
    document.getElementById('sidebar-overlay').addEventListener('click', closeSidebar);

    // Logout
    document.getElementById('logout-btn').addEventListener('click', logout);

    // Navigation
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const section = link.dataset.section;
            navigateTo(section);
            closeSidebar();
        });
    });

    // Estado pedido change
    document.getElementById('ped-estado').addEventListener('change', (e) => {
        const group = document.getElementById('anticipo-group');
        group.style.display = e.target.value === 'Anticipo' ? 'block' : 'none';
    });

    // Modal overlay
    document.getElementById('modal-overlay').addEventListener('click', closeAllModals);
}

// ========================================
// AUTH
// ========================================

async function login() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    try {
        const res = await fetch(`${API_URL}/api/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await res.json();

        if (data.success) {
            currentUser = data.user;
            localStorage.setItem('bloquera_user', JSON.stringify(currentUser));
            showMainScreen();
            showToast('Bienvenido, ' + currentUser.nombre);
        } else {
            showToast(data.message || 'Error de autenticacion', 'error');
        }
    } catch (err) {
        showToast('Error de conexion', 'error');
    }
}

function logout() {
    currentUser = null;
    localStorage.removeItem('bloquera_user');
    document.getElementById('login-screen').classList.add('active');
    document.getElementById('main-screen').classList.remove('active');
    document.getElementById('username').value = '';
    document.getElementById('password').value = '';
}

function checkSession() {
    const saved = localStorage.getItem('bloquera_user');
    if (saved) {
        currentUser = JSON.parse(saved);
        showMainScreen();
    }
}

function showMainScreen() {
    document.getElementById('login-screen').classList.remove('active');
    document.getElementById('main-screen').classList.add('active');
    document.getElementById('user-name').textContent = currentUser.nombre;
    loadDashboard();
}

// ========================================
// NAVIGATION
// ========================================

function navigateTo(section) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));

    document.getElementById(section).classList.add('active');
    document.querySelector(`[data-section="${section}"]`).classList.add('active');

    currentSection = section;

    // Load section data
    switch(section) {
        case 'dashboard': loadDashboard(); break;
        case 'pedidos': loadPedidos(); break;
        case 'facturas': loadFacturas(); break;
        case 'inventario': loadInventario(); break;
        case 'gastos': loadGastos(); break;
        case 'deudores': loadDeudores(); break;
        case 'config': loadConfig(); break;
    }
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('active');
    document.getElementById('sidebar-overlay').classList.toggle('active');
}

function closeSidebar() {
    document.getElementById('sidebar').classList.remove('active');
    document.getElementById('sidebar-overlay').classList.remove('active');
}

// ========================================
// API HELPERS
// ========================================

async function apiGet(endpoint) {
    const res = await fetch(`${API_URL}${endpoint}`);
    return res.json();
}

async function apiPost(endpoint, data) {
    const res = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    return res.json();
}

async function apiDelete(endpoint) {
    const res = await fetch(`${API_URL}${endpoint}`, { method: 'DELETE' });
    return res.json();
}

// ========================================
// DASHBOARD
// ========================================

async function loadDashboard() {
    try {
        const resumen = await apiGet('/api/reportes/resumen');

        document.getElementById('dash-ventas').textContent = formatMoney(resumen.ventas_total);
        document.getElementById('dash-gastos').textContent = formatMoney(resumen.gastos_total);
        document.getElementById('dash-balance').textContent = formatMoney(resumen.balance);
        document.getElementById('dash-por-cobrar').textContent = formatMoney(resumen.por_cobrar);
        document.getElementById('dash-bloques').textContent = formatNumber(resumen.bloques_vendidos);

        // Chart
        const ctx = document.getElementById('chart-resumen');
        if (ctx) {
            if (chartInstance) chartInstance.destroy();

            chartInstance = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Ventas', 'Gastos', 'Por Cobrar'],
                    datasets: [{
                        data: [resumen.ventas_total, resumen.gastos_total, resumen.por_cobrar],
                        backgroundColor: ['#28a745', '#dc3545', '#ffc107'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom' }
                    }
                }
            });
        }
    } catch (err) {
        console.error('Error loading dashboard:', err);
    }
}

// ========================================
// PEDIDOS
// ========================================

async function loadPedidos() {
    try {
        const pedidos = await apiGet('/api/pedidos');
        const tbody = document.querySelector('#tabla-pedidos tbody');

        if (pedidos.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:30px;color:#999;">No hay pedidos registrados</td></tr>';
            return;
        }

        tbody.innerHTML = pedidos.map(p => `
            <tr>
                <td>${p.id}</td>
                <td>${p.fecha}</td>
                <td>${p.cliente}</td>
                <td>${p.producto}</td>
                <td>${p.cantidad}</td>
                <td>${formatMoney(p.precio_unitario)}</td>
                <td><span class="badge badge-${p.estado.toLowerCase()}">${p.estado}</span></td>
                <td>
                    <button class="btn-success" onclick="prepararDespacho(${p.id})" title="Despachar"><i class="fas fa-truck"></i></button>
                    <button class="btn-danger" onclick="eliminarPedido(${p.id})" title="Eliminar"><i class="fas fa-trash"></i></button>
                </td>
            </tr>
        `).join('');
    } catch (err) {
        console.error('Error loading pedidos:', err);
    }
}

async function guardarPedido() {
    const data = {
        cliente: document.getElementById('ped-cliente').value,
        producto: document.getElementById('ped-producto').value,
        cantidad: parseInt(document.getElementById('ped-cantidad').value),
        precio: parseFloat(document.getElementById('ped-precio').value),
        estado: document.getElementById('ped-estado').value,
        anticipo: parseFloat(document.getElementById('ped-anticipo').value) || 0
    };

    if (!data.cliente || !data.cantidad || !data.precio) {
        showToast('Complete todos los campos', 'error');
        return;
    }

    try {
        await apiPost('/api/pedidos', data);
        closeModal('modal-nuevo-pedido');
        showToast('Pedido guardado exitosamente');
        loadPedidos();

        // Reset form
        document.getElementById('ped-cliente').value = '';
        document.getElementById('ped-cantidad').value = '100';
        document.getElementById('ped-precio').value = '25.00';
        document.getElementById('ped-anticipo').value = '0';
    } catch (err) {
        showToast('Error al guardar pedido', 'error');
    }
}

async function eliminarPedido(id) {
    if (!confirm('¿Esta seguro de eliminar este pedido?')) return;

    try {
        await apiDelete(`/api/pedidos/${id}`);
        showToast('Pedido eliminado');
        loadPedidos();
    } catch (err) {
        showToast('Error al eliminar', 'error');
    }
}

function prepararDespacho(id) {
    document.getElementById('desp-id').value = id;
    showModal('modal-despachar');
}

async function confirmarDespacho() {
    const id = document.getElementById('desp-id').value;
    const data = {
        identidad: document.getElementById('desp-identidad').value,
        rtn: document.getElementById('desp-rtn').value,
        telefono: document.getElementById('desp-telefono').value,
        direccion: document.getElementById('desp-direccion').value,
        tipo_impuesto: document.getElementById('desp-impuesto').value
    };

    try {
        const res = await apiPost(`/api/pedidos/${id}/despachar`, data);

        if (res.exito) {
            closeModal('modal-despachar');
            showToast(`Factura #${res.num_factura} generada exitosamente`);
            loadPedidos();

            // Reset form
            document.getElementById('desp-identidad').value = '';
            document.getElementById('desp-rtn').value = '';
            document.getElementById('desp-telefono').value = '';
        } else {
            showToast(res.mensaje || 'Error al despachar', 'error');
        }
    } catch (err) {
        showToast('Error al despachar', 'error');
    }
}

// ========================================
// FACTURAS
// ========================================

async function loadFacturas() {
    try {
        const facturas = await apiGet('/api/facturas');
        const tbody = document.querySelector('#tabla-facturas tbody');

        if (facturas.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:30px;color:#999;">No hay facturas registradas</td></tr>';
            return;
        }

        tbody.innerHTML = facturas.map(f => `
            <tr>
                <td>${f.num_factura}</td>
                <td>${f.fecha_despacho}</td>
                <td>${f.cliente}</td>
                <td>${f.producto}</td>
                <td>${f.cantidad}</td>
                <td>${formatMoney(f.total_venta)}</td>
                <td><span class="badge badge-${f.estado.toLowerCase()}">${f.estado}</span></td>
                <td>${formatMoney(f.saldo_pendiente)}</td>
                <td>
                    <button class="btn-info" onclick="descargarFactura(${f.num_factura})" title="PDF"><i class="fas fa-file-pdf"></i></button>
                    ${f.saldo_pendiente > 0 ? `<button class="btn-success" onclick="liquidarFactura(${f.num_factura})" title="Liquidar"><i class="fas fa-check"></i></button>` : ''}
                </td>
            </tr>
        `).join('');
    } catch (err) {
        console.error('Error loading facturas:', err);
    }
}

async function liquidarFactura(num) {
    if (!confirm('¿Confirmar liquidacion de esta factura?')) return;

    try {
        await apiPost(`/api/facturas/${num}/liquidar`, {});
        showToast('Factura liquidada');
        loadFacturas();
    } catch (err) {
        showToast('Error al liquidar', 'error');
    }
}

function descargarFactura(num) {
    window.open(`${API_URL}/api/facturas/${num}/pdf`, '_blank');
}

// ========================================
// INVENTARIO
// ========================================

async function loadInventario() {
    try {
        const inv = await apiGet('/api/inventario');
        const grid = document.getElementById('inventario-grid');

        const icons = {
            'cemento_bolsas': '🛢️',
            'arena_m3': '🏖️',
            'bloque_de_4"_estándar': '🧱',
            'bloque_de_5"_estándar': '🧱',
            'bloque_de_6"_estándar': '🧱'
        };

        const labels = {
            'cemento_bolsas': 'Cemento',
            'arena_m3': 'Arena',
            'bloque_de_4"_estándar': 'Bloque de 4"',
            'bloque_de_5"_estándar': 'Bloque de 5"',
            'bloque_de_6"_estándar': 'Bloque de 6"'
        };

        const units = {
            'cemento_bolsas': 'bolsas',
            'arena_m3': 'm3',
            'bloque_de_4"_estándar': 'unidades',
            'bloque_de_5"_estándar': 'unidades',
            'bloque_de_6"_estándar': 'unidades'
        };

        grid.innerHTML = Object.entries(inv).map(([key, value]) => `
            <div class="inventory-card">
                <div class="inv-icon">${icons[key] || '📦'}</div>
                <h4>${labels[key] || key}</h4>
                <div class="inv-value">${formatNumber(value)}</div>
                <div class="inv-unit">${units[key] || 'unidades'}</div>
            </div>
        `).join('');
    } catch (err) {
        console.error('Error loading inventario:', err);
    }
}

async function abastecer() {
    const data = {
        cemento: parseFloat(document.getElementById('abs-cemento').value) || 0,
        arena: parseFloat(document.getElementById('abs-arena').value) || 0,
        costo_cemento: parseFloat(document.getElementById('abs-costo-cemento').value) || 0,
        costo_arena: parseFloat(document.getElementById('abs-costo-arena').value) || 0
    };

    if (data.cemento <= 0 && data.arena <= 0) {
        showToast('Ingrese al menos una cantidad', 'warning');
        return;
    }

    try {
        await apiPost('/api/inventario/abastecer', data);
        closeModal('modal-abastecer');
        showToast('Inventario actualizado');
        loadInventario();

        // Reset form
        document.getElementById('abs-cemento').value = '0';
        document.getElementById('abs-arena').value = '0';
        document.getElementById('abs-costo-cemento').value = '0';
        document.getElementById('abs-costo-arena').value = '0';
    } catch (err) {
        showToast('Error al abastecer', 'error');
    }
}

// ========================================
// PRODUCCION
// ========================================

async function producir() {
    const data = {
        producto: document.getElementById('prod-producto').value,
        cantidad: parseInt(document.getElementById('prod-cantidad').value)
    };

    if (!data.cantidad || data.cantidad <= 0) {
        showToast('Ingrese una cantidad valida', 'warning');
        return;
    }

    try {
        const res = await apiPost('/api/inventario/producir', data);

        if (res.success) {
            showToast(`Produccion exitosa. Cemento: ${formatNumber(res.cemento_necesario)} bolsas, Arena: ${formatNumber(res.arena_necesaria)} m3`);
            loadInventario();
        } else {
            showToast(`Materiales insuficientes. Necesita: ${formatNumber(res.cemento_necesario)} bolsas cemento, ${formatNumber(res.arena_necesaria)} m3 arena`, 'error');
        }
    } catch (err) {
        showToast('Error en produccion', 'error');
    }
}

// ========================================
// GASTOS
// ========================================

async function loadGastos() {
    try {
        const gastos = await apiGet('/api/gastos');
        const tbody = document.querySelector('#tabla-gastos tbody');

        if (gastos.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:30px;color:#999;">No hay gastos registrados</td></tr>';
            return;
        }

        tbody.innerHTML = gastos.map(g => `
            <tr>
                <td>${g.id}</td>
                <td>${g.fecha}</td>
                <td>${g.descripcion}</td>
                <td>${g.categoria}</td>
                <td>${formatMoney(g.monto)}</td>
                <td>
                    <button class="btn-danger" onclick="eliminarGasto(${g.id})" title="Eliminar"><i class="fas fa-trash"></i></button>
                </td>
            </tr>
        `).join('');
    } catch (err) {
        console.error('Error loading gastos:', err);
    }
}

async function guardarGasto() {
    const data = {
        descripcion: document.getElementById('gasto-descripcion').value,
        categoria: document.getElementById('gasto-categoria').value,
        monto: parseFloat(document.getElementById('gasto-monto').value)
    };

    if (!data.descripcion || !data.monto) {
        showToast('Complete todos los campos', 'warning');
        return;
    }

    try {
        await apiPost('/api/gastos', data);
        closeModal('modal-nuevo-gasto');
        showToast('Gasto registrado');
        loadGastos();

        // Reset form
        document.getElementById('gasto-descripcion').value = '';
        document.getElementById('gasto-monto').value = '0';
    } catch (err) {
        showToast('Error al registrar gasto', 'error');
    }
}

async function eliminarGasto(id) {
    if (!confirm('¿Eliminar este gasto?')) return;

    try {
        await apiDelete(`/api/gastos/${id}`);
        showToast('Gasto eliminado');
        loadGastos();
    } catch (err) {
        showToast('Error al eliminar', 'error');
    }
}

// ========================================
// DEUDORES
// ========================================

async function loadDeudores() {
    try {
        const deudores = await apiGet('/api/deudores');
        const tbody = document.querySelector('#tabla-deudores tbody');

        if (deudores.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;padding:30px;color:#999;">No hay deudores registrados</td></tr>';
            return;
        }

        tbody.innerHTML = deudores.map(d => `
            <tr>
                <td>${d.cliente}</td>
                <td style="color:#dc3545;font-weight:600;">${formatMoney(d.deuda)}</td>
                <td>
                    <button class="btn-info" onclick="verFacturasDeudor('${d.cliente}')" title="Ver facturas"><i class="fas fa-eye"></i></button>
                </td>
            </tr>
        `).join('');
    } catch (err) {
        console.error('Error loading deudores:', err);
    }
}

function verFacturasDeudor(cliente) {
    navigateTo('facturas');
    showToast(`Filtrando facturas de: ${cliente}`);
}

// ========================================
// CONFIGURACION
// ========================================

async function loadConfig() {
    try {
        const config = await apiGet('/api/config');
        document.getElementById('config-bloques').value = config.bloques_por_bolsa || 42;
        document.getElementById('config-arena').value = config.arena_por_100_bloques || 0.40;
    } catch (err) {
        console.error('Error loading config:', err);
    }
}

async function guardarConfig() {
    const data = {
        bloques_por_bolsa: parseFloat(document.getElementById('config-bloques').value),
        arena_por_100_bloques: parseFloat(document.getElementById('config-arena').value)
    };

    try {
        await apiPost('/api/config', data);
        showToast('Configuracion guardada');
    } catch (err) {
        showToast('Error al guardar', 'error');
    }
}

// ========================================
// REPORTES
// ========================================

function descargarReporte(tipo) {
    window.open(`${API_URL}/api/reportes/${tipo}/pdf`, '_blank');
    showToast(`Descargando reporte de ${tipo}...`);
}

// ========================================
// MODALS
// ========================================

function showModal(id) {
    document.getElementById(id).classList.add('active');
    document.getElementById('modal-overlay').classList.add('active');
}

function closeModal(id) {
    document.getElementById(id).classList.remove('active');
    document.getElementById('modal-overlay').classList.remove('active');
}

function closeAllModals() {
    document.querySelectorAll('.modal').forEach(m => m.classList.remove('active'));
    document.getElementById('modal-overlay').classList.remove('active');
}

// ========================================
// UTILS
// ========================================

function formatMoney(amount) {
    return 'L. ' + parseFloat(amount || 0).toLocaleString('es-HN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function formatNumber(num) {
    return parseFloat(num || 0).toLocaleString('es-HN', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2
    });
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    const msg = document.getElementById('toast-message');

    toast.className = 'toast ' + type;
    msg.textContent = message;
    toast.classList.add('active');

    setTimeout(() => {
        toast.classList.remove('active');
    }, 3000);
}

// ========================================
// SERVICE WORKER (PWA)
// ========================================

if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/service-worker.js')
        .then(reg => console.log('Service Worker registrado'))
        .catch(err => console.log('Error registrando SW:', err));
}
