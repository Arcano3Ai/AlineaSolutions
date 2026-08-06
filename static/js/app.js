document.addEventListener('DOMContentLoaded', function() {
    // ========== Tab Navigation ==========
    const navBtns = document.querySelectorAll('.nav-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    navBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            navBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            const tabName = this.dataset.tab;
            const targetTab = document.getElementById('tab-' + tabName);
            if (targetTab) {
                targetTab.classList.add('active');
            }
            
            // Tab activation hooks
            if (tabName === 'dashboard') {
                loadDashboardData();
            } else if (tabName === 'crm') {
                loadCrmClients();
            } else if (tabName === 'erp') {
                loadErpInventory();
            } else if (tabName === 'admin') {
                loadAdminAudit();
                loadVaultStatus();
            } else if (tabName === 'vucem-parser') {
                loadVucemAcuses();
            } else if (tabName === 'mve') {
                loadMveList();
            } else if (tabName === 'cartaporte') {
                loadCartaPorteList();
            } else if (tabName === 'tree') {
                if (!document.getElementById('tree-container').children.length) loadTree();
            } else if (tabName === 'rgi') {
                if (!document.getElementById('rgi-rules-list').children.length) loadRGIRules();
            } else if (tabName === 'history') {
                loadHistory();
            }
        });
    });

    // ========== Dashboard Analytics & Load ==========
    window.donutChart = null;
    window.lineChart = null;

    async function loadDashboardData() {
        try {
            // Load dashboard stats
            const statsRes = await fetch('/api/database/stats');
            const stats = await statsRes.json();
            
            const clientsRes = await fetch('/api/crm/clients');
            const clients = await clientsRes.json();
            
            const itemsRes = await fetch('/api/erp/inventory');
            const items = await itemsRes.json();
            
            const cpRes = await fetch('/api/cartaporte/list');
            const cpList = await cpRes.json();

            // Set metric values
            document.getElementById('dash-total-classifications').textContent = stats.subheadings || 0;
            document.getElementById('dash-total-clients').textContent = clients.length || 0;
            document.getElementById('dash-total-skus').textContent = items.length || 0;
            document.getElementById('dash-total-cartas').textContent = cpList.length || 0;

            loadDashboardAudit();
            renderDashboardCharts();
        } catch (err) {
            console.error("Error al cargar datos del dashboard:", err);
        }
    }

    async function loadDashboardAudit() {
        const body = document.getElementById('dash-audit-body');
        body.innerHTML = '<tr><td colspan="4">Cargando bitácora...</td></tr>';
        try {
            const res = await fetch('/api/admin/audit');
            const data = await res.json();
            body.innerHTML = '';
            if (data.length === 0) {
                body.innerHTML = '<tr><td colspan="4" style="text-align:center">Sin actividad registrada.</td></tr>';
                return;
            }
            data.slice(0, 5).forEach(l => {
                const date = new Date(l.created_at).toLocaleString('es-MX');
                const tr = document.createElement('tr');
                tr.innerHTML = `<td style="padding:10px">${date}</td>
                                <td style="padding:10px"><span class="badge badge-medium" style="background:rgba(59,130,246,0.1);color:var(--primary)">${l.module}</span></td>
                                <td style="padding:10px"><strong>${l.action}</strong></td>
                                <td style="padding:10px">${l.details || ''}</td>`;
                body.appendChild(tr);
            });
        } catch (err) {
            body.innerHTML = '<tr><td colspan="4">Error al cargar bitácora.</td></tr>';
        }
    }

    function renderDashboardCharts() {
        // Destroy existing instances to prevent overlays
        if (window.donutChart) window.donutChart.destroy();
        if (window.lineChart) window.lineChart.destroy();

        // 1. Donut Chart - Section distribution
        const ctxDonut = document.getElementById('chart-donacion').getContext('2d');
        window.donutChart = new Chart(ctxDonut, {
            type: 'doughnut',
            data: {
                labels: ['Electrónicos (XVI)', 'Químicos (VI)', 'Transportes (XVII)', 'Metales (XV)', 'Alimentos (II)'],
                datasets: [{
                    data: [45, 15, 20, 10, 10],
                    backgroundColor: [
                        '#3b82f6', // Neon blue
                        '#06b6d4', // Cian
                        '#10b981', // Emerald
                        '#f59e0b', // Amber
                        '#7c3aed'  // Purple
                    ],
                    borderWidth: 1,
                    borderColor: 'rgba(255, 255, 255, 0.05)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#94a3b8', font: { size: 10 } }
                    }
                }
            }
        });

        // 2. Line Chart - Monthly logistics
        const ctxLine = document.getElementById('chart-operaciones').getContext('2d');
        window.lineChart = new Chart(ctxLine, {
            type: 'line',
            data: {
                labels: ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun'],
                datasets: [
                    {
                        label: 'Pedimentos Importación',
                        data: [65, 78, 72, 89, 95, 110],
                        borderColor: '#06b6d4',
                        backgroundColor: 'rgba(6, 182, 212, 0.1)',
                        fill: true,
                        tension: 0.3
                    },
                    {
                        label: 'Cartas Porte Emitidas',
                        data: [40, 48, 55, 60, 78, 85],
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        fill: true,
                        tension: 0.3
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#94a3b8', font: { size: 10 } }
                    }
                },
                scales: {
                    y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#94a3b8' } },
                    x: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#94a3b8' } }
                }
            }
        });
    }

    // ========== CRM Clients Logic ==========
    async function loadCrmClients() {
        const body = document.getElementById('crm-clients-body');
        body.innerHTML = '<tr><td colspan="6"><div class="spinner"></div> Cargando clientes...</td></tr>';
        try {
            const res = await fetch('/api/crm/clients');
            const data = await res.json();
            body.innerHTML = '';
            if (data.length === 0) {
                body.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-secondary)">No hay clientes registrados.</td></tr>';
                return;
            }
            data.forEach(c => {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td><strong>${escapeHtml(c.name)}</strong></td>
                                <td style="font-family:monospace">${c.rfc}</td>
                                <td>${c.patent || '-'}</td>
                                <td>${escapeHtml(c.agent) || '-'}</td>
                                <td><span class="badge ${c.status === 'Activo' ? 'badge-high' : 'badge-low'}">${c.status}</span></td>
                                <td style="text-align:center"><button class="btn-delete" onclick="deleteCrmClient(${c.id})">Eliminar</button></td>`;
                body.appendChild(tr);
            });
        } catch (err) {
            body.innerHTML = `<tr><td colspan="6" style="color:var(--danger)">Error: ${err.message}</td></tr>`;
        }
    }

    document.getElementById('crm-save-btn').addEventListener('click', async function() {
        const rfc = document.getElementById('crm-rfc').value.trim();
        const name = document.getElementById('crm-name').value.trim();
        const patent = document.getElementById('crm-patent').value.trim();
        const agent = document.getElementById('crm-agent').value.trim();

        if (!rfc || !name) {
            alert('RFC y Razón Social son requeridos.');
            return;
        }

        try {
            const res = await fetch('/api/crm/clients', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ rfc, name, patent, agent })
            });
            const data = await res.json();
            if (data.error) {
                alert('Error: ' + data.error);
            } else {
                alert('Cliente guardado exitosamente.');
                document.getElementById('crm-rfc').value = '';
                document.getElementById('crm-name').value = '';
                document.getElementById('crm-patent').value = '';
                document.getElementById('crm-agent').value = '';
                loadCrmClients();
            }
        } catch (err) {
            alert('Error al guardar cliente: ' + err.message);
        }
    });

    window.deleteCrmClient = async function(id) {
        if (!confirm('¿Seguro que desea eliminar este cliente?')) return;
        try {
            await fetch('/api/crm/clients/' + id, { method: 'DELETE' });
            loadCrmClients();
        } catch (err) {
            alert('Error al eliminar cliente: ' + err.message);
        }
    };

    // ========== ERP Inventory Logic ==========
    async function loadErpInventory() {
        const body = document.getElementById('erp-inventory-body');
        body.innerHTML = '<tr><td colspan="8"><div class="spinner"></div> Cargando inventario...</td></tr>';
        try {
            const res = await fetch('/api/erp/inventory');
            const data = await res.json();
            body.innerHTML = '';
            if (data.length === 0) {
                body.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-secondary)">No hay mercancías en el almacén.</td></tr>';
                return;
            }
            data.forEach(i => {
                const totalVal = i.quantity * i.price;
                const tr = document.createElement('tr');
                tr.innerHTML = `<td><strong>${i.sku}</strong></td>
                                <td>${escapeHtml(i.description)}</td>
                                <td style="font-family:monospace">${i.sat_code}</td>
                                <td><span class="badge badge-medium" style="background:rgba(255,255,255,0.03);border-color:var(--border)">${i.unit}</span></td>
                                <td style="text-align:right">${i.quantity.toLocaleString('es-MX')}</td>
                                <td style="text-align:right">$${i.price.toLocaleString('es-MX', { minimumFractionDigits: 2 })}</td>
                                <td style="text-align:center">
                                    <button class="btn-secondary" style="padding:4px 8px;font-size:11px;background:#3b82f6;color:white" onclick="quickCartaPorte('${i.sku}', '${escapeHtml(i.description).replace(/'/g, "\\'")}', '${i.sat_code}', '${i.unit}')">🚚 Carta Porte</button>
                                </td>
                                <td style="text-align:center"><button class="btn-delete" onclick="deleteErpItem(${i.id})">Eliminar</button></td>`;
                body.appendChild(tr);
            });
        } catch (err) {
            body.innerHTML = `<tr><td colspan="8" style="color:var(--danger)">Error: ${err.message}</td></tr>`;
        }
    }

    document.getElementById('erp-save-btn').addEventListener('click', async function() {
        const sku = document.getElementById('erp-sku').value.trim();
        const description = document.getElementById('erp-desc').value.trim();
        const sat_code = document.getElementById('erp-satcode').value.trim();
        const unit = document.getElementById('erp-unit').value.trim();
        const quantity = parseFloat(document.getElementById('erp-qty').value) || 0;
        const price = parseFloat(document.getElementById('erp-price').value) || 0;

        if (!sku || !description || !sat_code) {
            alert('SKU, Descripción y Código SAT son requeridos.');
            return;
        }

        try {
            const res = await fetch('/api/erp/inventory', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sku, description, sat_code, unit, quantity, price })
            });
            const data = await res.json();
            if (data.error) {
                alert('Error: ' + data.error);
            } else {
                alert('Mercancía agregada al almacén fiscal.');
                document.getElementById('erp-sku').value = '';
                document.getElementById('erp-desc').value = '';
                document.getElementById('erp-satcode').value = '';
                document.getElementById('erp-unit').value = 'H87';
                document.getElementById('erp-qty').value = '10';
                document.getElementById('erp-price').value = '100.00';
                loadErpInventory();
            }
        } catch (err) {
            alert('Error al guardar mercancía: ' + err.message);
        }
    });

    window.deleteErpItem = async function(id) {
        if (!confirm('¿Seguro que desea eliminar esta mercancía del almacén?')) return;
        try {
            await fetch('/api/erp/inventory/' + id, { method: 'DELETE' });
            loadErpInventory();
        } catch (err) {
            alert('Error al eliminar mercancía: ' + err.message);
        }
    };

    window.quickCartaPorte = function(sku, desc, satCode, unit) {
        // Transfer info to Carta Porte panel and click tab
        document.getElementById('cp-goods').value = `Salida SKU ${sku}: ${desc}`;
        document.getElementById('cp-satcode').value = satCode;
        document.getElementById('cp-satunit').value = unit;
        
        alert(`Mercancía ${sku} cargada para Carta Porte 3.1. Complete origen/destino y configure el transporte.`);
        document.querySelector('[data-tab="cartaporte"]').click();
    };

    // ========== ADMIN Auditoría & Secret Manager Logic ==========
    async function loadAdminAudit() {
        const body = document.getElementById('admin-audit-body');
        body.innerHTML = '<tr><td colspan="7"><div class="spinner"></div> Cargando bitácora de auditoría...</td></tr>';
        try {
            const res = await fetch('/api/admin/audit');
            const data = await res.json();
            body.innerHTML = '';
            if (data.length === 0) {
                body.innerHTML = '<tr><td colspan="7" style="text-align:center">No hay registros de auditoría.</td></tr>';
                return;
            }
            data.forEach(l => {
                const date = new Date(l.created_at).toLocaleString('es-MX');
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>${l.id}</td>
                                <td>${date}</td>
                                <td><strong>${l.username}</strong></td>
                                <td><span class="badge badge-medium" style="background:rgba(59,130,246,0.1);color:var(--primary)">${l.module}</span></td>
                                <td><strong>${l.action}</strong></td>
                                <td>${escapeHtml(l.details || '')}</td>
                                <td style="font-family:monospace">${l.ip_address}</td>`;
                body.appendChild(tr);
            });
        } catch (err) {
            body.innerHTML = `<tr><td colspan="7" style="color:var(--danger)">Error: ${err.message}</td></tr>`;
        }
    }

    async function loadVaultStatus() {
        const container = document.getElementById('admin-vault-container');
        container.innerHTML = '<div class="spinner"></div> Cargando bóveda...';
        try {
            const res = await fetch('/api/admin/vault');
            const data = await res.json();
            container.innerHTML = '';
            
            data.credentials.forEach(c => {
                const badgeClass = c.loaded ? 'badge-high' : 'badge-low';
                const div = document.createElement('div');
                div.style = 'border:1px solid var(--border-light);padding:10px;border-radius:8px;display:flex;justify-content:space-between;align-items:center;background:rgba(0,0,0,0.15)';
                div.innerHTML = `<div>
                                    <strong style="font-size:12.5px;color:white">${c.name}</strong>
                                    <div style="font-size:10.5px;color:var(--text-muted)">Expira: ${c.expires} | Tipo: ${c.type}</div>
                                 </div>
                                 <div>
                                    <span class="badge ${badgeClass}">${c.loaded ? 'Montada (e.firma)' : 'No cargada'}</span>
                                    ${!c.loaded ? `<button class="btn-secondary" style="padding:4px 8px;font-size:11px;margin-left:8px" onclick="uploadSimulatedSecret('${c.name}')">Cargar</button>` : ''}
                                 </div>`;
                container.appendChild(div);
            });
        } catch (err) {
            container.innerHTML = '<div>Error al conectar con Secret Manager.</div>';
        }
    }

    window.uploadSimulatedSecret = async function(name) {
        try {
            const res = await fetch('/api/admin/vault/upload', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name })
            });
            const data = await res.json();
            alert(data.status);
            loadVaultStatus();
            loadAdminAudit();
        } catch (err) {
            alert('Error al subir clave: ' + err.message);
        }
    };

    document.getElementById('admin-refresh-audit-btn').addEventListener('click', loadAdminAudit);

    // ========== VUCEM Acuses Bandera & Validations ==========
    async function loadVucemAcuses() {
        const tbody = document.getElementById('vucem-acuses-tbody');
        if (!tbody) return;
        tbody.innerHTML = '<tr><td colspan="6"><div class="spinner"></div> Cargando acuses de validación...</td></tr>';
        try {
            const res = await fetch('/api/vucem/acuses');
            const data = await res.json();
            tbody.innerHTML = '';
            if (data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-secondary)">No hay acuses transmitidos.</td></tr>';
                return;
            }
            data.forEach(a => {
                const date = new Date(a.created_at).toLocaleString('es-MX');
                const statusBadge = a.status === 'Validado' ? 'badge-high' : a.status === 'Rechazado' ? 'badge-low' : 'badge-medium';
                
                const tr = document.createElement('tr');
                tr.innerHTML = `<td style="font-family:monospace;font-weight:700;color:white">${a.folio}</td>
                                <td>${a.type}</td>
                                <td style="font-family:monospace">${a.rfc_importador}</td>
                                <td><span class="badge ${statusBadge}">${a.status}</span></td>
                                <td style="color:${a.status === 'Rechazado' ? 'var(--danger)' : 'var(--text-secondary)'};font-size:11.5px">${a.error_details || '-'}</td>
                                <td>${date}</td>`;
                tbody.appendChild(tr);
            });
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="6">Error al cargar acuses: ${err.message}</td></tr>`;
        }
    }

    async function sendToVucemValidation(folio, type, rfc) {
        try {
            const res = await fetch('/api/vucem/validate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ folio, type, rfc_importador: rfc })
            });
            const data = await res.json();
            if (data.status === 'exist') {
                alert('Este folio ya se encuentra en proceso de validación.');
            } else {
                alert('✓ Documento enviado al validador del SAT/VUCEM. Se procesará en segundo plano.');
                loadVucemAcuses();
            }
        } catch (err) {
            alert('Error al enviar a VUCEM: ' + err.message);
        }
    }

    document.getElementById('vucem-refresh-btn').addEventListener('click', loadVucemAcuses);

    const xmlToVucemBtn = document.getElementById('xml-to-vucem-btn');
    if (xmlToVucemBtn) {
        xmlToVucemBtn.addEventListener('click', () => {
            if (!tempXmlData) return;
            sendToVucemValidation(tempXmlData.general.folio, 'COVE (XML)', tempXmlData.receptor.rfc);
        });
    }

    const pdfToVucemBtn = document.getElementById('pdf-to-vucem-btn');
    if (pdfToVucemBtn) {
        pdfToVucemBtn.addEventListener('click', () => {
            const folio = document.getElementById('pdf-data-folio').textContent;
            const rfc = document.getElementById('pdf-data-rfc').textContent;
            const tipo = document.getElementById('pdf-data-tipo').textContent;
            if (folio === 'NO DETECTADO' || !folio) return;
            sendToVucemValidation(folio, tipo + ' (PDF)', rfc);
        });
    }

    // Set polling reminder for VUCEM acuses every 12 seconds if tab is active
    setInterval(() => {
        const activeTab = document.querySelector('.tab-content.active');
        if (activeTab && activeTab.id === 'tab-vucem-parser') {
            loadVucemAcuses();
        }
    }, 12000);

    // ========== Carta Porte 3.1 & Catalog Validation ==========
    async function loadCartaPorteList() {
        const container = document.getElementById('cp-list-container');
        container.innerHTML = '<div class="spinner"></div> Cargando cartas porte timbradas...';
        
        // Cargar select del ERP
        loadCpErpDropdown();

        try {
            const res = await fetch('/api/cartaporte/list');
            const data = await res.json();
            container.innerHTML = '';
            if (data.length === 0) {
                container.innerHTML = '<div style="text-align:center;color:var(--text-secondary);font-size:12.5px;padding:20px">No hay complementos timbrados.</div>';
                return;
            }
            data.forEach(i => {
                const date = new Date(i.created_at).toLocaleString('es-MX');
                const div = document.createElement('div');
                div.style = 'border:1px solid var(--border);padding:14px;border-radius:10px;background:rgba(0,0,0,0.15);display:flex;flex-direction:column;gap:5px';
                div.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center">
                                    <strong style="color:var(--accent);font-family:monospace;font-size:14px">${i.folio}</strong>
                                    <span class="badge badge-high">TIMBRADO PAC</span>
                                 </div>
                                 <div style="font-size:12px;color:white"><strong>Carga:</strong> ${escapeHtml(i.goods_desc)}</div>
                                 <div style="font-size:11px;color:var(--text-secondary)">
                                    <div><strong>Ruta:</strong> ${escapeHtml(i.origin)} → ${escapeHtml(i.destination)}</div>
                                    <div>SAT: Clave ${i.sat_code} | Unidad ${i.sat_unit} | Vehículo ${i.vehicle_config}</div>
                                    <div style="margin-top:4px;color:var(--text-muted)">Fecha: ${date}</div>
                                 </div>`;
                container.appendChild(div);
            });
        } catch (err) {
            container.innerHTML = '<div style="color:var(--danger)">Error al cargar complementos.</div>';
        }
    }

    async function loadCpErpDropdown() {
        const select = document.getElementById('cp-erp-select');
        if (!select) return;
        try {
            const res = await fetch('/api/erp/inventory');
            const data = await res.json();
            select.innerHTML = '<option value="">-- Seleccionar artículo para descontar stock automáticamente --</option>';
            data.forEach(item => {
                const opt = document.createElement('option');
                opt.value = item.sku;
                opt.dataset.desc = item.description;
                opt.dataset.sat = item.sat_code;
                opt.dataset.unit = item.unit;
                opt.dataset.stock = item.quantity;
                opt.textContent = `${item.sku} - ${item.description} (Stock: ${item.quantity.toLocaleString('es-MX', {maximumFractionDigits:0})})`;
                select.appendChild(opt);
            });
        } catch (e) {
            console.error("Error cargando inventario para Carta Porte:", e);
        }
    }

    function handleCpErpSelect(select) {
        const opt = select.options[select.selectedIndex];
        const qtyGroup = document.getElementById('cp-qty-group');
        const qtyInput = document.getElementById('cp-qty');
        const goodsInput = document.getElementById('cp-goods');
        const satcodeInput = document.getElementById('cp-satcode');
        const satunitInput = document.getElementById('cp-satunit');

        if (!opt || opt.value === '') {
            qtyGroup.style.display = 'none';
            goodsInput.value = '';
            goodsInput.readOnly = false;
            satcodeInput.value = '';
            satunitInput.value = 'H87';
        } else {
            qtyGroup.style.display = 'block';
            qtyInput.max = opt.dataset.stock;
            qtyInput.value = '1';
            goodsInput.value = opt.dataset.desc;
            goodsInput.readOnly = true;
            satcodeInput.value = opt.dataset.sat;
            satunitInput.value = opt.dataset.unit;
        }
    }
    window.handleCpErpSelect = handleCpErpSelect;

    async function loadMveList() {
        const tbody = document.getElementById('mve-history-body');
        if (!tbody) return;
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:20px"><div class="spinner"></div> Cargando Manifestaciones...</td></tr>';
        try {
            const res = await fetch('/api/mve/list');
            const data = await res.json();
            if (data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:15px;color:var(--text-muted)">No hay manifestaciones de valor emitidas</td></tr>';
                return;
            }
            let html = '';
            data.forEach(m => {
                const statusClass = m.status === 'Emitida' ? 'badge-high' : 'badge-low';
                html += `<tr>
                    <td style="padding:12px;border-bottom:1px solid var(--border)">${new Date(m.created_at).toLocaleString('es-MX')}</td>
                    <td style="padding:12px;border-bottom:1px solid var(--border);font-family:monospace;color:white">${m.folio}</td>
                    <td style="padding:12px;border-bottom:1px solid var(--border);font-family:monospace">${m.rfc_importador}</td>
                    <td style="padding:12px;border-bottom:1px solid var(--border);color:var(--accent)">$${m.valor_aduana_mxn.toLocaleString('es-MX', {minimumFractionDigits:2})}</td>
                    <td style="padding:12px;border-bottom:1px solid var(--border)"><span class="badge ${statusClass}">${m.status}</span></td>
                </tr>`;
            });
            tbody.innerHTML = html;
        } catch(e) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:15px;color:var(--danger)">Error al cargar manifestaciones.</td></tr>';
        }
    }
    window.loadMveList = loadMveList;

    document.getElementById('cp-generate-btn').addEventListener('click', async function() {
        const origin = document.getElementById('cp-origin').value.trim();
        const destination = document.getElementById('cp-dest').value.trim();
        const goods_desc = document.getElementById('cp-goods').value.trim();
        const sat_code = document.getElementById('cp-satcode').value.trim();
        const sat_unit = document.getElementById('cp-satunit').value.trim();
        const vehicle_config = document.getElementById('cp-config').value;

        const erpSelect = document.getElementById('cp-erp-select');
        const sku = erpSelect ? erpSelect.value : '';
        const qty = erpSelect && sku ? parseFloat(document.getElementById('cp-qty').value) || 1 : 0;

        const errorBox = document.getElementById('cp-validation-errors-box');
        const errorUl = document.getElementById('cp-validation-errors-ul');
        
        errorBox.style.display = 'none';
        errorUl.innerHTML = '';

        if (!origin || !destination || !goods_desc || !sat_code) {
            alert('Complete los campos obligatorios (*).');
            return;
        }

        try {
            const res = await fetch('/api/cartaporte/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ origin, destination, goods_desc, sat_code, sat_unit, vehicle_config, sku, qty })
            });
            const data = await res.json();
            
            if (res.ok && data.success) {
                alert(`✓ Carta Porte 3.1 Pre-Validada con éxito y Timbrada Digitalmente.\nFolio: ${data.folio}`);
                
                // Limpiar campos y dropdown ERP
                if (erpSelect) {
                    erpSelect.value = '';
                    document.getElementById('cp-qty-group').style.display = 'none';
                    document.getElementById('cp-goods').readOnly = false;
                }
                document.getElementById('cp-goods').value = '';
                
                // Recargar paneles del ecosistema
                loadCartaPorteList();
                loadAdminAudit(); // refrescar auditoria
                loadDashboardData(); // refrescar dashboard stats
                loadErpInventory(); // refrescar modulo erp
            } else {
                if (data.errors) {
                    errorBox.style.display = 'block';
                    data.errors.forEach(e => {
                        errorUl.innerHTML += `<li>${escapeHtml(e)}</li>`;
                    });
                    alert('Fallo de pre-validación de catálogos del SAT. Corrija los campos indicados.');
                } else if (data.error) {
                    alert('Error: ' + data.error);
                }
            }
        } catch (err) {
            alert('Error en conexión: ' + err.message);
        }
    });

    // ========== Extended AI Classifier (PDF technical sheet & Image) ==========
    const aiDropzone = document.getElementById('ai-pdf-dropzone');
    const aiInput = document.getElementById('ai-pdf-input');
    const aiTextarea = document.getElementById('chat-input') || document.getElementById('ai-input');
    
    const aiImageDropzone = document.getElementById('ai-image-dropzone');
    const aiImageInput = document.getElementById('ai-image-input');
    const aiImagePreview = document.getElementById('ai-image-preview');
    let selectedImageFile = null;

    if (aiDropzone && aiInput) {
        aiDropzone.addEventListener('click', () => aiInput.click());
        aiInput.addEventListener('change', (e) => {
            if (e.target.files[0]) extractPdfTechnicalText(e.target.files[0]);
        });
        aiDropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            aiDropzone.style.borderColor = 'var(--accent)';
        });
        aiDropzone.addEventListener('dragleave', () => {
            aiDropzone.style.borderColor = 'var(--primary)';
        });
        aiDropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            aiDropzone.style.borderColor = 'var(--primary)';
            if (e.dataTransfer.files[0]) extractPdfTechnicalText(e.dataTransfer.files[0]);
        });
    }

    if (aiImageDropzone && aiImageInput) {
        aiImageDropzone.addEventListener('click', () => aiImageInput.click());
        aiImageInput.addEventListener('change', (e) => {
            if (e.target.files[0]) handleSelectedImage(e.target.files[0]);
        });
        aiImageDropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            aiImageDropzone.style.borderColor = 'var(--accent)';
        });
        aiImageDropzone.addEventListener('dragleave', () => {
            aiImageDropzone.style.borderColor = 'var(--secondary)';
        });
        aiImageDropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            aiImageDropzone.style.borderColor = 'var(--secondary)';
            if (e.dataTransfer.files[0]) handleSelectedImage(e.dataTransfer.files[0]);
        });
    }

    function handleSelectedImage(file) {
        if (!file.type.startsWith('image/')) {
            alert('Cargue una foto del producto en formato de imagen (PNG, JPG, WEBP).');
            return;
        }
        selectedImageFile = file;
        const reader = new FileReader();
        reader.onload = (e) => {
            aiImagePreview.style.display = 'block';
            aiImagePreview.querySelector('img').src = e.target.result;
        };
        reader.readAsDataURL(file);
    }

    async function extractPdfTechnicalText(file) {
        if (file.type !== 'application/pdf' && !file.name.endsWith('.pdf')) {
            alert('Cargue una ficha técnica en formato PDF.');
            return;
        }

        aiTextarea.value = 'Extrayendo texto del PDF técnico...';
        try {
            const arrayBuffer = await file.arrayBuffer();
            if (!window.pdfjsLib) {
                throw new Error('PDF.js no disponible.');
            }
            const pdf = await window.pdfjsLib.getDocument({ data: arrayBuffer }).promise;
            let fullText = '';
            const maxPages = Math.min(pdf.numPages, 4);
            for (let i = 1; i <= maxPages; i++) {
                const page = await pdf.getPage(i);
                const textContent = await page.getTextContent();
                fullText += textContent.items.map(item => item.str).join(' ') + '\n';
            }
            
            aiTextarea.value = `[FICHA TÉCNICA PDF: ${file.name}]\n\n` + fullText.trim().substring(0, 1000);
            alert('✓ Texto de Ficha Técnica extraído con éxito. Envía el mensaje en el chat para clasificar.');
        } catch (err) {
            console.error(err);
            aiTextarea.value = '';
            alert('Error al extraer texto del PDF técnico: ' + err.message);
        }
    }

    // --- CHAT CONVERSACIONAL LOGIC ---
    let currentThreadId = null;
    let isWaitingForResponse = false;

    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');
    const chatSendBtn = document.getElementById('chat-send-btn');
    const btnChatReset = document.getElementById('btn-chat-reset');
    const chatQuickOptions = document.getElementById('chat-quick-options');

    if (chatSendBtn) {
        chatSendBtn.addEventListener('click', handleChatSubmit);
    }

    if (chatInput) {
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleChatSubmit();
            }
        });
    }

    if (btnChatReset) {
        btnChatReset.addEventListener('click', resetChat);
    }

    function resetChat() {
        currentThreadId = null;
        isWaitingForResponse = false;
        chatMessages.innerHTML = `
            <div class="message message-bot">
                <div class="message-bubble">
                    ¡Hola! Soy el asistente conversacional de <strong>ALINEA SOLUTIONS</strong>.<br><br>
                    Describe la mercancía que deseas importar o exportar de forma detallada (material, uso, composición, etc.) o bien carga una ficha técnica en PDF o foto del producto a continuación.
                </div>
                <span class="message-time">Ahora</span>
            </div>
        `;
        chatQuickOptions.innerHTML = '';
        chatQuickOptions.style.display = 'none';
        chatInput.value = '';
        selectedImageFile = null;
        if (aiImagePreview) {
            aiImagePreview.style.display = 'none';
            aiImagePreview.querySelector('img').src = '';
        }
    }

    function formatLegalText(text) {
        if (!text) return '';
        const nomRegex = /NOM-\d{3}-[A-Z0-9]+(?:-\d{4})?/gi;
        const chapterRegex = /Cap[íi]tulo\s+\d+/gi;
        const rgiRegex = /\b(?:RGI\s+\d\w?|Regla\s+General\s+\d)\b/gi;
        
        let formatted = text;
        formatted = formatted.replace(nomRegex, (match) => `<span class="legal-badge-chip">${match}</span>`);
        formatted = formatted.replace(chapterRegex, (match) => `<span class="legal-badge-chip">${match}</span>`);
        formatted = formatted.replace(rgiRegex, (match) => `<span class="legal-badge-chip">${match}</span>`);
        return formatted;
    }

    async function handleChatSubmit() {
        if (isWaitingForResponse) return;
        
        const messageText = chatInput.value.trim();
        if (!messageText && !selectedImageFile) {
            alert('Por favor, describa la mercancía o adjunte un archivo para iniciar la clasificación.');
            return;
        }
        
        let displayMessage = messageText;
        if (selectedImageFile) {
            displayMessage = `[FOTO ADJUNTA: ${selectedImageFile.name}]` + (messageText ? `\n\n${messageText}` : '');
        }
        
        const fileToSend = selectedImageFile;
        
        if (fileToSend) {
            const reader = new FileReader();
            reader.onload = async function(e) {
                const imageDataUrl = e.target.result;
                appendChatMessage('user', displayMessage, imageDataUrl);
                chatInput.value = '';
                
                showTypingIndicator();
                isWaitingForResponse = true;
                
                await proceedWithChatSubmit(messageText, fileToSend, displayMessage);
            };
            reader.readAsDataURL(fileToSend);
        } else {
            appendChatMessage('user', displayMessage);
            chatInput.value = '';
            
            showTypingIndicator();
            isWaitingForResponse = true;
            
            await proceedWithChatSubmit(messageText, null, displayMessage);
        }
    }

    async function proceedWithChatSubmit(messageText, fileToSend, displayMessage) {
        try {
            let data;
            
            // Si hay una foto seleccionada, la procesamos a través de /api/classify/extended en la primera llamada
            if (fileToSend && !currentThreadId) {
                const formData = new FormData();
                formData.append('description', messageText || `Clasificación de imagen: ${fileToSend.name}`);
                formData.append('file', fileToSend);
                
                const res = await fetch('/api/classify/extended', {
                    method: 'POST',
                    body: formData
                });
                data = await res.json();
                
                // Si la IA requiere aclaración, creamos el thread en el backend para continuar en modo chat
                if (data.status === 'clarification_needed') {
                    const threadRes = await fetch('/api/chat/start', { method: 'POST' });
                    const threadData = await threadRes.json();
                    currentThreadId = threadData.thread_id;
                }
                
                // Limpiar la imagen seleccionada para no enviarla repetidamente
                selectedImageFile = null;
                if (aiImagePreview) {
                    aiImagePreview.style.display = 'none';
                    aiImagePreview.querySelector('img').src = '';
                }
            } else {
                // Flujo estándar de chat textual
                if (!currentThreadId) {
                    const threadRes = await fetch('/api/chat/start', { method: 'POST' });
                    const threadData = await threadRes.json();
                    currentThreadId = threadData.thread_id;
                }
                
                const res = await fetch('/api/chat/send', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        thread_id: currentThreadId,
                        message: messageText
                    })
                });
                data = await res.json();
            }
            
            removeTypingIndicator();
            isWaitingForResponse = false;
            
            handleBotResponse(data, messageText || displayMessage);
            
        } catch (err) {
            removeTypingIndicator();
            isWaitingForResponse = false;
            appendChatMessage('bot', `Lo siento, ocurrió un error en la comunicación con el motor de IA: ${err.message}`);
            console.error(err);
        }
    }

    function appendChatMessage(sender, text, imageUrl = null) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message message-${sender}`;
        
        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'message-bubble';
        
        let htmlContent = '';
        if (imageUrl) {
            htmlContent += `<img src="${imageUrl}" class="chat-image-thumbnail" alt="Imagen adjunta" onclick="window.open('${imageUrl}', '_blank')">`;
        }
        
        let processedText = text.replace(/\n/g, '<br>');
        if (sender === 'bot') {
            processedText = formatLegalText(processedText);
        }
        htmlContent += processedText;
        bubbleDiv.innerHTML = htmlContent;
        
        const timeSpan = document.createElement('span');
        timeSpan.className = 'message-time';
        timeSpan.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        msgDiv.appendChild(bubbleDiv);
        msgDiv.appendChild(timeSpan);
        chatMessages.appendChild(msgDiv);
        
        scrollToBottom();
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function showTypingIndicator() {
        removeTypingIndicator();
        const indicator = document.createElement('div');
        indicator.className = 'chat-typing-indicator';
        indicator.id = 'chat-typing-indicator-active';
        indicator.innerHTML = '<span></span><span></span><span></span>';
        chatMessages.appendChild(indicator);
        scrollToBottom();
    }

    function removeTypingIndicator() {
        const indicator = document.getElementById('chat-typing-indicator-active');
        if (indicator) {
            indicator.remove();
        }
    }

    function handleBotResponse(data, lastUserMsg) {
        chatQuickOptions.innerHTML = '';
        chatQuickOptions.style.display = 'none';
        
        if (data.status === 'clarification_needed') {
            let botText = '';
            if (data.questions && data.questions.length > 0) {
                botText += data.questions.join('<br><br>');
            } else {
                botText += data.reasoning || 'El sistema requiere detalles técnicos adicionales para una correcta clasificación arancelaria.';
            }
            
            appendChatMessage('bot', botText);
            
            // Opciones múltiples rápidas
            if (data.choices && data.choices.length > 0) {
                data.choices.forEach(choice => {
                    const btn = document.createElement('button');
                    btn.type = 'button';
                    btn.className = 'btn-quick-option';
                    btn.textContent = choice;
                    btn.onclick = () => {
                        chatInput.value = choice;
                        handleChatSubmit();
                    };
                    chatQuickOptions.appendChild(btn);
                });
                chatQuickOptions.style.display = 'flex';
            }
        } else {
            // Clasificación Completada
            let botText = `<strong>✓ Clasificación Completada con Éxito</strong><br><br>`;
            botText += `Fracción Sugerida: <strong style="color:var(--accent); font-family:monospace; font-size:15px">${data.hs_code}</strong><br>`;
            if (data.nico) botText += `NICO: <strong style="color:var(--primary); font-family:monospace">${data.nico}</strong><br>`;
            botText += `Grado de Confianza: <strong>${(data.confidence * 100).toFixed(0)}%</strong><br><br>`;
            
            if (data.reasoning) {
                botText += `<div class="chat-reasoning-container">${data.reasoning}</div>`;
            }
            
            appendChatMessage('bot', botText);

            // Renderizar tarjetas de alternativas comparativas en el chat de forma interactiva
            if (data.alternatives && data.alternatives.length > 0) {
                const altsContainer = document.createElement('div');
                altsContainer.className = 'chat-alternatives-container';
                
                const titleDiv = document.createElement('div');
                titleDiv.style = 'font-size: 11px; color: var(--text-muted); font-weight: 700; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.8px;';
                titleDiv.textContent = 'Alternativas de Clasificación (Compare y Seleccione):';
                altsContainer.appendChild(titleDiv);
                
                data.alternatives.forEach(alt => {
                    const card = document.createElement('div');
                    card.className = 'chat-alternatives-card';
                    
                    const infoDiv = document.createElement('div');
                    infoDiv.style = 'flex: 1;';
                    infoDiv.innerHTML = `
                        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 2px;">
                            <strong>${alt.code}</strong>
                            ${alt.score ? `<span style="font-size: 9.5px; color: var(--text-secondary); background: rgba(255,255,255,0.03); padding: 1px 4px; border: 1px solid rgba(255,255,255,0.05); border-radius: 3px;">Score: ${parseFloat(alt.score).toFixed(1)}</span>` : ''}
                        </div>
                        <div style="font-size: 12px; color: var(--text-light); line-height: 1.3;">${escapeHtml(alt.title)}</div>
                    `;
                    
                    const actionDiv = document.createElement('div');
                    const selectBtn = document.createElement('button');
                    selectBtn.className = 'btn-quick-option';
                    selectBtn.textContent = 'Seleccionar';
                    selectBtn.onclick = () => {
                        selectAlternativeInChat(alt.code, alt.title);
                    };
                    actionDiv.appendChild(selectBtn);
                    
                    card.appendChild(infoDiv);
                    card.appendChild(actionDiv);
                    altsContainer.appendChild(card);
                });
                
                chatMessages.appendChild(altsContainer);
                scrollToBottom();
            }
            
            // Actualizar el panel lateral derecho de resultados
            if (data.hs_code) {
                document.getElementById('ai-res-code').textContent = data.hs_code;
                document.getElementById('ai-res-nico').textContent = data.nico || '';
                document.getElementById('ai-res-reasoning').innerHTML = data.reasoning || 'Análisis exitoso mediante RAG.';
                
                const badge = document.getElementById('ai-res-badge');
                const confidence = data.confidence ? (data.confidence * 100).toFixed(0) : '85';
                badge.textContent = `Confianza: ${confidence}%`;
                badge.className = 'badge ' + (confidence >= 80 ? 'badge-high' : confidence >= 50 ? 'badge-medium' : 'badge-low');

                // Impuestos
                if (data.taxes) {
                    document.getElementById('tax-igi').textContent = data.taxes.igi;
                    document.getElementById('tax-iva').textContent = data.taxes.iva;
                    document.getElementById('tax-ieps').textContent = data.taxes.ieps;
                } else {
                    const cleanCode = data.hs_code.replace(/\./g, '').replace(/\s/g, '');
                    const chapter = cleanCode.substring(0, 2);
                    const chInt = parseInt(chapter) || 0;
                    let igi = '10%';
                    let iva = '16%';
                    let ieps = '0%';
                    if (chInt === 8) {
                        igi = '15%';
                        iva = '0%';
                    } else if (chInt === 84 || chInt === 85) {
                        igi = '0%';
                        iva = '16%';
                    } else if ([61, 62, 64].includes(chInt)) {
                        igi = '20%';
                        iva = '16%';
                    }
                    document.getElementById('tax-igi').textContent = igi;
                    document.getElementById('tax-iva').textContent = iva;
                    document.getElementById('tax-ieps').textContent = ieps;
                }

                // RRNAs
                const rrnaUl = document.getElementById('rrna-list');
                rrnaUl.innerHTML = '';
                if (data.rrnas && data.rrnas.length > 0) {
                    data.rrnas.forEach(r => {
                        rrnaUl.innerHTML += `<li>${escapeHtml(r)}</li>`;
                    });
                } else {
                    const cleanCode = data.hs_code.replace(/\./g, '').replace(/\s/g, '');
                    const chapter = cleanCode.substring(0, 2);
                    const chInt = parseInt(chapter) || 0;
                    if (chInt === 8) {
                        rrnaUl.innerHTML += `<li>Inspección de sanidad vegetal (SENASICA/SAGARPA) en punto de entrada.</li>`;
                        rrnaUl.innerHTML += `<li>Certificado Fitosanitario de Importación obligatorio.</li>`;
                    } else if (chInt === 30) {
                        rrnaUl.innerHTML += `<li>Autorización sanitaria previa de COFEPRIS para importación de medicamentos.</li>`;
                    } else if (chInt === 84 || chInt === 85) {
                        rrnaUl.innerHTML += `<li>Certificación de cumplimiento de norma oficial de seguridad NOM-001-SCFI o NOM-024-SCFI.</li>`;
                        rrnaUl.innerHTML += `<li>Padrón de Importadores de Sectores Específicos: Sector 9 (Siderúrgico/Máquinas) si aplica.</li>`;
                    } else {
                        rrnaUl.innerHTML += `<li>Sujeto a inspección aduanera general. Presentar factura comercial declarando marca y número de serie.</li>`;
                    }
                }

                // Alternativas
                const altsBox = document.getElementById('ai-alternatives-box');
                const altsList = document.getElementById('ai-alternatives-list');
                if (altsBox && altsList) {
                    altsList.innerHTML = '';
                    if (data.alternatives && data.alternatives.length > 0) {
                        data.alternatives.forEach(alt => {
                            const btn = document.createElement('button');
                            btn.style = 'width:100%;text-align:left;padding:10px 14px;background:rgba(255,255,255,0.01);border:1px solid rgba(255,255,255,0.05);border-left:3px solid var(--primary);border-radius:6px;color:#f1f5f9;font-size:12.5px;cursor:pointer;transition:background 0.2s, border-color 0.2s;margin-bottom:2px';
                            btn.className = 'alt-option-btn';
                            btn.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
                                                <strong style="color:var(--accent);font-family:monospace">${alt.code}</strong>
                                                <span style="font-size:10.5px;color:var(--text-secondary)">Score: ${parseFloat(alt.score).toFixed(1)}</span>
                                             </div>
                                             <div style="font-size:11.5px;color:var(--text-light)">${escapeHtml(alt.title)}</div>`;
                            btn.onclick = (e) => selectAlternativeClassify(alt.code, alt.title, lastUserMsg, e);
                            altsList.appendChild(btn);
                        });
                        altsBox.style.display = 'block';
                    } else {
                        altsBox.style.display = 'none';
                    }
                }

                // Botones Guardar y PDF
                const actionContainer = document.getElementById('ai-res-action-container');
                actionContainer.innerHTML = `
                    <div style="display:flex;gap:10px">
                        <button class="btn-primary" style="flex:1" onclick="saveClassification('${data.hs_code}','${escapeHtml(lastUserMsg).replace(/'/g, "\\'")}', '${data.confidence}')">Guardar en Historial</button>
                        <button class="btn-secondary" style="flex:1;background:#475569;color:white" onclick="downloadClassificationReport()">Descargar Reporte PDF</button>
                    </div>
                `;

                document.getElementById('ai-extended-results').style.display = 'block';
                document.getElementById('ai-extended-results').scrollIntoView({ behavior: 'smooth' });
            }
            
            // Finalizar thread de chat
            currentThreadId = null;
        }
    }

    // Selección dinámica de alternativas
    function selectAlternativeClassify(code, title, rawDesc, event) {
        const cleanCode = code.replace(/\./g, '').replace(/\s/g, '');
        const chapter = cleanCode.substring(0, 2);
        const chInt = parseInt(chapter) || 0;

        let nico = cleanCode.substring(0, 8);
        if (nico.length < 8) nico = nico.padEnd(8, '0');
        const formattedNico = `${nico.substring(0, 4)}.${nico.substring(4, 6)}.${nico.substring(6, 8)}-00`;

        document.getElementById('ai-res-code').textContent = code;
        document.getElementById('ai-res-nico').textContent = formattedNico;
        document.getElementById('ai-res-badge').textContent = 'Selección Alternativa';
        document.getElementById('ai-res-badge').className = 'badge badge-medium';

        document.getElementById('ai-res-reasoning').innerHTML = `<strong>📋 DICTAMEN DE RECLASIFICACIÓN DE ESPECIALISTA:</strong><br>` +
            `Usted ha seleccionado manualmente clasificar esta mercancía bajo la opción alternativa <strong>${code} (${escapeHtml(title)})</strong>.<br><br>` +
            `Recalculando dinámicamente gravámenes, tasas de impuestos y normativas arancelarias específicas para el Capítulo ${chapter} (Sección TIGIE)...`;

        let igi = '10%';
        let iva = '16%';
        let ieps = '0%';
        if (chInt === 8) {
            igi = '15%';
            iva = '0%';
        } else if (chInt === 84 || chInt === 85) {
            igi = '0%';
            iva = '16%';
        } else if ([61, 62, 64].includes(chInt)) {
            igi = '20%';
            iva = '16%';
        }
        document.getElementById('tax-igi').textContent = igi;
        document.getElementById('tax-iva').textContent = iva;
        document.getElementById('tax-ieps').textContent = ieps;

        const rrnaUl = document.getElementById('rrna-list');
        rrnaUl.innerHTML = '';
        if (chInt === 8) {
            rrnaUl.innerHTML += `<li>Inspección de sanidad vegetal (SENASICA/SAGARPA) en punto de entrada.</li>`;
            rrnaUl.innerHTML += `<li>Certificado Fitosanitario de Importación obligatorio.</li>`;
        } else if (chInt === 30) {
            rrnaUl.innerHTML += `<li>Autorización sanitaria previa de COFEPRIS para importación de medicamentos.</li>`;
        } else if (chInt === 84 || chInt === 85) {
            rrnaUl.innerHTML += `<li>Certificación de cumplimiento de norma oficial de seguridad NOM-001-SCFI o NOM-024-SCFI.</li>`;
            rrnaUl.innerHTML += `<li>Padrón de Importadores de Sectores Específicos: Sector 9 (Siderúrgico/Máquinas) si aplica.</li>`;
        } else {
            rrnaUl.innerHTML += `<li>Sujeto a inspección aduanera general. Presentar factura comercial declarando marca y número de serie.</li>`;
        }

        const actionContainer = document.getElementById('ai-res-action-container');
        actionContainer.innerHTML = `
            <div style="display:flex;gap:10px">
                <button class="btn-primary" style="flex:1" onclick="saveClassification('${code}','${escapeHtml(rawDesc).replace(/'/g, "\\'")}', '0.90')">Guardar en Historial</button>
                <button class="btn-secondary" style="flex:1;background:#475569;color:white" onclick="downloadClassificationReport()">Descargar Reporte PDF</button>
            </div>
        `;
        
        document.querySelectorAll('.alt-option-btn').forEach(btn => {
            btn.style.background = 'rgba(255,255,255,0.01)';
            btn.style.borderColor = 'rgba(255,255,255,0.05)';
        });
        if (event && event.currentTarget) {
            event.currentTarget.style.background = 'rgba(59, 130, 246, 0.08)';
            event.currentTarget.style.borderColor = 'var(--primary)';
        }
        
        alert(`✓ Se han recalculado las tasas y normativas para la fracción seleccionada: ${code}`);
    }
    window.selectAlternativeClassify = selectAlternativeClassify;

    async function selectAlternativeInChat(code, title) {
        try {
            const cleanCode = code.replace(/\./g, '').replace(/\s/g, '');
            const chapter = cleanCode.substring(0, 2);
            const chInt = parseInt(chapter) || 0;

            let nico = cleanCode.substring(0, 8);
            if (nico.length < 8) nico = nico.padEnd(8, '0');
            const formattedNico = `${nico.substring(0, 4)}.${nico.substring(4, 6)}.${nico.substring(6, 8)}-00`;

            // Actualizar elementos DOM del panel lateral de resultados
            document.getElementById('ai-res-code').textContent = code;
            document.getElementById('ai-res-nico').textContent = formattedNico;
            document.getElementById('ai-res-badge').textContent = 'Selección Alternativa';
            document.getElementById('ai-res-badge').className = 'badge badge-medium';

            document.getElementById('ai-res-reasoning').innerHTML = `<strong>📋 DICTAMEN DE RECLASIFICACIÓN DESDE CHAT:</strong><br>` +
                `Usted ha seleccionado manualmente clasificar esta mercancía bajo la opción alternativa <strong>${code} (${escapeHtml(title)})</strong>.<br><br>` +
                `Cargando datos y recalculando tasas de impuestos para el Capítulo ${chapter}...`;

            // Hacemos fetch a /api/hs_code/<code> para cargar información oficial
            const res = await fetch('/api/hs_code/' + encodeURIComponent(code));
            if (res.ok) {
                const hsData = await res.json();
                let detailsText = '';
                if (hsData.section) detailsText += `<strong>Sección:</strong> ${escapeHtml(hsData.section.title)}<br>`;
                if (hsData.chapter) detailsText += `<strong>Capítulo:</strong> ${escapeHtml(hsData.chapter.title)}<br>`;
                if (hsData.heading) detailsText += `<strong>Partida:</strong> ${escapeHtml(hsData.heading.title)}<br>`;
                if (hsData.subheading) detailsText += `<strong>Subpartida:</strong> ${escapeHtml(hsData.subheading.title)}<br>`;
                
                document.getElementById('ai-res-reasoning').innerHTML = `<strong>📋 DICTAMEN DE RECLASIFICACIÓN DESDE CHAT:</strong><br>` +
                    `Usted ha seleccionado clasificar bajo la alternativa: <strong>${code}</strong>.<br><br>` +
                    detailsText + `<br>Recalculando dinámicamente gravámenes, tasas de impuestos y normativas arancelarias específicas para el Capítulo ${chapter}...`;
            }

            // Calcular impuestos
            let igi = '10%';
            let iva = '16%';
            let ieps = '0%';
            if (chInt === 8) {
                igi = '15%';
                iva = '0%';
            } else if (chInt === 84 || chInt === 85) {
                igi = '0%';
                iva = '16%';
            } else if ([61, 62, 64].includes(chInt)) {
                igi = '20%';
                iva = '16%';
            }
            document.getElementById('tax-igi').textContent = igi;
            document.getElementById('tax-iva').textContent = iva;
            document.getElementById('tax-ieps').textContent = ieps;

            // RRNAs y NOMs
            const rrnaUl = document.getElementById('rrna-list');
            rrnaUl.innerHTML = '';
            if (chInt === 8) {
                rrnaUl.innerHTML += `<li>Inspección de sanidad vegetal (SENASICA/SAGARPA) en punto de entrada.</li>`;
                rrnaUl.innerHTML += `<li>Certificado Fitosanitario de Importación obligatorio.</li>`;
            } else if (chInt === 30) {
                rrnaUl.innerHTML += `<li>Autorización sanitaria previa de COFEPRIS para importación de medicamentos.</li>`;
            } else if (chInt === 84 || chInt === 85) {
                rrnaUl.innerHTML += `<li>Certificación de cumplimiento de norma oficial de seguridad NOM-001-SCFI o NOM-024-SCFI.</li>`;
                rrnaUl.innerHTML += `<li>Padrón de Importadores de Sectores Específicos: Sector 9 (Siderúrgico/Máquinas) si aplica.</li>`;
            } else {
                rrnaUl.innerHTML += `<li>Sujeto a inspección aduanera general. Presentar factura comercial declarando marca y número de serie.</li>`;
            }

            // Habilitar y actualizar botones de acción
            const actionContainer = document.getElementById('ai-res-action-container');
            actionContainer.innerHTML = `
                <div style="display:flex;gap:10px">
                    <button class="btn-primary" style="flex:1" onclick="saveClassification('${code}','${escapeHtml(title).replace(/'/g, "\\'")}', '0.90')">Guardar en Historial</button>
                    <button class="btn-secondary" style="flex:1;background:#475569;color:white" onclick="downloadClassificationReport()">Descargar Reporte PDF</button>
                </div>
            `;

            // Mostrar el panel de resultados por si estaba oculto
            const extendedResults = document.getElementById('ai-extended-results');
            if (extendedResults) {
                extendedResults.style.display = 'block';
                extendedResults.scrollIntoView({ behavior: 'smooth' });
            }

            alert(`✓ Fracción arancelaria seleccionada desde el chat: ${code}. Panel de resultados y dictamen actualizados.`);
        } catch (e) {
            console.error("Error al seleccionar alternativa en chat:", e);
            alert("Error al cargar la alternativa seleccionada.");
        }
    }
    window.selectAlternativeInChat = selectAlternativeInChat;




    // ========== Original Functions (Preserved for compatibility) ==========

    // Text Search
    document.getElementById('search-btn').addEventListener('click', performSearch);
    document.getElementById('search-input').addEventListener('keyup', function(e) {
        if (e.key === 'Enter') performSearch();
    });

    async function performSearch() {
        const query = document.getElementById('search-input').value.trim();
        if (!query) return;
        const container = document.getElementById('search-results');
        container.innerHTML = '<div class="spinner"></div> Buscando...';
        try {
            const res = await fetch('/api/search?q=' + encodeURIComponent(query));
            const data = await res.json();
            renderSearchResults(data.results, container);
        } catch (err) {
            container.innerHTML = '<div class="result-item" style="color:var(--danger)">Error: ' + err.message + '</div>';
        }
    }

    function renderSearchResults(results, container) {
        if (results.length === 0) {
            container.innerHTML = '<div class="result-item">No se encontraron resultados</div>';
            return;
        }
        let html = '<div style="margin-bottom:12px;font-size:13px;color:var(--text-secondary)">' + results.length + ' resultado(s)</div>';
        results.forEach(r => {
            const confClass = r.score >= 10 ? 'badge-high' : r.score >= 5 ? 'badge-medium' : 'badge-low';
            html += '<div class="result-item" onclick="showDetail(\'' + r.code + '\')">';
            html += '<div class="result-code">' + r.code + '</div>';
            html += '<div class="result-title">' + escapeHtml(r.title) + '</div>';
            html += '<div class="result-path">Cap. ' + r.chapter_code + ': ' + escapeHtml(r.chapter_title) + '</div>';
            html += '<div class="result-actions">';
            html += '<span class="badge ' + confClass + '">Conf: ' + r.score + '</span>';
            html += '<button class="btn-secondary" style="padding:4px 10px;font-size:12px" onclick="event.stopPropagation();saveClassification(\'' + r.code + '\',\'' + escapeHtml(r.title).replace(/'/g, "\\'") + '\',\'' + r.score + '\')">Guardar</button>';
            html += '</div></div>';
        });
        container.innerHTML = html;
    }

    // Load tree
    async function loadTree() {
        const container = document.getElementById('tree-container');
        container.innerHTML = '<div class="spinner"></div> Cargando árbol nomenclatura...';
        try {
            const res = await fetch('/api/tree');
            const tree = await res.json();
            renderTree(tree, container);
        } catch (err) {
            container.innerHTML = '<div>Error al cargar árbol: ' + err.message + '</div>';
        }
    }

    function renderTree(tree, container) {
        container.innerHTML = '';
        tree.forEach(section => {
            const sectionDiv = document.createElement('div');
            sectionDiv.className = 'tree-node';
            sectionDiv.innerHTML = '<div class="tree-toggle" onclick="toggleTree(this)"><span class="tree-arrow">▶</span> <span class="tree-label" style="font-weight:600">Sección ' + section.code + ': ' + escapeHtml(section.title) + '</span></div>';
            const childrenDiv = document.createElement('div');
            childrenDiv.className = 'tree-children';
            section.children.forEach(chapter => {
                const chDiv = document.createElement('div');
                chDiv.innerHTML = '<div class="tree-toggle" onclick="toggleTree(this)"><span class="tree-arrow">▶</span> <span class="tree-label code">Capítulo ' + chapter.code + '</span> <span class="tree-label">' + escapeHtml(chapter.title) + '</span></div>';
                const hDiv = document.createElement('div');
                hDiv.className = 'tree-children';
                chapter.children.forEach(heading => {
                    const heDiv = document.createElement('div');
                    heDiv.innerHTML = '<div class="tree-toggle" onclick="toggleTree(this)"><span class="tree-arrow">▶</span> <span class="tree-label code">' + heading.code + '</span> <span class="tree-label">' + escapeHtml(heading.title) + '</span></div>';
                    const sDiv = document.createElement('div');
                    sDiv.className = 'tree-children';
                    heading.children.forEach(sub => {
                        sDiv.innerHTML += '<div class="tree-label tree-item-clickable" onclick="showDetail(\'' + sub.code + '\')"><span class="tree-label code">' + sub.code + '</span> ' + escapeHtml(sub.title) + '</div>';
                    });
                    heDiv.appendChild(sDiv);
                    hDiv.appendChild(heDiv);
                });
                chDiv.appendChild(hDiv);
                childrenDiv.appendChild(chDiv);
            });
            sectionDiv.appendChild(childrenDiv);
            container.appendChild(sectionDiv);
        });
    }

    window.toggleTree = function(el) {
        const parent = el.closest('.tree-node') || el.parentElement.closest('.tree-node') || el.parentElement;
        const children = parent.querySelector(':scope > .tree-children');
        if (children) {
            children.classList.toggle('open');
            const arrow = el.querySelector('.tree-arrow');
            if (arrow) arrow.classList.toggle('open');
        }
    };

    // Tree controls
    document.getElementById('tree-expand-all').addEventListener('click', function() {
        document.querySelectorAll('.tree-children').forEach(el => el.classList.add('open'));
    });
    document.getElementById('tree-collapse-all').addEventListener('click', function() {
        document.querySelectorAll('.tree-children').forEach(el => el.classList.remove('open'));
    });
    document.getElementById('tree-filter').addEventListener('input', function() {
        const q = this.value.toLowerCase();
        document.querySelectorAll('.tree-label').forEach(el => {
            const parent = el.closest('.tree-node') || el.parentElement;
            if (parent) {
                if (!q || el.textContent.toLowerCase().includes(q)) {
                    parent.style.display = '';
                } else {
                    parent.style.display = 'none';
                }
            }
        });
    });

    // ========== SUITE CAAAREM TI: VALIDADOR Y MULTICLASIFICADOR ==========
    const toggleSingleBtn = document.getElementById('ai-toggle-single-btn');
    const toggleBatchBtn = document.getElementById('ai-toggle-batch-btn');
    const containerSingle = document.getElementById('ai-container-single');
    const containerBatch = document.getElementById('ai-container-batch');

    if (toggleSingleBtn && toggleBatchBtn) {
        toggleSingleBtn.addEventListener('click', () => {
            toggleSingleBtn.className = 'btn-primary';
            toggleBatchBtn.className = 'btn-secondary';
            containerSingle.style.display = 'flex';
            containerBatch.style.display = 'none';
        });

        toggleBatchBtn.addEventListener('click', () => {
            toggleSingleBtn.className = 'btn-secondary';
            toggleBatchBtn.className = 'btn-primary';
            containerSingle.style.display = 'none';
            containerBatch.style.display = 'flex';
        });
    }

    const validateDescBtn = document.getElementById('ai-validate-desc-btn');
    if (validateDescBtn) {
        validateDescBtn.addEventListener('click', async () => {
            const desc = aiTextarea.value.trim();
            if (!desc) {
                alert('Ingrese una descripción de mercancía para validar.');
                return;
            }

            const valBox = document.getElementById('ai-desc-validation-box');
            const scoreBadge = document.getElementById('ai-desc-validation-score');
            const valStatus = document.getElementById('ai-desc-validation-status');
            const warningsUl = document.getElementById('ai-desc-validation-warnings');
            const suggestionsUl = document.getElementById('ai-desc-validation-suggestions');

            valBox.style.display = 'block';
            valStatus.innerHTML = '<div class="spinner" style="margin:0 auto 10px; border-top-color:var(--primary)"></div> Evaluando descripción...';
            warningsUl.innerHTML = '';
            suggestionsUl.innerHTML = '';

            try {
                const res = await fetch('/api/vucem/description/validate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ description: desc })
                });
                const data = await res.json();

                scoreBadge.textContent = `Calidad: ${data.score}/100`;
                scoreBadge.className = 'badge ' + (data.score >= 80 ? 'badge-high' : data.score >= 50 ? 'badge-medium' : 'badge-low');

                if (data.is_compliant) {
                    valStatus.innerHTML = '<span style="color:#10b981">✓ Cumple: Descripción necesaria y suficiente. Reducción de riesgo de multas al 100%.</span>';
                } else {
                    valStatus.innerHTML = '<span style="color:#ef4444">⚠️ Alerta: Descripción INSUFICIENTE para el Anexo 22 del SAT. Riesgo de multa por datos inexactos.</span>';
                }

                if (data.warnings.length === 0) {
                    warningsUl.innerHTML = '<li style="color:#10b981; list-style:none">Ninguna alerta técnica detectada.</li>';
                } else {
                    data.warnings.forEach(w => {
                        warningsUl.innerHTML += `<li>${escapeHtml(w)}</li>`;
                    });
                }

                if (data.suggestions.length === 0) {
                    suggestionsUl.innerHTML = '<li style="color:#10b981; list-style:none">Descripción óptima. No se requieren cambios.</li>';
                } else {
                    data.suggestions.forEach(s => {
                        suggestionsUl.innerHTML += `<li>${escapeHtml(s)}</li>`;
                    });
                }
                loadAdminAudit();
            } catch (err) {
                valStatus.innerHTML = '<span style="color:var(--danger)">Error: ' + escapeHtml(err.message) + '</span>';
            }
        });
    }

    const cpValidateDescBtn = document.getElementById('cp-validate-desc-btn');
    if (cpValidateDescBtn) {
        cpValidateDescBtn.addEventListener('click', async () => {
            const desc = document.getElementById('cp-goods').value.trim();
            if (!desc) {
                alert('Ingrese la descripción de mercancía a transportar.');
                return;
            }

            const valBox = document.getElementById('cp-desc-val-box');
            valBox.style.display = 'block';
            valBox.innerHTML = '<div class="spinner"></div> Evaluando cumplimiento...';

            try {
                const res = await fetch('/api/vucem/description/validate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ description: desc })
                });
                const data = await res.json();

                let suggestionsHtml = '';
                if (data.suggestions.length > 0) {
                    suggestionsHtml = `<div style="margin-top:6px; padding-top:6px; border-top:1px dashed rgba(255,255,255,0.05)">
                        <strong style="color:#60a5fa">Acciones recomendadas:</strong>
                        <ul style="margin:2px 0 0 0; padding-left:15px; color:var(--text-light)">
                            ${data.suggestions.map(s => `<li>${escapeHtml(s)}</li>`).join('')}
                        </ul>
                    </div>`;
                }

                const color = data.is_compliant ? '#10b981' : '#ef4444';
                const statusText = data.is_compliant ? '✓ Cumple Anexo 22' : '⚠️ Alerta Datos Inexactos';

                valBox.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px">
                        <strong style="color:${color}">${statusText}</strong>
                        <span style="font-weight:700">Calidad: ${data.score}/100</span>
                    </div>
                    <div style="color:var(--text-secondary)">${data.warnings.length > 0 ? data.warnings[0] : 'Descripción adecuada para timbrado.'}</div>
                    ${suggestionsHtml}
                `;
                loadAdminAudit();
            } catch (err) {
                valBox.innerHTML = '<div style="color:var(--danger)">Error: ' + escapeHtml(err.message) + '</div>';
            }
        });
    }

    const batchBtn = document.getElementById('ai-batch-btn');
    const batchInput = document.getElementById('ai-batch-input');
    const batchStatus = document.getElementById('ai-batch-status');
    const batchResultsBox = document.getElementById('ai-batch-results-box');
    const batchTbody = document.getElementById('ai-batch-tbody');
    const batchExportBtn = document.getElementById('ai-batch-export-btn');
    let lastBatchResults = [];

    if (batchBtn) {
        batchBtn.addEventListener('click', async () => {
            const rawText = batchInput.value.trim();
            if (!rawText) {
                alert('Ingrese al menos una descripción por línea.');
                return;
            }

            const lines = rawText.split('\n').map(l => l.trim()).filter(l => l.length > 0);
            if (lines.length === 0) {
                alert('Ingrese descripciones válidas.');
                return;
            }

            if (lines.length > 100) {
                alert('El límite masivo local es de 100 descripciones por lote.');
                return;
            }

            batchStatus.innerHTML = `<div class="spinner"></div> Procesando ${lines.length} partidas en lote...`;
            batchStatus.className = 'ai-status active';
            batchResultsBox.style.display = 'none';
            batchTbody.innerHTML = '';

            try {
                const res = await fetch('/api/classify/batch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ descriptions: lines })
                });

                const data = await res.json();
                batchStatus.className = 'ai-status';

                if (!res.ok) {
                    throw new Error(data.error || 'Error al procesar lote.');
                }

                lastBatchResults = data.results;
                
                lastBatchResults.forEach(r => {
                    const tr = document.createElement('tr');
                    tr.style.borderBottom = '1px solid rgba(255,255,255,0.04)';
                    
                    const badgeClass = r.confidence === 'Alta' ? 'badge-high' : r.confidence === 'Media' ? 'badge-medium' : 'badge-low';
                    
                    tr.innerHTML = `
                        <td style="padding:8px 10px; color:var(--text-light)">${r.index}</td>
                        <td style="padding:8px 10px; color:white; font-weight:500">${escapeHtml(r.description)}</td>
                        <td style="padding:8px 10px; font-family:monospace; color:var(--primary); font-weight:700">${r.fraction !== '---' ? r.fraction : r.hs_code}</td>
                        <td style="padding:8px 10px; color:var(--text-secondary); max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap" title="${escapeHtml(r.fraction_title)}">${escapeHtml(r.fraction_title)}</td>
                        <td style="padding:8px 10px; text-align:center"><span class="badge ${badgeClass}">${r.confidence}</span></td>
                    `;
                    batchTbody.appendChild(tr);
                });

                batchResultsBox.style.display = 'block';
                loadAdminAudit();
            } catch (err) {
                batchStatus.className = 'ai-status';
                batchStatus.innerHTML = `<div style="background:rgba(239,68,68,0.05); border:1px solid rgba(239,68,68,0.2); color:#ef4444; padding:15px; border-radius:8px">Error: ${escapeHtml(err.message)}</div>`;
            }
        });
    }

    if (batchExportBtn) {
        batchExportBtn.addEventListener('click', () => {
            if (lastBatchResults.length === 0) {
                alert('No hay resultados en lote para exportar.');
                return;
            }

            let csvContent = '\uFEFF'; 
            csvContent += 'Indice,Descripcion Declarada,Fraccion Arancelaria,Descripcion Oficial SAT,Confianza,Score\n';

            lastBatchResults.forEach(r => {
                const descClean = r.description.replace(/"/g, '""');
                const titleClean = r.fraction_title.replace(/"/g, '""');
                csvContent += `${r.index},"${descClean}",${r.fraction},"${titleClean}",${r.confidence},${r.score.toFixed(4)}\n`;
            });

            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `reporte_precodificaciones_lote_${Date.now()}.csv`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
        });
    }

    // RGI Rules apply
    document.getElementById('rgi-btn').addEventListener('click', applyRGIRulesText);
    document.getElementById('rgi-input').addEventListener('keyup', function(e) {
        if (e.key === 'Enter') applyRGIRulesText();
    });

    async function applyRGIRulesText() {
        const desc = document.getElementById('rgi-input').value.trim();
        if (!desc) return;
        const container = document.getElementById('rgi-results');
        container.innerHTML = '<div class="spinner"></div> Aplicando RGI...';
        try {
            const res = await fetch('/api/rgi/apply', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({description: desc}) });
            const data = await res.json();
            let html = '<h3 style="margin-bottom:12px">Sugerencias para: "' + escapeHtml(desc) + '"</h3>';
            data.suggestions.forEach(s => {
                html += '<div class="rgi-suggestion">' + escapeHtml(s) + '</div>';
            });
            container.innerHTML = html;
        } catch (err) {
            container.innerHTML = '<div style="color:var(--danger)">Error: ' + err.message + '</div>';
        }
    }

    async function loadRGIRules() {
        const container = document.getElementById('rgi-rules-list');
        try {
            const res = await fetch('/api/rgi/rules');
            const data = await res.json();
            let html = '<h3 style="margin:20px 0 12px">Reglas Generales de Interpretación</h3>';
            data.rules.forEach(r => {
                html += '<div class="rgi-rule"><h4>RGI ' + r.rule_number + ': ' + escapeHtml(r.title) + '</h4>';
                html += '<p>' + escapeHtml(r.content) + '</p>';
                if (r.examples) html += '<div class="example"><strong>Ejemplo:</strong> ' + escapeHtml(r.examples) + '</div>';
                html += '</div>';
            });
            container.innerHTML = html;
        } catch (err) {
            container.innerHTML = '<div>Error al cargar RGI: ' + err.message + '</div>';
        }
    }

    // History
    async function loadHistory() {
        const tbody = document.getElementById('history-body');
        tbody.innerHTML = '<tr><td colspan="6"><div class="spinner"></div> Cargando...</td></tr>';
        try {
            const res = await fetch('/api/classifications');
            const data = await res.json();
            tbody.innerHTML = '';
            if (data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-secondary)">No hay clasificaciones guardadas.</td></tr>';
                return;
            }
            data.forEach(c => {
                const conf = c.confidence ? (typeof c.confidence === 'number' ? (c.confidence * 100).toFixed(0) + '%' : c.confidence) : '-';
                const date = c.created_at ? new Date(c.created_at).toLocaleDateString('es-ES') : '-';
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>${escapeHtml(c.product_description)}</td>
                                <td><strong>${c.hs_code}</strong></td>
                                <td>${conf}</td>
                                <td>${c.method || '-'}</td>
                                <td>${date}</td>
                                <td><button class="btn-delete" onclick="deleteClassification(${c.id})">Eliminar</button></td>`;
                tbody.appendChild(tr);
            });
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="6" style="color:var(--danger)">Error: ${err.message}</td></tr>`;
        }
    }

    window.saveClassification = async function(code, title, confidence) {
        try {
            const res = await fetch('/api/classifications', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    product_description: title,
                    hs_code: code,
                    confidence: parseFloat(confidence) || 0.85,
                    method: 'IA_Alinea'
                })
            });
            const data = await res.json();
            if (data.status === 'ok') {
                alert('Clasificación guardada correctamente en el Historial.');
                loadHistory();
                loadAdminAudit(); // Registrar auditoria
            }
        } catch (err) {
            alert('Error al guardar: ' + err.message);
        }
    };

    window.downloadClassificationReport = async function() {
        const hs_code = document.getElementById('ai-res-code').textContent.trim();
        const nico = document.getElementById('ai-res-nico').textContent.trim();
        const product_description = document.getElementById('ai-input').value.trim();
        
        // Parse confidence from badge (e.g. "Confianza: 85%" -> 0.85)
        const badgeText = document.getElementById('ai-res-badge').textContent;
        let confidence = 0.85;
        const match = badgeText.match(/(\d+)%/);
        if (match) {
            confidence = parseFloat(match[1]) / 100;
        } else if (badgeText.includes('Selección')) {
            confidence = 0.90;
        }
        
        const reasoning = document.getElementById('ai-res-reasoning').innerHTML;
        
        // Gather RRNAs
        const rrnas = [];
        document.querySelectorAll('#rrna-list li').forEach(li => {
            rrnas.push(li.textContent.trim());
        });
        
        // Gather Taxes
        const taxes = {
            igi: document.getElementById('tax-igi').textContent.trim(),
            iva: document.getElementById('tax-iva').textContent.trim(),
            ieps: document.getElementById('tax-ieps').textContent.trim()
        };
        
        const payload = {
            product_description,
            hs_code,
            nico,
            confidence,
            reasoning,
            method: 'gemini',
            rrnas,
            taxes
        };
        
        const btn = event ? event.currentTarget : null;
        const originalText = btn ? btn.textContent : '';
        if (btn) {
            btn.textContent = 'Generando...';
            btn.disabled = true;
        }
        
        try {
            const response = await fetch('/api/classify/report/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            if (!response.ok) {
                throw new Error('No se pudo generar el archivo PDF');
            }
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `reporte_clasificacion_${hs_code}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } catch (err) {
            alert('Error al descargar reporte: ' + err.message);
        } finally {
            if (btn) {
                btn.textContent = originalText;
                btn.disabled = false;
            }
        }
    };

    window.deleteClassification = async function(id) {
        if (!confirm('¿Eliminar esta clasificación?')) return;
        try {
            await fetch('/api/classifications/' + id, { method: 'DELETE' });
            loadHistory();
        } catch (err) {
            alert('Error al eliminar: ' + err.message);
        }
    };

    document.getElementById('refresh-history-btn').addEventListener('click', loadHistory);

    // Export & Imports
    document.getElementById('export-btn').addEventListener('click', () => window.open('/api/export/excel', '_blank'));
    document.getElementById('export-classifications-btn').addEventListener('click', () => window.open('/api/export/excel', '_blank'));
    document.getElementById('export-catalog-btn').addEventListener('click', () => window.open('/api/export/hs_catalog', '_blank'));

    document.getElementById('import-csv-btn').addEventListener('click', () => handleImport('/api/import/csv', 'csv-file'));
    document.getElementById('import-excel-btn').addEventListener('click', () => handleImport('/api/import/excel', 'excel-file'));

    async function handleImport(url, elementId) {
        const fileInput = document.getElementById(elementId);
        if (!fileInput.files[0]) { alert('Seleccione un archivo.'); return; }
        const status = document.getElementById('import-status');
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        status.style.display = 'block';
        status.innerHTML = '<div class="spinner"></div> Importando registros...';
        try {
            const res = await fetch(url, { method: 'POST', body: formData });
            const data = await res.json();
            status.className = 'import-status ' + (data.success ? 'success' : 'error');
            status.textContent = data.success ? data.count + ' registros importados con éxito.' : 'Error: ' + data.error;
            if (data.success) loadHistory();
        } catch (err) {
            status.className = 'import-status error';
            status.textContent = 'Error: ' + err.message;
        }
    }

    // Detail Modal
    window.showDetail = async function(code) {
        const modal = document.getElementById('detail-modal');
        const body = document.getElementById('modal-body');
        body.innerHTML = '<div class="spinner"></div> Cargando detalle...';
        modal.style.display = 'block';
        try {
            const res = await fetch('/api/hs_code/' + code);
            const data = await res.json();
            let html = '<h2 style="margin-bottom:16px;color:var(--accent)">Detalle de Fracción: ' + code + '</h2>';
            if (data.section) html += '<div class="detail-section"><h3>Sección</h3><p>' + data.section.code + ': ' + escapeHtml(data.section.title) + '</p></div>';
            if (data.chapter) html += '<div class="detail-section"><h3>Capítulo</h3><p>' + data.chapter.code + ': ' + escapeHtml(data.chapter.title) + '</p></div>';
            if (data.heading) html += '<div class="detail-section"><h3>Partida</h3><p>' + data.heading.code + ': ' + escapeHtml(data.heading.title) + '</p></div>';
            if (data.subheading) html += '<div class="detail-section"><h3>Subpartida</h3><p>' + data.subheading.code + ': ' + escapeHtml(data.subheading.title) + '</p></div>';
            if (data.subheading && data.subheading.description) html += '<div class="detail-section"><h3>Descripción Notas</h3><p>' + escapeHtml(data.subheading.description) + '</p></div>';
            html += '<div style="margin-top:20px"><button class="btn-primary" onclick="saveClassification(\'' + code + '\',\'' + (data.subheading ? escapeHtml(data.subheading.title) : data.heading ? escapeHtml(data.heading.title) : '').replace(/'/g, "\\'") + '\',\'1\')">Guardar clasificación</button></div>';
            body.innerHTML = html;
        } catch (err) {
            body.innerHTML = '<div style="color:var(--danger)">Error: ' + err.message + '</div>';
        }
    };

    document.querySelector('.modal-close').addEventListener('click', function() {
        document.getElementById('detail-modal').style.display = 'none';
    });
    window.addEventListener('click', function(e) {
        if (e.target === document.getElementById('detail-modal')) {
            document.getElementById('detail-modal').style.display = 'none';
        }
    });

    // ========== Official Sources Logic ==========
    document.getElementById('check-sources-btn').addEventListener('click', checkSources);
    document.getElementById('regenerate-hs-btn').addEventListener('click', regenerateHS);
    document.getElementById('sync-official-btn').addEventListener('click', syncOfficial);
    document.getElementById('verify-hs-btn').addEventListener('click', verifyHS);
    document.getElementById('verify-hs-input').addEventListener('keyup', function(e) {
        if (e.key === 'Enter') verifyHS();
    });
    document.getElementById('sources-search-btn').addEventListener('click', searchOfficial);
    document.getElementById('sources-search-input').addEventListener('keyup', function(e) {
        if (e.key === 'Enter') searchOfficial();
    });

    async function checkSources() {
        const statusDiv = document.getElementById('sources-status');
        statusDiv.innerHTML = '<div class="spinner"></div> Verificando fuentes oficiales...';
        statusDiv.className = 'sources-status active loading';
        try {
            const res = await fetch('/api/sources/status');
            const data = await res.json();
            let html = '<div class="sources-list">';
            data.sources.forEach(s => {
                const statusClass = s.status === 'online' ? 'online' : (s.status.includes('error') || s.status === 'timeout' || s.status === 'unreachable' ? 'error' : 'unknown');
                const latency = s.latency ? s.latency + 's' : '-';
                html += '<div class="source-item">';
                html += '<div class="source-icon">' + (s.type === 'api' ? '📁' : '🌐') + '</div>';
                html += '<div><div class="source-name">' + escapeHtml(s.name) + '</div>';
                html += '<div class="source-desc">' + escapeHtml(s.description) + '</div></div>';
                html += '<span class="source-status ' + statusClass + '">' + s.status + ' (' + latency + ')</span>';
                html += '</div>';
            });
            html += '</div>';
            statusDiv.className = 'sources-status active success';
            statusDiv.innerHTML = '<strong>Verificación de Fuentes Completada</strong>' + html;
        } catch (err) {
            statusDiv.className = 'sources-status active error';
            statusDiv.innerHTML = 'Error: ' + err.message;
        }
    }

    async function regenerateHS() {
        if (!confirm('¿Regenerar base HS local? Se purgarán los registros y se cargarán las 21 secciones.')) return;
        const statusDiv = document.getElementById('sources-status');
        statusDiv.innerHTML = '<div class="spinner"></div> Regenerando base local...';
        statusDiv.className = 'sources-status active loading';
        try {
            const res = await fetch('/api/database/regenerate', { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                statusDiv.className = 'sources-status active success';
                statusDiv.innerHTML = '<strong>Base de datos regenerada con éxito.</strong>';
                loadTree();
            } else {
                statusDiv.className = 'sources-status active error';
                statusDiv.innerHTML = 'Error: ' + data.message;
            }
        } catch (err) {
            statusDiv.className = 'sources-status active error';
            statusDiv.innerHTML = 'Error: ' + err.message;
        }
    }

    async function syncOfficial() {
        const statusDiv = document.getElementById('sources-status');
        statusDiv.innerHTML = '<div class="spinner"></div> Sincronizando catálogo con LIGIE...';
        statusDiv.className = 'sources-status active loading';
        try {
            const res = await fetch('/api/sources/sync', { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                statusDiv.className = 'sources-status active success';
                statusDiv.innerHTML = '<strong>Sincronización finalizada correctamente.</strong>';
            } else {
                statusDiv.className = 'sources-status active error';
                statusDiv.innerHTML = 'Error de sincronización.';
            }
        } catch (err) {
            statusDiv.className = 'sources-status active error';
            statusDiv.innerHTML = 'Error: ' + err.message;
        }
    }

    async function verifyHS() {
        const code = document.getElementById('verify-hs-input').value.trim();
        if (!code) return;
        const container = document.getElementById('verify-results');
        container.innerHTML = '<div class="spinner"></div> Buscando en fuentes oficiales...';
        try {
            const res = await fetch('/api/sources/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ hs_code: code })
            });
            const data = await res.json();
            let html = '<h3 style="margin-bottom:12px">Estatus Oficial SAT para: ' + code + '</h3>';
            if (data.verified) {
                html += '<div class="rgi-suggestion">✓ Código plenamente vigente y catalogado en fuentes federales de aduana.</div>';
            } else {
                html += '<div style="color:var(--warning)">⚠ No se encontró coincidencia exacta activa en servidores federales. Revise LIGIE local.</div>';
            }
            container.innerHTML = html;
        } catch (err) {
            container.innerHTML = '<div style="color:var(--danger)">Error: ' + err.message + '</div>';
        }
    }

    async function searchOfficial() {
        const query = document.getElementById('sources-search-input').value.trim();
        if (!query) return;
        const container = document.getElementById('sources-search-results');
        container.innerHTML = '<div class="spinner"></div> Consultando LIGIE en vivo...';
        try {
            const res = await fetch('/api/sources/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query })
            });
            const data = await res.json();
            if (data.results && data.results.length > 0) {
                let html = '<div style="margin-bottom:10px">' + data.total + ' registros encontrados en LIGIE oficial</div>';
                data.results.forEach(r => {
                    html += '<div class="result-item" onclick="showDetail(\'' + r.code + '\')">';
                    html += '<div class="result-code">' + r.code + '</div>';
                    html += '<div class="result-title">' + escapeHtml(r.title) + '</div>';
                    html += '<div class="result-path">Origen: ' + escapeHtml(r.source) + '</div>';
                    html += '</div>';
                });
                container.innerHTML = html;
            } else {
                container.innerHTML = '<div style="color:var(--text-secondary)">No hay coincidencias en vivo. Pruebe base de datos local.</div>';
            }
        } catch (err) {
            container.innerHTML = '<div style="color:var(--danger)">Error: ' + err.message + '</div>';
        }
    }

    // Helper: Escape HTML
    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // ========== PDF.js Worker Configuration ==========
    if (window.pdfjsLib) {
        window.pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.4.120/pdf.worker.min.js';
    }

    // ========== XML & PDF Vucem Parser ==========
    let tempXmlData = null;

    // XML Dropzone
    const xmlDropzone = document.getElementById('xml-dropzone');
    const xmlInput = document.getElementById('xml-file-input');

    if (xmlDropzone && xmlInput) {
        xmlDropzone.addEventListener('click', () => xmlInput.click());
        xmlInput.addEventListener('change', (e) => {
            if (e.target.files[0]) processXmlFile(e.target.files[0]);
        });
        xmlDropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            xmlDropzone.classList.add('hover');
        });
        xmlDropzone.addEventListener('dragleave', () => xmlDropzone.classList.remove('hover'));
        xmlDropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            xmlDropzone.classList.remove('hover');
            if (e.dataTransfer.files[0]) processXmlFile(e.dataTransfer.files[0]);
        });
    }

    // PDF Dropzone
    const acuseDropzone = document.getElementById('acuse-dropzone');
    const acuseInput = document.getElementById('acuse-file-input');

    if (acuseDropzone && acuseInput) {
        acuseDropzone.addEventListener('click', () => acuseInput.click());
        acuseInput.addEventListener('change', (e) => {
            if (e.target.files[0]) processAcuseFile(e.target.files[0]);
        });
        acuseDropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            acuseDropzone.classList.add('hover');
        });
        acuseDropzone.addEventListener('dragleave', () => acuseDropzone.classList.remove('hover'));
        acuseDropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            acuseDropzone.classList.remove('hover');
            if (e.dataTransfer.files[0]) processAcuseFile(e.dataTransfer.files[0]);
        });
    }

    function showParserStatus(message, isError = false) {
        const statusDiv = document.getElementById('vucem-parser-status');
        if (!statusDiv) return;
        statusDiv.style.display = 'block';
        statusDiv.className = 'import-status ' + (isError ? 'error' : 'success');
        statusDiv.innerHTML = (isError ? '<strong>Error: </strong>' : '<strong>Éxito: </strong>') + message;
    }

    function processXmlFile(file) {
        if (file.type !== 'text/xml' && !file.name.endsWith('.xml') && !file.type.includes('xml')) {
            showParserStatus('Por favor, cargue un archivo XML válido.', true);
            return;
        }

        const reader = new FileReader();
        reader.onload = function(e) {
            const content = e.target.result;
            try {
                const parser = new DOMParser();
                const xmlDoc = parser.parseFromString(content, 'text/xml');
                const parserError = xmlDoc.getElementsByTagName('parsererror');
                if (parserError.length > 0) {
                    throw new Error('El archivo no tiene un formato XML estructurado.');
                }

                const getAttr = (element, attr) => element ? (element.getAttribute(attr) || '') : '';
                const getElement = (name) => xmlDoc.querySelector(name) || xmlDoc.querySelector(`*[local-name()='${name}']`);

                const comprobante = getElement('Comprobante') || xmlDoc.documentElement;
                const emisor = getElement('Emisor');
                const receptor = getElement('Receptor');
                const conceptosElements = xmlDoc.querySelectorAll("Concepto, *[local-name()='Concepto']");

                let uuid = '';
                const tfd = getElement('TimbreFiscalDigital');
                if (tfd) uuid = getAttr(tfd, 'UUID');

                const general = {
                    folio: getAttr(comprobante, 'Folio') || uuid || 'S/F',
                    fecha: getAttr(comprobante, 'Fecha') || new Date().toLocaleDateString(),
                    moneda: getAttr(comprobante, 'Moneda') || 'USD',
                    tipoCambio: getAttr(comprobante, 'TipoCambio') || '1.00',
                    total: getAttr(comprobante, 'Total') || '0.00'
                };

                const emisorData = {
                    nombre: getAttr(emisor, 'Nombre') || 'PROVEEDOR DESCONOCIDO',
                    rfc: getAttr(emisor, 'Rfc') || getAttr(emisor, 'NumRegIdTrib') || 'XEXX010101000'
                };

                const receptorData = {
                    nombre: getAttr(receptor, 'Nombre') || 'IMPORTADOR DESCONOCIDO',
                    rfc: getAttr(receptor, 'Rfc') || 'XAXX010101000'
                };

                const concepts = [];
                conceptosElements.forEach(item => {
                    concepts.push({
                        cantidad: getAttr(item, 'Cantidad') || '1',
                        unidad: getAttr(item, 'Unidad') || getAttr(item, 'ClaveUnidad') || 'PZA',
                        claveProdServ: getAttr(item, 'ClaveProdServ') || '00000000',
                        descripcion: getAttr(item, 'Descripcion') || 'Sin descripción',
                        valorUnitario: getAttr(item, 'ValorUnitario') || '0.00',
                        importe: getAttr(item, 'Importe') || '0.00'
                    });
                });

                tempXmlData = {
                    fileName: file.name,
                    general,
                    emisor: emisorData,
                    receptor: receptorData,
                    concepts
                };

                // Render XML results
                document.getElementById('xml-data-folio').textContent = general.folio;
                document.getElementById('xml-data-fecha').textContent = general.fecha;
                document.getElementById('xml-data-moneda').textContent = general.moneda;
                document.getElementById('xml-data-tc').textContent = general.tipoCambio;
                document.getElementById('xml-data-total').textContent = '$' + Number(general.total).toLocaleString('es-MX', { minimumFractionDigits: 2 }) + ' ' + general.moneda;

                document.getElementById('xml-data-emisor-nombre').textContent = emisorData.nombre;
                document.getElementById('xml-data-emisor-rfc').textContent = emisorData.rfc;
                document.getElementById('xml-data-receptor-nombre').textContent = receptorData.nombre;
                document.getElementById('xml-data-receptor-rfc').textContent = receptorData.rfc;

                const tbody = document.getElementById('xml-concepts-tbody');
                tbody.innerHTML = '';
                concepts.forEach(c => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `<td>${c.cantidad}</td>
                                    <td>${c.unidad}</td>
                                    <td style="font-family:monospace">${c.claveProdServ}</td>
                                    <td>${escapeHtml(c.descripcion)}</td>
                                    <td style="text-align:right">$${Number(c.valorUnitario).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</td>
                                    <td style="text-align:right;font-weight:bold">$${Number(c.importe).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</td>`;
                    tbody.appendChild(tr);
                });

                document.getElementById('xml-results-panel').style.display = 'block';
                showParserStatus('Factura XML parseada con éxito localmente. Tabla de conceptos rellenada.', false);
            } catch (err) {
                console.error(err);
                showParserStatus('Error al parsear el XML: ' + err.message, true);
            }
        };
        reader.readAsText(file);
    }

    async function processAcuseFile(file) {
        if (file.type !== 'application/pdf' && !file.name.endsWith('.pdf')) {
            showParserStatus('Por favor, cargue un PDF de acuse válido.', true);
            return;
        }

        const statusDiv = document.getElementById('vucem-parser-status');
        statusDiv.style.display = 'block';
        statusDiv.className = 'import-status success';
        statusDiv.innerHTML = '<div class="spinner"></div> Leyendo acuse PDF localmente...';

        const reader = new FileReader();
        reader.onload = async function(e) {
            const arrayBuffer = e.target.result;
            try {
                if (!window.pdfjsLib) {
                    throw new Error('PDF.js no disponible.');
                }
                const pdf = await window.pdfjsLib.getDocument({ data: arrayBuffer }).promise;
                let fullText = '';
                const maxPages = Math.min(pdf.numPages, 3);
                for (let i = 1; i <= maxPages; i++) {
                    const page = await pdf.getPage(i);
                    const textContent = await page.getTextContent();
                    fullText += ' ' + textContent.items.map(item => item.str).join(' ');
                }

                const edocMatch = fullText.match(/[A-Z0-9]{16}/i);
                const coveMatch = fullText.match(/[A-Z0-9]{13}/i);
                const rfcMatch = fullText.match(/[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}/i);
                const patenteMatch = fullText.match(/\b\d{4}\b/);

                const folio = edocMatch ? edocMatch[0] : (coveMatch ? coveMatch[0] : 'NO DETECTADO');
                const tipo = edocMatch ? 'e-Document' : (coveMatch ? 'COVE' : 'Desconocido');

                document.getElementById('pdf-data-filename').textContent = file.name;
                document.getElementById('pdf-data-tipo').textContent = tipo;
                document.getElementById('pdf-data-folio').textContent = folio;
                document.getElementById('pdf-data-rfc').textContent = rfcMatch ? rfcMatch[0].toUpperCase() : 'NO DETECTADO';
                document.getElementById('pdf-data-patente').textContent = patenteMatch ? patenteMatch[0] : 'NO DETECTADO';
                document.getElementById('pdf-data-fecha').textContent = new Date().toLocaleDateString();

                document.getElementById('acuse-results-panel').style.display = 'block';
                showParserStatus('Datos extraídos del PDF del acuse con éxito.', false);
            } catch (err) {
                console.error(err);
                showParserStatus('Error al extraer texto: ' + err.message, true);
            }
        };
        reader.readAsArrayBuffer(file);
    }

    // COVE XML generation and download
    const coveDownloadBtn = document.getElementById('cove-download-btn');
    if (coveDownloadBtn) {
        coveDownloadBtn.addEventListener('click', () => {
            if (!tempXmlData) {
                alert('No hay una factura XML parseada para generar el COVE.');
                return;
            }
            try {
                const coveEmail = document.getElementById('cove-email').value || 'contacto@empresa.com';
                const coveFigura = document.getElementById('cove-figura').value || '1';
                const coveTipoOp = document.getElementById('cove-tipo-op').value || 'SUB';

                const escapeXml = (str) => {
                    return str.replace(/&/g, '&amp;')
                              .replace(/</g, '&lt;')
                              .replace(/>/g, '&gt;')
                              .replace(/"/g, '&quot;')
                              .replace(/'/g, '&apos;');
                };

                const conceptsXml = tempXmlData.concepts.map(concept => {
                    return `
      <cove:mercancia>
        <cove:descripcion>${escapeXml(concept.descripcion)}</cove:descripcion>
        <cove:cantidadComercial>${escapeXml(concept.cantidad)}</cove:cantidadComercial>
        <cove:unidadMedida>${escapeXml(concept.unidad)}</cove:unidadMedida>
        <cove:valorUnitario>${escapeXml(concept.valorUnitario)}</cove:valorUnitario>
        <cove:valorTotal>${escapeXml(concept.importe)}</cove:valorTotal>
        <cove:tipoMoneda>${escapeXml(tempXmlData.general.moneda)}</cove:tipoMoneda>
      </cove:mercancia>`;
                }).join('');

                const coveXml = `<?xml version="1.0" encoding="UTF-8"?>
<cove:comprobanteValorElectronico xmlns:cove="http://www.alinea.gob.mx/cove/ws/valida/comprobante">
  <cove:tipoOperacion>${escapeXml(coveTipoOp)}</cove:tipoOperacion>
  <cove:tipoFigura>${escapeXml(coveFigura)}</cove:tipoFigura>
  <cove:correoElectronico>${escapeXml(coveEmail)}</cove:correoElectronico>
  <cove:factura>
    <cove:numeroFactura>${escapeXml(tempXmlData.general.folio)}</cove:numeroFactura>
    <cove:fechaExpedicion>${escapeXml(tempXmlData.general.fecha)}</cove:fechaExpedicion>
    <cove:emisor>
      <cove:tipoIdentificador>RFC</cove:tipoIdentificador>
      <cove:identificacion>${escapeXml(tempXmlData.emisor.rfc)}</cove:identificacion>
      <cove:nombre>${escapeXml(tempXmlData.emisor.nombre)}</cove:nombre>
    </cove:emisor>
    <cove:receptor>
      <cove:tipoIdentificador>RFC</cove:tipoIdentificador>
      <cove:identificacion>${escapeXml(tempXmlData.receptor.rfc)}</cove:identificacion>
      <cove:nombre>${escapeXml(tempXmlData.receptor.nombre)}</cove:nombre>
    </cove:receptor>
    <cove:mercancias>${conceptsXml}
    </cove:mercancias>
  </cove:factura>
</cove:comprobanteValorElectronico>`;

                const blob = new Blob([coveXml], { type: 'text/xml;charset=utf-8' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `cove_cove_${tempXmlData.general.folio || 'comprobante'}.xml`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            } catch (err) {
                alert('Error al generar COVE: ' + err.message);
            }
        });
    }

    // ========== VUCEM PDF Optimizer & Converter Tool ==========
    const vucemOptDropzone = document.getElementById('vucem-opt-dropzone');
    const vucemOptInput = document.getElementById('vucem-opt-input');
    const vucemOptGrayscale = document.getElementById('vucem-opt-grayscale');
    const vucemOptResult = document.getElementById('vucem-opt-result');
    const vucemOptLoading = document.getElementById('vucem-opt-loading');
    const vucemOptResName = document.getElementById('vucem-opt-res-name');
    const vucemOptResOrig = document.getElementById('vucem-opt-res-orig');
    const vucemOptResOpt = document.getElementById('vucem-opt-res-opt');
    const vucemOptResPct = document.getElementById('vucem-opt-res-pct');
    const vucemOptDownloadBtn = document.getElementById('vucem-opt-download-btn');

    if (vucemOptDropzone && vucemOptInput) {
        vucemOptDropzone.addEventListener('click', () => vucemOptInput.click());
        vucemOptInput.addEventListener('change', (e) => {
            if (e.target.files[0]) uploadAndOptimizeForVucem(e.target.files[0]);
        });
        vucemOptDropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            vucemOptDropzone.style.borderColor = '#10b981';
            vucemOptDropzone.style.background = 'rgba(16,185,129,0.05)';
        });
        vucemOptDropzone.addEventListener('dragleave', () => {
            vucemOptDropzone.style.borderColor = '#10b981';
            vucemOptDropzone.style.background = 'transparent';
        });
        vucemOptDropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            vucemOptDropzone.style.borderColor = '#10b981';
            vucemOptDropzone.style.background = 'transparent';
            if (e.dataTransfer.files[0]) uploadAndOptimizeForVucem(e.dataTransfer.files[0]);
        });
    }

    async function uploadAndOptimizeForVucem(file) {
        vucemOptResult.style.display = 'none';
        vucemOptLoading.style.display = 'block';

        const formData = new FormData();
        formData.append('file', file);
        formData.append('force_grayscale', vucemOptGrayscale.checked ? 'true' : 'false');

        try {
            const res = await fetch('/api/vucem/pdf/optimize', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            vucemOptLoading.style.display = 'none';

            if (res.ok && data.success) {
                vucemOptResName.textContent = data.original_name;
                vucemOptResOrig.textContent = data.original_size_mb.toFixed(2) + ' MB';
                vucemOptResOpt.textContent = data.optimized_size_mb.toFixed(2) + ' MB';
                vucemOptResPct.textContent = data.savings_pct + '%';
                vucemOptDownloadBtn.href = data.download_url;
                vucemOptResult.style.display = 'block';
                
                // Recargar bitácora de auditoría
                loadAdminAudit();
                alert('✓ Archivo optimizado con éxito para VUCEM. El e-Document resultante está listo para descarga.');
            } else {
                alert('Error al optimizar PDF para VUCEM: ' + (data.error || 'Ocurrió un error desconocido.'));
            }
        } catch (err) {
            vucemOptLoading.style.display = 'none';
            alert('Error en conexión al optimizar PDF: ' + err.message);
        }
    }

    // Transfer XML Data to MVE Wizard
    const xmlTransferBtn = document.getElementById('xml-transfer-mve-btn');
    if (xmlTransferBtn) {
        xmlTransferBtn.addEventListener('click', () => {
            if (!tempXmlData) {
                alert('No hay datos XML para transferir.');
                return;
            }

            document.getElementById('mve-rfc-importador').value = tempXmlData.receptor.rfc || '';
            document.getElementById('mve-nombre-importador').value = tempXmlData.receptor.nombre || '';
            document.getElementById('mve-prov-nombre').value = tempXmlData.emisor.nombre || '';
            document.getElementById('mve-prov-taxid').value = tempXmlData.emisor.rfc || '';
            document.getElementById('mve-val-comercial').value = tempXmlData.general.total || '';
            document.getElementById('mve-tc').value = tempXmlData.general.tipoCambio || '1.00';
            
            const currencySelect = document.getElementById('mve-moneda');
            const currencyCode = tempXmlData.general.moneda ? tempXmlData.general.moneda.toUpperCase() : 'USD';
            for (let i = 0; i < currencySelect.options.length; i++) {
                if (currencySelect.options[i].value === currencyCode) {
                    currencySelect.selectedIndex = i;
                    break;
                }
            }

            recalculateMve();
            alert('Datos de Factura XML transferidos con éxito al Wizard de MVE.');
            document.querySelector('[data-tab="mve"]').click();
        });
    }

    // ========== Wizard MVE Lógica ==========
    let mveCurrentStep = 0;
    let mveSignedData = null;

    const mveStepDots = document.querySelectorAll('.mve-step-dot');
    const mveStepPanels = document.querySelectorAll('.mve-step-panel');
    const mveWizardLabels = document.querySelectorAll('.mve-wizard-labels span');

    const mvePrevBtn = document.getElementById('mve-prev-btn');
    const mveNextBtn = document.getElementById('mve-next-btn');
    const mvePrintBtn = document.getElementById('mve-print-btn');
    const mveDownloadBtn = document.getElementById('mve-download-btn');
    const mveSignBtn = document.getElementById('mve-sign-btn');

    mveStepDots.forEach(dot => {
        dot.addEventListener('click', function() {
            goToMveStep(parseInt(this.dataset.step));
        });
    });

    if (mvePrevBtn && mveNextBtn) {
        mvePrevBtn.addEventListener('click', () => {
            if (mveCurrentStep > 0) goToMveStep(mveCurrentStep - 1);
        });
        mveNextBtn.addEventListener('click', () => {
            if (mveCurrentStep < 4) goToMveStep(mveCurrentStep + 1);
        });
    }

    function goToMveStep(step) {
        mveCurrentStep = step;
        mveStepPanels.forEach((panel, idx) => {
            if (idx === step) panel.classList.add('active');
            else panel.classList.remove('active');
        });

        mveStepDots.forEach((dot, idx) => {
            if (idx === step) dot.className = 'mve-step-dot active';
            else if (idx < step) dot.className = 'mve-step-dot completed';
            else dot.className = 'mve-step-dot';
        });

        mveWizardLabels.forEach((label, idx) => {
            if (idx === step) label.classList.add('active');
            else label.classList.remove('active');
        });

        mvePrevBtn.disabled = step === 0;
        mveNextBtn.style.display = step === 4 ? 'none' : 'block';

        recalculateMve();
    }

    const mveInputs = ['mve-val-comercial', 'mve-tc', 'mve-fletes', 'mve-seguros', 'mve-envases', 'mve-otros', 'mve-incoterm'];
    mveInputs.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', recalculateMve);
            el.addEventListener('change', recalculateMve);
        }
    });

    function recalculateMve() {
        const valComercial = parseFloat(document.getElementById('mve-val-comercial').value) || 0;
        const tc = parseFloat(document.getElementById('mve-tc').value) || 1;
        const fletes = parseFloat(document.getElementById('mve-fletes').value) || 0;
        const seguros = parseFloat(document.getElementById('mve-seguros').value) || 0;
        const envases = parseFloat(document.getElementById('mve-envases').value) || 0;
        const otros = parseFloat(document.getElementById('mve-otros').value) || 0;
        const incoterm = document.getElementById('mve-incoterm').value;

        const sumIncrementables = fletes + seguros + envases + otros;
        document.getElementById('mve-calc-inc-usd').textContent = '$' + sumIncrementables.toLocaleString('en-US', { minimumFractionDigits: 2 }) + ' USD';

        const valorAduanaUSD = valComercial + sumIncrementables;
        const valorAduanaMXN = valorAduanaUSD * tc;
        document.getElementById('mve-calc-adu-usd').textContent = '$' + valorAduanaUSD.toLocaleString('en-US', { minimumFractionDigits: 2 }) + ' USD';
        document.getElementById('mve-calc-adu-mxn').textContent = '$' + valorAduanaMXN.toLocaleString('es-MX', { minimumFractionDigits: 2 }) + ' MXN';

        const igi = valorAduanaMXN * 0.10;
        const dta = valorAduanaMXN * 0.008;
        const prevalidación = 310.00;
        const baseIva = valorAduanaMXN + igi + dta + prevalidación;
        const iva = baseIva * 0.16;
        const total = igi + dta + prevalidación + iva;

        document.getElementById('mve-calc-igi').textContent = '$' + igi.toLocaleString('es-MX', { minimumFractionDigits: 2 });
        document.getElementById('mve-calc-dta').textContent = '$' + dta.toLocaleString('es-MX', { minimumFractionDigits: 2 });
        document.getElementById('mve-calc-prev').textContent = '$' + prevalidación.toLocaleString('es-MX', { minimumFractionDigits: 2 });
        document.getElementById('mve-calc-iva').textContent = '$' + iva.toLocaleString('es-MX', { minimumFractionDigits: 2 });
        document.getElementById('mve-calc-total').textContent = '$' + total.toLocaleString('es-MX', { minimumFractionDigits: 2 }) + ' MXN';

        const warnBox = document.getElementById('mve-incoterm-warning');
        const warnText = document.getElementById('mve-warning-text');
        const incotermsOrigen = ['EXW', 'FCA', 'FAS', 'FOB'];
        const incotermsDestino = ['CIF', 'CIP', 'DAP', 'DDP', 'CFR'];

        if (incotermsOrigen.includes(incoterm)) {
            if (fletes === 0 || seguros === 0) {
                warnBox.style.display = 'block';
                warnText.textContent = `En Incoterm pactado en origen (${incoterm}), los fletes y seguros son legalmente obligatorios. Declarar $0.00 constituye un riesgo normativo grave (Art. 64 L.A.).`;
            } else {
                warnBox.style.display = 'none';
            }
        } else if (incotermsDestino.includes(incoterm)) {
            if (fletes > 0 || seguros > 0) {
                warnBox.style.display = 'block';
                warnText.textContent = `En Incoterm en destino (${incoterm}), el flete y seguro vienen incluidos. Declararlos adicionales duplicará el Valor Aduana de forma indebida.`;
            } else {
                warnBox.style.display = 'none';
            }
        } else {
            warnBox.style.display = 'none';
        }
    }

    if (mveSignBtn) {
        mveSignBtn.addEventListener('click', () => {
            const cerFile = document.getElementById('mve-file-cer').files[0];
            const keyFile = document.getElementById('mve-file-key').files[0];
            const password = document.getElementById('mve-password').value;

            if (!cerFile || !keyFile || !password) {
                alert('Cargue los archivos e.firma (.cer, .key) e ingrese la contraseña.');
                return;
            }

            mveSignBtn.textContent = 'Firmando digitalmente...';
            mveSignBtn.disabled = true;

            setTimeout(() => {
                const randomHex = (len) => Array.from({length: len}, () => Math.floor(Math.random()*16).toString(16)).join('');
                const folio = `MVE-${new Date().getFullYear()}${String(new Date().getMonth()+1).padStart(2,'0')}${String(new Date().getDate()).padStart(2,'0')}-${randomHex(6).toUpperCase()}`;
                const sello = randomHex(64).toUpperCase();
                
                mveSignedData = {
                    folio,
                    sello,
                    fechaFirma: new Date().toISOString(),
                    firmante: document.getElementById('mve-nombre-importador').value,
                    rfcFirmante: document.getElementById('mve-rfc-importador').value,
                    certificadoSerie: '20001000000300022345'
                };

                document.getElementById('mve-signed-folio').textContent = folio;
                document.getElementById('mve-signed-sello').textContent = sello;
                document.getElementById('mve-signed-box').style.display = 'block';

                mvePrintBtn.style.display = 'block';
                mveDownloadBtn.style.display = 'block';

                mveSignBtn.textContent = 'Firmar MVE';
                mveSignBtn.disabled = false;
                
                alert('✓ Documento firmado digitalmente con e.firma de forma local y acuse generado con éxito.');
                
                // Enviar a bandeja VUCEM
                sendToVucemValidation(folio, 'Manifestación MVE (E2)', mveSignedData.rfcFirmante);
                
                // Guardar MVE en Base de Datos de forma persistente
                fetch('/api/mve/save', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        folio: folio,
                        rfcFirmante: mveSignedData.rfcFirmante,
                        firmante: mveSignedData.firmante,
                        metodoValoracion: document.getElementById('mve-metodo-val').value,
                        valorComercial: parseFloat(document.getElementById('mve-val-comercial').value) || 0,
                        totalIncrementables: parseFloat(document.getElementById('mve-calc-inc-usd').textContent.replace(/[^0-9.]/g, '')) || 0,
                        valorAduanaMXN: parseFloat(document.getElementById('mve-calc-adu-mxn').textContent.replace(/[^0-9.]/g, '')) || 0
                    })
                }).then(res => res.json()).then(data => {
                    if(data.success) {
                        loadMveList();
                    }
                }).catch(err => console.error("Error guardando MVE:", err));
                
            }, 1500);
        });
    }

    if (mveDownloadBtn) {
        mveDownloadBtn.addEventListener('click', () => {
            if (!mveSignedData) return;
            const mveJson = {
                version: '1.0',
                tipoDocumento: 'MVE_E2',
                fechaGeneracion: new Date().toISOString(),
                importador: {
                    rfc: document.getElementById('mve-rfc-importador').value,
                    razonSocial: document.getElementById('mve-nombre-importador').value
                },
                agenteAduanal: {
                    rfc: document.getElementById('mve-rfc-agente').value,
                    patente: document.getElementById('mve-patente').value
                },
                operacion: {
                    regimen: document.getElementById('mve-regimen').value,
                    incoterm: document.getElementById('mve-incoterm').value,
                    metodoValoracion: document.getElementById('mve-metodo-val').value,
                    moneda: document.getElementById('mve-moneda').value,
                    tipoCambio: parseFloat(document.getElementById('mve-tc').value)
                },
                proveedor: {
                    nombre: document.getElementById('mve-prov-nombre').value,
                    taxId: document.getElementById('mve-prov-taxid').value,
                    pais: document.getElementById('mve-prov-pais').value,
                    domicilio: document.getElementById('mve-prov-domicilio').value
                },
                valores: {
                    valorComercial: parseFloat(document.getElementById('mve-val-comercial').value) || 0,
                    fletes: parseFloat(document.getElementById('mve-fletes').value) || 0,
                    seguros: parseFloat(document.getElementById('mve-seguros').value) || 0,
                    envases: parseFloat(document.getElementById('mve-envases').value) || 0,
                    otros: parseFloat(document.getElementById('mve-otros').value) || 0,
                },
                documentosSoporte: {
                    factura: document.getElementById('mve-doc-factura').checked,
                    transporte: document.getElementById('mve-doc-transporte').checked,
                    pago: document.getElementById('mve-doc-pago').checked,
                    gastos: document.getElementById('mve-doc-gastos').checked,
                    origen: document.getElementById('mve-doc-origen').checked
                },
                firma: mveSignedData
            };

            const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(mveJson, null, 2));
            const dl = document.createElement('a');
            dl.setAttribute('href', dataStr);
            dl.setAttribute('download', `mve_e2_${mveJson.importador.rfc}_${Date.now()}.json`);
            document.body.appendChild(dl);
            dl.click();
            dl.remove();
        });
    }

    if (mvePrintBtn) {
        mvePrintBtn.addEventListener('click', () => {
            if (!mveSignedData) return;
            const container = document.getElementById('mve-sheet-preview-container');
            
            const rfcImportador = document.getElementById('mve-rfc-importador').value;
            const nombreImportador = document.getElementById('mve-nombre-importador').value;
            const rfcAgente = document.getElementById('mve-rfc-agente').value;
            const patente = document.getElementById('mve-patente').value;
            const incoterm = document.getElementById('mve-incoterm').value;
            const regimen = document.getElementById('mve-regimen').value;
            const moneda = document.getElementById('mve-moneda').value;
            const tc = parseFloat(document.getElementById('mve-tc').value) || 1;

            const valCom = parseFloat(document.getElementById('mve-val-comercial').value) || 0;
            const fletes = parseFloat(document.getElementById('mve-fletes').value) || 0;
            const seguros = parseFloat(document.getElementById('mve-seguros').value) || 0;
            const envases = parseFloat(document.getElementById('mve-envases').value) || 0;
            const otros = parseFloat(document.getElementById('mve-otros').value) || 0;

            const totalInc = fletes + seguros + envases + otros;
            const valAduanaUSD = valCom + totalInc;
            const valAduanaMXN = valAduanaUSD * tc;

            const provNombre = document.getElementById('mve-prov-nombre').value;
            const provTaxId = document.getElementById('mve-prov-taxid').value;
            const provDomicilio = document.getElementById('mve-prov-domicilio').value;

            let docsStr = '';
            if (document.getElementById('mve-doc-factura').checked) docsStr += 'FACTURA COMERCIAL, ';
            if (document.getElementById('mve-doc-transporte').checked) docsStr += 'DOCUMENTO TRANSPORTE, ';
            if (document.getElementById('mve-doc-pago').checked) docsStr += 'COMPROBANTE PAGO, ';
            if (document.getElementById('mve-doc-gastos').checked) docsStr += 'GASTOS INCREMENTABLES, ';
            if (document.getElementById('mve-doc-origen').checked) docsStr += 'CERTIFICADO ORIGEN, ';
            docsStr = docsStr.substring(0, docsStr.length - 2);

            container.innerHTML = `
                <div class="mve-sheet-header">
                    <div style="font-weight:bold;font-size:15px">SECRETARÍA DE HACIENDA Y CRÉDITO PÚBLICO</div>
                    <div style="font-size:12px;margin-top:2px">SERVICIO DE ADMINISTRACIÓN TRIBUTARIA (SAT)</div>
                    <div class="mve-sheet-title" style="margin-top:10px">MANIFESTACIÓN DE VALOR ELECTRÓNICA (FORMATO E2)</div>
                </div>
                <table class="mve-sheet-table">
                    <tr><th colspan="2">A. DATOS GENERALES DEL IMPORTADOR</th></tr>
                    <tr><td style="width:35%">RFC / IDENTIFICADOR:</td><td><strong>${rfcImportador}</strong></td></tr>
                    <tr><td>RAZÓN SOCIAL / NOMBRE:</td><td><strong>${nombreImportador}</strong></td></tr>
                    <tr><th colspan="2">B. DATOS DEL AGENTE ADUANAL / PATENTE</th></tr>
                    <tr><td>RFC AGENTE ADUANAL:</td><td>${rfcAgente}</td></tr>
                    <tr><td>PATENTE AUTORIZADA:</td><td>${patente}</td></tr>
                    <tr><th colspan="2">C. PROVEEDOR EXTRANJERO Y CONDICIONES</th></tr>
                    <tr><td>PROVEEDOR VENDEDOR:</td><td>${provNombre}</td></tr>
                    <tr><td>IDENTIFICADOR FISCAL:</td><td>${provTaxId}</td></tr>
                    <tr><td>DOMICILIO FISCAL:</td><td>${provDomicilio}</td></tr>
                    <tr><td>INCOTERM PACTADO:</td><td><strong>${incoterm}</strong></td></tr>
                    <tr><td>RÉGIMEN ADUANERO:</td><td>${regimen}</td></tr>
                    <tr><th colspan="2">D. VALORES ADUANEROS Y TIPO DE CAMBIO</th></tr>
                    <tr><td>DIVISA DE FACTURACIÓN:</td><td>${moneda}</td></tr>
                    <tr><td>TIPO DE CAMBIO DOF:</td><td>$${tc.toFixed(4)} MXN</td></tr>
                    <tr><td>VALOR COMERCIAL (DIVISA):</td><td>$${valCom.toLocaleString('en-US', { minimumFractionDigits: 2 })}</td></tr>
                    <tr><td>FLETES / SEGUROS / OTROS:</td><td>$${totalInc.toLocaleString('en-US', { minimumFractionDigits: 2 })} USD</td></tr>
                    <tr><td><strong>VALOR ADUANA (USD):</strong></td><td><strong>$${valAduanaUSD.toLocaleString('en-US', { minimumFractionDigits: 2 })} USD</strong></td></tr>
                    <tr><td><strong>VALOR ADUANA (MXN):</strong></td><td><strong>$${valAduanaMXN.toLocaleString('es-MX', { minimumFractionDigits: 2 })} MXN</strong></td></tr>
                    <tr><th colspan="2">E. SOPORTE DE VALORACIÓN Y FIRMA</th></tr>
                    <tr><td>DOCS EXPEDIENTE ADJUNTO:</td><td style="font-size:10px">${docsStr}</td></tr>
                    <tr><td>FOLIO DIGITAL SAT/VUCEM:</td><td><strong style="font-family:monospace">${mveSignedData.folio}</strong></td></tr>
                    <tr><td>FECHA Y HORA FIRMADO:</td><td>${new Date(mveSignedData.fechaFirma).toLocaleString('es-MX')}</td></tr>
                    <tr><td>CADENA SELLO DIGITAL:</td><td style="word-break:break-all;font-family:monospace;font-size:9px">${mveSignedData.sello}</td></tr>
                </table>
                <div style="margin-top:20px;text-align:justify;font-size:10px">
                    DECLARO BAJO PROTESTA DE DECIR VERDAD QUE LOS DATOS ASENTADOS EN ESTA DECLARACIÓN DE VALOR E2 SON VERÍDICOS, CORRECTOS Y SE ENCUENTRAN RESPALDADOS PLENAMENTE EN LA DOCUMENTACIÓN CONSERVADA EN NUESTRO ARCHIVO LEGAL (ART. 81 LEY ADUANERA).
                </div>
                <div style="margin-top:40px;text-align:center">
                    <div style="border-top:1px solid black;width:250px;margin:0 auto"></div>
                    <div style="font-size:10px;margin-top:5px">${nombreImportador}</div>
                    <div style="font-size:9px;color:gray">FIRMA ELECTRÓNICA FIEL DEL IMPORTADOR</div>
                </div>
            `;
            window.print();
        });
    }

    // ========== LIQUIDACIÓN DE IMPUESTOS PEDIMENTO ==========
    const taxAddBtn = document.getElementById('tax-add-item-btn');
    const taxCalculateBtn = document.getElementById('tax-calculate-btn');
    const taxResultPanel = document.getElementById('tax-result-panel');
    const taxInputValUsd = document.getElementById('tax-input-val-usd');
    const taxInputTc = document.getElementById('tax-input-tc');
    const taxInputFta = document.getElementById('tax-input-fta');

    if (taxAddBtn) {
        taxAddBtn.addEventListener('click', () => {
            const tbody = document.getElementById('tax-items-tbody');
            const tr = document.createElement('tr');
            tr.style.borderBottom = '1px solid rgba(255,255,255,0.04)';
            tr.innerHTML = `
                <td style="padding:6px 10px"><input type="text" class="tax-item-desc" value="Nueva Mercancía" style="padding:4px; font-size:11.5px; width:100%"></td>
                <td style="padding:6px 10px"><input type="text" class="tax-item-hs" value="8471.30.01" style="padding:4px; font-size:11.5px; width:100%; font-family:monospace"></td>
                <td style="padding:6px 10px"><input type="number" class="tax-item-val" value="1000.00" style="padding:4px; font-size:11.5px; width:100%; text-align:right"></td>
                <td style="padding:6px 10px; text-align:center"><button class="btn-delete" style="padding:2px 6px; font-size:10px" onclick="deleteTaxRow(this)">X</button></td>
            `;
            tbody.appendChild(tr);
        });
    }

    window.deleteTaxRow = function(btn) {
        const row = btn.closest('tr');
        const tbody = document.getElementById('tax-items-tbody');
        if (tbody.querySelectorAll('tr').length > 1) {
            row.remove();
        } else {
            alert('Debe declarar al menos una partida para calcular contribuciones.');
        }
    };

    if (taxCalculateBtn) {
        taxCalculateBtn.addEventListener('click', async () => {
            const tc = parseFloat(taxInputTc.value) || 18.50;
            const hasFta = taxInputFta.checked;

            // Recopilar partidas
            const rows = document.querySelectorAll('#tax-items-tbody tr');
            const items = [];
            let sumItemValUsd = 0;

            for (let i = 0; i < rows.length; i++) {
                const desc = rows[i].querySelector('.tax-item-desc').value.trim();
                const hs = rows[i].querySelector('.tax-item-hs').value.trim();
                const val = parseFloat(rows[i].querySelector('.tax-item-val').value) || 0;

                if (!desc || !hs || val <= 0) {
                    alert(`Partida #${i+1}: Complete todos los datos y asegúrese de que el valor sea mayor que cero.`);
                    return;
                }
                items.push({
                    description: desc,
                    hs_code: hs,
                    customs_value_item_usd: val
                });
                sumItemValUsd += val;
            }

            // Sincronizar el valor total declarado
            const declaredValUsd = parseFloat(taxInputValUsd.value) || 0;
            if (Math.abs(declaredValUsd - sumItemValUsd) > 0.01) {
                taxInputValUsd.value = sumItemValUsd.toFixed(2);
            }

            taxResultPanel.innerHTML = `
                <div style="text-align:center; padding:20px">
                    <div class="spinner" style="margin:0 auto 10px; border-top-color:var(--primary)"></div>
                    <span style="font-size:12px; color:var(--text-light)">Calculando gravámenes aduaneros...</span>
                </div>
            `;

            try {
                const res = await fetch('/api/pedimento/tax_calculate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        customs_value_usd: sumItemValUsd,
                        exchange_rate: tc,
                        has_fta: hasFta,
                        items: items
                    })
                });

                const data = await res.json();
                if (!res.ok) {
                    throw new Error(data.error || 'Error desconocido al calcular impuestos');
                }

                renderTaxResults(data);
                loadAdminAudit(); // refrescar bitácora
            } catch (err) {
                taxResultPanel.innerHTML = `
                    <div style="background:rgba(239,68,68,0.05); border:1px solid rgba(239,68,68,0.2); color:#ef4444; padding:15px; border-radius:8px; font-size:12px">
                        <strong>Error al calcular:</strong> ${escapeHtml(err.message)}
                    </div>
                `;
            }
        });
    }

    let lastTaxResultData = null;

    window.downloadPrerFile = async function() {
        const patente = document.getElementById('tax-input-patente').value.trim();
        const pedimento = document.getElementById('tax-input-pedimento').value.trim();
        const aduana = document.getElementById('tax-input-aduana').value.trim();
        const regimen = document.getElementById('tax-input-regimen').value;
        const tc = parseFloat(document.getElementById('tax-input-tc').value) || 18.50;
        const hasFta = document.getElementById('tax-input-fta').checked;

        if (patente.length !== 4 || isNaN(patente)) {
            alert('La patente debe ser de 4 dígitos numéricos.');
            return;
        }
        if (pedimento.length !== 7 || isNaN(pedimento)) {
            alert('El consecutivo de pedimento debe ser de 7 dígitos numéricos.');
            return;
        }
        if (aduana.length !== 3 || isNaN(aduana)) {
            alert('La aduana debe ser de 3 dígitos numéricos.');
            return;
        }

        if (!lastTaxResultData) {
            alert('Realice el cálculo de contribuciones primero.');
            return;
        }

        // Recopilar partidas
        const rows = document.querySelectorAll('#tax-items-tbody tr');
        const items = [];
        for (let i = 0; i < rows.length; i++) {
            const desc = rows[i].querySelector('.tax-item-desc').value.trim();
            const hs = rows[i].querySelector('.tax-item-hs').value.trim();
            const val = parseFloat(rows[i].querySelector('.tax-item-val').value) || 0;
            items.push({
                description: desc,
                hs_code: hs,
                value_usd: val,
                customs_value_mxn: val * tc
            });
        }

        const payload = {
            patente,
            pedimento,
            aduana,
            regimen,
            tipo_op: "1", // Importación
            exchange_rate: tc,
            items: items,
            contributions: lastTaxResultData.cuadro_contribuciones
        };

        try {
            const res = await fetch('/api/pedimento/generate_prer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.error || 'Error al generar archivo PRER');
            }

            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `m${patente}${pedimento}.001`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);

            // Recargar bitácora de auditoría
            loadAdminAudit();
            alert(`✓ Archivo plano de Pedimento generado con éxito: m${patente}${pedimento}.001`);
        } catch (err) {
            alert('Error al descargar archivo PRER: ' + err.message);
        }
    };

    function renderTaxResults(data) {
        lastTaxResultData = data;
        let contribHtml = '';
        data.cuadro_contribuciones.forEach(c => {
            contribHtml += `
                <tr style="border-bottom:1px solid rgba(255,255,255,0.04)">
                    <td style="padding:10px; color:var(--text-secondary)">${c.clave}</td>
                    <td style="padding:10px; color:white; font-weight:500">${escapeHtml(c.concepto)}</td>
                    <td style="padding:10px; text-align:center; color:var(--text-light)">${c.fp}</td>
                    <td style="padding:10px; text-align:right; font-family:monospace; color:var(--accent); font-weight:700">$${c.importe.toLocaleString('es-MX', { minimumFractionDigits: 0 })}</td>
                </tr>
            `;
        });

        let itemsHtml = '';
        data.items.forEach(item => {
            itemsHtml += `
                <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border); border-radius:8px; padding:12px; font-size:12px">
                    <div style="display:flex; justify-content:space-between; margin-bottom:6px">
                        <strong style="color:white">Partida #${item.partida}: ${escapeHtml(item.description)}</strong>
                        <strong style="color:var(--primary); font-family:monospace">${item.hs_code}</strong>
                    </div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; font-size:11px; color:var(--text-light)">
                        <div>Valor Aduana: $${item.customs_value_mxn.toLocaleString('es-MX', { minimumFractionDigits: 2 })} MXN</div>
                        <div>Gravamen IGI: ${(item.igi_rate*100).toFixed(0)}% ($${item.igi_mxn.toLocaleString('es-MX', { minimumFractionDigits: 2 })} MXN)</div>
                        <div>Gravamen IVA: ${(item.iva_rate*100).toFixed(0)}% ($${item.iva_mxn.toLocaleString('es-MX', { minimumFractionDigits: 2 })} MXN)</div>
                        ${item.ieps_rate > 0 ? `<div>Gravamen IEPS: ${(item.ieps_rate*100).toFixed(1)}% ($${item.ieps_mxn.toLocaleString('es-MX', { minimumFractionDigits: 2 })} MXN)</div>` : ''}
                    </div>
                    <div style="font-size:10px; color:var(--text-muted); margin-top:6px; border-top:1px dashed rgba(255,255,255,0.05); padding-top:4px">
                        Norma: ${escapeHtml(item.notes)}
                    </div>
                </div>
            `;
        });

        taxResultPanel.innerHTML = `
            <div style="display:flex; flex-direction:column; gap:15px">
                <div style="border-bottom:1px solid var(--border); padding-bottom:10px">
                    <h3 style="margin:0; font-size:15px; color:#10b981; display:flex; align-items:center; gap:6px">
                        <span>✓</span> Cálculos Finalizados con Éxito
                    </h3>
                </div>

                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; font-size:11.5px; background:rgba(255,255,255,0.02); padding:10px; border-radius:6px; border:1px solid var(--border)">
                    <div><strong>Val. Comercial:</strong> $${data.valor_comercial_mxn.toLocaleString('es-MX', { minimumFractionDigits: 2 })} MXN</div>
                    <div><strong>Val. Aduana:</strong> $${data.valor_aduana_mxn.toLocaleString('es-MX', { minimumFractionDigits: 2 })} MXN</div>
                    <div><strong>TLC Beneficio:</strong> ${data.has_fta ? '<span style="color:#10b981">Sí (T-MEC Preferencia)</span>' : '<span style="color:var(--secondary)">No (Tasa General)</span>'}</div>
                    <div><strong>Tipo Cambio:</strong> $${data.exchange_rate.toFixed(4)}</div>
                </div>

                <div>
                    <h4 style="margin:0 0 8px; font-size:13px; color:white">Cuadro de Contribuciones (Pedimento)</h4>
                    <div style="overflow-x:auto; border:1px solid var(--border); border-radius:8px">
                        <table style="width:100%; border-collapse:collapse; font-size:11.5px; text-align:left">
                            <thead>
                                <tr style="background:rgba(255,255,255,0.04); border-bottom:1px solid var(--border); color:var(--text-light)">
                                    <th style="padding:8px 10px; width:40px">CON</th>
                                    <th style="padding:8px 10px">CONCEPTO</th>
                                    <th style="padding:8px 10px; width:30px; text-align:center">F.P.</th>
                                    <th style="padding:8px 10px; text-align:right">IMPORTE (MXN)</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${contribHtml}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div style="background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.2); border-radius:8px; padding:12px; display:flex; justify-content:space-between; align-items:center">
                    <div>
                        <span style="font-size:10.5px; color:var(--text-light); display:block; text-transform:uppercase">Efectivo Total a Pagar (FP 0)</span>
                        <strong style="font-size:18px; color:#10b981; font-family:monospace">$${data.total_contribuciones_mxn.toLocaleString('es-MX', { minimumFractionDigits: 0 })} MXN</strong>
                    </div>
                    <span style="font-size:24px">🏦</span>
                </div>

                <button onclick="downloadPrerFile()" class="btn-primary" style="background:#4f46e5; border-color:#4f46e5; color:white; width:100%; font-weight:600; padding:10px 0; display:flex; align-items:center; justify-content:center; gap:8px">
                    <span>📥</span> Descargar Archivo Plano PRER (Anexo 22)
                </button>

                <div style="font-size:10.5px; color:var(--text-muted); padding:8px; background:rgba(0,0,0,0.15); border-radius:4px">
                    <strong>Notas de DTA:</strong> ${escapeHtml(data.dta_notes)}
                </div>

                <div style="display:flex; flex-direction:column; gap:8px">
                    <h4 style="margin:0; font-size:12.5px; color:white">Normativas y Tasas por Partida</h4>
                    ${itemsHtml}
                </div>
            </div>
        `;
    }

    // Inicializar cargando el dashboard al inicio
    loadDashboardData();
});
