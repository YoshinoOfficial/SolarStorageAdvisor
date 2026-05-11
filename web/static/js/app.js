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
                loadParkPowerChart();
            } else if (tabId === 'optimization') {
                loadOptimizationData();
            } else if (tabId === 'comparison') {
                loadComparisonImages();
            }
        });
    });
    
    const chartSubTabBtns = document.querySelectorAll('.chart-sub-tab-btn');
    chartSubTabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const subTabId = btn.dataset.chartSubTab;
            
            chartSubTabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            document.querySelectorAll('.chart-sub-tab-content').forEach(pane => {
                pane.classList.remove('active');
            });
            document.getElementById('chart-sub-tab-' + subTabId).classList.add('active');
            
            if (subTabId === 'park') {
                loadParkPowerChart();
            }
            if (subTabId === 'community') {
                loadChartCommunityPower();
            }
        });
    });
    
    const subTabBtns = document.querySelectorAll('.sub-tab-btn');
    subTabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const subTabId = btn.dataset.subTab;
            
            subTabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            document.querySelectorAll('.sub-tab-content').forEach(pane => {
                pane.classList.remove('active');
            });
            document.getElementById('sub-tab-' + subTabId).classList.add('active');
            
            if (subTabId === 'convergence') {
                loadConvergenceChart();
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
    document.getElementById('feed-in-price').value = currentConfig.feed_in_price;
    
    loadPanelDetail();
}

