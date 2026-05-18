const plotlyConfig = {
    responsive: true,
    displayModeBar: false
};

const darkLayout = {
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: '#7b8fa8', family: 'JetBrains Mono, Microsoft YaHei, sans-serif' },
    xaxis: {
        gridcolor: 'rgba(20, 48, 77, 0.4)',
        zerolinecolor: 'rgba(20, 48, 77, 0.6)',
        tickfont: { size: 11, color: '#7b8fa8' }
    },
    yaxis: {
        gridcolor: 'rgba(20, 48, 77, 0.4)',
        zerolinecolor: 'rgba(20, 48, 77, 0.6)',
        tickfont: { size: 11, color: '#7b8fa8' }
    },
    margin: { t: 30, b: 40, l: 50, r: 20 },
    legend: {
        font: { size: 11, color: '#7b8fa8' },
        bgcolor: 'rgba(0,0,0,0)'
    }
};

const communityMap = {
    'commercial': { id: '2', name: '商业区' },
    'residential': { id: '3', name: '居民区' },
    'industrial': { id: '1', name: '工业区' }
};

let currentView = 'overview';
let currentMode = 'scenario';

const scenarioSelectors = ['scenario-select', 'h2-scenario-select', 'dr-scenario-select'];
const weatherSelectors = ['weather-select', 'h2-weather-select', 'dr-weather-select'];

function switchMode(mode) {
    currentMode = mode;

    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });

    const showScenario = mode === 'scenario';
    scenarioSelectors.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = showScenario ? '' : 'none';
    });
    weatherSelectors.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = showScenario ? 'none' : '';
    });

    loadDailyKPIs();
    loadParkPowerChart();
    loadH2PowerChart();
    loadDRPowerChart();
    loadEnergySummary();
}

function syncAndLoad(sourceId) {
    const isWeather = sourceId.includes('weather');
    const selectors = isWeather ? weatherSelectors : scenarioSelectors;
    const source = document.getElementById(sourceId);
    if (!source) return;
    const value = source.value;

    selectors.forEach(id => {
        if (id !== sourceId) {
            const el = document.getElementById(id);
            if (el) el.value = value;
        }
    });

    if (sourceId === 'scenario-select' || sourceId === 'weather-select') {
        loadParkPowerChart();
    }
    loadDailyKPIs();
    loadH2PowerChart();
    loadDRPowerChart();
    loadEnergySummary();
}

function updateDateTime() {
    const now = new Date();
    const options = {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    };
    const el = document.getElementById('current-datetime');
    if (el) {
        el.textContent = now.toLocaleString('zh-CN', options);
    }
}

setInterval(updateDateTime, 1000);
updateDateTime();

function showOverview() {
    document.getElementById('overview-view').style.display = 'grid';
    document.getElementById('community-view').style.display = 'none';
    currentView = 'overview';

    document.querySelectorAll('.community-card, .map-community').forEach(card => {
        card.classList.remove('active');
    });
}

function selectCommunity(type) {
    const community = communityMap[type];
    if (!community) return;

    document.querySelectorAll('.community-card, .map-community').forEach(card => {
        card.classList.remove('active');
    });
    const targetCard = document.querySelector(`[data-community="${type}"]`);
    if (targetCard) {
        targetCard.classList.add('active');
    }

    document.getElementById('overview-view').style.display = 'none';
    document.getElementById('community-view').style.display = 'block';
    document.getElementById('community-title').textContent = community.name + ' - 运行监控';
    currentView = 'community';

    // Sync community mode toggle and select values with current mode
    const commView = document.getElementById('community-view');
    commView.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === currentMode);
    });
    const cSel = document.getElementById('community-scenario-select');
    const wSel = document.getElementById('community-weather-select');
    if (cSel) cSel.style.display = currentMode === 'scenario' ? '' : 'none';
    if (wSel) wSel.style.display = currentMode === 'scenario' ? 'none' : '';
    // Sync select values
    const ovScenario = document.getElementById('scenario-select');
    const ovWeather = document.getElementById('weather-select');
    if (cSel && ovScenario) cSel.value = ovScenario.value;
    if (wSel && ovWeather) wSel.value = ovWeather.value;

    loadCommunityData(community.id);
}

function switchCommunityMode(mode) {
    const view = document.getElementById('community-view');
    view.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });

    const showScenario = mode === 'scenario';
    const cSel = document.getElementById('community-scenario-select');
    const wSel = document.getElementById('community-weather-select');
    if (cSel) cSel.style.display = showScenario ? '' : 'none';
    if (wSel) wSel.style.display = showScenario ? 'none' : '';

    // Sync with overview mode
    currentMode = mode;
    document.querySelectorAll('#overview-view .mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });
    scenarioSelectors.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = showScenario ? '' : 'none';
    });
    weatherSelectors.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = showScenario ? 'none' : '';
    });

    // Reload community data with current community
    const activeCard = document.querySelector('.map-community.active');
    if (activeCard) {
        const type = activeCard.dataset.community;
        const community = communityMap[type];
        if (community) loadCommunityData(community.id);
    }
}

function onCommunitySelectChange() {
    const activeCard = document.querySelector('.map-community.active');
    if (activeCard) {
        const type = activeCard.dataset.community;
        const community = communityMap[type];
        if (community) loadCommunityData(community.id);
    }
}

async function loadOverviewData() {
    loadAnnualSummary();
    loadDailyKPIs();
    loadParkPowerChart();
    loadEconomicChart();
    loadRenewableChart();
    loadCarbonChart();
    loadH2PowerChart();
    loadH2ShortageChart();
    loadDRPowerChart();
    loadCostBreakdownChart();
    loadScenariosTable();
    loadCapacityTable();
    loadDeviceStatus();
    loadEnergySummary();
}

function updateOverviewMetrics(data) {
    if (!data.chart) return;

    const chart = data.chart;
    const totalSolar = chart.solar.reduce((a, b) => a + Math.max(0, b), 0);
    const totalWind = chart.wind.reduce((a, b) => a + Math.max(0, b), 0);
    const totalGeneration = (totalSolar + totalWind) / 1000;

    document.getElementById('total-generation').textContent = totalGeneration.toFixed(1);

    updateStorageGauge(chart.soc);
}

