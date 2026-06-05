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
let currentDashboardWindow = 'daily';
let annualDataLoaded = false;
let dailyDispatchLoaded = false;
let dashboardVoltageData = null;
let currentDailyDispatchData = null;
let currentDailyCurves = { pv_24: [], wind_24: [], matchedDdre: 13 };
let selectedDailyCommunityId = '3';
let selectedDailyNodeId = '1';
let selectedDashboardNodeId = '1';
let dailyVoltageHourIndex = 0;
let dashboardVoltageHourIndex = 0;
let dailyVoltagePlaybackTimer = null;
let dashboardVoltagePlaybackTimer = null;
let communitySource = 'annual';

const scenarioSelectors = ['scenario-select', 'h2-scenario-select', 'dr-scenario-select'];
const weatherSelectors = ['weather-select', 'h2-weather-select', 'dr-weather-select'];

function prepareDashboardWindows() {
    // Daily monitoring now has its own annual-style dashboard layout in the template.
}

let dailyCurrentMode = 'realtime';
const dailyScenarioSelectors = [];
const dailyWeatherSelectors = [];

let weatherConfigLoaded = false;

function switchDashboardWindow(windowName) {
    currentDashboardWindow = windowName === 'annual' ? 'annual' : (windowName === 'weather' ? 'weather' : 'daily');

    const dailyView = document.getElementById('daily-view');
    const annualView = document.getElementById('overview-view');
    const weatherView = document.getElementById('weather-view');
    const communityView = document.getElementById('community-view');

    document.querySelectorAll('.dashboard-window-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.window === currentDashboardWindow);
    });

    if (communityView) {
        communityView.style.display = 'none';
    }
    if (dailyView) {
        dailyView.style.display = currentDashboardWindow === 'daily' ? 'grid' : 'none';
    }
    if (annualView) {
        annualView.style.display = currentDashboardWindow === 'annual' ? 'grid' : 'none';
    }
    if (weatherView) {
        weatherView.style.display = currentDashboardWindow === 'weather' ? 'flex' : 'none';
    }

    if (currentDashboardWindow === 'daily' && !dailyDispatchLoaded) {
        dailyDispatchLoaded = true;
        loadDailyOverviewData();
    } else if (currentDashboardWindow === 'daily') {
        loadDailyScenarioData();
    }
    if (currentDashboardWindow === 'annual' && !annualDataLoaded) {
        annualDataLoaded = true;
        loadOverviewData();
    }
    if (currentDashboardWindow === 'weather' && !weatherConfigLoaded) {
        weatherConfigLoaded = true;
        dbLoadWeatherConfig();
        dbLoadScenarioPower();
        dbLoadMatlabConfig();
    }

    setTimeout(() => {
        window.dispatchEvent(new Event('resize'));
    }, 50);
}

function dailySwitchMode(mode) {
    dailyCurrentMode = mode;

    document.querySelectorAll('#daily-view .mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.dailyMode === mode);
    });

    const showScenario = mode === 'scenario';
    dailyScenarioSelectors.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = showScenario ? '' : 'none';
    });
    dailyWeatherSelectors.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = showScenario ? 'none' : '';
    });

    loadDailyScenarioData();
}

function dailySyncAndLoad(sourceId) {
    const isWeather = sourceId.includes('weather');
    const selectors = isWeather ? dailyWeatherSelectors : dailyScenarioSelectors;
    const source = document.getElementById(sourceId);
    if (!source) return;
    const value = source.value;

    selectors.forEach(id => {
        if (id !== sourceId) {
            const el = document.getElementById(id);
            if (el) el.value = value;
        }
    });

    loadDailyScenarioData();
}

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
    loadNodeVoltageChart();
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
    loadNodeVoltageChart();
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
    if (communitySource === 'daily') {
        const commView = document.getElementById('community-view');
        if (commView) {
            commView.querySelectorAll('.mode-toggle').forEach(el => el.style.display = '');
            document.getElementById('community-scenario-select').style.display = '';
            document.getElementById('community-weather-select').style.display = 'none';
        }
        switchDashboardWindow('daily');
    } else {
        switchDashboardWindow('annual');
    }
    currentView = 'overview';
    communitySource = 'annual';

    document.querySelectorAll('.community-card, .map-community').forEach(card => {
        card.classList.remove('active');
    });
}

function selectCommunity(type) {
    communitySource = 'annual';
    const community = communityMap[type];
    if (!community) return;

    document.querySelectorAll('.community-card, .map-community').forEach(card => {
        card.classList.remove('active');
    });
    const targetCard = document.querySelector(`[data-community="${type}"]`);
    if (targetCard) {
        targetCard.classList.add('active');
    }

    const dailyView = document.getElementById('daily-view');
    if (dailyView) dailyView.style.display = 'none';
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
    loadS4AnnualKPIs();
    loadDailyKPIs();
    loadParkPowerChart();
    loadH2PowerChart();
    loadDRPowerChart();
    loadCostBreakdownChart();
    loadScenariosTable();
    loadCapacityTable();
    loadEnergySummary();
    loadNodeVoltageChart();
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

            document.getElementById('annual-carbon').textContent =
                summary.annual_carbon_emission.toFixed(0);
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
        }
    } catch (error) {
        console.error('加载年度汇总失败:', error);
    }
}

async function loadS4AnnualKPIs() {
    try {
        const res = await fetch('/api/optimization/s4-annual-kpis');
        const result = await res.json();

        if (result.success) {
            const d = result.data;
            document.getElementById('total-generation').textContent =
                (d.annual_renewable_generation_mwh / 1000).toFixed(1);
            document.getElementById('annual-cost').textContent =
                (d.annual_cost / 10000).toFixed(0);
            document.getElementById('renewable-ratio').textContent =
                d.renewable_use_rate.toFixed(1);
        }
    } catch (e) {
        console.error('加载S4年指标失败:', e);
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
    renderPowerOverviewChart('overview-power-chart', data);
}

function renderPowerOverviewChart(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';

    const supplyDiv = document.createElement('div');
    supplyDiv.style.height = '220px';
    supplyDiv.style.marginBottom = '22px';

    const demandDiv = document.createElement('div');
    demandDiv.style.height = '220px';
    demandDiv.style.marginBottom = '22px';

    const socDiv = document.createElement('div');
    socDiv.style.height = '190px';

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
        xaxis: { ...darkLayout.xaxis, title: { text: '', font: { size: 12 } }, dtick: 2 },
        yaxis: { ...darkLayout.yaxis, title: { text: '功率 (MW)', font: { size: 12 }, standoff: 10 } },
        hovermode: 'x unified',
        legend: { ...darkLayout.legend, x: 0, y: -0.26, orientation: 'h', font: { size: 10, color: '#7b8fa8' }, itemwidth: 42 },
        margin: { t: 42, b: 68, l: 62, r: 36 }
    };

    const demandLayout = {
        ...darkLayout,
        title: { text: '用电侧', font: { size: 14, color: '#e2ecf7' } },
        xaxis: { ...darkLayout.xaxis, title: { text: '', font: { size: 12 } }, dtick: 2 },
        yaxis: { ...darkLayout.yaxis, title: { text: '功率 (MW)', font: { size: 12 }, standoff: 10 } },
        hovermode: 'x unified',
        legend: { ...darkLayout.legend, x: 0, y: -0.26, orientation: 'h', font: { size: 10, color: '#7b8fa8' }, itemwidth: 42 },
        margin: { t: 42, b: 68, l: 62, r: 36 }
    };

    const socLayout = {
        ...darkLayout,
        title: { text: '储能SOC', font: { size: 14, color: '#e2ecf7' } },
        xaxis: { ...darkLayout.xaxis, title: { text: '时间 (h)', font: { size: 12 } }, dtick: 2 },
        yaxis: { ...darkLayout.yaxis, title: { text: '电/热储能 (MWh)', font: { size: 12 }, standoff: 10 }, side: 'left' },
        yaxis2: { title: { text: '氢储能 (kg)', font: { size: 12 }, standoff: 14 }, side: 'right', overlaying: 'y', gridcolor: 'rgba(0,0,0,0)', tickfont: { size: 11, color: '#7b8fa8' } },
        hovermode: 'x unified',
        legend: { ...darkLayout.legend, x: 0, y: -0.3, orientation: 'h', font: { size: 10, color: '#7b8fa8' }, itemwidth: 42 },
        margin: { t: 42, b: 76, l: 62, r: 88 }
    };

    Plotly.newPlot(supplyDiv, supplyTraces, supplyLayout, plotlyConfig);
    Plotly.newPlot(demandDiv, demandTraces, demandLayout, plotlyConfig);
    Plotly.newPlot(socDiv, socTraces, socLayout, plotlyConfig);
}

async function loadNodeVoltageChart() {
    const summaryEl = document.getElementById('dashboard-voltage-summary');
    const chartEl = document.getElementById('dashboard-voltage-chart');
    if (!summaryEl || !chartEl) return;

    let url;
    if (currentMode === 'weather') {
        const select = document.getElementById('weather-select');
        const weather = select ? select.value : 'Sunny_LowWind';
        url = `/api/optimization/chart/node-voltage-data?mode=weather&weather=${weather}`;
    } else {
        const select = document.getElementById('scenario-select');
        const scenario = select ? select.value : 'S4';
        url = `/api/optimization/chart/node-voltage-data?scenario=${scenario}`;
    }

    summaryEl.innerHTML = '<div class="dashboard-voltage-error">节点电压数据加载中...</div>';
    chartEl.innerHTML = '';

    try {
        const res = await fetch(url);
        const result = await res.json();

        if (!result.success) {
            dashboardVoltageData = null;
            renderDashboardVoltageUnavailable(result.error || '节点电压数据未导出/不可用');
            return;
        }

        dashboardVoltageData = result;
        dashboardVoltageHourIndex = getDefaultVoltageHourIndex(result);
        updateDashboardVoltageNodeSelect(result.nodes || []);
        renderDashboardVoltageSummary(result);
        renderDashboardVoltageTopology(result);
        renderDashboardSelectedNodeVoltage();
    } catch (e) {
        dashboardVoltageData = null;
        renderDashboardVoltageUnavailable(`节点电压数据加载失败: ${e.message}`);
        console.error('加载节点电压数据失败:', e);
    }
}

function renderDashboardVoltageUnavailable(message) {
    const summaryEl = document.getElementById('dashboard-voltage-summary');
    const chartEl = document.getElementById('dashboard-voltage-chart');
    const topologyEl = document.getElementById('dashboard-voltage-topology');
    if (summaryEl) {
        summaryEl.innerHTML = `<div class="dashboard-voltage-error">${message}</div>`;
    }
    if (chartEl) {
        chartEl.innerHTML = '';
    }
    if (topologyEl) {
        topologyEl.innerHTML = `<div class="dashboard-voltage-error">${message}</div>`;
    }
    stopVoltageDeviationPlayback('dashboard');
}

function renderDashboardVoltageSummary(data) {
    const container = document.getElementById('dashboard-voltage-summary');
    if (!container || !data.summary) return;

    const minText = data.summary.min == null ? '--' : data.summary.min.toFixed(4);
    const maxText = data.summary.max == null ? '--' : data.summary.max.toFixed(4);
    container.innerHTML = `
        <div class="dashboard-voltage-summary-card">
            <span>最低电压</span>
            <strong>${minText}</strong>
            <small>p.u.</small>
        </div>
        <div class="dashboard-voltage-summary-card">
            <span>最高电压</span>
            <strong>${maxText}</strong>
            <small>p.u.</small>
        </div>
        <div class="dashboard-voltage-summary-card">
            <span>低压越限</span>
            <strong>${data.summary.low_violations}</strong>
            <small>次</small>
        </div>
        <div class="dashboard-voltage-summary-card">
            <span>高压越限</span>
            <strong>${data.summary.high_violations}</strong>
            <small>次</small>
        </div>
    `;
}

function updateDashboardVoltageNodeSelect(nodes) {
    const select = document.getElementById('dashboard-voltage-node-select');
    if (!select) return;

    const previous = select.value;
    select.innerHTML = '';
    nodes.forEach(node => {
        const option = document.createElement('option');
        option.value = String(node);
        option.textContent = `Node ${node}`;
        select.appendChild(option);
    });

    if (nodes.map(String).includes(previous)) {
        select.value = previous;
    } else if (nodes.length > 0) {
        select.value = String(nodes[0]);
    }
    selectedDashboardNodeId = select.value || String(nodes[0] || '1');
}

