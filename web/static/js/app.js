let currentConfig = null;
let modalMode = null;

async function fetchAPI(url, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    if (data) {
        options.body = JSON.stringify(data);
    }
    const response = await fetch(url, options);
    return await response.json();
}

function showLoading() {
    document.getElementById('loading').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;
            
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            document.querySelectorAll('.tab-pane').forEach(pane => {
                pane.classList.remove('active');
            });
            document.getElementById('tab-' + tabId).classList.add('active');
            
            if (tabId === 'chart') {
                setTimeout(() => {
                    Plotly.Plots.resize('power-chart');
                    Plotly.Plots.resize('soc-chart');
                }, 50);
            }
        });
    });
}

async function loadConfig() {
    showLoading();
    try {
        const result = await fetchAPI('/api/config');
        if (result.success) {
            currentConfig = result.data;
            updateUI();
            await recalculate();
        } else {
            alert('加载配置失败: ' + result.error);
        }
    } catch (e) {
        alert('加载配置失败: ' + e.message);
    } finally {
        hideLoading();
    }
}

function updateUI() {
    const panelSelect = document.getElementById('panel-select');
    panelSelect.innerHTML = '';
    currentConfig.panels.forEach(panel => {
        const option = document.createElement('option');
        option.value = panel.id;
        option.textContent = panel.name;
        panelSelect.appendChild(option);
    });

    const quantitiesList = document.getElementById('panel-quantities-list');
    quantitiesList.innerHTML = '';
    currentConfig.panels.forEach(panel => {
        const quantity = currentConfig.panel_quantities[panel.id] || 0;
        const item = document.createElement('div');
        item.className = 'panel-quantity-item';
        item.innerHTML = `
            <span class="panel-name">${panel.name}</span>
            <span class="panel-desc">${panel.description}</span>
            <input type="number" class="quantity-input" data-panel-id="${panel.id}" value="${quantity}" min="0" step="1">
        `;
        quantitiesList.appendChild(item);
    });

    const storageSelect = document.getElementById('storage-select');
    storageSelect.innerHTML = '';
    currentConfig.storages.forEach(storage => {
        const option = document.createElement('option');
        option.value = storage.id;
        option.textContent = storage.name;
        if (storage.id === currentConfig.current_storage_id) {
            option.selected = true;
        }
        storageSelect.appendChild(option);
    });

    const storageConfig = currentConfig.current_storage_config;
    document.getElementById('storage-capacity').value = storageConfig.capacity;
    document.getElementById('storage-charge-power').value = storageConfig.max_charge_power;
    document.getElementById('storage-discharge-power').value = storageConfig.max_discharge_power;
    document.getElementById('storage-charge-eff').value = storageConfig.charge_efficiency;
    document.getElementById('storage-discharge-eff').value = storageConfig.discharge_efficiency;
    document.getElementById('storage-initial-soc').value = storageConfig.initial_soc;
    document.getElementById('storage-min-soc').value = storageConfig.min_soc;
    document.getElementById('storage-max-soc').value = storageConfig.max_soc;

    document.getElementById('electricity-price').value = currentConfig.electricity_price;
    
    loadPanelDetail();
}

async function recalculate() {
    showLoading();
    try {
        const result = await fetchAPI('/api/calculate', 'POST');
        if (result.success) {
            updateCharts(result.data.chart_data);
            document.getElementById('daily-cost').textContent = result.data.daily_cost.toFixed(2);
        } else {
            alert('计算失败: ' + result.error);
        }
    } catch (e) {
        alert('计算失败: ' + e.message);
    } finally {
        hideLoading();
    }
}