function updateStorageGauge(socData) {
    if (!socData || socData.length === 0) return;

    const currentSOC = socData[socData.length - 1] * 100;
    const socValue = document.getElementById('soc-value');
    const socArc = document.getElementById('soc-arc');

    if (socValue) {
        socValue.textContent = currentSOC.toFixed(0);
    }

    if (socArc) {
        const circumference = 339.292;
        const offset = circumference - (circumference * currentSOC / 100);
        socArc.style.strokeDashoffset = offset;
    }
}

async function loadAnnualSummary() {
    try {
        const response = await fetch('/api/optimization/annual-summary');
        const result = await response.json();

        if (result.success && result.data.length > 0) {
            const summary = result.data[0];

            // Annual cost will be updated from planning cost breakdown for consistency
            document.getElementById('annual-carbon').textContent =
                summary.annual_carbon_emission.toFixed(0);
            document.getElementById('renewable-ratio').textContent =
                summary.annual_renewable_use_rate.toFixed(1);
            document.getElementById('annual-grid-energy').textContent =
                summary.annual_grid_energy.toFixed(0);
            document.getElementById('annual-gas-energy').textContent =
                summary.annual_gas_energy.toFixed(0);
            document.getElementById('annual-carbon-quota').textContent =
                summary.annual_carbon_quota.toFixed(0);
            document.getElementById('annual-carbon-sell').textContent =
                summary.annual_carbon_sell.toFixed(0);
            document.getElementById('annual-curtailment').textContent =
                summary.annual_renewable_curtailment.toFixed(0);
            document.getElementById('annual-h2-shortage').textContent =
                summary.annual_h2_shortage.toFixed(0);

            const totalGeneration = summary.annual_renewable_use / 1000;
            document.getElementById('total-generation').textContent =
                totalGeneration.toFixed(1);
        }
    } catch (error) {
        console.error('加载年度汇总失败:', error);
    }
}

async function loadDailyKPIs() {
    let url;
    if (currentMode === 'weather') {
        const select = document.getElementById('weather-select');
        const weather = select ? select.value : 'Sunny_LowWind';
        url = `/api/optimization/daily-kpis?mode=weather&weather=${weather}`;
    } else {
        const select = document.getElementById('scenario-select');
        const scenario = select ? select.value : 'S4';
        url = `/api/optimization/daily-kpis?scenario=${scenario}`;
    }

    try {
        const res = await fetch(url);
        const result = await res.json();
        if (result.success) {
            const d = result.data;
            animateKPI('kpi-cost', d.cost, 0);
            animateKPI('kpi-grid', d.grid_energy, 1);
            animateKPI('kpi-carbon', d.carbon_emission, 1);
            animateKPI('kpi-renewable', d.renewable_rate, 1);
        }
    } catch (e) {
        console.error('加载日核心指标失败:', e);
    }
}

function animateKPI(id, target, decimals) {
    const el = document.getElementById(id);
    if (!el) return;

    const current = parseFloat(el.textContent.replace(/,/g, '')) || 0;
    const diff = target - current;
    const steps = 20;
    const stepVal = diff / steps;
    let frame = 0;

    function tick() {
        frame++;
        const val = frame >= steps ? target : current + stepVal * frame;
        el.textContent = val.toFixed(decimals).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
        if (frame < steps) requestAnimationFrame(tick);
    }

    requestAnimationFrame(tick);
}

async function loadParkPowerChart() {
    let url;
    if (currentMode === 'weather') {
        const select = document.getElementById('weather-select');
        const weather = select ? select.value : 'Sunny_LowWind';
        url = `/api/optimization/chart/hourly-power-data?mode=weather&weather=${weather}`;
    } else {
        const select = document.getElementById('scenario-select');
        const scenario = select ? select.value : 'S4';
        url = `/api/optimization/chart/hourly-power-data?scenario=${scenario}`;
    }

    try {
        const res = await fetch(url);
        const result = await res.json();

        if (result.success) {
            renderParkPowerChart(result);
        }
    } catch (e) {
        console.error('加载功率曲线失败:', e);
    }

    loadEnergySummary();
}