function renderDashboardSelectedNodeVoltage() {
    if (!dashboardVoltageData) return;

    const select = document.getElementById('dashboard-voltage-node-select');
    const nodes = dashboardVoltageData.nodes || [];
    const selectedNode = select ? parseInt(select.value || nodes[0] || 1, 10) : (nodes[0] || 1);
    const nodeIndex = nodes.indexOf(selectedNode);
    const voltage = nodeIndex >= 0 ? (dashboardVoltageData.voltage || [])[nodeIndex] || [] : [];

    selectedDashboardNodeId = String(selectedNode);
    updateVoltageTopologySelection('dashboard', selectedDashboardNodeId);
    renderDashboardVoltageTimeSeries(dashboardVoltageData.hours || [], voltage, selectedNode);
}

function renderDashboardVoltageTimeSeries(hours, voltages, selectedNode) {
    const container = document.getElementById('dashboard-voltage-chart');
    if (!container) return;

    const trace = {
        x: hours,
        y: voltages,
        type: 'scatter',
        mode: 'lines+markers',
        name: `Node ${selectedNode}`,
        line: { color: '#00d4ff', width: 2.5 },
        marker: { size: 5, color: '#00e676', line: { color: '#06203a', width: 1 } },
        hovertemplate: `Node ${selectedNode}<br>%{x}h: %{y:.4f} p.u.<extra></extra>`
    };

    const limitLine = (y, color, dash) => ({
        type: 'line',
        xref: 'x',
        yref: 'y',
        x0: hours[0] || 1,
        x1: hours[hours.length - 1] || 24,
        y0: y,
        y1: y,
        line: { color, width: 1.4, dash }
    });

    const layout = {
        ...darkLayout,
        title: { text: `Node ${selectedNode} 电压时序`, font: { size: 13, color: '#e2ecf7' } },
        xaxis: { ...darkLayout.xaxis, title: { text: '时间 (h)', font: { size: 11 } }, dtick: 2 },
        yaxis: { ...darkLayout.yaxis, title: { text: '电压 (p.u.)', font: { size: 11 } }, range: [0.93, 1.07] },
        hovermode: 'x unified',
        showlegend: false,
        shapes: [
            limitLine(0.95, '#ff5252', 'dash'),
            limitLine(1.05, '#ff5252', 'dash'),
            limitLine(1.0, '#7b8fa8', 'dot')
        ],
        annotations: [
            { x: hours[hours.length - 1] || 24, y: 0.95, text: '下限 0.95', showarrow: false, xanchor: 'left', font: { size: 10, color: '#ff5252' } },
            { x: hours[hours.length - 1] || 24, y: 1.05, text: '上限 1.05', showarrow: false, xanchor: 'left', font: { size: 10, color: '#ff5252' } }
        ],
        margin: { t: 40, b: 50, l: 55, r: 80 }
    };

    Plotly.newPlot(container, [trace], layout, plotlyConfig);
}

const IEEE33_TOPOLOGY_NODES = [
    { id: 1, x: 0, y: 0 },
    { id: 2, x: 1, y: 0 },
    { id: 3, x: 2, y: 0 },
    { id: 4, x: 3, y: 0 },
    { id: 5, x: 4, y: 0 },
    { id: 6, x: 5, y: 0 },
    { id: 7, x: 6, y: 0 },
    { id: 8, x: 7, y: 0 },
    { id: 9, x: 8, y: 0 },
    { id: 10, x: 9, y: 0 },
    { id: 11, x: 10, y: 0 },
    { id: 12, x: 11, y: 0 },
    { id: 13, x: 12, y: 0 },
    { id: 14, x: 13, y: 0 },
    { id: 15, x: 14, y: 0 },
    { id: 16, x: 15, y: 0 },
    { id: 17, x: 16, y: 0 },
    { id: 18, x: 17, y: 0 },
    { id: 19, x: 1.9, y: -1.2 },
    { id: 20, x: 3.6, y: -1.2 },
    { id: 21, x: 5.3, y: -1.2 },
    { id: 22, x: 7.0, y: -1.2 },
    { id: 23, x: 2.9, y: 2.4 },
    { id: 24, x: 4.5, y: 2.4 },
    { id: 25, x: 6.1, y: 2.4 },
    { id: 26, x: 5.6, y: 1.35 },
    { id: 27, x: 7.0, y: 1.35 },
    { id: 28, x: 8.4, y: 1.35 },
    { id: 29, x: 9.8, y: 1.35 },
    { id: 30, x: 11.2, y: 1.35 },
    { id: 31, x: 12.6, y: 1.35 },
    { id: 32, x: 14.0, y: 1.35 },
    { id: 33, x: 15.4, y: 1.35 }
];

const IEEE33_TOPOLOGY_EDGES = [
    [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 8], [8, 9],
    [9, 10], [10, 11], [11, 12], [12, 13], [13, 14], [14, 15], [15, 16],
    [16, 17], [17, 18], [2, 19], [19, 20], [20, 21], [21, 22],
    [3, 23], [23, 24], [24, 25], [6, 26], [26, 27], [27, 28], [28, 29],
    [29, 30], [30, 31], [31, 32], [32, 33]
];

const IEEE33_TOPOLOGY_BOUNDS = IEEE33_TOPOLOGY_NODES.reduce((acc, node) => ({
    minX: Math.min(acc.minX, node.x),
    maxX: Math.max(acc.maxX, node.x),
    minY: Math.min(acc.minY, node.y),
    maxY: Math.max(acc.maxY, node.y)
}), { minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity });

function ieee33TopologyPoint(node) {
    const width = 1000;
    const height = 330;
    const padX = 42;
    const padY = 42;
    return {
        x: padX + ((node.x - IEEE33_TOPOLOGY_BOUNDS.minX) / (IEEE33_TOPOLOGY_BOUNDS.maxX - IEEE33_TOPOLOGY_BOUNDS.minX)) * (width - padX * 2),
        y: padY + ((IEEE33_TOPOLOGY_BOUNDS.maxY - node.y) / (IEEE33_TOPOLOGY_BOUNDS.maxY - IEEE33_TOPOLOGY_BOUNDS.minY)) * (height - padY * 2)
    };
}

function getVoltageMatrixByNode(data) {
    const voltageByNode = new Map();
    (data?.nodes || []).forEach((node, index) => {
        voltageByNode.set(String(node), (data.voltage || [])[index] || []);
    });
    return voltageByNode;
}

function getVoltageDeviationScale(data) {
    let maxAbs = 0;
    (data?.voltage || []).forEach(row => {
        (row || []).forEach(value => {
            const num = Number(value);
            if (Number.isFinite(num)) {
                maxAbs = Math.max(maxAbs, Math.abs(num - 1.0));
            }
        });
    });
    return Math.max(0.01, Math.min(0.08, maxAbs || 0.05));
}

function getDefaultVoltageHourIndex(data) {
    const hours = data?.hours || [];
    let bestIndex = 0;
    let bestAbs = -1;
    hours.forEach((_, hourIndex) => {
        (data?.voltage || []).forEach(row => {
            const num = Number((row || [])[hourIndex]);
            if (Number.isFinite(num)) {
                const abs = Math.abs(num - 1.0);
                if (abs > bestAbs) {
                    bestAbs = abs;
                    bestIndex = hourIndex;
                }
            }
        });
    });
    return bestIndex;
}

function getVoltageDeviationColor(deviation, scale) {
    if (!Number.isFinite(deviation)) return '#b7c0ca';
    const t = Math.max(-1, Math.min(1, deviation / scale));
    if (t >= 0) {
        const a = t;
        const r = Math.round(247 + (180 - 247) * a);
        const g = Math.round(247 + (15 - 247) * a);
        const b = Math.round(242 + (46 - 242) * a);
        return `rgb(${r}, ${g}, ${b})`;
    }
    const a = Math.abs(t);
    const r = Math.round(247 + (8 - 247) * a);
    const g = Math.round(247 + (61 - 247) * a);
    const b = Math.round(242 + (186 - 242) * a);
    return `rgb(${r}, ${g}, ${b})`;
}

function clipPolygonByHalfPlane(polygon, a, b, c) {
    const clipped = [];
    if (!polygon.length) return clipped;

    for (let i = 0; i < polygon.length; i += 1) {
        const current = polygon[i];
        const previous = polygon[(i + polygon.length - 1) % polygon.length];
        const currentInside = a * current.x + b * current.y <= c + 1e-6;
        const previousInside = a * previous.x + b * previous.y <= c + 1e-6;

        if (currentInside !== previousInside) {
            const dx = current.x - previous.x;
            const dy = current.y - previous.y;
            const denom = a * dx + b * dy;
            if (Math.abs(denom) > 1e-9) {
                const t = (c - a * previous.x - b * previous.y) / denom;
                clipped.push({
                    x: previous.x + dx * t,
                    y: previous.y + dy * t
                });
            }
        }
        if (currentInside) {
            clipped.push(current);
        }
    }

    return clipped;
}

function getVoltageRegionCells(pointsByNode) {
    const padding = 0;
    const allPoints = IEEE33_TOPOLOGY_NODES
        .map(node => ({ id: node.id, ...pointsByNode.get(node.id) }))
        .filter(point => Number.isFinite(point.x) && Number.isFinite(point.y));
    const bounds = [
        { x: padding, y: padding },
        { x: 1000 - padding, y: padding },
        { x: 1000 - padding, y: 330 - padding },
        { x: padding, y: 330 - padding }
    ];

    return allPoints.map(point => {
        let polygon = bounds.map(p => ({ ...p }));
        allPoints.forEach(other => {
            if (other.id === point.id || polygon.length === 0) return;
            const a = 2 * (other.x - point.x);
            const b = 2 * (other.y - point.y);
            const c = other.x * other.x + other.y * other.y - point.x * point.x - point.y * point.y;
            polygon = clipPolygonByHalfPlane(polygon, a, b, c);
        });
        return { id: point.id, polygon };
    });
}

function polygonToPath(polygon) {
    if (!polygon.length) return '';
    const [first, ...rest] = polygon;
    return [
        `M ${first.x.toFixed(2)} ${first.y.toFixed(2)}`,
        ...rest.map(point => `L ${point.x.toFixed(2)} ${point.y.toFixed(2)}`),
        'Z'
    ].join(' ');
}

function getVoltageScopeState(scope) {
    if (scope === 'dashboard') {
        return {
            hourIndex: dashboardVoltageHourIndex,
            selectedNodeId: selectedDashboardNodeId,
            setHourIndex: value => { dashboardVoltageHourIndex = value; },
            setSelectedNodeId: value => { selectedDashboardNodeId = value; },
            data: dashboardVoltageData,
            render: () => renderDashboardVoltageTopology(dashboardVoltageData),
            onNodeSelect: nodeId => {
                selectedDashboardNodeId = nodeId;
                const select = document.getElementById('dashboard-voltage-node-select');
                if (select) select.value = nodeId;
                renderDashboardSelectedNodeVoltage();
            }
        };
    }
    return {
        hourIndex: dailyVoltageHourIndex,
        selectedNodeId: selectedDailyNodeId,
        setHourIndex: value => { dailyVoltageHourIndex = value; },
        setSelectedNodeId: value => { selectedDailyNodeId = value; },
        data: currentDailyDispatchData?.node_voltage,
        render: () => renderDailyVoltageTopology(currentDailyDispatchData?.node_voltage),
        onNodeSelect: nodeId => {
            selectedDailyNodeId = nodeId;
            const select = document.getElementById('daily-voltage-node-select');
            if (select) select.value = nodeId;
            renderDailySelectedNodeVoltage();
        }
    };
}

function stopVoltageDeviationPlayback(scope) {
    if (scope === 'dashboard' && dashboardVoltagePlaybackTimer) {
        clearInterval(dashboardVoltagePlaybackTimer);
        dashboardVoltagePlaybackTimer = null;
    }
    if (scope === 'daily' && dailyVoltagePlaybackTimer) {
        clearInterval(dailyVoltagePlaybackTimer);
        dailyVoltagePlaybackTimer = null;
    }
}

function toggleVoltageDeviationPlayback(scope) {
    const state = getVoltageScopeState(scope);
    const hours = state.data?.hours || [];
    if (hours.length <= 1) return;

    const isRunning = scope === 'dashboard' ? dashboardVoltagePlaybackTimer : dailyVoltagePlaybackTimer;
    if (isRunning) {
        stopVoltageDeviationPlayback(scope);
        state.render();
        return;
    }

    const timer = setInterval(() => {
        const next = (getVoltageScopeState(scope).hourIndex + 1) % hours.length;
        state.setHourIndex(next);
        state.render();
    }, 700);

    if (scope === 'dashboard') {
        dashboardVoltagePlaybackTimer = timer;
    } else {
        dailyVoltagePlaybackTimer = timer;
    }
    state.render();
}