async function recalculate() {
    showLoading();
    try {
        const result = await fetchAPI('/api/calculate', 'POST');
        if (result.success) {
            updateCharts(result.data.chart_data);
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
    const electricityPrice = parseFloat(document.getElementById('electricity-price').value);
    const feedInPrice = parseFloat(document.getElementById('feed-in-price').value);
    try {
        const result1 = await fetchAPI('/api/electricity-price/update', 'POST', { electricity_price: electricityPrice });
        const result2 = await fetchAPI('/api/feed-in-price/update', 'POST', { feed_in_price: feedInPrice });
        if (result1.success && result2.success) {
            alert('电价配置已保存');
        } else {
            alert('保存失败: ' + (result1.error || result2.error));
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
    loadParkPowerChart();
});

async function loadOptimizationData() {
    try {
        const [scenariosRes, metricsRes, summaryRes, economicRes, renewableRes, carbonRes] = await Promise.all([
            fetchAPI('/api/optimization/typical-scenarios'),
            fetchAPI('/api/optimization/typical-metrics'),
            fetchAPI('/api/optimization/annual-summary'),
            fetchAPI('/api/optimization/chart/economic-comparison'),
            fetchAPI('/api/optimization/chart/renewable-utilization'),
            fetchAPI('/api/optimization/chart/carbon-analysis')
        ]);
        
        if (scenariosRes.success && metricsRes.success && summaryRes.success) {
            renderAnnualSummary(summaryRes.data);
            renderScenariosTable(scenariosRes.data, metricsRes.data);
        }
        
        if (economicRes.success) {
            renderClickableChart('economic-chart', economicRes.data, '经济性对比');
        }
        
        if (renewableRes.success) {
            renderClickableChart('renewable-chart', renewableRes.data, '可再生能源利用');
        }
        
        if (carbonRes.success) {
            renderClickableChart('carbon-chart', carbonRes.data, '碳排放分析');
        }
        
        loadPowerChartByScenario();
    } catch (e) {
        console.error('加载优化数据失败:', e);
    }
}

async function loadConvergenceChart() {
    try {
        const res = await fetchAPI('/api/optimization/chart/admm-convergence');
        if (res.success) {
            renderClickableChart('admm-convergence-chart', res.data, 'ADMM算法收敛曲线');
        }
    } catch (e) {
        console.error('加载收敛曲线失败:', e);
    }
}

async function loadPowerChartByScenario() {
    const select = document.getElementById('power-scenario-select');
    const scenario = select ? select.value : 'S3';
    
    try {
        const res = await fetchAPI(`/api/optimization/chart/hourly-power-data?scenario=${scenario}`);
        if (res.success) {
            renderInteractivePowerChart('hourly-power-chart', res);
        }
    } catch (e) {
        console.error('加载功率曲线失败:', e);
    }
}

async function loadParkPowerChart() {
    const select = document.getElementById('park-scenario-select');
    const scenario = select ? select.value : 'S3';
    
    try {
        const res = await fetchAPI(`/api/optimization/chart/hourly-power-data?scenario=${scenario}`);
        if (res.success) {
            renderInteractivePowerChart('park-power-chart', res);
        }
    } catch (e) {
        console.error('加载功率曲线失败:', e);
    }
}

async function loadCommunityChartByScenario() {
    const scenarioSelect = document.getElementById('community-scenario-select');
    const communitySelect = document.getElementById('community-id-select');
    const scenario = scenarioSelect ? scenarioSelect.value : 'S3';
    const community = communitySelect ? communitySelect.value : '1';
    
    try {
        const res = await fetchAPI(`/api/optimization/chart/community-power-data?scenario=${scenario}&community=${community}`);
        if (res.success) {
            renderInteractivePowerChart('community-power-chart', res);
        }
    } catch (e) {
        console.error('加载社区功率曲线失败:', e);
    }
}

async function loadChartCommunityPower() {
    const scenarioSelect = document.getElementById('chart-community-scenario-select');
    const communitySelect = document.getElementById('chart-community-id-select');
    const scenario = scenarioSelect ? scenarioSelect.value : 'S3';
    const community = communitySelect ? communitySelect.value : '1';
    
    try {
        const res = await fetchAPI(`/api/optimization/chart/community-power-data?scenario=${scenario}&community=${community}`);
        if (res.success) {
            renderInteractivePowerChart('chart-community-power-chart', res);
        }
    } catch (e) {
        console.error('加载社区功率曲线失败:', e);
    }
}

function renderInteractivePowerChart(containerId, data) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    
    const supplyDiv = document.createElement('div');
    supplyDiv.id = 'power-supply-chart';
    supplyDiv.style.height = '300px';
    
    const demandDiv = document.createElement('div');
    demandDiv.id = 'power-demand-chart';
    demandDiv.style.height = '300px';
    
    const socDiv = document.createElement('div');
    socDiv.id = 'power-soc-chart';
    socDiv.style.height = '280px';
    
    container.appendChild(supplyDiv);
    container.appendChild(demandDiv);
    container.appendChild(socDiv);
    
    const hours = data.supply.hours;
    
    const supplyTraces = [
        { x: hours, y: data.supply.pv, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '光伏', line: { color: '#f1c40f' }, hovertemplate: '光伏: %{y:.2f} MW<extra></extra>' },
        { x: hours, y: data.supply.wind, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '风电', line: { color: '#3498db' }, hovertemplate: '风电: %{y:.2f} MW<extra></extra>' },
        { x: hours, y: data.supply.grid, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '电网', line: { color: '#95a5a6' }, hovertemplate: '电网: %{y:.2f} MW<extra></extra>' },
        { x: hours, y: data.supply.discharge, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '储能放电', line: { color: '#2ecc71' }, hovertemplate: '储能放电: %{y:.2f} MW<extra></extra>' },
        { x: hours, y: data.supply.chp, type: 'scatter', mode: 'lines', stackgroup: 'one', name: 'CHP', line: { color: '#e74c3c' }, hovertemplate: 'CHP: %{y:.2f} MW<extra></extra>' },
        { x: hours, y: data.supply.fc, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '燃料电池', line: { color: '#8e44ad' }, hovertemplate: '燃料电池: %{y:.2f} MW<extra></extra>' },
        { x: hours, y: data.demand_total, type: 'scatter', mode: 'lines', name: '总用电', line: { color: '#000000', width: 2.5 }, hovertemplate: '总用电: %{y:.2f} MW<extra></extra>' }
    ];
    
    const demandTraces = [
        { x: hours, y: data.demand.load, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '电负荷', line: { color: '#e74c3c' }, hovertemplate: '电负荷: %{y:.2f} MW<extra></extra>' },
        { x: hours, y: data.demand.elec, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '电解槽', line: { color: '#9b59b6' }, hovertemplate: '电解槽: %{y:.2f} MW<extra></extra>' },
        { x: hours, y: data.demand.eb, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '电锅炉', line: { color: '#f39c12' }, hovertemplate: '电锅炉: %{y:.2f} MW<extra></extra>' },
        { x: hours, y: data.demand.comp, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '压缩机', line: { color: '#1abc9c' }, hovertemplate: '压缩机: %{y:.2f} MW<extra></extra>' },
        { x: hours, y: data.demand.charge, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '储能充电', line: { color: '#2ecc71' }, hovertemplate: '储能充电: %{y:.2f} MW<extra></extra>' },
        { x: hours, y: data.supply_total, type: 'scatter', mode: 'lines', name: '总供电', line: { color: '#000000', width: 2.5 }, hovertemplate: '总供电: %{y:.2f} MW<extra></extra>' }
    ];
    
    const socTraces = [
        { x: hours, y: data.soc.soc_e, type: 'scatter', mode: 'lines+markers', name: '电储能SOC', line: { color: '#3498db', width: 2 }, marker: { size: 4 }, yaxis: 'y', hovertemplate: '电储能: %{y:.2f} MWh<extra></extra>' },
        { x: hours, y: data.soc.soc_th, type: 'scatter', mode: 'lines+markers', name: '热储能SOC', line: { color: '#e74c3c', width: 2 }, marker: { size: 4 }, yaxis: 'y', hovertemplate: '热储能: %{y:.2f} MWh<extra></extra>' },
        { x: hours, y: data.soc.soc_h2, type: 'scatter', mode: 'lines+markers', name: '氢储能SOC', line: { color: '#2ecc71', width: 2 }, marker: { size: 4 }, yaxis: 'y2', hovertemplate: '氢储能: %{y:.2f} kg<extra></extra>' }
    ];
    
    const supplyLayout = {
        title: { text: '供电侧', font: { size: 14 } },
        xaxis: { title: '时间 (h)', dtick: 2 },
        yaxis: { title: '功率 (MW)' },
        hovermode: 'x unified',
        legend: { x: 0, y: 1.25, orientation: 'h', font: { size: 10 } },
        margin: { t: 65, b: 40, l: 55, r: 25 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(248,249,250,1)'
    };
    
    const demandLayout = {
        title: { text: '用电侧', font: { size: 14 } },
        xaxis: { title: '时间 (h)', dtick: 2 },
        yaxis: { title: '功率 (MW)' },
        hovermode: 'x unified',
        legend: { x: 0, y: 1.25, orientation: 'h', font: { size: 10 } },
        margin: { t: 65, b: 40, l: 55, r: 25 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(248,249,250,1)'
    };
    
    const socLayout = {
        title: { text: '储能SOC', font: { size: 14 } },
        xaxis: { title: '时间 (h)', dtick: 2 },
        yaxis: { title: '电/热储能 (MWh)', side: 'left' },
        yaxis2: { title: '氢储能', side: 'right', overlaying: 'y' },
        hovermode: 'x unified',
        legend: { x: 0, y: 1.25, orientation: 'h', font: { size: 10 } },
        margin: { t: 65, b: 40, l: 55, r: 55 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(248,249,250,1)'
    };
    
    const config = { responsive: true, displayModeBar: true };
    
    Plotly.newPlot(supplyDiv, supplyTraces, supplyLayout, config);
    Plotly.newPlot(demandDiv, demandTraces, demandLayout, config);
    Plotly.newPlot(socDiv, socTraces, socLayout, config);
}

function renderClickableChart(containerId, imageData, title) {
    const container = document.getElementById(containerId);
    const img = document.createElement('img');
    img.src = `data:image/png;base64,${imageData}`;
    img.style.cssText = 'width:100%;height:auto;cursor:pointer;';
    img.onclick = () => showFullscreenChart(imageData, title);
    container.innerHTML = '';
    container.appendChild(img);
}

function showFullscreenChart(imageData, title) {
    const overlay = document.createElement('div');
    overlay.className = 'fullscreen-overlay';
    overlay.onclick = (e) => {
        if (e.target === overlay) {
            document.body.removeChild(overlay);
        }
    };
    
    const closeBtn = document.createElement('div');
    closeBtn.className = 'fullscreen-close';
    closeBtn.innerHTML = '&times;';
    closeBtn.onclick = () => document.body.removeChild(overlay);
    
    const img = document.createElement('img');
    img.src = `data:image/png;base64,${imageData}`;
    img.onclick = (e) => e.stopPropagation();
    
    const label = document.createElement('div');
    label.className = 'fullscreen-label';
    label.innerHTML = `<strong>${title}</strong>`;
    
    overlay.appendChild(closeBtn);
    overlay.appendChild(img);
    overlay.appendChild(label);
    document.body.appendChild(overlay);
    
    document.addEventListener('keydown', function escHandler(e) {
        if (e.key === 'Escape') {
            if (document.body.contains(overlay)) {
                document.body.removeChild(overlay);
            }
            document.removeEventListener('keydown', escHandler);
        }
    });
}

function renderAnnualSummary(data) {
    if (!data || data.length === 0) return;
    
    const summary = data[0];
    const container = document.getElementById('annual-summary');
    
    container.innerHTML = `
        <div class="summary-card">
            <div class="summary-label">全年总成本</div>
            <div class="summary-value">${(summary.annual_objective / 10000).toFixed(2)} 万元</div>
        </div>
        <div class="summary-card">
            <div class="summary-label">全年购电量</div>
            <div class="summary-value">${summary.annual_grid_energy.toFixed(0)} MWh</div>
        </div>
        <div class="summary-card">
            <div class="summary-label">全年购气量</div>
            <div class="summary-value">${summary.annual_gas_energy.toFixed(0)} MWh</div>
        </div>
        <div class="summary-card">
            <div class="summary-label">全年碳排放</div>
            <div class="summary-value">${summary.annual_carbon_emission.toFixed(0)} tCO₂</div>
        </div>
        <div class="summary-card">
            <div class="summary-label">全年碳配额</div>
            <div class="summary-value">${summary.annual_carbon_quota.toFixed(0)} tCO₂</div>
        </div>
        <div class="summary-card">
            <div class="summary-label">碳交易收益</div>
            <div class="summary-value">${summary.annual_carbon_sell.toFixed(0)} tCO₂</div>
        </div>
        <div class="summary-card">
            <div class="summary-label">新能源利用率</div>
            <div class="summary-value">${summary.annual_renewable_use_rate.toFixed(1)}%</div>
        </div>
        <div class="summary-card">
            <div class="summary-label">全年弃风弃光</div>
            <div class="summary-value">${summary.annual_renewable_curtailment.toFixed(0)} MWh</div>
        </div>
    `;
}

function renderScenariosTable(scenarios, metrics) {
    const container = document.getElementById('scenarios-table');
    
    const uniqueMetrics = metrics.filter((item, index, self) => 
        index === self.findIndex((t) => t.scenario === item.scenario)
    );
    
    let html = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>场景</th>
                    <th>代表天数</th>
                    <th>日成本(元)</th>
                    <th>购电量(MWh)</th>
                    <th>碳排放(tCO₂)</th>
                    <th>新能源利用率(%)</th>
                    <th>弃能量(MWh)</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    uniqueMetrics.forEach((metric, idx) => {
        const scenario = scenarios[idx];
        html += `
            <tr>
                <td>${scenario.scenario_cn}</td>
                <td>${metric.representative_days}</td>
                <td>${metric.total_objective.toFixed(0)}</td>
                <td>${metric.grid_energy.toFixed(2)}</td>
                <td>${metric.carbon_emission.toFixed(1)}</td>
                <td>${metric.renewable_use_rate.toFixed(1)}</td>
                <td>${metric.renewable_curtailment.toFixed(2)}</td>
            </tr>
        `;
    });
    
    html += '</tbody></table>';
    container.innerHTML = html;
}

async function loadComparisonImages() {
    const container = document.getElementById('comparison-images');
    
    if (container.innerHTML.trim() !== '') return;
    
    try {
        const costRes = await fetchAPI('/api/optimization/chart/cost-breakdown');
        if (costRes.success) {
            renderClickableChart('cost-breakdown-chart', costRes.data, '成本构成分解');
        }
        
        const result = await fetchAPI('/api/optimization/comparison/images');
        
        if (result.success) {
            const imageMap = {};
            const descMap = {};
            
            result.data.forEach(img => {
                const figNum = img.figure_num;
                if (!imageMap[figNum]) {
                    imageMap[figNum] = [];
                    descMap[figNum] = {
                        title: img.title,
                        description: img.description
                    };
                }
                imageMap[figNum].push(img);
            });
            
            const sortedNums = Object.keys(imageMap).sort((a, b) => {
                const order = ['Fig1', 'Fig4', 'Fig5', 'Fig7a', 'Fig7b', 'Fig8', 'Fig9', 'Fig10'];
                return order.indexOf(a) - order.indexOf(b);
            });
            
            const singleImageSections = [];
            const multiImageSections = [];
            
            sortedNums.forEach(figNum => {
                if (imageMap[figNum].length === 1) {
                    singleImageSections.push({
                        figNum: figNum,
                        data: imageMap[figNum],
                        info: descMap[figNum]
                    });
                } else {
                    multiImageSections.push({
                        figNum: figNum,
                        data: imageMap[figNum],
                        info: descMap[figNum]
                    });
                }
            });
            
            for (let i = 0; i < singleImageSections.length; i += 2) {
                const rowContainer = document.createElement('div');
                rowContainer.className = 'comparison-row';
                
                for (let j = 0; j < 2 && i + j < singleImageSections.length; j++) {
                    const item = singleImageSections[i + j];
                    const section = document.createElement('div');
                    section.className = 'comparison-section comparison-section-half';
                    
                    const titleEl = document.createElement('h4');
                    titleEl.textContent = item.info.title;
                    section.appendChild(titleEl);
                    
                    const descEl = document.createElement('p');
                    descEl.className = 'comparison-description';
                    descEl.textContent = item.info.description;
                    section.appendChild(descEl);
                    
                    const grid = document.createElement('div');
                    grid.className = 'comparison-images-grid';
                    grid.style.gridTemplateColumns = '1fr';
                    
                    item.data.forEach(img => {
                        const wrapper = document.createElement('div');
                        wrapper.className = 'comparison-image-wrapper';
                        wrapper.onclick = () => showFullscreenImage(img.data, img.scenario, img.title);
                        
                        const scenarioLabel = document.createElement('div');
                        scenarioLabel.className = 'comparison-scenario-label';
                        scenarioLabel.textContent = img.scenario;
                        
                        const imgEl = document.createElement('img');
                        imgEl.src = `data:image/png;base64,${img.data}`;
                        imgEl.alt = img.filename;
                        
                        wrapper.appendChild(scenarioLabel);
                        wrapper.appendChild(imgEl);
                        grid.appendChild(wrapper);
                    });
                    
                    section.appendChild(grid);
                    rowContainer.appendChild(section);
                }
                
                container.appendChild(rowContainer);
            }
            
            multiImageSections.forEach(item => {
                const section = document.createElement('div');
                section.className = 'comparison-section';
                
                const titleEl = document.createElement('h4');
                titleEl.textContent = item.info.title;
                section.appendChild(titleEl);
                
                const descEl = document.createElement('p');
                descEl.className = 'comparison-description';
                descEl.textContent = item.info.description;
                section.appendChild(descEl);
                
                const grid = document.createElement('div');
                grid.className = 'comparison-images-grid';
                
                item.data.forEach(img => {
                    const wrapper = document.createElement('div');
                    wrapper.className = 'comparison-image-wrapper';
                    wrapper.onclick = () => showFullscreenImage(img.data, img.scenario, img.title);
                    
                    const scenarioLabel = document.createElement('div');
                    scenarioLabel.className = 'comparison-scenario-label';
                    scenarioLabel.textContent = img.scenario;
                    
                    const imgEl = document.createElement('img');
                    imgEl.src = `data:image/png;base64,${img.data}`;
                    imgEl.alt = img.filename;
                    
                    wrapper.appendChild(scenarioLabel);
                    wrapper.appendChild(imgEl);
                    grid.appendChild(wrapper);
                });
                
                section.appendChild(grid);
                container.appendChild(section);
            });
        }
    } catch (e) {
        console.error('加载对比图片失败:', e);
        container.innerHTML = '<p>加载失败，请重试</p>';
    }
}

function showFullscreenImage(imageData, scenario, title) {
    const overlay = document.createElement('div');
    overlay.className = 'fullscreen-overlay';
    overlay.onclick = (e) => {
        if (e.target === overlay) {
            document.body.removeChild(overlay);
        }
    };
    
    const closeBtn = document.createElement('div');
    closeBtn.className = 'fullscreen-close';
    closeBtn.innerHTML = '&times;';
    closeBtn.onclick = () => document.body.removeChild(overlay);
    
    const img = document.createElement('img');
    img.src = `data:image/png;base64,${imageData}`;
    img.onclick = (e) => e.stopPropagation();
    
    const label = document.createElement('div');
    label.className = 'fullscreen-label';
    label.innerHTML = `<strong>${title}</strong> - ${scenario}`;
    
    overlay.appendChild(closeBtn);
    overlay.appendChild(img);
    overlay.appendChild(label);
    document.body.appendChild(overlay);
    
    document.addEventListener('keydown', function escHandler(e) {
        if (e.key === 'Escape') {
            if (document.body.contains(overlay)) {
                document.body.removeChild(overlay);
            }
            document.removeEventListener('keydown', escHandler);
        }
    });
}