function renderParkPowerChart(data) {
    const container = document.getElementById('overview-power-chart');
    container.innerHTML = '';

    const supplyDiv = document.createElement('div');
    supplyDiv.style.height = '200px';
    supplyDiv.style.marginBottom = '8px';

    const demandDiv = document.createElement('div');
    demandDiv.style.height = '200px';
    demandDiv.style.marginBottom = '8px';

    const socDiv = document.createElement('div');
    socDiv.style.height = '160px';

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
        { x: hours, y: data.demand_total, type: 'scatter', mode: 'lines', name: '总用电', line: { color: '#ffffff', width: 2.5 }, hovertemplate: '总用电: %{y:.2f} MW<extra></extra>' }
    ];

    const demandTraces = [
        { x: hours, y: data.demand.load, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '电负荷', line: { color: '#e74c3c' }, hovertemplate: '电负荷: %{y:.2f} MW<extra></extra>' },
        { x: hours, y: data.demand.elec, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '电解槽', line: { color: '#9b59b6' }, hovertemplate: '电解槽: %{y:.2f} MW<extra></extra>' },
        { x: hours, y: data.demand.eb, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '电锅炉', line: { color: '#f39c12' }, hovertemplate: '电锅炉: %{y:.2f} MW<extra></extra>' },
        { x: hours, y: data.demand.comp, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '压缩机', line: { color: '#1abc9c' }, hovertemplate: '压缩机: %{y:.2f} MW<extra></extra>' },
        { x: hours, y: data.demand.charge, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '储能充电', line: { color: '#2ecc71' }, hovertemplate: '储能充电: %{y:.2f} MW<extra></extra>' },
        { x: hours, y: data.supply_total, type: 'scatter', mode: 'lines', name: '总供电', line: { color: '#ffffff', width: 2.5 }, hovertemplate: '总供电: %{y:.2f} MW<extra></extra>' }
    ];

    const socTraces = [
        { x: hours, y: data.soc.soc_e, type: 'scatter', mode: 'lines+markers', name: '电储能SOC', line: { color: '#3498db', width: 2 }, marker: { size: 4 }, yaxis: 'y', hovertemplate: '电储能: %{y:.2f} MWh<extra></extra>' },
        { x: hours, y: data.soc.soc_th, type: 'scatter', mode: 'lines+markers', name: '热储能SOC', line: { color: '#e74c3c', width: 2 }, marker: { size: 4 }, yaxis: 'y', hovertemplate: '热储能: %{y:.2f} MWh<extra></extra>' },
        { x: hours, y: data.soc.soc_h2, type: 'scatter', mode: 'lines+markers', name: '氢储能SOC', line: { color: '#2ecc71', width: 2 }, marker: { size: 4 }, yaxis: 'y2', hovertemplate: '氢储能: %{y:.2f} kg<extra></extra>' }
    ];

    const supplyLayout = {
        ...darkLayout,
        title: { text: '供电侧', font: { size: 14, color: '#e2ecf7' } },
        xaxis: { ...darkLayout.xaxis, title: { text: '时间 (h)', font: { size: 12 } }, dtick: 2 },
        yaxis: { ...darkLayout.yaxis, title: { text: '功率 (MW)', font: { size: 12 } } },
        hovermode: 'x unified',
        legend: { ...darkLayout.legend, x: 0, y: -0.35, orientation: 'h', font: { size: 10, color: '#7b8fa8' } },
        margin: { t: 40, b: 80, l: 55, r: 25 }
    };

    const demandLayout = {
        ...darkLayout,
        title: { text: '用电侧', font: { size: 14, color: '#e2ecf7' } },
        xaxis: { ...darkLayout.xaxis, title: { text: '时间 (h)', font: { size: 12 } }, dtick: 2 },
        yaxis: { ...darkLayout.yaxis, title: { text: '功率 (MW)', font: { size: 12 } } },
        hovermode: 'x unified',
        legend: { ...darkLayout.legend, x: 0, y: -0.35, orientation: 'h', font: { size: 10, color: '#7b8fa8' } },
        margin: { t: 40, b: 80, l: 55, r: 25 }
    };

    const socLayout = {
        ...darkLayout,
        title: { text: '储能SOC', font: { size: 14, color: '#e2ecf7' } },
        xaxis: { ...darkLayout.xaxis, title: { text: '时间 (h)', font: { size: 12 } }, dtick: 2 },
        yaxis: { ...darkLayout.yaxis, title: { text: '电/热储能 (MWh)', font: { size: 12 } }, side: 'left' },
        yaxis2: { title: { text: '氢储能 (kg)', font: { size: 12 } }, side: 'right', overlaying: 'y', gridcolor: 'rgba(0,0,0,0)', tickfont: { size: 11, color: '#7b8fa8' } },
        hovermode: 'x unified',
        legend: { ...darkLayout.legend, x: 0, y: -0.35, orientation: 'h', font: { size: 10, color: '#7b8fa8' } },
        margin: { t: 40, b: 80, l: 55, r: 55 }
    };

    Plotly.newPlot(supplyDiv, supplyTraces, supplyLayout, plotlyConfig);
    Plotly.newPlot(demandDiv, demandTraces, demandLayout, plotlyConfig);
    Plotly.newPlot(socDiv, socTraces, socLayout, plotlyConfig);
}

async function loadEconomicChart() {
    try {
        const response = await fetch('/api/optimization/chart/economic-comparison');
        const result = await response.json();

        if (result.success) {
            renderEconomicChart(result.data);
        }
    } catch (error) {
        console.error('加载经济性对比失败:', error);
    }
}

function renderEconomicChart(imageData) {
    const container = document.getElementById('economic-chart');
    const img = document.createElement('img');
    img.src = `data:image/png;base64,${imageData}`;
    img.style.cssText = 'width:100%;height:auto;max-height:300px;object-fit:contain;';
    container.innerHTML = '';
    container.appendChild(img);
}

async function loadRenewableChart() {
    try {
        const response = await fetch('/api/optimization/chart/renewable-utilization');
        const result = await response.json();

        if (result.success) {
            renderRenewableChart(result.data);
        }
    } catch (error) {
        console.error('加载可再生能源利用失败:', error);
    }
}

function renderRenewableChart(imageData) {
    const container = document.getElementById('renewable-chart');
    const img = document.createElement('img');
    img.src = `data:image/png;base64,${imageData}`;
    img.style.cssText = 'width:100%;height:auto;max-height:300px;object-fit:contain;';
    container.innerHTML = '';
    container.appendChild(img);
}

async function loadCarbonChart() {
    try {
        const response = await fetch('/api/optimization/chart/carbon-analysis');
        const result = await response.json();

        if (result.success) {
            renderCarbonChart(result.data);
        }
    } catch (error) {
        console.error('加载碳排放分析失败:', error);
    }
}

function renderCarbonChart(imageData) {
    const container = document.getElementById('carbon-chart');
    const img = document.createElement('img');
    img.src = `data:image/png;base64,${imageData}`;
    img.style.cssText = 'width:100%;height:auto;max-height:300px;object-fit:contain;';
    container.innerHTML = '';
    container.appendChild(img);
}

async function loadEnergySummary() {
    try {
        let url;
        if (currentMode === 'weather') {
            const select = document.getElementById('weather-select');
            const weather = select ? select.value : 'Sunny_LowWind';
            url = `/api/optimization/energy-summary?mode=weather&weather=${weather}`;
        } else {
            const select = document.getElementById('scenario-select');
            const scenario = select ? select.value : 'S4';
            url = `/api/optimization/energy-summary?scenario=${scenario}`;
        }
        const response = await fetch(url);
        const result = await response.json();

        if (result.success) {
            const data = result.data;

            if (currentMode !== 'weather') {
                document.getElementById('total-generation').textContent =
                    (data.total / 1000).toFixed(1);
            }

            const traces = [{
                values: [data.pv, data.wind, data.grid, data.chp, data.fc, data.discharge],
                labels: ['光伏', '风电', '市电', 'CHP', '燃料电池', '储能放电'],
                type: 'pie',
                hole: 0.6,
                marker: {
                    colors: ['#f1c40f', '#3498db', '#95a5a6', '#e74c3c', '#8e44ad', '#2ecc71']
                },
                textinfo: 'percent',
                textfont: { size: 12, color: '#e2ecf7' },
                hoverinfo: 'label+value+percent',
                hovertemplate: '%{label}<br>%{value:.1f} MWh<br>%{percent}<extra></extra>'
            }];

            const layout = {
                ...darkLayout,
                showlegend: true,
                legend: {
                    font: { size: 11, color: '#7b8fa8' },
                    bgcolor: 'rgba(0,0,0,0)',
                    x: 0,
                    y: -0.15,
                    orientation: 'h'
                },
                margin: { t: 20, b: 50, l: 10, r: 10 }
            };

            Plotly.newPlot('energy-mix-chart', traces, layout, plotlyConfig);
        }
    } catch (error) {
        console.error('加载能源构成失败:', error);
    }
}