function updateVoltageTopologySelection(scope, selectedNodeId) {
    const containerId = scope === 'dashboard' ? 'dashboard-voltage-topology' : 'daily-voltage-topology';
    const statusId = scope === 'dashboard' ? 'dashboard-voltage-topology-status' : 'daily-voltage-topology-status';
    const container = document.getElementById(containerId);
    if (!container) return;
    container.querySelectorAll('.daily-topology-node').forEach(nodeEl => {
        nodeEl.classList.toggle('selected', nodeEl.dataset.node === String(selectedNodeId));
    });
    const status = document.getElementById(statusId);
    if (status && selectedNodeId) {
        status.textContent = `当前选中 Node ${selectedNodeId}`;
        status.classList.remove('warning');
    }
}

function renderVoltageDeviationTopology(scope, data, containerId, statusId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const hours = data?.hours || [];
    const voltageByNode = getVoltageMatrixByNode(data);
    if (!data || (!data.available && data.success === false) || !hours.length || !voltageByNode.size) {
        container.innerHTML = '<div class="dashboard-voltage-error">拓扑数据等待节点电压结果</div>';
        const status = document.getElementById(statusId);
        if (status) {
            status.textContent = '暂无可播放的电压偏差数据';
            status.classList.add('warning');
        }
        stopVoltageDeviationPlayback(scope);
        return;
    }

    const state = getVoltageScopeState(scope);
    if (!Number.isInteger(state.hourIndex) || state.hourIndex < 0 || state.hourIndex >= hours.length) {
        state.setHourIndex(getDefaultVoltageHourIndex(data));
    }
    const hourIndex = getVoltageScopeState(scope).hourIndex;
    const hour = hours[hourIndex] || (hourIndex + 1);
    const selected = String(getVoltageScopeState(scope).selectedNodeId || '');
    const scale = getVoltageDeviationScale(data);
    const isPlaying = scope === 'dashboard' ? !!dashboardVoltagePlaybackTimer : !!dailyVoltagePlaybackTimer;
    const points = new Map(IEEE33_TOPOLOGY_NODES.map(node => [node.id, ieee33TopologyPoint(node)]));
    const svgNS = 'http://www.w3.org/2000/svg';

    container.innerHTML = '';

    const toolbar = document.createElement('div');
    toolbar.className = 'voltage-deviation-toolbar';

    const playBtn = document.createElement('button');
    playBtn.type = 'button';
    playBtn.className = 'voltage-play-btn';
    playBtn.title = isPlaying ? '暂停播放' : '播放一天过程';
    playBtn.setAttribute('aria-label', playBtn.title);
    playBtn.textContent = isPlaying ? 'Ⅱ' : '▶';
    playBtn.addEventListener('click', () => toggleVoltageDeviationPlayback(scope));
    toolbar.appendChild(playBtn);

    const range = document.createElement('input');
    range.type = 'range';
    range.className = 'voltage-hour-range';
    range.min = '0';
    range.max = String(Math.max(0, hours.length - 1));
    range.step = '1';
    range.value = String(hourIndex);
    range.addEventListener('input', event => {
        state.setHourIndex(Number(event.target.value));
        state.render();
    });
    toolbar.appendChild(range);

    const hourLabel = document.createElement('div');
    hourLabel.className = 'voltage-hour-label';
    hourLabel.textContent = `${hour}:00`;
    toolbar.appendChild(hourLabel);
    container.appendChild(toolbar);

    const stage = document.createElement('div');
    stage.className = 'voltage-deviation-stage';
    const svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('class', 'voltage-topology-svg');
    svg.setAttribute('viewBox', '0 0 1000 330');
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', 'IEEE33节点电压偏差拓扑');

    const bg = document.createElementNS(svgNS, 'rect');
    bg.setAttribute('x', '0');
    bg.setAttribute('y', '0');
    bg.setAttribute('width', '1000');
    bg.setAttribute('height', '330');
    bg.setAttribute('fill', '#f7f7f2');
    svg.appendChild(bg);

    getVoltageRegionCells(points).forEach(cell => {
        const voltage = voltageByNode.get(String(cell.id)) || [];
        const value = Number(voltage[hourIndex]);
        const region = document.createElementNS(svgNS, 'path');
        region.setAttribute('d', polygonToPath(cell.polygon));
        region.setAttribute('class', 'voltage-region-cell');
        region.setAttribute('fill', Number.isFinite(value) ? getVoltageDeviationColor(value - 1.0, scale) : '#d6dbe0');
        svg.appendChild(region);
    });

    IEEE33_TOPOLOGY_EDGES.forEach(([from, to]) => {
        const a = points.get(from);
        const b = points.get(to);
        if (!a || !b) return;
        const line = document.createElementNS(svgNS, 'line');
        line.setAttribute('x1', a.x);
        line.setAttribute('y1', a.y);
        line.setAttribute('x2', b.x);
        line.setAttribute('y2', b.y);
        line.setAttribute('class', 'daily-topology-edge');
        svg.appendChild(line);
    });

    IEEE33_TOPOLOGY_NODES.forEach(node => {
        const point = points.get(node.id);
        const key = String(node.id);
        const voltage = voltageByNode.get(key) || [];
        const value = Number(voltage[hourIndex]);
        const hasData = Number.isFinite(value);
        const isSelected = selected === key;
        const hasViolation = (voltage || []).some(v => Number(v) < 0.95 || Number(v) > 1.05);

        const group = document.createElementNS(svgNS, 'g');
        group.setAttribute('class', [
            'daily-topology-node',
            hasData ? 'available' : 'unavailable',
            isSelected ? 'selected' : '',
            hasViolation ? 'violation' : ''
        ].filter(Boolean).join(' '));
        group.setAttribute('data-node', key);
        group.setAttribute('tabindex', hasData ? '0' : '-1');
        group.setAttribute('role', hasData ? 'button' : 'img');
        group.setAttribute('aria-label', hasData ? `Node ${key} 电压偏差` : `Node ${key} 暂无电压数据`);

        const clickNode = () => {
            if (!hasData) return;
            getVoltageScopeState(scope).onNodeSelect(key);
        };
        group.addEventListener('click', clickNode);
        group.addEventListener('keydown', event => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                clickNode();
            }
        });

        const circle = document.createElementNS(svgNS, 'circle');
        circle.setAttribute('cx', point.x);
        circle.setAttribute('cy', point.y);
        circle.setAttribute('r', '15');
        circle.setAttribute('fill', hasData ? getVoltageDeviationColor(value - 1.0, scale) : '#b7c0ca');
        group.appendChild(circle);

        const label = document.createElementNS(svgNS, 'text');
        label.setAttribute('x', point.x);
        label.setAttribute('y', point.y + 4);
        label.textContent = key;
        group.appendChild(label);

        svg.appendChild(group);
    });

    stage.appendChild(svg);
    container.appendChild(stage);

    const colorbar = document.createElement('div');
    colorbar.className = 'voltage-colorbar';
    const gradient = document.createElement('div');
    gradient.className = 'voltage-colorbar-gradient';
    const label = document.createElement('div');
    label.className = 'voltage-colorbar-label';
    label.textContent = `${(-scale).toFixed(3)} ~ +${scale.toFixed(3)} p.u.`;
    colorbar.appendChild(gradient);
    colorbar.appendChild(label);
    container.appendChild(colorbar);

    const status = document.getElementById(statusId);
    if (status) {
        status.textContent = `当前小时 ${hour}:00，电压偏差 = V - 1.0 p.u.`;
        status.classList.remove('warning');
    }
}

