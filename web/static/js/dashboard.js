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

    loadCommunityData(community.id);
}

async function loadOverviewData() {
    loadAnnualSummary();
    loadParkPowerChart();
    loadEconomicChart();
    loadRenewableChart();
    loadCarbonChart();
    loadScenariosTable();
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

            document.getElementById('annual-cost').textContent =
                (summary.annual_objective / 10000).toFixed(2);
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

            const totalGeneration = summary.annual_renewable_use / 1000;
            document.getElementById('total-generation').textContent =
                totalGeneration.toFixed(1);
        }
    } catch (error) {
        console.error('加载年度汇总失败:', error);
    }
}

async function loadParkPowerChart() {
    const select = document.getElementById('scenario-select');
    const scenario = select ? select.value : 'S3';

    try {
        const res = await fetch(`/api/optimization/chart/hourly-power-data?scenario=${scenario}`);
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
    supplyDiv.style.height = '280px';
    supplyDiv.style.marginBottom = '10px';

    const demandDiv = document.createElement('div');
    demandDiv.style.height = '280px';
    demandDiv.style.marginBottom = '10px';

    const socDiv = document.createElement('div');
    socDiv.style.height = '250px';

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
        const select = document.getElementById('scenario-select');
        const scenario = select ? select.value : 'S3';
        const response = await fetch(`/api/optimization/energy-summary?scenario=${scenario}`);
        const result = await response.json();

        if (result.success) {
            const data = result.data;

            document.getElementById('total-generation').textContent =
                (data.total / 1000).toFixed(1);

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
        const response = await fetch('/api/calculate', { method: 'POST' });
        const result = await response.json();

        if (result.success && result.data.chart) {
            const chart = result.data.chart;
            const lastIndex = chart.solar.length - 1;

            document.getElementById('device-solar-power').textContent =
                (chart.solar[lastIndex] || 0).toFixed(1) + ' kW';
            document.getElementById('device-wind-power').textContent =
                (chart.wind[lastIndex] || 0).toFixed(1) + ' kW';
            document.getElementById('device-storage-power').textContent =
                (chart.storage_power[lastIndex] || 0).toFixed(1) + ' kW';
            document.getElementById('device-load-power').textContent =
                (chart.consumption[lastIndex] || 0).toFixed(1) + ' kW';
        }
    } catch (error) {
        console.error('加载设备状态失败:', error);
    }
}

async function loadCommunityData(communityId) {
    try {
        const response = await fetch(`/api/optimization/chart/community-power-data?scenario=S3&community=${communityId}`);
        const result = await response.json();

        if (result.success) {
            renderCommunityCharts(result);
        }
    } catch (error) {
        console.error('加载社区数据失败:', error);
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