async function loadScenariosTable() {
    try {
        const response = await fetch('/api/optimization/typical-metrics');
        const result = await response.json();

        if (result.success) {
            renderScenariosTable(result.data);
        }
    } catch (error) {
        console.error('加载场景数据失败:', error);
    }
}

function renderScenariosTable(metrics) {
    const container = document.getElementById('scenarios-table');

    if (!metrics || metrics.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted); text-align: center; padding: 20px;">暂无数据</div>';
        return;
    }

    const uniqueMetrics = metrics.filter((item, index, self) =>
        index === self.findIndex((t) => t.scenario === item.scenario)
    );

    let html = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>场景</th>
                    <th>天数</th>
                    <th>成本</th>
                    <th>碳排放</th>
                    <th>新能源率</th>
                </tr>
            </thead>
            <tbody>
    `;

    uniqueMetrics.forEach(metric => {
        const scenarioName = metric.scenario_cn || metric.scenario;
        html += `
            <tr>
                <td>${scenarioName}</td>
                <td>${metric.representative_days}</td>
                <td>${(metric.total_objective / 1000).toFixed(1)}k</td>
                <td>${metric.carbon_emission.toFixed(0)}</td>
                <td>${metric.renewable_use_rate.toFixed(1)}%</td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

async function loadDeviceStatus() {
    try {
        const response = await fetch('/api/planning/device-status');
        const result = await response.json();

        if (result.success) {
            const d = result.data;

            document.getElementById('device-solar-power').textContent =
                d.pv_mw.toFixed(1) + ' MW';
            document.getElementById('device-wind-power').textContent =
                d.wind_mw.toFixed(1) + ' MW';
            document.getElementById('device-storage-power').textContent =
                d.battery_mwh.toFixed(1) + ' MWh';
            document.getElementById('device-load-power').textContent =
                d.battery_power_mw.toFixed(1) + ' MW';

            // Update storage gauge with battery capacity info
            const storageCapacity = document.getElementById('storage-capacity');
            if (storageCapacity) storageCapacity.textContent = d.battery_mwh.toFixed(1) + ' MWh';
            const storageCharge = document.getElementById('storage-charge');
            if (storageCharge) storageCharge.textContent = d.battery_power_mw.toFixed(1) + ' MW';
            const storageDischarge = document.getElementById('storage-discharge');
            if (storageDischarge) storageDischarge.textContent = d.battery_power_mw.toFixed(1) + ' MW';

            // Update alerts
            const alertList = document.querySelector('.alert-list');
            if (alertList && d.alerts && d.alerts.length > 0) {
                alertList.innerHTML = d.alerts.map(a => `
                    <div class="alert-item ${a.level}">
                        <span class="alert-icon">
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
                        </span>
                        <span class="alert-text">${a.text}</span>
                        <span class="alert-time">${a.time}</span>
                    </div>
                `).join('');
            }
        }
    } catch (error) {
        console.error('加载设备状态失败:', error);
    }
}

async function loadCommunityData(communityId) {
    let param;
    if (currentMode === 'weather') {
        const sel = document.getElementById('community-weather-select');
        const weather = sel ? sel.value : 'Sunny_LowWind';
        param = `mode=weather&weather=${weather}`;
    } else {
        const sel = document.getElementById('community-scenario-select');
        const scenario = sel ? sel.value : 'S4';
        param = `scenario=${scenario}`;
    }

    try {
        const response = await fetch(`/api/optimization/chart/community-power-data?${param}&community=${communityId}`);
        const result = await response.json();

        if (result.success) {
            renderCommunityCharts(result);
            // Compute daily generation from supply data
            const s = result.supply;
            const sum = arr => arr.reduce((a, b) => a + Math.max(0, b), 0);
            const dailyGen = sum(s.pv) + sum(s.wind) + sum(s.chp) + sum(s.fc) + sum(s.discharge);
            document.getElementById('community-generation').textContent = dailyGen.toFixed(1);
        }
    } catch (error) {
        console.error('加载社区数据失败:', error);
    }

    try {
        const h2drRes = await fetch(`/api/optimization/chart/community-h2-dr-data?${param}&community=${communityId}`);
        const h2drResult = await h2drRes.json();

        if (h2drResult.success) {
            renderCommunityH2Chart(h2drResult.data);
            renderCommunityDRChart(h2drResult.data);
        }
    } catch (error) {
        console.error('加载社区H2/DR数据失败:', error);
    }

    // Load capacity data
    try {
        const capRes = await fetch('/api/planning/capacity');
        const capResult = await capRes.json();

        if (capResult.success) {
            const c = capResult.data.communities.find(x => String(x.id) === String(communityId));
            if (c) {
                document.getElementById('community-solar-capacity').textContent = c.pv_mw.toFixed(1);
                document.getElementById('community-wind-capacity').textContent = c.wind_mw.toFixed(1);
                document.getElementById('community-storage-capacity').textContent = c.battery_mwh.toFixed(1);
                document.getElementById('community-thermal-capacity').textContent = c.thermal_mwh.toFixed(1);
                document.getElementById('community-h2-capacity').textContent = c.h2_kg.toFixed(0);
                document.getElementById('community-battery-power').textContent = c.battery_power_mw.toFixed(1);
            }
        }
    } catch (error) {
        console.error('加载社区容量数据失败:', error);
    }
}