function updateCharts(data) {
    const timestamps = data.timestamps.map(t => t.split('+')[0].replace('T', ' ').slice(0, 16));

    const powerTrace = [
        {
            x: timestamps,
            y: data.solar,
            name: '光伏发电',
            type: 'scatter',
            mode: 'lines',
            line: { color: '#f1c40f' }
        },
        {
            x: timestamps,
            y: data.wind,
            name: '风力发电',
            type: 'scatter',
            mode: 'lines',
            line: { color: '#17becf' }
        },
        {
            x: timestamps,
            y: data.consumption,
            name: '负荷',
            type: 'scatter',
            mode: 'lines',
            line: { color: '#e74c3c' }
        },
        {
            x: timestamps,
            y: data.storage_power,
            name: '储能功率',
            type: 'scatter',
            mode: 'lines',
            line: { color: '#3498db' }
        },
        {
            x: timestamps,
            y: data.net_load,
            name: '净负荷',
            type: 'scatter',
            mode: 'lines',
            line: { color: '#2ecc71' }
        }
    ];

    const powerLayout = {
        title: '功率曲线',
        xaxis: { title: '时间' },
        yaxis: { title: '功率 (kW)' },
        legend: { orientation: 'h', y: -0.2 },
        margin: { t: 50, b: 80, l: 60, r: 20 },
        autosize: true
    };

    Plotly.newPlot('power-chart', powerTrace, powerLayout, { 
        responsive: true,
        displayModeBar: true
    }).then(() => {
        setTimeout(() => Plotly.Plots.resize('power-chart'), 100);
    });

    const socTrace = [{
        x: timestamps,
        y: data.soc.map(v => v * 100),
        name: 'SOC',
        type: 'scatter',
        mode: 'lines',
        fill: 'tozeroy',
        line: { color: '#9b59b6' }
    }];

    const socLayout = {
        title: '储能荷电状态 (SOC)',
        xaxis: { title: '时间' },
        yaxis: { title: 'SOC (%)', range: [0, 100] },
        margin: { t: 50, b: 80, l: 60, r: 20 },
        autosize: true
    };

    Plotly.newPlot('soc-chart', socTrace, socLayout, { 
        responsive: true,
        displayModeBar: true
    }).then(() => {
        setTimeout(() => Plotly.Plots.resize('soc-chart'), 100);
    });
}

async function switchStorage() {
    const storageId = document.getElementById('storage-select').value;
    showLoading();
    try {
        const result = await fetchAPI('/api/storages/switch', 'POST', { storage_id: storageId });
        if (result.success) {
            await loadConfig();
        } else {
            alert('切换失败: ' + result.error);
        }
    } catch (e) {
        alert('切换失败: ' + e.message);
    } finally {
        hideLoading();
    }
}

async function loadPanelDetail() {
    const panelId = document.getElementById('panel-select').value;
    if (!panelId) {
        document.getElementById('panel-detail-form').style.display = 'none';
        return;
    }
    
    try {
        const result = await fetchAPI(`/api/panels/${panelId}`);
        if (result.success) {
            const panelConfig = result.data;
            document.getElementById('panel-area').value = panelConfig.system.area;
            document.getElementById('panel-tilt').value = panelConfig.system_config.surface_tilt;
            document.getElementById('panel-azimuth').value = panelConfig.system_config.surface_azimuth;
            document.getElementById('panel-lat').value = panelConfig.location.lat;
            document.getElementById('panel-lon').value = panelConfig.location.lon;
            document.getElementById('panel-altitude').value = panelConfig.location.altitude;
            document.getElementById('panel-temp-air').value = panelConfig.weather.temp_air;
            document.getElementById('panel-wind-speed').value = panelConfig.weather.wind_speed;
            document.getElementById('panel-detail-form').style.display = 'block';
        }
    } catch (e) {
        console.error('加载光伏板详情失败:', e);
        document.getElementById('panel-detail-form').style.display = 'none';
    }
}

async function savePanelQuantities() {
    const inputs = document.querySelectorAll('.quantity-input');
    const quantities = {};
    inputs.forEach(input => {
        quantities[input.dataset.panelId] = parseInt(input.value) || 0;
    });
    
    showLoading();
    try {
        const result = await fetchAPI('/api/panels/quantities', 'POST', { quantities: quantities });
        if (result.success) {
            alert(result.message);
            await recalculate();
        } else {
            alert('保存失败: ' + result.error);
        }
    } catch (e) {
        alert('保存失败: ' + e.message);
    } finally {
        hideLoading();
    }
}