function renderDashboardVoltageTopology(data) {
    renderVoltageDeviationTopology('dashboard', data, 'dashboard-voltage-topology', 'dashboard-voltage-topology-status');
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

        const res = await fetch(url);
        const result = await res.json();

        if (result.success) {
            const data = result.data;

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

async function loadWeatherOptions() {
    try {
        const res = await fetch('/api/weather/config');
        const result = await res.json();
        if (!result.success) return;

        const selectIds = ['weather-select', 'h2-weather-select', 'dr-weather-select', 'community-weather-select'];
        selectIds.forEach(id => {
            const sel = document.getElementById(id);
            if (!sel) return;
            const prev = sel.value;
            sel.innerHTML = '';
            result.data.forEach((item, i) => {
                const opt = document.createElement('option');
                opt.value = item.scenario;
                opt.textContent = `${item.name} (${item.days}天)`;
                if (item.scenario === prev || (i === 0 && !prev)) opt.selected = true;
                sel.appendChild(opt);
            });
        });
    } catch (e) {
        console.error('加载天气选项失败:', e);
    }
}

let dailyCsvCurves = null;

function parseNormalizedCSVValue(value, rowNumber, columnName) {
    const normalized = Number(String(value ?? '').trim());
    if (!Number.isFinite(normalized) || normalized < 0 || normalized > 1) {
        throw new Error(`第 ${rowNumber} 行 ${columnName} 不是 0-1 归一化 p.u. 数值`);
    }
    return normalized;
}

function curveTo24Points(curve) {
    if (curve.length === 24) return curve.slice();
    const hourly = [];
    for (let i = 0; i < 24; i++) {
        const start = i * 4;
        hourly.push((curve[start] + curve[start + 1] + curve[start + 2] + curve[start + 3]) / 4);
    }
    return hourly;
}

function handleScenarioCSVUpload(file) {
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function (e) {
        try {
            const text = e.target.result;
            const lines = text.split(/\r?\n/).filter(line => line.trim().length > 0);
            if (lines.length < 2) {
                setCSVStatus('CSV 文件为空或格式不正确', true);
                return;
            }

            const headers = lines[0].split(',').map(h => h.trim());
            const pv18Idx = headers.indexOf('node_18_PV');
            const pv33Idx = headers.indexOf('node_33_PV');
            const w22Idx = headers.indexOf('node_22_wind');
            const w25Idx = headers.indexOf('node_25_wind');

            if (pv18Idx === -1 || pv33Idx === -1 || w22Idx === -1 || w25Idx === -1) {
                setCSVStatus('CSV 缺少必要列: node_18_PV, node_33_PV, node_22_wind, node_25_wind', true);
                return;
            }

            const pv18 = [];
            const pv33 = [];
            const w22 = [];
            const w25 = [];

            for (let i = 1; i < lines.length; i++) {
                const cols = lines[i].split(',');
                if (cols.length <= Math.max(pv18Idx, pv33Idx, w22Idx, w25Idx)) continue;
                const rowNumber = i + 1;
                pv18.push(parseNormalizedCSVValue(cols[pv18Idx], rowNumber, 'node_18_PV'));
                pv33.push(parseNormalizedCSVValue(cols[pv33Idx], rowNumber, 'node_33_PV'));
                w22.push(parseNormalizedCSVValue(cols[w22Idx], rowNumber, 'node_22_wind'));
                w25.push(parseNormalizedCSVValue(cols[w25Idx], rowNumber, 'node_25_wind'));
            }

            if (pv18.length === 0) {
                setCSVStatus('CSV 中无有效数据行', true);
                return;
            }

            const pvCurve = pv18.map((v, i) => (v + (pv33[i] || 0)) / 2);
            const windCurve = w22.map((v, i) => (v + (w25[i] || 0)) / 2);

            if (pvCurve.length !== 96 && pvCurve.length !== 24) {
                setCSVStatus(`数据点数为 ${pvCurve.length}，需要 96 点（15分钟间隔）或 24 点`, true);
                return;
            }

            dailyCsvCurves = { pv_curve: pvCurve, wind_curve: windCurve };
            renderNormalizedCurves(curveTo24Points(pvCurve), curveTo24Points(windCurve));
            setCSVStatus(`已导入 ${file.name}（${pvCurve.length} 点归一化 p.u. 数据），点击"实时优化"匹配场景`, false);
        } catch (err) {
            setCSVStatus('CSV 解析失败: ' + err.message + '；CSV 已要求为归一化 p.u. 数据', true);
        }
    };
    reader.onerror = function () {
        setCSVStatus('文件读取失败', true);
    };
    reader.readAsText(file);
}

function setCSVStatus(msg, isError) {
    const el = document.getElementById('daily-csv-status');
    if (!el) return;
    el.textContent = msg;
    el.style.color = isError ? '#ff5252' : '#2ecc71';
}

async function loadDailyOverviewData() {
    setText('daily-overview-status', '实时优化中...');
    loadDailyCapacityTable();
    await runDailyDispatch();
}

async function loadDailyScenarioData() {
    if (currentDailyDispatchData) {
        renderDailyOverview(currentDailyDispatchData);
        return;
    }
    await loadDailyOverviewData();
}

async function loadCurveForMainView(ddreId) {
    try {
        const res = await fetch(`/api/daily-dispatch/curve?ddre=${ddreId}`);
        const result = await res.json();
        if (!result.success) throw new Error(result.error || '加载曲线失败');
        const d = result.data;
        currentDailyCurves = { pv_24: d.pv_24, wind_24: d.wind_24, matchedDdre: d.ddre_id };
        renderNormalizedCurves(d.pv_24, d.wind_24);
    } catch (e) {
        console.error('加载归一化曲线失败:', e);
    }
}

function renderNormalizedCurves(pv24, wind24, matchedPv24 = null, matchedWind24 = null) {
    const hours = Array.from({ length: 24 }, (_, i) => i + 1);
    const pvEl = document.getElementById('daily-pv-curve-chart');
    if (pvEl) {
        const traces = [{
            x: hours, y: pv24, type: 'scatter', mode: 'lines+markers',
            line: { color: '#f1c40f', shape: 'spline' },
            marker: { color: '#f1c40f', size: 5 },
            fill: 'tozeroy', fillcolor: 'rgba(241,196,15,0.12)',
            name: '',
            hovertemplate: '光伏归一化出力: %{y:.2f} p.u.<extra></extra>'
        }];
        if (matchedPv24) {
            traces.push({
                x: hours, y: matchedPv24, type: 'scatter', mode: 'lines',
                line: { color: '#ffe082', width: 2, dash: 'dash' },
                name: '',
                hovertemplate: '匹配参考: %{y:.2f} p.u.<extra></extra>'
            });
        }
        Plotly.newPlot(pvEl, traces, {
            ...darkLayout,
            xaxis: { ...darkLayout.xaxis, dtick: 4, title: { text: 'h', font: { size: 9 } } },
            yaxis: { ...darkLayout.yaxis, range: [0, 1], title: { text: 'p.u.', font: { size: 9 } } },
            margin: { t: 10, b: 28, l: 36, r: 8 },
            legend: { ...darkLayout.legend, orientation: 'h', y: -0.35, font: { size: 9 } },
            showlegend: false
        }, plotlyConfig);
    }
    const windEl = document.getElementById('daily-wind-curve-chart');
    if (windEl) {
        const traces = [{
            x: hours, y: wind24, type: 'scatter', mode: 'lines+markers',
            line: { color: '#3498db', shape: 'spline' },
            marker: { color: '#3498db', size: 5 },
            fill: 'tozeroy', fillcolor: 'rgba(52,152,219,0.12)',
            name: '',
            hovertemplate: '风电归一化出力: %{y:.2f} p.u.<extra></extra>'
        }];
        if (matchedWind24) {
            traces.push({
                x: hours, y: matchedWind24, type: 'scatter', mode: 'lines',
                line: { color: '#8ecbff', width: 2, dash: 'dash' },
                name: '',
                hovertemplate: '匹配参考: %{y:.2f} p.u.<extra></extra>'
            });
        }
        Plotly.newPlot(windEl, traces, {
            ...darkLayout,
            xaxis: { ...darkLayout.xaxis, dtick: 4, title: { text: 'h', font: { size: 9 } } },
            yaxis: { ...darkLayout.yaxis, range: [0, 1], title: { text: 'p.u.', font: { size: 9 } } },
            margin: { t: 10, b: 28, l: 36, r: 8 },
            legend: { ...darkLayout.legend, orientation: 'h', y: -0.35, font: { size: 9 } },
            showlegend: false
        }, plotlyConfig);
    }
}



async function runRealtimeFromCurves() {
    const { pv_24, wind_24 } = currentDailyCurves;
    if (!pv_24 || !wind_24 || pv_24.length !== 24 || wind_24.length !== 24) {
        setText('daily-overview-status', '曲线数据不完整');
        return;
    }
    const status = document.getElementById('daily-overview-status');
    if (status) status.textContent = '实时优化中...';

    try {
        const res = await fetch('/api/daily-dispatch/optimize-milp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pv_curve: pv_24, wind_curve: wind_24 })
        });
        const result = await res.json();
        if (!result.success) throw new Error(result.error || '实时优化失败');

        currentDailyDispatchData = result.data;
        const curves = result.data.weather_curves || {};
        if (curves.pv_24 && curves.wind_24) {
            renderNormalizedCurves(curves.pv_24, curves.wind_24, curves.matched_pv_24, curves.matched_wind_24);
        }
        setText('daily-overview-status', '实时优化完成');
        renderDailyOverview(result.data);
    } catch (e) {
        setText('daily-overview-status', e.message || '实时优化失败');
        console.error('实时优化失败:', e);
    }
}

function renderDailyOverview(data) {
    if (!data) return;

    const k = data.kpis || {};
    setText('daily-overview-kpi-cost', formatNumber(k.cost, 0));
    setText('daily-overview-kpi-grid', formatNumber(k.grid_energy, 1));
    setText('daily-overview-kpi-carbon', formatNumber(k.carbon_emission, 1));
    setText('daily-overview-kpi-renewable', formatNumber(k.renewable_rate, 1));

    const metrics = data.metrics || {};
    setText('daily-total-renewable', formatNumber(metrics.renewable_use, 1));
    setText('daily-total-cost', formatNumber((metrics.cost || 0) / 10000, 1));
    setText('daily-total-carbon', formatNumber(metrics.carbon_emission, 1));
    setText('daily-total-renewable-rate', formatNumber(metrics.renewable_rate, 1));
    setText('daily-summary-grid', formatNumber(metrics.grid_energy, 1));
    setText('daily-summary-gas', formatNumber(metrics.gas_energy, 1));
    setText('daily-summary-quota', formatNumber(metrics.carbon_quota, 1));
    setText('daily-summary-carbon-sell', formatNumber(metrics.carbon_sell, 1));
    setText('daily-summary-curtailment', formatNumber(metrics.renewable_curtailment, 1));
    setText('daily-summary-h2-shortage', formatNumber(metrics.h2_shortage, 1));

    renderPowerOverviewChart('daily-overview-power-chart', data.chart);
    renderDailyH2OverviewChart(data.h2);
    renderDailyDROverviewChart(data.dr);
    renderDailyNodeVoltage(data.node_voltage);
    renderDailyCostBreakdownChart(data.cost_breakdown);
    renderDailyEnergyMixChart(data.energy_summary);
    renderDailyScenarioTable(data.scenario_table || [], data.scenario_id);
}

function renderDailyH2OverviewChart(h2) {
    const el = document.getElementById('daily-overview-h2-chart');
    const socEl = document.getElementById('daily-overview-h2-soc-chart');
    if (!el || !h2) return;

    el.innerHTML = '';
    const h2Div = document.createElement('div');
    h2Div.style.height = '260px';
    h2Div.style.marginBottom = '5px';
    el.appendChild(h2Div);

    const hours = h2.hours;
    const h2Traces = [
        { x: hours, y: h2.production, type: 'scatter', mode: 'lines', stackgroup: 'supply', name: '电解制氢', line: { color: '#3498db' }, hovertemplate: '电解制氢: %{y:.3f} kg<extra></extra>' },
        { x: hours, y: h2.storage_discharge, type: 'scatter', mode: 'lines', stackgroup: 'supply', name: '储氢放氢', line: { color: '#2ecc71' }, hovertemplate: '储氢放氢: %{y:.3f} kg<extra></extra>' },
        { x: hours, y: (h2.fuel_cell || h2.hours.map(() => 0)), type: 'scatter', mode: 'lines', stackgroup: 'demand', name: '燃料电池', line: { color: '#8e44ad' }, hovertemplate: '燃料电池: %{y:.3f} kg<extra></extra>' },
        { x: hours, y: (h2.storage_charge || h2.hours.map(() => 0)), type: 'scatter', mode: 'lines', stackgroup: 'demand', name: '储氢充氢', line: { color: '#f39c12' }, hovertemplate: '储氢充氢: %{y:.3f} kg<extra></extra>' },
        { x: hours, y: h2.load, type: 'scatter', mode: 'lines', stackgroup: 'demand', name: '氢负荷', line: { color: '#e74c3c' }, hovertemplate: '氢负荷: %{y:.3f} kg<extra></extra>' },
    ];
    const hasShortage = h2.shortage && h2.shortage.some(v => Math.abs(v) > 1e-6);
    if (hasShortage) {
        h2Traces.push({ x: hours, y: h2.shortage, type: 'bar', name: '短缺', marker: { color: '#e74c3c', opacity: 0.6 }, yaxis: 'y2', hovertemplate: '短缺: %{y:.3f} kg<extra></extra>' });
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
    Plotly.newPlot(h2Div, h2Traces, h2Layout, plotlyConfig);

    if (socEl && h2.soc_h2) {
        socEl.innerHTML = '';
        const socDiv = document.createElement('div');
        socDiv.style.height = '160px';
        socEl.appendChild(socDiv);
        const socTraces = [
            { x: hours, y: h2.soc_h2, type: 'scatter', mode: 'lines+markers', name: '氢储能SOC', line: { color: '#2ecc71', width: 2 }, marker: { size: 4 }, hovertemplate: 'SOC: %{y:.2f} kg<extra></extra>' }
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
        Plotly.newPlot(socDiv, socTraces, socLayout, plotlyConfig);
    }
}

function renderDailyDROverviewChart(dr) {
    const loadEl = document.getElementById('daily-overview-dr-load-chart');
    const el = document.getElementById('daily-overview-dr-chart');
    const summary = document.getElementById('daily-overview-dr-summary');
    if (!el || !dr) return;

    const sum = arr => (arr || []).reduce((a, b) => a + (Number(b) || 0), 0);
    const sumMWh = arr => sum(arr);
    if (summary) {
        summary.innerHTML = `
            <div class="dr-metric-item"><div class="dr-metric-value">${formatNumber(sumMWh(dr.shift), 2)}</div><div class="dr-metric-label">负荷转移 (MWh)</div></div>
            <div class="dr-metric-item"><div class="dr-metric-value">${formatNumber(sumMWh(dr.cut_e), 2)}</div><div class="dr-metric-label">电力削减 (MWh)</div></div>
            <div class="dr-metric-item"><div class="dr-metric-value">${formatNumber(sumMWh(dr.hdr_cut), 2)}</div><div class="dr-metric-label">热力削减 (MWh)</div></div>
            <div class="dr-metric-item"><div class="dr-metric-value">${formatNumber(sumMWh(dr.h2dr_cut), 2)}</div><div class="dr-metric-label">氢削减 (kg)</div></div>
        `;
    }

    const hours = dr.hours;
    const loadOriginal = dr.load_original || dr.hours.map(() => 0);

    if (loadEl) {
        loadEl.innerHTML = '';
        const loadDiv = document.createElement('div');
        loadDiv.style.height = '180px';
        loadEl.appendChild(loadDiv);
        const loadTraces = [
            { x: hours, y: loadOriginal, type: 'scatter', mode: 'lines', name: '原始负荷', line: { color: '#e74c3c', width: 2, dash: 'dash' }, hovertemplate: '原始: %{y:.3f} MW<extra></extra>' },
            { x: hours, y: dr.load_after_dr, type: 'scatter', mode: 'lines', name: 'DR调整后', line: { color: '#3498db', width: 2.5 }, hovertemplate: '调整后: %{y:.3f} MW<extra></extra>' }
        ];
        const loadLayout = {
            ...darkLayout,
            title: { text: '负荷曲线对比', font: { size: 12, color: '#e2ecf7' } },
            xaxis: { ...darkLayout.xaxis, dtick: 2, showticklabels: false },
            yaxis: { ...darkLayout.yaxis, title: { text: '功率 (MW)', font: { size: 10 } } },
            hovermode: 'x unified',
            legend: { ...darkLayout.legend, x: 0, y: -0.12, orientation: 'h', font: { size: 9, color: '#7b8fa8' } },
            margin: { t: 30, b: 30, l: 45, r: 15 }
        };
        Plotly.newPlot(loadDiv, loadTraces, loadLayout, plotlyConfig);
    }

    el.innerHTML = '';
    const drDiv = document.createElement('div');
    drDiv.style.height = '260px';
    el.appendChild(drDiv);

    const drTraces = [
        { x: hours, y: dr.shift, type: 'scatter', mode: 'lines', stackgroup: 'dr', name: '负荷转移', line: { color: '#f39c12' }, hovertemplate: '转移: %{y:.3f} MW<extra></extra>' },
        { x: hours, y: dr.cut_e, type: 'scatter', mode: 'lines', stackgroup: 'dr', name: '电力削减', line: { color: '#e74c3c' }, hovertemplate: '电力削减: %{y:.3f} MW<extra></extra>' },
    ];
    const hdrCut = dr.hdr_cut || [];
    if (hdrCut.some(v => Math.abs(v) > 1e-6)) {
        drTraces.push({ x: hours, y: hdrCut, type: 'scatter', mode: 'lines', stackgroup: 'dr', name: '热力削减', line: { color: '#9b59b6' }, hovertemplate: '热力削减: %{y:.3f} MW<extra></extra>' });
    }

    const drLayout = {
        ...darkLayout,
        title: { text: '需求响应动作', font: { size: 12, color: '#e2ecf7' } },
        xaxis: { ...darkLayout.xaxis, dtick: 2 },
        yaxis: { ...darkLayout.yaxis, title: { text: '功率 (MW)', font: { size: 10 } } },
        hovermode: 'x unified',
        legend: { ...darkLayout.legend, x: 0, y: -0.15, orientation: 'h', font: { size: 9, color: '#7b8fa8' } },
        margin: { t: 30, b: 45, l: 45, r: 15 }
    };
    Plotly.newPlot(drDiv, drTraces, drLayout, plotlyConfig);
}

function renderDailyEnergyMixChart(data) {
    const el = document.getElementById('daily-energy-mix-chart');
    if (!el || !data) return;

    const traces = [{
        values: [data.pv, data.wind, data.grid, data.chp, data.fc, data.discharge],
        labels: ['光伏', '风电', '市电', 'CHP', '燃料电池', '储能放电'],
        type: 'pie',
        hole: 0.6,
        marker: { colors: ['#f1c40f', '#3498db', '#95a5a6', '#e74c3c', '#8e44ad', '#2ecc71'] },
        textinfo: 'percent',
        textfont: { size: 12, color: '#e2ecf7' },
        hovertemplate: '%{label}<br>%{value:.1f} MWh<br>%{percent}<extra></extra>'
    }];
    const layout = {
        ...darkLayout,
        showlegend: true,
        legend: { font: { size: 11, color: '#7b8fa8' }, bgcolor: 'rgba(0,0,0,0)', x: 0, y: -0.15, orientation: 'h' },
        margin: { t: 20, b: 50, l: 10, r: 10 }
    };
    Plotly.newPlot(el, traces, layout, plotlyConfig);
}

function renderDailyScenarioTable(rows, activeId) {
    const container = document.getElementById('daily-scenarios-table');
    if (!container) return;

    if (!rows || rows.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted); text-align: center; padding: 20px;">暂无数据</div>';
        return;
    }

    const visible = rows.filter(r => r.scenario_id === activeId || r.scenario_id <= 10);
    if (!visible.some(r => r.scenario_id === activeId)) {
        const active = rows.find(r => r.scenario_id === activeId);
        if (active) visible.unshift(active);
    }

    let html = `
        <table class="data-table">
            <thead><tr><th>场景</th><th>成本</th><th>购电</th><th>消纳率</th></tr></thead>
            <tbody>
    `;
    visible.forEach(row => {
        const cls = row.scenario_id === activeId ? ' class="daily-table-active-row"' : '';
        html += `
            <tr${cls}>
                <td>${row.label}</td>
                <td>${formatNumber(row.cost / 1000, 1)}k</td>
                <td>${formatNumber(row.grid_energy, 1)}</td>
                <td>${formatNumber(row.renewable_rate, 1)}%</td>
            </tr>
        `;
    });
    html += '</tbody></table>';
    container.innerHTML = html;
}

function renderDailyCommunityVoltage(community) {
    const select = document.getElementById('daily-voltage-community-select');
    const summary = document.getElementById('daily-voltage-summary');
    const chart = document.getElementById('daily-voltage-chart');
    if (!select || !summary || !chart) return;

    if (!community || !community.available || !community.communities || community.communities.length === 0) {
        summary.innerHTML = `<div class="dashboard-voltage-error">${community?.message || '社区电压数据不可用'}</div>`;
        chart.innerHTML = '';
        select.innerHTML = '';
        return;
    }

    const previous = selectedDailyCommunityId || select.value || '3';
    select.innerHTML = '';
    community.communities.forEach(item => {
        const option = document.createElement('option');
        option.value = String(item.id);
        option.textContent = item.name;
        select.appendChild(option);
    });

    selectedDailyCommunityId = community.communities.some(item => String(item.id) === String(previous))
        ? String(previous)
        : String(community.communities[0].id);
    select.value = selectedDailyCommunityId;
    renderDailySelectedCommunityVoltage();
}

function selectDailyCommunityView(id) {
    const data = currentDailyDispatchData?.community;
    if (!data || !data.available) {
        console.error('日运行社区数据不可用');
        return;
    }

    communitySource = 'daily';
    selectedDailyCommunityId = String(id);

    document.querySelectorAll('.map-community').forEach(card => {
        card.classList.toggle('active', card.dataset.community === 'daily-' + id);
    });

    const dailyView = document.getElementById('daily-view');
    if (dailyView) dailyView.style.display = 'none';
    document.getElementById('overview-view').style.display = 'none';
    const commView = document.getElementById('community-view');
    if (commView) commView.style.display = 'block';

    const names = { '1': '工业区', '2': '商业区', '3': '居民区' };
    document.getElementById('community-title').textContent = (names[id] || '社区' + id) + ' - 日运行监控';

    commView.querySelectorAll('.mode-toggle').forEach(el => el.style.display = 'none');
    document.getElementById('community-scenario-select').style.display = 'none';
    document.getElementById('community-weather-select').style.display = 'none';

    currentView = 'community';
    renderDailyCommunityView(id);
}

function renderDailyCommunityView(id) {
    const data = currentDailyDispatchData?.community;
    if (!data || !data.available) return;

    const item = data.communities.find(x => String(x.id) === String(id));
    if (!item) return;

    const chartData = {
        supply: { hours: item.hours, ...item.supply },
        demand: { hours: item.hours, ...item.demand },
        soc: { hours: item.hours, ...item.soc }
    };
    renderCommunityCharts(chartData);

    const h2Data = {
        hours: item.hours,
        h2: {
            production: item.h2.production || [],
            storage_discharge: item.h2.storage_discharge || [],
            fuel_cell: item.h2.fuel_cell || (item.h2.production ? item.h2.production.map(() => 0) : []),
            storage_charge: item.h2.storage_charge || (item.h2.load ? item.h2.load.map(() => 0) : []),
            load: item.h2.load || [],
            shortage: item.h2.shortage || []
        }
    };
    renderCommunityH2Chart(h2Data);

    const drData = {
        hours: item.hours,
        dr: {
            load_original: item.dr.load_original || (item.demand.load || []),
            load_after_dr: item.dr.load_after_dr || (item.demand.load || []),
            shift: item.dr.shift || [],
            cut_e: item.dr.cut_e || [],
            hdr_cut: item.dr.hdr_cut || (item.dr.cut_e ? item.dr.cut_e.map(() => 0) : [])
        }
    };
    renderCommunityDRChart(drData);

    const sum = arr => arr.reduce((a, b) => a + Math.max(0, b), 0);
    const dailyGen = sum(item.supply.pv) + sum(item.supply.wind) + sum(item.supply.chp) + sum(item.supply.fc) + sum(item.supply.discharge);
    document.getElementById('community-generation').textContent = dailyGen.toFixed(1);

    fetch('/api/planning/capacity').then(res => res.json()).then(result => {
        if (result.success) {
            const c = result.data.communities.find(x => String(x.id) === String(id));
            if (c) {
                document.getElementById('community-solar-capacity').textContent = c.pv_mw.toFixed(1);
                document.getElementById('community-wind-capacity').textContent = c.wind_mw.toFixed(1);
                document.getElementById('community-storage-capacity').textContent = c.battery_mwh.toFixed(1);
                document.getElementById('community-thermal-capacity').textContent = c.thermal_mwh.toFixed(1);
                document.getElementById('community-h2-capacity').textContent = c.h2_kg.toFixed(0);
                document.getElementById('community-battery-power').textContent = (c.battery_power_mw || 0).toFixed(1);
            }
        }
    }).catch(e => console.error('加载容量配置失败:', e));
}

function renderDailySelectedCommunityVoltage() {
    const data = currentDailyDispatchData?.community;
    const select = document.getElementById('daily-voltage-community-select');
    const summary = document.getElementById('daily-voltage-summary');
    const chart = document.getElementById('daily-voltage-chart');
    if (!data || !data.available || !select || !summary || !chart) return;

    selectedDailyCommunityId = String(select.value || selectedDailyCommunityId || '3');
    document.querySelectorAll('[data-community^="daily-"]').forEach(card => {
        card.classList.toggle('active', card.dataset.community === 'daily-' + selectedDailyCommunityId);
    });

    const item = data.communities.find(x => String(x.id) === selectedDailyCommunityId) || data.communities[0];
    if (!item) return;

    const minText = item.summary?.min_voltage_pu == null ? '--' : item.summary.min_voltage_pu.toFixed(4);
    const maxText = item.summary?.max_voltage_pu == null ? '--' : item.summary.max_voltage_pu.toFixed(4);
    const all = data.voltage_summary || {};
    summary.innerHTML = `
        <div class="dashboard-voltage-summary-card"><span>社区最低电压</span><strong>${minText}</strong><small>p.u.</small></div>
        <div class="dashboard-voltage-summary-card"><span>社区最高电压</span><strong>${maxText}</strong><small>p.u.</small></div>
        <div class="dashboard-voltage-summary-card"><span>全日低压越限</span><strong>${all.low_violations || 0}</strong><small>次</small></div>
        <div class="dashboard-voltage-summary-card"><span>全日高压越限</span><strong>${all.high_violations || 0}</strong><small>次</small></div>
    `;

    const trace = {
        x: item.hours,
        y: item.voltage,
        type: 'scatter',
        mode: 'lines+markers',
        name: item.name,
        line: { color: '#00d4ff', width: 2.5 },
        marker: { size: 5, color: '#00e676', line: { color: '#06203a', width: 1 } },
        hovertemplate: `${item.name}<br>%{x}h: %{y:.4f} p.u.<extra></extra>`
    };
    const limitLine = (y, color, dash) => ({
        type: 'line',
        xref: 'x',
        yref: 'y',
        x0: item.hours[0] || 1,
        x1: item.hours[item.hours.length - 1] || 24,
        y0: y,
        y1: y,
        line: { color, width: 1.4, dash }
    });
    const layout = {
        ...darkLayout,
        title: { text: `${item.name} 电压时序`, font: { size: 13, color: '#e2ecf7' } },
        xaxis: { ...darkLayout.xaxis, title: { text: '时间 (h)', font: { size: 11 } }, dtick: 2 },
        yaxis: { ...darkLayout.yaxis, title: { text: '电压 (p.u.)', font: { size: 11 } }, range: [0.93, 1.07] },
        hovermode: 'x unified',
        showlegend: false,
        shapes: [limitLine(0.95, '#ff5252', 'dash'), limitLine(1.05, '#ff5252', 'dash'), limitLine(1.0, '#7b8fa8', 'dot')],
        margin: { t: 40, b: 50, l: 55, r: 30 }
    };
    Plotly.newPlot(chart, [trace], layout, plotlyConfig);
}

const DAILY_VOLTAGE_TOPOLOGY_NODES = [
    { id: 0, x: 2.14256117612853, y: 4.03543293340162 },
    { id: 1, x: 2.54921261140423, y: 3.98375977636718 },
    { id: 2, x: 3.24885170622048, y: 3.98375978256257 },
    { id: 3, x: 3.2185039311051, y: 4.86958652594558 },
    { id: 4, x: 4.12107879380945, y: 4.8892715611599 },
    { id: 5, x: 4.89631138545575, y: 4.8892715611599 },
    { id: 6, x: 5.58070858012645, y: 4.8892715611599 },
    { id: 7, x: 6.44677656874835, y: 4.8892715611599 },
    { id: 8, x: 7.29648461291837, y: 4.92126001367948 },
    { id: 9, x: 8.00870313805102, y: 4.92864164040735 },
    { id: 10, x: 8.77247434368726, y: 4.92864164040735 },
    { id: 11, x: 9.54770693533356, y: 4.92126001367948 },
    { id: 12, x: 10.3229395269799, y: 4.92126001367948 },
    { id: 13, x: 10.3219365748854, y: 3.87829824235933 },
    { id: 14, x: 11.0971691665317, y: 3.87829824235933 },
    { id: 15, x: 11.7558825730838, y: 3.84850541553973 },
    { id: 16, x: 12.5377364969653, y: 3.84850541553973 },
    { id: 17, x: 13.3195904208467, y: 3.84850541553973 },
    { id: 18, x: 13.9631865241982, y: 3.84850541553973 },
    { id: 19, x: 4.12107879380944, y: 3.94438970331512 },
    { id: 20, x: 4.89631138545575, y: 3.94438970331512 },
    { id: 21, x: 5.6781653093372, y: 3.94438970331512 },
    { id: 22, x: 5.4101049180855, y: 2.80757887426399 },
    { id: 23, x: 3.2185040182132, y: 5.85383868872698 },
    { id: 24, x: 4.12107879380945, y: 5.85383868872698 },
    { id: 25, x: 5.09513031326593, y: 5.85383868872698 },
    { id: 26, x: 5.67154397710205, y: 5.85383868872698 },
    { id: 27, x: 6.44677656874835, y: 5.85383868872698 },
    { id: 28, x: 7.21456702844376, y: 5.85383868872698 },
    { id: 29, x: 7.84363248444243, y: 5.85383874981189 },
    { id: 30, x: 8.77247434368726, y: 5.45275608773051 },
    { id: 31, x: 9.53810473055086, y: 5.85383868872698 },
    { id: 32, x: 10.3255063119003, y: 5.85383868872698 },
    { id: 33, x: 11.0925198317078, y: 5.85383868872698 }
];

const DAILY_VOLTAGE_TOPOLOGY_EDGES = [
    [0, 1], [1, 2], [2, 3], [2, 19], [3, 4], [3, 23], [4, 5], [5, 6],
    [6, 7], [6, 26], [7, 8], [8, 9], [9, 10], [10, 11], [11, 12],
    [12, 13], [13, 14], [14, 15], [15, 16], [16, 17], [17, 18],
    [19, 20], [20, 21], [21, 22], [23, 24], [24, 25], [26, 27],
    [27, 28], [28, 29], [29, 30], [30, 31], [31, 32], [32, 33]
];

const DAILY_VOLTAGE_TOPOLOGY_BOUNDS = DAILY_VOLTAGE_TOPOLOGY_NODES.reduce((acc, node) => ({
    minX: Math.min(acc.minX, node.x),
    maxX: Math.max(acc.maxX, node.x),
    minY: Math.min(acc.minY, node.y),
    maxY: Math.max(acc.maxY, node.y)
}), { minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity });

function dailyTopologyPoint(node) {
    const width = 1000;
    const height = 360;
    const padX = 34;
    const padY = 30;
    return {
        x: padX + ((node.x - DAILY_VOLTAGE_TOPOLOGY_BOUNDS.minX) / (DAILY_VOLTAGE_TOPOLOGY_BOUNDS.maxX - DAILY_VOLTAGE_TOPOLOGY_BOUNDS.minX)) * (width - padX * 2),
        y: padY + ((DAILY_VOLTAGE_TOPOLOGY_BOUNDS.maxY - node.y) / (DAILY_VOLTAGE_TOPOLOGY_BOUNDS.maxY - DAILY_VOLTAGE_TOPOLOGY_BOUNDS.minY)) * (height - padY * 2)
    };
}

function getDailyVoltageNodeInfo(data) {
    const nodes = (data?.nodes || []).map(String);
    const voltageByNode = new Map();
    nodes.forEach((node, index) => {
        voltageByNode.set(node, (data.voltage || [])[index] || []);
    });
    return voltageByNode;
}

function setDailyTopologyStatus(message, isWarning = false) {
    const status = document.getElementById('daily-voltage-topology-status');
    if (!status) return;
    status.textContent = message;
    status.classList.toggle('warning', isWarning);
}

function renderDailyVoltageTopology(nodeVoltage) {
    renderVoltageDeviationTopology('daily', nodeVoltage, 'daily-voltage-topology', 'daily-voltage-topology-status');
}

function updateDailyVoltageTopologySelection(nodeVoltage = currentDailyDispatchData?.node_voltage) {
    if (!nodeVoltage?.available) return;
    updateVoltageTopologySelection('daily', selectedDailyNodeId);
}

function renderDailyNodeVoltage(nodeVoltage) {
    const select = document.getElementById('daily-voltage-node-select');
    const summary = document.getElementById('daily-voltage-summary');
    const chart = document.getElementById('daily-voltage-chart');
    if (!select || !summary || !chart) return;

    if (!nodeVoltage || !nodeVoltage.available || !nodeVoltage.nodes || nodeVoltage.nodes.length === 0) {
        summary.innerHTML = `<div class="dashboard-voltage-error">${nodeVoltage?.message || '节点电压数据不可用'}</div>`;
        chart.innerHTML = '';
        select.innerHTML = '';
        stopVoltageDeviationPlayback('daily');
        renderDailyVoltageTopology(nodeVoltage);
        return;
    }

    const previous = selectedDailyNodeId || select.value || '1';
    select.innerHTML = '';
    nodeVoltage.nodes.forEach(node => {
        const option = document.createElement('option');
        option.value = String(node);
        option.textContent = `Node ${node}`;
        select.appendChild(option);
    });

    selectedDailyNodeId = nodeVoltage.nodes.map(String).includes(String(previous))
        ? String(previous)
        : String(nodeVoltage.nodes[0]);
    select.value = selectedDailyNodeId;
    dailyVoltageHourIndex = getDefaultVoltageHourIndex(nodeVoltage);
    renderDailyVoltageTopology(nodeVoltage);
    renderDailySelectedNodeVoltage();
}

function renderDailySelectedNodeVoltage() {
    const data = currentDailyDispatchData?.node_voltage;
    const select = document.getElementById('daily-voltage-node-select');
    const summary = document.getElementById('daily-voltage-summary');
    const chart = document.getElementById('daily-voltage-chart');
    if (!data || !data.available || !select || !summary || !chart) return;

    selectedDailyNodeId = String(select.value || selectedDailyNodeId || '1');
    const nodeIndex = (data.nodes || []).map(String).indexOf(selectedDailyNodeId);
    const selectedNode = nodeIndex >= 0 ? data.nodes[nodeIndex] : (data.nodes || [])[0];
    const voltage = nodeIndex >= 0 ? (data.voltage || [])[nodeIndex] || [] : (data.voltage || [])[0] || [];
    if (selectedNode == null) return;
    selectedDailyNodeId = String(selectedNode);
    if (select.value !== selectedDailyNodeId) select.value = selectedDailyNodeId;
    updateDailyVoltageTopologySelection(data);

    const validVoltage = voltage.filter(v => v != null && !Number.isNaN(Number(v))).map(Number);
    const nodeMin = validVoltage.length ? Math.min(...validVoltage) : null;
    const nodeMax = validVoltage.length ? Math.max(...validVoltage) : null;
    const nodeLowViolations = validVoltage.filter(v => v < 0.95).length;
    const nodeHighViolations = validVoltage.filter(v => v > 1.05).length;
    summary.innerHTML = `
        <div class="dashboard-voltage-summary-card"><span>当前节点最低电压</span><strong>${nodeMin == null ? '--' : nodeMin.toFixed(4)}</strong><small>p.u.</small></div>
        <div class="dashboard-voltage-summary-card"><span>当前节点最高电压</span><strong>${nodeMax == null ? '--' : nodeMax.toFixed(4)}</strong><small>p.u.</small></div>
        <div class="dashboard-voltage-summary-card"><span>节点低压越限</span><strong>${nodeLowViolations}</strong><small>次</small></div>
        <div class="dashboard-voltage-summary-card"><span>节点高压越限</span><strong>${nodeHighViolations}</strong><small>次</small></div>
    `;

    const trace = {
        x: data.hours || [],
        y: voltage,
        type: 'scatter',
        mode: 'lines+markers',
        name: `Node ${selectedNode}`,
        line: { color: '#00d4ff', width: 2.5 },
        marker: { size: 5, color: '#00e676', line: { color: '#06203a', width: 1 } },
        hovertemplate: `Node ${selectedNode}<br>%{x}h: %{y:.4f} p.u.<extra></extra>`
    };
    const limitLine = (y, color, dash) => ({
        type: 'line',
        xref: 'x',
        yref: 'y',
        x0: (data.hours || [])[0] || 1,
        x1: (data.hours || [])[((data.hours || []).length - 1)] || 24,
        y0: y,
        y1: y,
        line: { color, width: 1.4, dash }
    });
    const layout = {
        ...darkLayout,
        title: { text: `Node ${selectedNode} 电压时序`, font: { size: 13, color: '#e2ecf7' } },
        xaxis: { ...darkLayout.xaxis, title: { text: '时间 (h)', font: { size: 11 } }, dtick: 2 },
        yaxis: { ...darkLayout.yaxis, title: { text: '电压 (p.u.)', font: { size: 11 } }, range: [0.93, 1.07] },
        hovermode: 'x unified',
        showlegend: false,
        shapes: [limitLine(0.95, '#ff5252', 'dash'), limitLine(1.05, '#ff5252', 'dash'), limitLine(1.0, '#7b8fa8', 'dot')],
        margin: { t: 40, b: 50, l: 55, r: 30 }
    };
    Plotly.newPlot(chart, [trace], layout, plotlyConfig);
}

function renderDailyCostBreakdownChart(data) {
    const container = document.getElementById('daily-cost-breakdown-chart');
    if (!container) return;

    if (!data) {
        container.innerHTML = '<div style="color: var(--text-muted); text-align: center; padding: 20px;">成本构成数据不可用</div>';
        return;
    }

    const items = [
        { label: '购电成本', value: data.grid, color: '#3498db' },
        { label: '燃气成本', value: data.gas, color: '#e74c3c' },
        { label: '碳交易成本', value: data.carbon_trading, color: '#2ecc71' },
        { label: '燃气碳成本', value: data.gas_carbon, color: '#95a5a6' },
        { label: '弃光成本', value: data.pv_curt, color: '#f1c40f' },
        { label: '弃风成本', value: data.wind_curt, color: '#1abc9c' },
        { label: '氢气短缺', value: data.h2_short, color: '#ff5252' },
        { label: '需求响应', value: data.demand_response, color: '#9b59b6' },
        { label: '无功支撑', value: data.q_support, color: '#ff9100' }
    ].filter(item => Math.abs(Number(item.value) || 0) > 0.01);

    if (items.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted); text-align: center; padding: 20px;">暂无非零成本项</div>';
        return;
    }

    const trace = [{
        values: items.map(item => Math.abs(Number(item.value) || 0)),
        labels: items.map(item => item.label),
        type: 'pie',
        hole: 0.55,
        marker: { colors: items.map(item => item.color) },
        textinfo: 'percent',
        textfont: { size: 11, color: '#e2ecf7' },
        hovertemplate: '%{label}<br>%{value:,.0f} 元<br>%{percent}<extra></extra>'
    }];

    const total = Number(data.total) || items.reduce((sum, item) => sum + Math.abs(Number(item.value) || 0), 0);
    const layout = {
        ...darkLayout,
        title: { text: `日总成本 ${(total / 10000).toFixed(2)} 万元`, font: { size: 13, color: '#e2ecf7' } },
        showlegend: true,
        legend: { font: { size: 10, color: '#7b8fa8' }, bgcolor: 'rgba(0,0,0,0)', x: 0.5, y: -0.18, xanchor: 'center', orientation: 'h' },
        margin: { t: 42, b: 58, l: 10, r: 10 }
    };

    Plotly.newPlot(container, trace, layout, plotlyConfig);
}

async function loadDailyCapacityTable() {
    const container = document.getElementById('daily-capacity-table');
    if (!container) return;

    try {
        const res = await fetch('/api/planning/capacity');
        const result = await res.json();
        if (!result.success) throw new Error(result.error || '加载容量配置失败');

        const { communities, totals } = result.data;
        let html = `
            <table class="data-table">
                <thead><tr><th>区域</th><th>PV</th><th>风电</th><th>电池</th><th>氢储</th></tr></thead>
                <tbody>
        `;
        communities.forEach(c => {
            html += `
                <tr>
                    <td>${c.name}</td>
                    <td>${c.pv_mw.toFixed(1)}</td>
                    <td>${c.wind_mw.toFixed(1)}</td>
                    <td>${c.battery_mwh.toFixed(1)}</td>
                    <td>${c.h2_kg.toFixed(0)}</td>
                </tr>
            `;
        });
        html += `
                <tr style="font-weight:bold;border-top:2px solid var(--border-color)">
                    <td>合计</td>
                    <td>${totals.PV_MW.toFixed(1)}</td>
                    <td>${totals.Wind_MW.toFixed(1)}</td>
                    <td>${totals.BatteryEnergy_MWh.toFixed(1)}</td>
                    <td>${totals.HydrogenStorage_kg.toFixed(0)}</td>
                </tr>
            </tbody></table>
        `;
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = `<div style="color: var(--text-muted); text-align: center; padding: 20px;">${e.message}</div>`;
        console.error('加载日运行容量配置失败:', e);
    }
}

async function loadDailyDispatchConfig() {
    try {
        const res = await fetch('/api/daily-dispatch/config');
        const result = await res.json();
        if (result.success && result.data.latest) {
            renderDailyDispatch(result.data.latest);
        }
    } catch (e) {
        console.error('加载日运行调度配置失败:', e);
    }
}

async function runDailyDispatch() {
    const btn = document.querySelector('.daily-run-btn');
    const status = document.getElementById('daily-dispatch-status');

    if (!dailyCsvCurves) {
        setCSVStatus('请先导入风光出力 CSV 文件', true);
        if (status) status.textContent = '缺少CSV数据';
        setText('daily-overview-status', '请先导入CSV文件');
        return;
    }

    const payload = {
        pv_curve: dailyCsvCurves.pv_curve,
        wind_curve: dailyCsvCurves.wind_curve
    };

    if (btn) btn.disabled = true;
    if (status) status.textContent = '实时优化中...';
    setText('daily-overview-status', '实时优化中...');

    try {
        const res = await fetch('/api/daily-dispatch/optimize-milp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await res.json();
        if (!result.success) {
            if (status) status.textContent = result.error || '实时优化失败';
            setText('daily-overview-status', result.error || '实时优化失败');
            return;
        }
        renderDailyDispatch(result.data);
    } catch (e) {
        if (status) status.textContent = '实时优化失败';
        setText('daily-overview-status', '实时优化失败');
        console.error('运行日调度失败:', e);
    } finally {
        if (btn) btn.disabled = false;
    }
}

function renderDailyDispatch(data) {
    if (!data) return;
    currentDailyDispatchData = data;
    const status = document.getElementById('daily-dispatch-status');
    if (status) status.textContent = '实时优化完成';
    setText('daily-overview-status', '实时优化完成');

    setText('daily-runtime', formatRuntimeSeconds(data));

    const curves = data.weather_curves || {};
    if (curves.pv_24 && curves.wind_24) {
        currentDailyCurves = {
            pv_24: curves.pv_24,
            wind_24: curves.wind_24,
            matchedDdre: data.matched_ddre || data.scenario_id || currentDailyCurves.matchedDdre
        };
        renderNormalizedCurves(curves.pv_24, curves.wind_24, curves.matched_pv_24, curves.matched_wind_24);
    }

    const k = data.kpis || {};
    setText('daily-kpi-cost', formatNumber(k.cost, 0));
    setText('daily-kpi-grid', formatNumber(k.grid_energy, 1));
    setText('daily-kpi-carbon', formatNumber(k.carbon_emission, 1));
    setText('daily-kpi-renewable', formatNumber(k.renewable_rate, 1));
    setText('daily-kpi-carbon-cost', formatNumber(k.carbon_trading_cost, 0));

    renderDailyPowerChart(data.chart);
    renderDailySocChart(data.chart);
    renderDailyH2Chart(data.h2);
    renderDailyDRChart(data.dr);
    renderDailyOverview(data);
}

function formatRuntimeSeconds(data) {
    if (data?.runtime_s != null && !Number.isNaN(Number(data.runtime_s))) {
        return `${Number(data.runtime_s).toFixed(1)} s`;
    }
    if (data?.runtime_ms != null && !Number.isNaN(Number(data.runtime_ms))) {
        return `${(Number(data.runtime_ms) / 1000).toFixed(1)} s`;
    }
    return '--';
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function formatNumber(value, decimals) {
    if (value == null || Number.isNaN(Number(value))) return '--';
    return Number(value).toFixed(decimals).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

function renderDailyPowerChart(chart) {
    const el = document.getElementById('daily-power-chart');
    if (!el || !chart) return;
    const hours = chart.supply.hours;
    const traces = [
        { x: hours, y: chart.supply.pv, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '光伏', line: { color: '#f1c40f' } },
        { x: hours, y: chart.supply.wind, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '风电', line: { color: '#3498db' } },
        { x: hours, y: chart.supply.grid, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '电网', line: { color: '#95a5a6' } },
        { x: hours, y: chart.supply.discharge, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '储能放电', line: { color: '#2ecc71' } },
        { x: hours, y: chart.supply.chp, type: 'scatter', mode: 'lines', stackgroup: 'one', name: 'CHP', line: { color: '#e74c3c' } },
        { x: hours, y: chart.supply.fc, type: 'scatter', mode: 'lines', stackgroup: 'one', name: '燃料电池', line: { color: '#8e44ad' } },
        { x: hours, y: chart.demand_total, type: 'scatter', mode: 'lines', name: '总用电', line: { color: '#ffffff', width: 2.4 } }
    ];
    const layout = {
        ...darkLayout,
        title: { text: '日供电调度', font: { size: 13, color: '#e2ecf7' } },
        xaxis: { ...darkLayout.xaxis, title: { text: 'h', font: { size: 10 } }, dtick: 4 },
        yaxis: { ...darkLayout.yaxis, title: { text: 'MW', font: { size: 10 } } },
        legend: { ...darkLayout.legend, orientation: 'h', y: -0.32, font: { size: 9 } },
        margin: { t: 34, b: 62, l: 42, r: 12 }
    };
    Plotly.newPlot(el, traces, layout, plotlyConfig);
}

function renderDailySocChart(chart) {
    const el = document.getElementById('daily-soc-chart');
    if (!el || !chart) return;
    const hours = chart.soc.hours;
    const traces = [
        { x: hours, y: chart.soc.soc_e, type: 'scatter', mode: 'lines+markers', name: '电储能', line: { color: '#00d4ff' }, marker: { size: 4 } },
        { x: hours, y: chart.soc.soc_th, type: 'scatter', mode: 'lines+markers', name: '热储能', line: { color: '#ff9100' }, marker: { size: 4 } },
        { x: hours, y: chart.soc.soc_h2, type: 'scatter', mode: 'lines+markers', name: '氢储能', yaxis: 'y2', line: { color: '#00e676' }, marker: { size: 4 } }
    ];
    const layout = {
        ...darkLayout,
        title: { text: '储能状态', font: { size: 13, color: '#e2ecf7' } },
        xaxis: { ...darkLayout.xaxis, title: { text: 'h', font: { size: 10 } }, dtick: 4 },
        yaxis: { ...darkLayout.yaxis, title: { text: 'MWh', font: { size: 10 } } },
        yaxis2: { overlaying: 'y', side: 'right', title: { text: 'kg', font: { size: 10 } }, tickfont: { size: 10, color: '#7b8fa8' }, gridcolor: 'rgba(0,0,0,0)' },
        legend: { ...darkLayout.legend, orientation: 'h', y: -0.32, font: { size: 9 } },
        margin: { t: 34, b: 62, l: 42, r: 42 }
    };
    Plotly.newPlot(el, traces, layout, plotlyConfig);
}

function renderDailyH2Chart(h2) {
    const el = document.getElementById('daily-h2-chart');
    if (!el || !h2) return;
    const traces = [
        { x: h2.hours, y: h2.load, type: 'scatter', mode: 'lines', name: '氢负荷', line: { color: '#ffffff', width: 2.2 } },
        { x: h2.hours, y: h2.production, type: 'bar', name: '制氢', marker: { color: '#00d4ff' } },
        { x: h2.hours, y: h2.storage_discharge, type: 'bar', name: '放氢', marker: { color: '#00e676' } },
        { x: h2.hours, y: h2.shortage, type: 'bar', name: '短缺', marker: { color: '#ff5252' } }
    ];
    const layout = {
        ...darkLayout,
        title: { text: '氢气供需', font: { size: 13, color: '#e2ecf7' } },
        barmode: 'stack',
        xaxis: { ...darkLayout.xaxis, title: { text: 'h', font: { size: 10 } }, dtick: 4 },
        yaxis: { ...darkLayout.yaxis, title: { text: 'kg', font: { size: 10 } } },
        legend: { ...darkLayout.legend, orientation: 'h', y: -0.32, font: { size: 9 } },
        margin: { t: 34, b: 62, l: 42, r: 12 }
    };
    Plotly.newPlot(el, traces, layout, plotlyConfig);
}

function renderDailyDRChart(dr) {
    const el = document.getElementById('daily-dr-chart');
    if (!el || !dr) return;
    const traces = [
        { x: dr.hours, y: dr.shift_base, type: 'scatter', mode: 'lines', name: '基准响应', line: { color: '#7b8fa8', dash: 'dash' } },
        { x: dr.hours, y: dr.shift, type: 'scatter', mode: 'lines+markers', name: '实际转移', line: { color: '#00d4ff' }, marker: { size: 4 } },
        { x: dr.hours, y: dr.cut_e, type: 'bar', name: '削减', marker: { color: '#ff9100' } }
    ];
    const layout = {
        ...darkLayout,
        title: { text: '需求响应', font: { size: 13, color: '#e2ecf7' } },
        xaxis: { ...darkLayout.xaxis, title: { text: 'h', font: { size: 10 } }, dtick: 4 },
        yaxis: { ...darkLayout.yaxis, title: { text: 'MW', font: { size: 10 } } },
        legend: { ...darkLayout.legend, orientation: 'h', y: -0.32, font: { size: 9 } },
        margin: { t: 34, b: 62, l: 42, r: 12 }
    };
    Plotly.newPlot(el, traces, layout, plotlyConfig);
}

/* ========== 天气配置模块 ========== */

let dbScenarioPowerData = null;
let dbCsvFileData = null;
let dbTableChartTimer = null;

// ---- 天数配置 ----
async function dbLoadWeatherConfig() {
    const body = document.getElementById('db-weather-config-body');
    const statusEl = document.getElementById('db-weather-config-status');
    if (!body) return;
    statusEl.textContent = '';
    try {
        const res = await fetch('/api/weather/config');
        const result = await res.json();
        if (result.success) {
            body.innerHTML = '';
            result.data.forEach(item => {
                body.innerHTML += `
                    <tr>
                        <td>${item.name} (${item.scenario})</td>
                        <td><input type="number" class="weather-days-input" data-scenario="${item.scenario}" value="${item.days}" min="0" max="365"></td>
                        <td class="weather-days-pct">${(item.days / 365 * 100).toFixed(1)}%</td>
                    </tr>
                `;
            });
            dbUpdateWeatherTotal();
            // bind change events
            body.querySelectorAll('.weather-days-input').forEach(inp => {
                inp.addEventListener('input', dbUpdateWeatherTotal);
            });
        }
    } catch (e) {
        console.error('加载天气配置失败:', e);
    }
}

function dbUpdateWeatherTotal() {
    const inputs = document.querySelectorAll('#db-weather-config-body .weather-days-input');
    let total = 0;
    inputs.forEach(inp => {
        total += parseInt(inp.value) || 0;
    });
    const totalEl = document.getElementById('db-weather-total-days');
    if (totalEl) totalEl.textContent = total;
    // update percentages
    inputs.forEach(inp => {
        const pctEl = inp.closest('tr').querySelector('.weather-days-pct');
        if (pctEl) {
            const val = parseInt(inp.value) || 0;
            pctEl.textContent = total > 0 ? (val / 365 * 100).toFixed(1) + '%' : '0%';
        }
    });
    // validate
    if (totalEl) {
        totalEl.style.color = total === 365 ? 'var(--accent-cyan)' : 'var(--accent-red)';
    }
}

async function dbSaveWeatherConfig() {
    const statusEl = document.getElementById('db-weather-config-status');
    const inputs = document.querySelectorAll('#db-weather-config-body .weather-days-input');
    const days = {};
    let total = 0;
    inputs.forEach(inp => {
        const val = parseInt(inp.value) || 0;
        days[inp.dataset.scenario] = val;
        total += val;
    });
    if (total !== 365) {
        statusEl.textContent = '总天数必须为365';
        statusEl.style.color = 'var(--accent-red)';
        return;
    }
    try {
        const res = await fetch('/api/weather/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ days })
        });
        const result = await res.json();
        if (result.success) {
            statusEl.textContent = '保存成功';
            statusEl.style.color = 'var(--accent-green)';
        } else {
            statusEl.textContent = result.error || '保存失败';
            statusEl.style.color = 'var(--accent-red)';
        }
    } catch (e) {
        statusEl.textContent = '保存失败';
        statusEl.style.color = 'var(--accent-red)';
    }
}

// ---- 功率曲线配置 ----
function dbSwitchPowerMethod(method) {
    document.querySelectorAll('.weather-method-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.method === method);
    });
    document.querySelectorAll('.weather-method-content').forEach(pane => {
        pane.classList.remove('active');
    });
    document.getElementById('db-power-method-' + method).classList.add('active');
    dbRenderActivePowerChart();
}

async function dbLoadScenarioPower() {
    const select = document.getElementById('db-scenario-power-select');
    const scenarioId = select.value;
    const statusEl = document.getElementById('db-scenario-power-status');
    if (statusEl) statusEl.textContent = '';
    try {
        const res = await fetch(`/api/scenario-power/${scenarioId}`);
        const result = await res.json();
        if (result.success) {
            dbScenarioPowerData = result.data.hourly;
            const body = document.getElementById('db-scenario-power-body');
            body.innerHTML = '';
            dbScenarioPowerData.forEach(item => {
                const hh = String(item.hour).padStart(2, '0');
                body.innerHTML += `
                    <tr>
                        <td>${hh}:00</td>
                        <td><input type="number" class="weather-power-input" data-col="node_22_wind" value="${item.node_22_wind}" step="0.01" min="0" max="1"></td>
                        <td><input type="number" class="weather-power-input" data-col="node_25_wind" value="${item.node_25_wind}" step="0.01" min="0" max="1"></td>
                        <td><input type="number" class="weather-power-input" data-col="node_18_PV" value="${item.node_18_PV}" step="0.01" min="0" max="1"></td>
                        <td><input type="number" class="weather-power-input" data-col="node_33_PV" value="${item.node_33_PV}" step="0.01" min="0" max="1"></td>
                    </tr>
                `;
            });
            dbRenderActivePowerChart();
        } else {
            if (statusEl) {
                statusEl.textContent = result.error || '加载失败';
                statusEl.style.color = 'var(--accent-red)';
            }
        }
    } catch (e) {
        console.error('加载场景功率失败:', e);
        if (statusEl) {
            statusEl.textContent = '加载失败';
            statusEl.style.color = 'var(--accent-red)';
        }
    }
}

function dbOnScenarioSelectChange() {
    dbLoadScenarioPower();
}

function dbRenderPowerCurveChart(chartId) {
    if (!dbScenarioPowerData) return;
    const el = document.getElementById(chartId);
    if (!el) return;
    const labels = dbScenarioPowerData.map(d => String(d.hour).padStart(2, '0') + ':00');
    const cfg = [
        { name: '风电 node_22', color: '#1e90ff', key: 'node_22_wind' },
        { name: '风电 node_25', color: '#00bcd4', key: 'node_25_wind' },
        { name: '光伏 node_18', color: '#ff9100', key: 'node_18_PV' },
        { name: '光伏 node_33', color: '#ff5252', key: 'node_33_PV' },
    ];
    const traces = cfg.map(t => ({
        x: labels,
        y: dbScenarioPowerData.map(d => d[t.key]),
        mode: 'lines+markers',
        name: t.name,
        line: { color: t.color, width: 2 },
        marker: { color: t.color, size: 7 },
    }));
    const layout = {
        ...darkLayout,
        title: { text: '风光功率曲线预览', font: { size: 13, color: '#e2ecf7' } },
        xaxis: { ...darkLayout.xaxis, title: { text: '时刻', font: { size: 10 } }, dtick: 2, fixedrange: true },
        yaxis: { ...darkLayout.yaxis, title: { text: '标幺值 (p.u.)', font: { size: 10 } }, range: [-0.05, 1.05], dtick: 0.1, fixedrange: true, autorange: false },
        legend: { ...darkLayout.legend, orientation: 'h', y: -0.22 },
        margin: { t: 40, b: 70, l: 50, r: 20 },
    };
    Plotly.react(chartId, traces, layout, plotlyConfig);
}

function dbRenderActivePowerChart() {
    const activeBtn = document.querySelector('.weather-method-btn.active');
    if (!activeBtn) return;
    const method = activeBtn.dataset.method;
    if (method === 'csv') {
        dbRenderPowerCurveChart('db-csv-power-chart');
    } else if (method === 'table') {
        dbRenderPowerCurveChart('db-table-power-chart');
    }
}

function dbSyncTableFromData() {
    if (!dbScenarioPowerData) return;
    const rows = document.querySelectorAll('#db-scenario-power-body tr');
    rows.forEach((row, idx) => {
        if (idx >= dbScenarioPowerData.length) return;
        const inputs = row.querySelectorAll('.weather-power-input');
        const d = dbScenarioPowerData[idx];
        if (inputs[0]) inputs[0].value = d.node_22_wind.toFixed(4);
        if (inputs[1]) inputs[1].value = d.node_25_wind.toFixed(4);
        if (inputs[2]) inputs[2].value = d.node_18_PV.toFixed(4);
        if (inputs[3]) inputs[3].value = d.node_33_PV.toFixed(4);
    });
}

function dbSyncDataFromTable() {
    if (!dbScenarioPowerData) return;
    const rows = document.querySelectorAll('#db-scenario-power-body tr');
    rows.forEach((row, idx) => {
        if (idx >= dbScenarioPowerData.length) return;
        const inputs = row.querySelectorAll('.weather-power-input');
        dbScenarioPowerData[idx].node_22_wind = parseFloat(inputs[0].value) || 0;
        dbScenarioPowerData[idx].node_25_wind = parseFloat(inputs[1].value) || 0;
        dbScenarioPowerData[idx].node_18_PV = parseFloat(inputs[2].value) || 0;
        dbScenarioPowerData[idx].node_33_PV = parseFloat(inputs[3].value) || 0;
    });
}

// table input debounce listener
document.addEventListener('DOMContentLoaded', () => {
    const tableBody = document.getElementById('db-scenario-power-body');
    if (tableBody) {
        tableBody.addEventListener('input', () => {
            clearTimeout(dbTableChartTimer);
            dbTableChartTimer = setTimeout(() => {
                dbSyncDataFromTable();
                dbRenderPowerCurveChart('db-table-power-chart');
            }, 300);
        });
    }
});

async function dbSaveScenarioPower() {
    const select = document.getElementById('db-scenario-power-select');
    const scenarioId = select.value;
    const statusEl = document.getElementById('db-scenario-power-status');
    const activeBtn = document.querySelector('.weather-method-btn.active');
    const method = activeBtn ? activeBtn.dataset.method : 'table';
    if (method === 'table') dbSyncDataFromTable();

    if (!dbScenarioPowerData) {
        statusEl.textContent = '请先加载数据';
        statusEl.style.color = 'var(--accent-red)';
        return;
    }
    try {
        const res = await fetch(`/api/scenario-power/${scenarioId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ hourly: dbScenarioPowerData })
        });
        const result = await res.json();
        if (result.success) {
            statusEl.textContent = '保存成功';
            statusEl.style.color = 'var(--accent-green)';
        } else {
            statusEl.textContent = result.error || '保存失败';
            statusEl.style.color = 'var(--accent-red)';
        }
    } catch (e) {
        statusEl.textContent = '保存失败';
        statusEl.style.color = 'var(--accent-red)';
    }
}

function dbOnCsvFileSelected(input) {
    const file = input.files[0];
    const nameEl = document.getElementById('db-csv-file-name');
    const previewArea = document.getElementById('db-csv-preview-area');
    const statusEl = document.getElementById('db-csv-import-status');
    statusEl.textContent = '';
    if (!file) {
        nameEl.textContent = '未选择文件';
        previewArea.style.display = 'none';
        dbCsvFileData = null;
        return;
    }
    nameEl.textContent = file.name;
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const text = e.target.result;
            const lines = text.trim().split('\n');
            const headers = lines[0].split(',').map(h => h.trim());
            const requiredCols = ['node_22_wind', 'node_25_wind', 'node_18_PV', 'node_33_PV'];
            const colIndices = requiredCols.map(c => {
                const idx = headers.indexOf(c);
                if (idx < 0) throw new Error(`缺少列: ${c}`);
                return idx;
            });
            const tsIdx = headers.indexOf('timestamp');
            const rows = [];
            for (let i = 1; i < lines.length; i++) {
                const cells = lines[i].split(',').map(c => c.trim());
                if (cells.length < 4) continue;
                const row = { timestamp: tsIdx >= 0 ? cells[tsIdx] : `行${i}` };
                colIndices.forEach((idx, j) => { row[requiredCols[j]] = parseFloat(cells[idx]) || 0; });
                rows.push(row);
            }
            if (rows.length < 24) throw new Error(`数据行数不足：需要至少24行，实际${rows.length}行`);
            dbCsvFileData = rows;
            const body = document.getElementById('db-csv-preview-body');
            body.innerHTML = '';
            rows.slice(0, 10).forEach((row, idx) => {
                body.innerHTML += `<tr><td>${idx+1}</td><td>${row.timestamp}</td><td>${row.node_22_wind.toFixed(4)}</td><td>${row.node_25_wind.toFixed(4)}</td><td>${row.node_18_PV.toFixed(4)}</td><td>${row.node_33_PV.toFixed(4)}</td></tr>`;
            });
            if (rows.length > 10) {
                body.innerHTML += `<tr><td colspan="6" style="text-align:center;color:var(--text-muted);">... 共 ${rows.length} 行</td></tr>`;
            }
            previewArea.style.display = 'block';
        } catch (err) {
            nameEl.textContent = '解析失败：' + err.message;
            previewArea.style.display = 'none';
            dbCsvFileData = null;
        }
    };
    reader.readAsText(file);
}

async function dbImportCsvToScenario() {
    const statusEl = document.getElementById('db-csv-import-status');
    const fileInput = document.getElementById('db-csv-file-input');
    const select = document.getElementById('db-scenario-power-select');
    const scenarioId = select.value;
    if (!fileInput.files[0]) {
        statusEl.textContent = '请先选择CSV文件';
        statusEl.style.color = 'var(--accent-red)';
        return;
    }
    const formData = new FormData();
    formData.append('scenario_id', scenarioId);
    formData.append('file', fileInput.files[0]);
    statusEl.textContent = '导入中...';
    statusEl.style.color = 'var(--accent-yellow)';
    try {
        const res = await fetch('/api/scenario-power/import-csv', { method: 'POST', body: formData });
        const result = await res.json();
        if (result.success) {
            statusEl.textContent = result.message || '导入成功';
            statusEl.style.color = 'var(--accent-green)';
            dbScenarioPowerData = result.hourly;
            dbSyncTableFromData();
            dbRenderActivePowerChart();
        } else {
            statusEl.textContent = result.error || '导入失败';
            statusEl.style.color = 'var(--accent-red)';
        }
    } catch (e) {
        statusEl.textContent = '导入失败';
        statusEl.style.color = 'var(--accent-red)';
    }
}

async function dbSaveAndRerun() {
    const statusEl = document.getElementById('db-scenario-power-status');
    const activeBtn = document.querySelector('.weather-method-btn.active');
    const method = activeBtn ? activeBtn.dataset.method : 'table';
    if (method === 'table') dbSyncDataFromTable();
    if (!dbScenarioPowerData) {
        statusEl.textContent = '请先加载数据';
        statusEl.style.color = 'var(--accent-red)';
        return;
    }
    const select = document.getElementById('db-scenario-power-select');
    const currentId = select.value;
    const scenarioIds = ['116', '178', '137', '183', '40'];
    statusEl.textContent = '正在保存并调用MATLAB运算，请勿关闭页面...';
    statusEl.style.color = 'var(--accent-yellow)';
    const hourlyData = {};
    hourlyData[currentId] = dbScenarioPowerData.map(d => ({ ...d }));
    for (const sid of scenarioIds) {
        if (sid === currentId) continue;
        try {
            const res = await fetch(`/api/scenario-power/${sid}`);
            const result = await res.json();
            if (result.success) hourlyData[sid] = result.data.hourly;
        } catch (e) {
            console.error(`获取场景${sid}数据失败:`, e);
        }
    }
    try {
        const res = await fetch('/api/scenario-power/save-and-rerun', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ hourly_data: hourlyData })
        });
        const result = await res.json();
        if (result.success) {
            statusEl.textContent = '运算完成';
            statusEl.style.color = 'var(--accent-green)';
        } else {
            statusEl.textContent = result.error || '运算失败';
            statusEl.style.color = 'var(--accent-red)';
        }
    } catch (e) {
        statusEl.textContent = '运算失败';
        statusEl.style.color = 'var(--accent-red)';
    }
}

async function dbLoadMatlabConfig() {
    try {
        const res = await fetch('/api/matlab/config');
        const result = await res.json();
        if (result.success) {
            const inp = document.getElementById('db-matlab-path-input');
            if (inp) inp.value = result.data.matlab_path || '';
        }
    } catch (e) {
        console.error('加载MATLAB配置失败:', e);
    }
}

async function dbSaveMatlabPath() {
    const statusEl = document.getElementById('db-matlab-config-status');
    const inp = document.getElementById('db-matlab-path-input');
    try {
        const res = await fetch('/api/matlab/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ matlab_path: inp.value })
        });
        const result = await res.json();
        if (result.success) {
            statusEl.textContent = '保存成功';
            statusEl.style.color = 'var(--accent-green)';
        } else {
            statusEl.textContent = result.error || '保存失败';
            statusEl.style.color = 'var(--accent-red)';
        }
    } catch (e) {
        statusEl.textContent = '保存失败';
        statusEl.style.color = 'var(--accent-red)';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadWeatherOptions().then(() => {
        prepareDashboardWindows();
        switchDashboardWindow('daily');
    });
});