function renderCommunityCharts(data) {
    const hours = data.supply.hours;

    const supplyTraces = [
        { x: hours, y: data.supply.pv, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '光伏', line: { color: '#f1c40f' } },
        { x: hours, y: data.supply.wind, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '风电', line: { color: '#3498db' } },
        { x: hours, y: data.supply.grid, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '电网', line: { color: '#95a5a6' } },
        { x: hours, y: data.supply.discharge, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '储能放电', line: { color: '#2ecc71' } },
        { x: hours, y: data.supply.chp, type: 'scatter', mode: 'lines', stackgroup: 'one', name: 'CHP', line: { color: '#e74c3c' } },
        { x: hours, y: data.supply.fc, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '燃料电池', line: { color: '#8e44ad' } }
    ];

    const demandTraces = [
        { x: hours, y: data.demand.load, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '电负荷', line: { color: '#e74c3c' } },
        { x: hours, y: data.demand.elec, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '电解槽', line: { color: '#9b59b6' } },
        { x: hours, y: data.demand.eb, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '电锅炉', line: { color: '#f39c12' } },
        { x: hours, y: data.demand.comp, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '压缩机', line: { color: '#1abc9c' } },
        { x: hours, y: data.demand.charge, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '储能充电', line: { color: '#2ecc71' } }
    ];

    const socTraces = [
        { x: hours, y: data.soc.soc_e, type: 'scatter', mode: 'lines+markers', name: '电储能SOC', line: { color: '#3498db', width: 2 }, marker: { size: 4 }, yaxis: 'y' },
        { x: hours, y: data.soc.soc_th, type: 'scatter', mode: 'lines+markers', name: '热储能SOC', line: { color: '#e74c3c', width: 2 }, marker: { size: 4 }, yaxis: 'y' },
        { x: hours, y: data.soc.soc_h2, type: 'scatter', mode: 'lines+markers', name: '氢储能SOC', line: { color: '#2ecc71', width: 2 }, marker: { size: 4 }, yaxis: 'y2' }
    ];

    const supplyLayout = {
        ...darkLayout,
        title: { text: '供电侧', font: { size: 14, color: '#e2ecf7' } },
        xaxis: { ...darkLayout.xaxis, title: { text: '时间 (h)' }, dtick: 2 },
        yaxis: { ...darkLayout.yaxis, title: { text: '功率 (MW)' } },
        hovermode: 'x unified',
        legend: { ...darkLayout.legend, x: 0, y: -0.35, orientation: 'h', font: { size: 10, color: '#7b8fa8' } },
        margin: { t: 40, b: 80, l: 55, r: 25 }
    };

    const demandLayout = {
        ...darkLayout,
        title: { text: '用电侧', font: { size: 14, color: '#e2ecf7' } },
        xaxis: { ...darkLayout.xaxis, title: { text: '时间 (h)' }, dtick: 2 },
        yaxis: { ...darkLayout.yaxis, title: { text: '功率 (MW)' } },
        hovermode: 'x unified',
        legend: { ...darkLayout.legend, x: 0, y: -0.35, orientation: 'h', font: { size: 10, color: '#7b8fa8' } },
        margin: { t: 40, b: 80, l: 55, r: 25 }
    };

    const socLayout = {
        ...darkLayout,
        title: { text: '储能SOC', font: { size: 14, color: '#e2ecf7' } },
        xaxis: { ...darkLayout.xaxis, title: { text: '时间 (h)' }, dtick: 2 },
        yaxis: { ...darkLayout.yaxis, title: { text: '电/热储能 (MWh)' }, side: 'left' },
        yaxis2: { title: { text: '氢储能 (kg)' }, side: 'right', overlaying: 'y', gridcolor: 'rgba(0,0,0,0)', tickfont: { size: 11, color: '#7b8fa8' } },
        hovermode: 'x unified',
        legend: { ...darkLayout.legend, x: 0, y: -0.35, orientation: 'h', font: { size: 10, color: '#7b8fa8' } },
        margin: { t: 40, b: 80, l: 55, r: 55 }
    };

    Plotly.newPlot('community-supply-chart', supplyTraces, supplyLayout, plotlyConfig);
    Plotly.newPlot('community-demand-chart', demandTraces, demandLayout, plotlyConfig);
    Plotly.newPlot('community-soc-chart', socTraces, socLayout, plotlyConfig);

    // Community energy mix pie chart
    const sum = arr => arr.reduce((a, b) => a + Math.max(0, b), 0);
    const mixValues = [sum(data.supply.pv), sum(data.supply.wind), sum(data.supply.grid), sum(data.supply.chp), sum(data.supply.fc), sum(data.supply.discharge)];
    const mixLabels = ['光伏', '风电', '市电', 'CHP', '燃料电池', '储能放电'];
    const mixColors = ['#f1c40f', '#3498db', '#95a5a6', '#e74c3c', '#8e44ad', '#2ecc71'];

    // Filter out zero segments
    const filtered = mixValues.map((v, i) => ({ v, l: mixLabels[i], c: mixColors[i] })).filter(x => x.v > 0);

    const mixTraces = [{
        values: filtered.map(x => x.v),
        labels: filtered.map(x => x.l),
        type: 'pie',
        hole: 0.6,
        marker: { colors: filtered.map(x => x.c) },
        textinfo: 'percent',
        textfont: { size: 12, color: '#e2ecf7' },
        hoverinfo: 'label+value+percent',
        hovertemplate: '%{label}<br>%{value:.1f} MWh<br>%{percent}<extra></extra>'
    }];

    const mixLayout = {
        ...darkLayout,
        showlegend: true,
        legend: {
            font: { size: 11, color: '#7b8fa8' },
            bgcolor: 'rgba(0,0,0,0)',
            x: 0,
            y: -0.15,
            orientation: 'h'
        },
        margin: { t: 20, b: 50, l: 10, r: 10 }
    };

    Plotly.newPlot('community-energy-mix-chart', mixTraces, mixLayout, plotlyConfig);
}

function renderCommunityH2Chart(data) {
    const hours = data.hours;
    const h2 = data.h2;

    const traces = [
        { x: hours, y: h2.production, type: 'scatter', mode: 'lines', stackgroup: 'supply', name: '电解制氢', line: { color: '#3498db' } },
        { x: hours, y: h2.storage_discharge, type: 'scatter', mode: 'lines', stackgroup: 'supply', name: '储氢放氢', line: { color: '#2ecc71' } },
        { x: hours, y: h2.fuel_cell, type: 'scatter', mode: 'lines', stackgroup: 'demand', name: '燃料电池', line: { color: '#8e44ad' } },
        { x: hours, y: h2.storage_charge, type: 'scatter', mode: 'lines', stackgroup: 'demand', name: '储氢充氢', line: { color: '#f39c12' } },
        { x: hours, y: h2.load, type: 'scatter', mode: 'lines', stackgroup: 'demand', name: '氢负荷', line: { color: '#e74c3c' } }
    ];

    const layout = {
        ...darkLayout,
        title: { text: '社区氢气供需', font: { size: 14, color: '#e2ecf7' } },
        xaxis: { ...darkLayout.xaxis, title: { text: '时间 (h)' }, dtick: 2 },
        yaxis: { ...darkLayout.yaxis, title: { text: '氢气流量 (kg)' } },
        hovermode: 'x unified',
        legend: { ...darkLayout.legend, x: 0, y: -0.35, orientation: 'h', font: { size: 10, color: '#7b8fa8' } },
        margin: { t: 40, b: 80, l: 55, r: 25 }
    };

    Plotly.newPlot('community-h2-chart', traces, layout, plotlyConfig);
}