async function updatePanelConfig() {
    const panelId = document.getElementById('panel-select').value;
    if (!panelId) {
        alert('请先选择光伏板');
        return;
    }
    const data = {
        panel_id: panelId,
        area: parseFloat(document.getElementById('panel-area').value),
        surface_tilt: parseFloat(document.getElementById('panel-tilt').value),
        surface_azimuth: parseFloat(document.getElementById('panel-azimuth').value),
        lat: parseFloat(document.getElementById('panel-lat').value),
        lon: parseFloat(document.getElementById('panel-lon').value),
        altitude: parseFloat(document.getElementById('panel-altitude').value),
        temp_air: parseFloat(document.getElementById('panel-temp-air').value),
        wind_speed: parseFloat(document.getElementById('panel-wind-speed').value)
    };
    try {
        const result = await fetchAPI('/api/panels/update', 'POST', data);
        if (result.success) {
            alert(result.message);
        } else {
            alert('保存失败: ' + result.error);
        }
    } catch (e) {
        alert('保存失败: ' + e.message);
    }
}

async function updateStorageConfig() {
    const data = {
        capacity: parseFloat(document.getElementById('storage-capacity').value),
        max_charge_power: parseFloat(document.getElementById('storage-charge-power').value),
        max_discharge_power: parseFloat(document.getElementById('storage-discharge-power').value),
        charge_efficiency: parseFloat(document.getElementById('storage-charge-eff').value),
        discharge_efficiency: parseFloat(document.getElementById('storage-discharge-eff').value),
        initial_soc: parseFloat(document.getElementById('storage-initial-soc').value),
        min_soc: parseFloat(document.getElementById('storage-min-soc').value),
        max_soc: parseFloat(document.getElementById('storage-max-soc').value)
    };
    try {
        const result = await fetchAPI('/api/storages/update', 'POST', data);
        if (result.success) {
            alert(result.message);
        } else {
            alert('保存失败: ' + result.error);
        }
    } catch (e) {
        alert('保存失败: ' + e.message);
    }
}

async function updateElectricityPrice() {
    const price = parseFloat(document.getElementById('electricity-price').value);
    try {
        const result = await fetchAPI('/api/electricity-price/update', 'POST', { electricity_price: price });
        if (result.success) {
            alert(result.message);
        } else {
            alert('保存失败: ' + result.error);
        }
    } catch (e) {
        alert('保存失败: ' + e.message);
    }
}

async function deleteCurrentPanel() {
    const panelId = document.getElementById('panel-select').value;
    if (!panelId) {
        alert('请先选择光伏板');
        return;
    }
    const quantity = currentConfig.panel_quantities[panelId] || 0;
    if (quantity > 0) {
        alert('该光伏板当前数量不为 0，请先将数量设为 0 再删除');
        return;
    }
    if (!confirm(`确定要删除光伏配置 "${panelId}" 吗？`)) {
        return;
    }
    try {
        const result = await fetchAPI('/api/panels/delete', 'POST', { panel_id: panelId });
        if (result.success) {
            alert(result.message);
            await loadConfig();
        } else {
            alert('删除失败: ' + result.error);
        }
    } catch (e) {
        alert('删除失败: ' + e.message);
    }
}

async function deleteCurrentStorage() {
    const storageId = document.getElementById('storage-select').value;
    if (storageId === currentConfig.current_storage_id) {
        alert('无法删除当前正在使用的配置，请先切换到其他配置');
        return;
    }
    if (!confirm(`确定要删除储能配置 "${storageId}" 吗？`)) {
        return;
    }
    try {
        const result = await fetchAPI('/api/storages/delete', 'POST', { storage_id: storageId });
        if (result.success) {
            alert(result.message);
            await loadConfig();
        } else {
            alert('删除失败: ' + result.error);
        }
    } catch (e) {
        alert('删除失败: ' + e.message);
    }
}