function renderCommunityDRChart(data) {
    const hours = data.hours;
    const dr = data.dr;

    const traces = [
        { x: hours, y: dr.load_original, type: 'scatter', mode: 'lines', name: '原始负荷', line: { color: '#e74c3c', width: 2, dash: 'dash' } },
        { x: hours, y: dr.load_after_dr, type: 'scatter', mode: 'lines', name: 'DR调整后', line: { color: '#3498db', width: 2.5 } },
        { x: hours, y: dr.shift, type: 'scatter', mode: 'lines', name: '负荷转移', line: { color: '#f39c12' }, visible: 'legendonly' },
        { x: hours, y: dr.cut_e, type: 'scatter', mode: 'lines', name: '电力削减', line: { color: '#9b59b6' }, visible: 'legendonly' },
        { x: hours, y: dr.hdr_cut, type: 'scatter', mode: 'lines', name: '热力削减', line: { color: '#1abc9c' }, visible: 'legendonly' }
    ];

    const layout = {
        ...darkLayout,
        title: { text: '社区需求响应', font: { size: 14, color: '#e2ecf7' } },
        xaxis: { ...darkLayout.xaxis, title: { text: '时间 (h)' }, dtick: 2 },
        yaxis: { ...darkLayout.yaxis, title: { text: '功率 (MW)' } },
        hovermode: 'x unified',
        legend: { ...darkLayout.legend, x: 0, y: -0.35, orientation: 'h', font: { size: 10, color: '#7b8fa8' } },
        margin: { t: 40, b: 80, l: 55, r: 25 }
    };

    Plotly.newPlot('community-dr-chart', traces, layout, plotlyConfig);
}

async function loadH2PowerChart() {
    let url;
    if (currentMode === 'weather') {
        const select = document.getElementById('h2-weather-select');
        const weather = select ? select.value : 'Sunny_LowWind';
        url = `/api/optimization/chart/h2-power-data?mode=weather&weather=${weather}`;
    } else {
        const select = document.getElementById('h2-scenario-select');
        const scenario = select ? select.value : 'S4';
        url = `/api/optimization/chart/h2-power-data?scenario=${scenario}`;
    }

    try {
        const res = await fetch(url);
        const result = await res.json();

        if (result.success) {
            renderH2PowerChart(result.data);
        }
    } catch (e) {
        console.error('加载氢气供需曲线失败:', e);
    }
}

function renderH2PowerChart(data) {
    const container = document.getElementById('h2-power-chart');
    if (!container) return;
    container.innerHTML = '';

    const h2Div = document.createElement('div');
    h2Div.style.height = '260px';
    h2Div.style.marginBottom = '5px';

    const socDiv = document.createElement('div');
    socDiv.style.height = '180px';

    container.appendChild(h2Div);
    container.appendChild(socDiv);

    const hours = data.hours;

    const h2Traces = [
        { x: hours, y: data.production, type: 'scatter', mode: 'lines', stackgroup: 'supply', name: '电解制氢', line: { color: '#3498db' }, hovertemplate: '电解制氢: %{y:.3f} kg<extra></extra>' },
        { x: hours, y: data.storage_discharge, type: 'scatter', mode: 'lines', stackgroup: 'supply', name: '储氢放氢', line: { color: '#2ecc71' }, hovertemplate: '储氢放氢: %{y:.3f} kg<extra></extra>' },
        { x: hours, y: data.fuel_cell, type: 'scatter', mode: 'lines', stackgroup: 'demand', name: '燃料电池', line: { color: '#8e44ad' }, hovertemplate: '燃料电池: %{y:.3f} kg<extra></extra>' },
        { x: hours, y: data.storage_charge, type: 'scatter', mode: 'lines', stackgroup: 'demand', name: '储氢充氢', line: { color: '#f39c12' }, hovertemplate: '储氢充氢: %{y:.3f} kg<extra></extra>' },
        { x: hours, y: data.load, type: 'scatter', mode: 'lines', stackgroup: 'demand', name: '氢负荷', line: { color: '#e74c3c' }, hovertemplate: '氢负荷: %{y:.3f} kg<extra></extra>' },
    ];

    if (data.shortage.some(v => Math.abs(v) > 1e-6)) {
        h2Traces.push({ x: hours, y: data.shortage, type: 'bar', name: '短缺', marker: { color: '#e74c3c', opacity: 0.6 }, yaxis: 'y2', hovertemplate: '短缺: %{y:.3f} kg<extra></extra>' });
    }

    const h2Layout = {
        ...darkLayout,
        title: { text: '氢气供需平衡', font: { size: 13, color: '#e2ecf7' } },
        xaxis: { ...darkLayout.xaxis, title: { text: '时间 (h)', font: { size: 11 } }, dtick: 2 },
        yaxis: { ...darkLayout.yaxis, title: { text: '氢气流量 (kg)', font: { size: 11 } }, side: 'left' },
        yaxis2: { title: { text: '短缺 (kg)', font: { size: 11 } }, side: 'right', overlaying: 'y', gridcolor: 'rgba(0,0,0,0)', tickfont: { size: 10, color: '#7b8fa8' } },
        hovermode: 'x unified',
        legend: { ...darkLayout.legend, x: 0, y: -0.3, orientation: 'h', font: { size: 9, color: '#7b8fa8' } },
        margin: { t: 35, b: 70, l: 50, r: 45 },
        barmode: 'group'
    };

    const socTraces = [
        { x: hours, y: data.soc_h2, type: 'scatter', mode: 'lines+markers', name: '氢储能SOC', line: { color: '#2ecc71', width: 2 }, marker: { size: 4 }, hovertemplate: 'SOC: %{y:.2f} kg<extra></extra>' }
    ];

    const socLayout = {
        ...darkLayout,
        title: { text: '氢储能状态', font: { size: 12, color: '#e2ecf7' } },
        xaxis: { ...darkLayout.xaxis, title: { text: '时间 (h)', font: { size: 11 } }, dtick: 2 },
        yaxis: { ...darkLayout.yaxis, title: { text: '储氢量 (kg)', font: { size: 11 } } },
        hovermode: 'x unified',
        showlegend: false,
        margin: { t: 30, b: 45, l: 50, r: 20 }
    };

    Plotly.newPlot(h2Div, h2Traces, h2Layout, plotlyConfig);
    Plotly.newPlot(socDiv, socTraces, socLayout, plotlyConfig);
}

async function loadH2ShortageChart() {
    try {
        const response = await fetch('/api/optimization/chart/h2-shortage');
        const result = await response.json();

        if (result.success) {
            renderH2ShortageChart(result.data);
        }
    } catch (error) {
        console.error('加载氢气短缺分析失败:', error);
    }
}

function renderH2ShortageChart(imageData) {
    const container = document.getElementById('h2-shortage-chart');
    if (!container) return;
    const img = document.createElement('img');
    img.src = `data:image/png;base64,${imageData}`;
    img.style.cssText = 'width:100%;height:auto;max-height:300px;object-fit:contain;';
    container.innerHTML = '';
    container.appendChild(img);
}

async function loadDRPowerChart() {
    let url;
    if (currentMode === 'weather') {
        const select = document.getElementById('dr-weather-select');
        const weather = select ? select.value : 'Sunny_LowWind';
        url = `/api/optimization/chart/dr-power-data?mode=weather&weather=${weather}`;
    } else {
        const select = document.getElementById('dr-scenario-select');
        const scenario = select ? select.value : 'S4';
        url = `/api/optimization/chart/dr-power-data?scenario=${scenario}`;
    }

    try {
        const res = await fetch(url);
        const result = await res.json();

        if (result.success) {
            renderDRSummaryMetrics(result.data.summary);
            renderDRPowerChart(result.data);
        }
    } catch (e) {
        console.error('加载需求响应曲线失败:', e);
    }
}

function renderDRSummaryMetrics(summary) {
    const container = document.getElementById('dr-summary-metrics');
    if (!container) return;

    container.innerHTML = `
        <div class="dr-metric-item">
            <div class="dr-metric-value">${summary.total_shift_mwh.toFixed(2)}</div>
            <div class="dr-metric-label">负荷转移 (MWh)</div>
        </div>
        <div class="dr-metric-item">
            <div class="dr-metric-value">${summary.total_cut_e_mwh.toFixed(2)}</div>
            <div class="dr-metric-label">电力削减 (MWh)</div>
        </div>
        <div class="dr-metric-item">
            <div class="dr-metric-value">${summary.total_cut_h_mwh.toFixed(2)}</div>
            <div class="dr-metric-label">热力削减 (MWh)</div>
        </div>
        <div class="dr-metric-item">
            <div class="dr-metric-value">${summary.total_cut_h2_kg.toFixed(2)}</div>
            <div class="dr-metric-label">氢削减 (kg)</div>
        </div>
    `;
}

function renderDRPowerChart(data) {
    const container = document.getElementById('dr-power-chart');
    if (!container) return;
    container.innerHTML = '';

    const loadDiv = document.createElement('div');
    loadDiv.style.height = '200px';
    loadDiv.style.marginBottom = '5px';

    const drDiv = document.createElement('div');
    drDiv.style.height = '260px';

    container.appendChild(loadDiv);
    container.appendChild(drDiv);

    const hours = data.hours;

    const loadTraces = [
        { x: hours, y: data.load_original, type: 'scatter', mode: 'lines', name: '原始负荷', line: { color: '#e74c3c', width: 2, dash: 'dash' }, hovertemplate: '原始: %{y:.3f} MW<extra></extra>' },
        { x: hours, y: data.load_after_dr, type: 'scatter', mode: 'lines', name: 'DR调整后', line: { color: '#3498db', width: 2.5 }, hovertemplate: '调整后: %{y:.3f} MW<extra></extra>' }
    ];

    const loadLayout = {
        ...darkLayout,
        title: { text: '负荷曲线对比', font: { size: 13, color: '#e2ecf7' } },
        xaxis: { ...darkLayout.xaxis, dtick: 2, showticklabels: false },
        yaxis: { ...darkLayout.yaxis, title: { text: '功率 (MW)', font: { size: 11 } } },
        hovermode: 'x unified',
        legend: { ...darkLayout.legend, x: 0, y: -0.12, orientation: 'h', font: { size: 10, color: '#7b8fa8' } },
        margin: { t: 35, b: 35, l: 50, r: 20 }
    };

    const drTraces = [
        { x: hours, y: data.shift, type: 'scatter', mode: 'lines', stackgroup: 'dr', name: '负荷转移', line: { color: '#f39c12' }, hovertemplate: '转移: %{y:.3f} MW<extra></extra>' },
        { x: hours, y: data.cut_e, type: 'scatter', mode: 'lines', stackgroup: 'dr', name: '电力削减', line: { color: '#e74c3c' }, hovertemplate: '电力削减: %{y:.3f} MW<extra></extra>' },
        { x: hours, y: data.hdr_cut, type: 'scatter', mode: 'lines', stackgroup: 'dr', name: '热力削减', line: { color: '#9b59b6' }, hovertemplate: '热力削减: %{y:.3f} MW<extra></extra>' }
    ];

    const drLayout = {
        ...darkLayout,
        title: { text: '需求响应动作', font: { size: 13, color: '#e2ecf7' } },
        xaxis: { ...darkLayout.xaxis, dtick: 2 },
        yaxis: { ...darkLayout.yaxis, title: { text: '功率 (MW)', font: { size: 11 } } },
        hovermode: 'x unified',
        legend: { ...darkLayout.legend, x: 0, y: -0.15, orientation: 'h', font: { size: 10, color: '#7b8fa8' } },
        margin: { t: 30, b: 45, l: 50, r: 20 }
    };

    Plotly.newPlot(loadDiv, loadTraces, loadLayout, plotlyConfig);
    Plotly.newPlot(drDiv, drTraces, drLayout, plotlyConfig);
}

async function loadCostBreakdownChart() {
    try {
        const res = await fetch('/api/planning/annual-cost-breakdown');
        const result = await res.json();

        if (result.success) {
            renderCostBreakdownChart(result.data);
            document.getElementById('annual-cost').textContent =
                (result.data.total / 10000).toFixed(2);
        }
    } catch (e) {
        console.error('加载年度成本构成失败:', e);
    }
}