function showCreatePanelModal() {
    modalMode = 'panel';
    document.getElementById('modal-title').textContent = '新建光伏配置';
    document.getElementById('modal-content').innerHTML = `
        <div class="form-group">
            <label>配置 ID:</label>
            <input type="text" id="new-panel-id" placeholder="如: panel_custom_1">
        </div>
        <div class="form-group">
            <label>名称:</label>
            <input type="text" id="new-panel-name" placeholder="如: 自定义光伏板">
        </div>
        <div class="form-group">
            <label>描述:</label>
            <input type="text" id="new-panel-desc" placeholder="描述信息">
        </div>
        <div class="form-group">
            <label>面积 (m²):</label>
            <input type="number" id="new-panel-area" value="1000">
        </div>
        <div class="form-group">
            <label>倾角 (°):</label>
            <input type="number" id="new-panel-tilt" value="30">
        </div>
        <div class="form-group">
            <label>方位角 (°):</label>
            <input type="number" id="new-panel-azimuth" value="180">
        </div>
    `;
    document.getElementById('modal-overlay').style.display = 'flex';
}

function showCreateStorageModal() {
    modalMode = 'storage';
    document.getElementById('modal-title').textContent = '新建储能配置';
    document.getElementById('modal-content').innerHTML = `
        <div class="form-group">
            <label>配置 ID:</label>
            <input type="text" id="new-storage-id" placeholder="如: storage_custom_1">
        </div>
        <div class="form-group">
            <label>名称:</label>
            <input type="text" id="new-storage-name" placeholder="如: 自定义储能">
        </div>
        <div class="form-group">
            <label>描述:</label>
            <input type="text" id="new-storage-desc" placeholder="描述信息">
        </div>
        <div class="form-group">
            <label>容量 (kWh):</label>
            <input type="number" id="new-storage-capacity" value="500">
        </div>
        <div class="form-group">
            <label>最大充电功率 (kW):</label>
            <input type="number" id="new-storage-charge-power" value="250">
        </div>
        <div class="form-group">
            <label>最大放电功率 (kW):</label>
            <input type="number" id="new-storage-discharge-power" value="250">
        </div>
    `;
    document.getElementById('modal-overlay').style.display = 'flex';
}

function closeModal() {
    document.getElementById('modal-overlay').style.display = 'none';
    modalMode = null;
}

async function confirmModal() {
    if (modalMode === 'panel') {
        const data = {
            panel_id: document.getElementById('new-panel-id').value,
            name: document.getElementById('new-panel-name').value,
            description: document.getElementById('new-panel-desc').value,
            area: parseFloat(document.getElementById('new-panel-area').value),
            surface_tilt: parseFloat(document.getElementById('new-panel-tilt').value),
            surface_azimuth: parseFloat(document.getElementById('new-panel-azimuth').value)
        };
        if (!data.panel_id || !data.name) {
            alert('请填写配置 ID 和名称');
            return;
        }
        try {
            const result = await fetchAPI('/api/panels/create', 'POST', data);
            if (result.success) {
                alert(result.message);
                closeModal();
                await loadConfig();
            } else {
                alert('创建失败: ' + result.error);
            }
        } catch (e) {
            alert('创建失败: ' + e.message);
        }
    } else if (modalMode === 'storage') {
        const data = {
            storage_id: document.getElementById('new-storage-id').value,
            name: document.getElementById('new-storage-name').value,
            description: document.getElementById('new-storage-desc').value,
            capacity: parseFloat(document.getElementById('new-storage-capacity').value),
            max_charge_power: parseFloat(document.getElementById('new-storage-charge-power').value),
            max_discharge_power: parseFloat(document.getElementById('new-storage-discharge-power').value)
        };
        if (!data.storage_id || !data.name) {
            alert('请填写配置 ID 和名称');
            return;
        }
        try {
            const result = await fetchAPI('/api/storages/create', 'POST', data);
            if (result.success) {
                alert(result.message);
                closeModal();
                await loadConfig();
            } else {
                alert('创建失败: ' + result.error);
            }
        } catch (e) {
            alert('创建失败: ' + e.message);
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    loadConfig();
});