function renderCostBreakdownChart(data) {
    const container = document.getElementById('cost-breakdown-chart');
    if (!container) return;

    const inv = data.investment;
    const om = data.fixed_om;

    const items = [
        { label: '运行成本', value: data.operation, color: '#3498db' },
        { label: '碳罚成本', value: data.carbon_penalty, color: '#e74c3c' },
        { label: '碳交易成本', value: data.carbon_trading, color: '#2ecc71' },
        { label: '固定运维', value: om.total, color: '#f39c12' },
        { label: '投资成本', value: inv.total, color: '#9b59b6' }
    ];

    const subItems = [
        { label: '热储投资', value: inv.thermal, color: '#e67e22' },
        { label: '氢储投资', value: inv.h2, color: '#1abc9c' },
        { label: '光伏运维', value: om.pv, color: '#f1c40f' },
        { label: '风电运维', value: om.wind, color: '#3498db' },
        { label: '电池运维', value: om.battery, color: '#2ecc71' },
        { label: '热储运维', value: om.thermal, color: '#e74c3c' },
        { label: '氢储运维', value: om.h2, color: '#8e44ad' }
    ];

    const positiveMain = items.filter(x => Math.abs(x.value) > 0.01);
    const positiveSub = subItems.filter(x => Math.abs(x.value) > 0.01);

    container.innerHTML = '';

    const mainDiv = document.createElement('div');
    mainDiv.style.height = '250px';

    const subDiv = document.createElement('div');
    subDiv.style.height = '250px';

    container.appendChild(mainDiv);
    container.appendChild(subDiv);

    const total = data.total;

    const mainTrace = [{
        values: positiveMain.map(x => Math.abs(x.value)),
        labels: positiveMain.map(x => x.label),
        type: 'pie',
        hole: 0.45,
        marker: { colors: positiveMain.map(x => x.color) },
        textinfo: 'percent',
        textfont: { size: 11, color: '#e2ecf7' },
        hoverinfo: 'label+value+percent',
        hovertemplate: '%{label}<br>%{value:,.0f} 元<br>%{percent}<extra></extra>'
    }];

    const subTrace = [{
        values: positiveSub.map(x => Math.abs(x.value)),
        labels: positiveSub.map(x => x.label),
        type: 'pie',
        hole: 0.45,
        marker: { colors: positiveSub.map(x => x.color) },
        textinfo: 'percent',
        textfont: { size: 10, color: '#e2ecf7' },
        hoverinfo: 'label+value+percent',
        hovertemplate: '%{label}<br>%{value:,.0f} 元<br>%{percent}<extra></extra>'
    }];

    const mainLayout = {
        ...darkLayout,
        title: { text: `年总成本 ${(total / 10000).toFixed(1)}万元`, font: { size: 12, color: '#e2ecf7' } },
        showlegend: true,
        legend: { font: { size: 9, color: '#7b8fa8' }, bgcolor: 'rgba(0,0,0,0)', x: 0.5, y: -0.15, xanchor: 'center', orientation: 'h' },
        margin: { t: 30, b: 45, l: 10, r: 10 }
    };

    const subLayout = {
        ...darkLayout,
        title: { text: '投资/运维明细', font: { size: 12, color: '#e2ecf7' } },
        showlegend: true,
        legend: { font: { size: 9, color: '#7b8fa8' }, bgcolor: 'rgba(0,0,0,0)', x: 0.5, y: -0.15, xanchor: 'center', orientation: 'h' },
        margin: { t: 30, b: 45, l: 10, r: 10 }
    };

    Plotly.newPlot(mainDiv, mainTrace, mainLayout, plotlyConfig);
    Plotly.newPlot(subDiv, subTrace, subLayout, plotlyConfig);
}

async function loadCapacityTable() {
    try {
        const res = await fetch('/api/planning/capacity');
        const result = await res.json();

        if (result.success) {
            renderCapacityTable(result.data);
        }
    } catch (e) {
        console.error('加载容量配置失败:', e);
    }
}

function renderCapacityTable(data) {
    const container = document.getElementById('capacity-table');
    if (!container) return;

    const { communities, totals } = data;

    let html = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>区域</th>
                    <th>PV (MW)</th>
                    <th>风电 (MW)</th>
                    <th>电池 (MWh)</th>
                    <th>热储 (MWh)</th>
                    <th>氢储 (kg)</th>
                </tr>
            </thead>
            <tbody>
    `;

    communities.forEach(c => {
        html += `
            <tr>
                <td>${c.name}</td>
                <td>${c.pv_mw.toFixed(1)}</td>
                <td>${c.wind_mw.toFixed(1)}</td>
                <td>${c.battery_mwh.toFixed(1)}</td>
                <td>${c.thermal_mwh.toFixed(1)}</td>
                <td>${c.h2_kg.toFixed(0)}</td>
            </tr>
        `;
    });

    html += `
            <tr style="font-weight:bold;border-top:2px solid var(--border-color)">
                <td>园区合计</td>
                <td>${totals.PV_MW.toFixed(1)}</td>
                <td>${totals.Wind_MW.toFixed(1)}</td>
                <td>${totals.BatteryEnergy_MWh.toFixed(1)}</td>
                <td>${totals.ThermalStorage_MWh.toFixed(1)}</td>
                <td>${totals.HydrogenStorage_kg.toFixed(0)}</td>
            </tr>
        </tbody></table>
    `;

    container.innerHTML = html;
}

const plotlyDarkTemplate = {
    layout: {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#7b8fa8', family: 'JetBrains Mono, Microsoft YaHei, sans-serif' },
        xaxis: {
            gridcolor: 'rgba(20, 48, 77, 0.4)',
            zerolinecolor: 'rgba(20, 48, 77, 0.6)'
        },
        yaxis: {
            gridcolor: 'rgba(20, 48, 77, 0.4)',
            zerolinecolor: 'rgba(20, 48, 77, 0.6)'
        }
    }
};

Plotly.setPlotConfig(plotlyDarkTemplate);

document.addEventListener('DOMContentLoaded', () => {
    loadOverviewData();

    setInterval(() => {
        if (currentView === 'overview') {
            loadDeviceStatus();
        }
    }, 30000);
});
