/**
 * 竞品详情 v3.0 — 完整版：真实矩阵 + 情感趋势 + diff可视化 + 错误隔离 + WS实时推送
 */
const { createApp, ref, reactive, computed, onMounted, onUnmounted, nextTick } = Vue;

const CC = {
    cyan: '#00fff0', magenta: '#ff2a6d', amber: '#f0e000', green: '#05ffa1',
    purple: '#b537f2', grid: 'rgba(26,26,62,.6)', tick: '#6a6a8e',
};

const BASE_OPTS = {
    responsive: true, maintainAspectRatio: false,
    animation: { duration: 600 },
    plugins: {
        legend: { labels: { color: CC.tick, font: { family: 'JetBrains Mono', size: 11 }, boxWidth: 12, padding: 12 } },
        tooltip: { backgroundColor: 'rgba(13,13,24,.95)', titleColor: CC.cyan, bodyColor: '#e0e0ff', borderColor: CC.cyan, borderWidth: 1, padding: 10 }
    },
    scales: {
        x: { grid: { color: CC.grid }, ticks: { color: CC.tick, font: { family: 'JetBrains Mono', size: 10 } } },
        y: { grid: { color: CC.grid }, ticks: { color: CC.tick, font: { family: 'JetBrains Mono', size: 10 } } }
    }
};

function mergeOpts(base, override) {
    const out = { ...base };
    for (const k of Object.keys(override)) {
        if (override[k] && typeof override[k] === 'object' && !Array.isArray(override[k]))
            out[k] = mergeOpts(out[k] || {}, override[k]);
        else out[k] = override[k];
    }
    return out;
}

function simpleDiff(oldText, newText) {
    if (!oldText && !newText) return [];
    if (!oldText) return [{ type: 'added', text: String(newText) }];
    if (!newText) return [{ type: 'removed', text: String(oldText) }];
    const a = String(oldText), b = String(newText);
    const result = [];
    const maxLen = Math.max(a.length, b.length);
    let i = 0;
    while (i < maxLen && a[i] === b[i]) i++;
    const prefix = a.slice(0, i);
    if (prefix) result.push({ type: 'same', text: prefix });

    let jA = a.length - 1, jB = b.length - 1;
    while (jA >= i && jB >= i && a[jA] === b[jB]) { jA--; jB--; }
    if (i <= jA) result.push({ type: 'removed', text: a.slice(i, jA + 1) });
    if (i <= jB) result.push({ type: 'added', text: b.slice(i, jB + 1) });
    if (jA + 1 < a.length) result.push({ type: 'same', text: a.slice(jA + 1) });
    return result;
}

createApp({
    setup() {
        const tabs = [
            { key: 'overview', label: '概览' },
            { key: 'price', label: '价格分析' },
            { key: 'reviews', label: '评论分析' },
            { key: 'analytics', label: '深度分析' },
        ];
        const currentTab = ref('overview');
        const loading = ref(true);
        const error = ref(null);
        const competitorId = ref(1);
        const competitorName = ref('');
        const competitors = ref([]);
        const timeRange = ref('30');

        // Data
        const priceData = ref([]);
        const reviews = ref([]);
        const sentimentDist = ref({ positive: 0, neutral: 0, negative: 0 });
        const sentimentTrend = ref([]);
        const changes = ref([]);
        const reports = ref([]);
        const keywords = ref([]);
        const matrixData = ref([]);
        const postureScores = ref([]);
        const wsConnected = ref(false);
        const loadedTabs = ref(new Set(['overview'])); // tracks which tabs have data loaded
        const dataFreshness = ref({ text: '加载中...', stale: false, lastUpdate: null });
        const dataVersion = ref(0); // increments on each data refresh for animations
        let freshnessTimer = null;

        // Posture radar: which competitors to show
        const postureVisible = ref([]);
        const postureColors = { 1: CC.cyan, 2: CC.magenta, 3: CC.amber, 4: CC.green, 5: CC.purple };

        // Per-section error isolation
        const sectionStatus = reactive({
            matrix: { error: null },
            priceChart: { error: null },
            sentiment: { error: null },
            changes: { error: null },
            reviews: { error: null },
            keywords: { error: null },
            comparison: { error: null },
        });

        // UI state
        const reviewFilter = ref('all');
        const predictionDays = ref(7);
        const predictionLoading = ref(false);
        const autoRefresh = ref(true);
        const refreshInterval = ref(30);
        let refreshTimer = null;

        const notification = ref({ show: false, type: 'info', message: '' });
        const showToast = (msg, type = 'info') => { notification.value = { show: true, type, message: msg }; setTimeout(() => notification.value.show = false, 3000); };

        // === Helpers ===
        const formatNumber = (n, d = 0) => (!n && n !== 0) ? '0' : Number(n).toFixed(d);
        const formatTimestamp = ts => { if (!ts) return ''; try { return new Date(ts).toLocaleString('zh-CN', { month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit' }); } catch { return ts; } };
        const trendLabel = t => ({ rising:'上涨', falling:'下跌', stable:'持平' }[t] || t);
        const getSentimentLabel = s => ({ positive:'正面', neutral:'中性', negative:'负面' }[s] || s);

        // === Computed: competitor ===
        const competitor = computed(() => competitors.value.find(x => x.id === competitorId.value));

        // === Computed: metrics (card values) ===
        const metrics = computed(() => {
            const prices = priceData.value;
            const latestPrice = prices.length ? prices[prices.length - 1].price : 0;
            const firstPrice = prices.length ? prices[0].price : 0;
            const priceChange = firstPrice ? ((latestPrice - firstPrice) / firstPrice * 100) : 0;
            const anomalyCount = changes.value.filter(x => x.severity === 'P0' || x.severity === 'P1').length;
            const trendDirection = priceChange > 2 ? 'rising' : priceChange < -2 ? 'falling' : 'stable';
            const avgSentiment = reviews.value.length
                ? reviews.value.reduce((s, r) => s + (r.sentiment_score || 0), 0) / reviews.value.length
                : 0;
            const totalReviews = reviews.value.length;
            return { latestPrice, priceChange, anomalyCount, trendDirection, avgSentiment, totalReviews };
        });

        const trendArrow = computed(() => {
            const d = metrics.value.trendDirection;
            return d === 'rising' ? '↗' : d === 'falling' ? '↘' : '→';
        });
        const trendText = computed(() => trendLabel(metrics.value.trendDirection));

        // === Computed: competitorSummaries (from real matrix data) ===
        const competitorSummaries = computed(() => {
            if (matrixData.value.length) {
                return matrixData.value.map(m => ({
                    id: m.id, name: m.name,
                    priceIndex: m.price_index || 0,
                    trend: (m.growth || 0) > 3 ? 'rising' : (m.growth || 0) < -3 ? 'falling' : 'stable',
                    changePct: m.growth || 0,
                    anomalyCount: m.anomaly_count || 0,
                    rating: (m.user_rating || 0).toFixed(1),
                    marketShare: (m.market_share || 0) / 100,
                    snapshots: m.snapshot_count || 0,
                }));
            }
            return competitors.value.map(c => {
                const m = c.metrics || {};
                return {
                    id: c.id, name: c.name,
                    priceIndex: m.price_index || 0,
                    trend: (m.growth || 0) > 3 ? 'rising' : (m.growth || 0) < -3 ? 'falling' : 'stable',
                    changePct: m.growth || 0,
                    anomalyCount: 0,
                    rating: (m.user_rating || 0).toFixed(1),
                    marketShare: (m.market_share || 0) / 100,
                    snapshots: 0,
                };
            });
        });

        // === Computed: diffTimeline ===
        const diffTimeline = computed(() => changes.value.map(c => {
            const changeType = c.change_type || '';
            const isUp = changeType.includes('up') || changeType === 'price_up';
            const isDown = changeType.includes('down') || changeType === 'price_down';
            return {
                timestamp: c.detected_at || '',
                hash: String(c.id || ''),
                has_change: true,
                diffs: simpleDiff(c.old_value || '', c.new_value || ''),
                diff_count: 1,
                field_name: c.field_name || c.change_type,
                change_type: changeType,
                old_value: c.old_value || '',
                new_value: c.new_value || '',
                dotClass: isUp ? 'up' : isDown ? 'down' : 'no-change',
            };
        }));

        const anomalyList = computed(() => {
            const prices = priceData.value.map(d => d.price);
            if (prices.length < 5) return [];
            const mean = prices.reduce((a, b) => a + b, 0) / prices.length;
            const std = Math.sqrt(prices.reduce((s, v) => s + (v - mean) ** 2, 0) / prices.length);
            if (std === 0) return [];
            return priceData.value
                .map((d, i) => ({ value: d.price, z_score: Math.abs((d.price - mean) / std), timestamp: d.recorded_at }))
                .filter(a => a.z_score > 1.5)
                .slice(0, 10);
        });

        const correlationMatrix = computed(() => []);

        const filteredReviews = computed(() => {
            if (reviewFilter.value === 'all') return reviews.value;
            if (reviewFilter.value === 'neutral') return reviews.value.filter(r => (r.sentiment_score || 0) > -0.3 && (r.sentiment_score || 0) < 0.3);
            return reviews.value.filter(r => reviewFilter.value === 'positive' ? (r.sentiment_score || 0) >= 0.3 : (r.sentiment_score || 0) <= -0.3);
        });

        // === Chart instances ===
        const charts = {};
        const destroyChart = id => { if (charts[id]) { charts[id].destroy(); delete charts[id]; } };
        const mkChart = (id, type, data, opts = {}) => {
            const c = document.getElementById(id);
            if (!c) return null;
            destroyChart(id);
            charts[id] = new Chart(c, { type, data, options: mergeOpts(BASE_OPTS, opts) });
            return charts[id];
        };

        // === API fetchers (with per-section error isolation) ===
        const fetchWithSection = async (url, setter, sectionKey, transform) => {
            try {
                const r = await fetch(url);
                const j = await r.json();
                if (j.success && j.data != null) {
                    const val = transform ? transform(j.data) : j.data;
                    setter(val);
                    sectionStatus[sectionKey].error = null;
                }
            } catch (e) {
                sectionStatus[sectionKey].error = '加载失败';
                console.error(`${sectionKey}:`, e);
            }
        };

        const fetchCompetitors = () => fetchWithSection('/api/competitors', v => { competitors.value = v; }, 'matrix', null);
        const fetchMatrix = () => fetchWithSection('/api/competitors/matrix', v => { matrixData.value = v; }, 'matrix', null);

        const fetchPriceHistory = async () => {
            try {
                const r = await fetch(`/api/v1/prices/history?competitor_id=${competitorId.value}&limit=200`);
                const j = await r.json();
                if (j.success && j.data) {
                    priceData.value = (j.data && j.data.prices) ? j.data.prices.sort((a, b) => new Date(a.recorded_at) - new Date(b.recorded_at)) : [];
                    sectionStatus.priceChart.error = null;
                }
            } catch (e) { sectionStatus.priceChart.error = '价格数据加载失败'; console.error('价格:', e); }
        };

        const fetchReviews = async () => {
            try {
                const r = await fetch(`/api/v1/reviews?competitor_id=${competitorId.value}&limit=100`);
                const j = await r.json();
                if (j.success && Array.isArray(j.data)) {
                    reviews.value = j.data;
                    sectionStatus.reviews.error = null;
                }
            } catch (e) { sectionStatus.reviews.error = '评论数据加载失败'; console.error('评论:', e); }
        };

        const fetchSentiment = async () => {
            try {
                const r = await fetch(`/api/v1/reviews/sentiment?competitor_id=${competitorId.value}&days=${timeRange.value}`);
                const j = await r.json();
                if (j.success && j.data) {
                    sentimentDist.value = j.data.sentiment_distribution || { positive: 0, neutral: 0, negative: 0 };
                    sectionStatus.sentiment.error = null;
                }
            } catch (e) { sectionStatus.sentiment.error = '情感数据加载失败'; console.error('情感:', e); }
        };

        const fetchSentimentTrend = async () => {
            try {
                const r = await fetch(`/api/reviews/sentiment-trend?competitor_id=${competitorId.value}&days=${timeRange.value}`);
                const j = await r.json();
                if (j.success && Array.isArray(j.data)) {
                    sentimentTrend.value = j.data;
                    sectionStatus.sentiment.error = null;
                }
            } catch (e) { console.error('情感趋势:', e); }
        };

        const fetchChanges = async () => {
            try {
                const r = await fetch(`/api/diff/changes?limit=50`);
                const j = await r.json();
                if (j.success && Array.isArray(j.data)) {
                    changes.value = j.data.filter(c => c.competitor_id === competitorId.value);
                    sectionStatus.changes.error = null;
                }
            } catch (e) { sectionStatus.changes.error = '变更加载失败'; console.error('变更:', e); }
        };

        const fetchReports = async () => {
            try {
                const r = await fetch(`/api/reports?competitor_id=${competitorId.value}&limit=5`);
                const j = await r.json();
                if (j.success && Array.isArray(j.data)) reports.value = j.data;
            } catch (e) { console.error('报告:', e); }
        };

        const fetchKeywords = async () => {
            try {
                const r = await fetch(`/api/product/${competitorId.value}/keywords`);
                const j = await r.json();
                if (j.success && j.data && Array.isArray(j.data.keywords)) {
                    keywords.value = j.data.keywords;
                    sectionStatus.keywords.error = null;
                }
            } catch (e) { sectionStatus.keywords.error = '关键词加载失败'; console.error('关键词:', e); }
        };

        const fetchPosture = async () => {
            try {
                const r = await fetch('/api/competitors/posture');
                const j = await r.json();
                if (j.success && Array.isArray(j.data)) {
                    postureScores.value = j.data;
                    postureVisible.value = j.data.map(p => p.competitor_id);
                    sectionStatus.matrix.error = null;
                }
            } catch (e) { console.error('态势评分:', e); }
        };

        // === Chart renders ===
        const renderPriceTrendChart = (canvasId = 'priceTrendChart') => {
            const arr = priceData.value;
            if (!arr.length) return;
            const labels = arr.map(d => formatTimestamp(d.recorded_at));
            mkChart(canvasId, 'line', {
                labels,
                datasets: [{
                    label: '价格 (CNY)', data: arr.map(d => d.price),
                    borderColor: CC.cyan, backgroundColor: 'rgba(0,255,240,.08)',
                    borderWidth: 2, pointRadius: 3, pointBackgroundColor: CC.cyan, fill: true, tension: 0.3
                }]
            });
        };

        const renderSentimentTrendChart = () => {
            const arr = sentimentTrend.value;
            if (!arr.length) return;
            const labels = arr.map(d => d.day);
            mkChart('sentimentTrendChart', 'line', {
                labels,
                datasets: [
                    {
                        label: '情感均值', data: arr.map(d => d.avg_sentiment),
                        borderColor: CC.green, backgroundColor: 'rgba(5,255,161,.06)',
                        borderWidth: 2, pointRadius: 4, pointBackgroundColor: CC.green, fill: true, tension: 0.3,
                    },
                    {
                        label: '评论数', data: arr.map(d => d.review_count), yAxisID: 'y1',
                        borderColor: CC.cyan, backgroundColor: 'rgba(0,255,240,.04)',
                        borderWidth: 1, borderDash: [3, 3], pointRadius: 2, fill: false, tension: 0.3,
                    }
                ]
            }, {
                scales: {
                    y: { position: 'left', title: { display: true, text: '情感分数', color: CC.green } },
                    y1: { position: 'right', title: { display: true, text: '评论数', color: CC.cyan }, grid: { drawOnChartArea: false } },
                }
            });
        };

        const renderSentimentPie = (canvasId = 'sentimentPieChart') => {
            const d = sentimentDist.value;
            const vals = [d.positive || 0, d.neutral || 0, d.negative || 0];
            if (vals.every(x => x === 0)) return;
            mkChart(canvasId, 'doughnut', {
                labels: ['正面', '中性', '负面'],
                datasets: [{ data: vals, backgroundColor: ['rgba(5,255,161,.6)', 'rgba(106,106,142,.6)', 'rgba(255,42,109,.6)'], borderColor: [CC.green, CC.tick, CC.magenta], borderWidth: 1 }]
            }, { cutout: '45%', plugins: { legend: { position: 'bottom' } }, scales: {} });
        };

        const renderSentimentBar = (canvasId = 'sentimentDistributionChart') => {
            const d = sentimentDist.value;
            const vals = [d.positive || 0, d.neutral || 0, d.negative || 0];
            if (vals.every(x => x === 0)) return;
            mkChart(canvasId, 'bar', {
                labels: ['正面', '中性', '负面'],
                datasets: [{ label: '评论数', data: [d.positive || 0, d.neutral || 0, d.negative || 0], backgroundColor: ['rgba(5,255,161,.5)', 'rgba(106,106,142,.5)', 'rgba(255,42,109,.5)'], borderColor: [CC.green, CC.tick, CC.magenta], borderWidth: 1 }]
            });
        };

        const renderKeywordsChart = (canvasId = 'topKeywordsChart') => {
            const kws = keywords.value;
            if (!kws.length) return;
            const top = kws.slice(0, 12);
            mkChart(canvasId, 'bar', {
                labels: top.map(k => k.word),
                datasets: [{ label: '热度', data: top.map(k => k.count), backgroundColor: 'rgba(0,255,240,.5)', borderColor: CC.cyan, borderWidth: 1 }]
            }, { indexAxis: 'y' });
        };

        const renderMonitoringFreq = () => {
            const arr = priceData.value;
            if (!arr.length) return;
            const days = {};
            arr.forEach(d => {
                const day = formatTimestamp(d.recorded_at).split(' ')[0] || '';
                days[day] = (days[day] || 0) + 1;
            });
            const keys = Object.keys(days).slice(-14);
            mkChart('monitoringFreqChart', 'bar', {
                labels: keys,
                datasets: [{ label: '采集频率', data: keys.map(k => days[k]), backgroundColor: 'rgba(181,55,242,.4)', borderColor: CC.purple, borderWidth: 1 }]
            });
        };

        const renderPostureRadar = () => {
            const scores = postureScores.value;
            if (!scores.length) return;
            const dims = ['攻击性', '稳定度', '创新力', '客户口碑', '威胁等级'];
            const keys = ['aggressiveness', 'stability', 'innovation', 'sentiment', 'threat'];
            const visible = scores.filter(p => postureVisible.value.includes(p.competitor_id));
            const datasets = visible.map(p => ({
                label: p.name,
                data: keys.map(k => p.scores[k].value),
                borderColor: postureColors[p.competitor_id] || CC.cyan,
                backgroundColor: (postureColors[p.competitor_id] || CC.cyan) + '20',
                borderWidth: 2, pointRadius: 4, pointBackgroundColor: postureColors[p.competitor_id] || CC.cyan,
            }));
            mkChart('postureRadarChart', 'radar', {
                labels: dims,
                datasets,
            }, {
                scales: {
                    r: { min: 0, max: 100, ticks: { stepSize: 20, color: CC.tick, backdropColor: 'transparent', font: { size: 9 } }, grid: { color: CC.grid }, pointLabels: { color: CC.tick, font: { size: 11 } } }
                },
                plugins: { legend: { position: 'bottom' } },
            });
        };

        const renderTrendChart = () => {
            const arr = priceData.value;
            if (!arr.length) return;
            const labels = arr.map(d => formatTimestamp(d.recorded_at));
            const prices = arr.map(d => d.price);
            const mean = prices.reduce((a, b) => a + b, 0) / prices.length;
            mkChart('trendChartCanvas', 'line', {
                labels,
                datasets: [
                    { label: '价格', data: prices, borderColor: CC.cyan, borderWidth: 2, pointRadius: 2, fill: false, tension: 0.3 },
                    { label: '上界', data: prices.map(() => mean * 1.1), borderColor: CC.magenta, borderWidth: 1, borderDash: [4, 4], pointRadius: 0, fill: false },
                    { label: '下界', data: prices.map(() => mean * 0.9), borderColor: CC.magenta, borderWidth: 1, borderDash: [4, 4], pointRadius: 0, fill: false },
                ]
            });
            const el = document.getElementById('trendSummary');
            if (el) el.textContent = `均值 ${formatNumber(mean, 1)} · 异常 ${anomalyList.value.length} 项`;
        };

        const renderComparisonChart = () => {
            const allComps = competitors.value;
            if (!allComps.length) return;
            const colors = [CC.cyan, CC.magenta, CC.amber, CC.green, CC.purple];
            const datasets = allComps.slice(0, 5).map((comp, i) => ({
                label: comp.name,
                data: [(comp.metrics?.price_index) || (comp.price_index) || 0],
                backgroundColor: colors[i] + '80', borderColor: colors[i], borderWidth: 1,
            }));
            mkChart('priceComparisonChart', 'bar', { labels: ['价格指数'], datasets });
        };

        // === Tab renders ===
        const renderOverview = () => {
            nextTick(() => {
                renderPriceTrendChart('priceTrendChart');
                renderSentimentPie('sentimentPieChart');
                renderSentimentTrendChart();
                renderMonitoringFreq();
                renderPostureRadar();
            });
        };
        const renderPriceTab = () => {
            nextTick(() => {
                renderPriceTrendChart('priceHistoryChart');
                renderComparisonChart();
            });
        };
        const renderReviewsTab = () => {
            nextTick(() => {
                renderSentimentBar('sentimentDistributionChart');
                if (keywords.value.length) renderKeywordsChart('topKeywordsChart');
            });
        };
        const renderAnalyticsTab = () => {
            nextTick(() => { renderTrendChart(); });
        };

        // === Actions ===
        const switchTab = async (tab) => {
            currentTab.value = tab;
            // Sync tab to URL
            const u = new URL(window.location);
            u.searchParams.set('tab', tab);
            window.history.replaceState({}, '', u);
            // Lazy-load tab data
            if (tab === 'reviews' && !loadedTabs.value.has('reviews')) {
                await fetchReviews();
                loadedTabs.value.add('reviews');
            } else if (tab === 'analytics' && !loadedTabs.value.has('analytics')) {
                await fetchChanges();
                loadedTabs.value.add('analytics');
            }
            await nextTick();
            await nextTick();
            if (tab === 'overview') renderOverview();
            else if (tab === 'price') renderPriceTab();
            else if (tab === 'reviews') renderReviewsTab();
            else if (tab === 'analytics') renderAnalyticsTab();
        };

        const selectCompetitor = (id) => {
            competitorId.value = id;
            const u = new URL(window.location);
            u.searchParams.set('competitor_id', id);
            window.history.replaceState({}, '', u);
            loadData();
        };
        const onCompetitorChange = () => selectCompetitor(competitorId.value);

        const setTimeRange = (r) => {
            timeRange.value = r;
            fetchSentiment();
            fetchSentimentTrend();
            loadData();
        };

        // Auto-refresh
        const toggleAutoRefresh = () => {
            autoRefresh.value = !autoRefresh.value;
            autoRefresh.value ? startAutoRefresh() : stopAutoRefresh();
        };
        const startAutoRefresh = () => {
            stopAutoRefresh();
            refreshTimer = setInterval(async () => {
                await Promise.all([fetchPriceHistory(), fetchReviews(), fetchSentiment(), fetchChanges()]);
                if (currentTab.value === 'overview') renderOverview();
                else if (currentTab.value === 'price') renderPriceTab();
                else if (currentTab.value === 'reviews') renderReviewsTab();
                else if (currentTab.value === 'analytics') renderAnalyticsTab();
            }, refreshInterval.value * 1000);
        };
        const stopAutoRefresh = () => { if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null; } };

        // Price prediction
        const predictPrice = async () => {
            predictionLoading.value = true;
            try {
                const arr = priceData.value;
                if (!arr.length) { showToast('数据不足，无法预测', 'error'); return; }
                const prices = arr.map(d => d.price);
                const lastPrice = prices[prices.length - 1];
                const recentChanges = prices.slice(-5);
                const avgChange = recentChanges.length > 1
                    ? recentChanges.reduce((s, v, i, a) => i > 0 ? s + (v - a[i-1]) : s, 0) / Math.max(1, recentChanges.length - 1)
                    : 0;
                const labels = [], predPrices = [];
                const histLabels = arr.map(d => formatTimestamp(d.recorded_at));
                for (let i = 1; i <= predictionDays.value; i++) {
                    const d = new Date(); d.setDate(d.getDate() + i);
                    labels.push(d.toLocaleString('zh-CN', { month:'2-digit', day:'2-digit' }));
                    predPrices.push(lastPrice + avgChange * i);
                }
                mkChart('pricePredictionChart', 'line', {
                    labels: [...histLabels.slice(-14), ...labels],
                    datasets: [
                        { label: '历史价格', data: [...prices.slice(-14), ...Array(predictionDays.value).fill(null)], borderColor: CC.cyan, borderWidth: 2, pointRadius: 2, fill: false, tension: 0.3 },
                        { label: '预测价格', data: [...Array(Math.min(14, prices.length)).fill(null), ...predPrices], borderColor: CC.amber, borderWidth: 2, borderDash: [5, 5], pointRadius: 3, pointBackgroundColor: CC.amber, fill: false, tension: 0.3 },
                    ]
                });
                showToast(`预测完成：${predictionDays.value}天后预估 ${formatNumber(predPrices[predPrices.length-1], 1)} CNY`, 'info');
            } catch (e) { showToast('预测失败', 'error'); }
            finally { predictionLoading.value = false; }
        };

        const corrColor = v => {
            if (v > 0.7) return 'rgba(5,255,161,.7)';
            if (v > 0.4) return 'rgba(5,255,161,.35)';
            if (v > 0) return 'rgba(5,255,161,.15)';
            if (v > -0.4) return 'rgba(255,42,109,.15)';
            return 'rgba(255,42,109,.5)';
        };

        // Freshness
        const updateFreshness = () => {
            if (!dataFreshness.value.lastUpdate) return;
            const diff = Math.floor((Date.now() - dataFreshness.value.lastUpdate) / 1000);
            if (diff < 60) {
                dataFreshness.value = { text: `${diff}秒前更新`, stale: false, lastUpdate: dataFreshness.value.lastUpdate };
            } else if (diff < 3600) {
                dataFreshness.value = { text: `${Math.floor(diff/60)}分钟前更新`, stale: diff > 300, lastUpdate: dataFreshness.value.lastUpdate };
            } else {
                dataFreshness.value = { text: `${Math.floor(diff/3600)}小时前更新`, stale: true, lastUpdate: dataFreshness.value.lastUpdate };
            }
        };

        // === Main load ===
        const loadData = async () => {
            loading.value = true;
            error.value = null;
            Object.keys(sectionStatus).forEach(k => { sectionStatus[k].error = null; });
            try {
                const u = new URLSearchParams(window.location.search);
                competitorId.value = parseInt(u.get('competitor_id')) || 1;
                // Restore tab from URL
                const urlTab = u.get('tab');
                if (urlTab && tabs.some(t => t.key === urlTab)) currentTab.value = urlTab;

                await Promise.all([fetchCompetitors(), fetchMatrix()]);
                const c = competitors.value.find(x => x.id === competitorId.value);
                if (c) competitorName.value = c.name;

                // Core data (all tabs need these)
                const fetches = [
                    fetchPriceHistory(), fetchSentiment(),
                    fetchSentimentTrend(), fetchChanges(), fetchKeywords(), fetchPosture()
                ];
                // Lazy: only fetch reviews if starting on reviews tab
                if (currentTab.value === 'reviews') {
                    fetches.push(fetchReviews());
                    loadedTabs.value.add('reviews');
                }
                await Promise.all(fetches);

                // Track freshness
                dataFreshness.value = { text: '刚刚更新', stale: false, lastUpdate: Date.now() };
                dataVersion.value++;
                if (freshnessTimer) clearInterval(freshnessTimer);
                freshnessTimer = setInterval(updateFreshness, 5000);
            } catch (e) {
                error.value = e.message;
            } finally {
                loading.value = false;
                await nextTick();
                await nextTick();
                if (currentTab.value === 'overview') renderOverview();
                else if (currentTab.value === 'price') renderPriceTab();
                else if (currentTab.value === 'reviews') renderReviewsTab();
                else if (currentTab.value === 'analytics') renderAnalyticsTab();
            }
        };

        // === WebSocket with real data consumption ===
        let socket = null;
        const connectWS = () => {
            try {
                const p = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                socket = new WebSocket(`${p}//${window.location.host}/ws/monitoring`);
                socket.onopen = () => {
                    wsConnected.value = true;
                    if (competitorId.value) socket.send(JSON.stringify({ action: 'subscribe', competitor_id: competitorId.value }));
                };
                socket.onmessage = (event) => {
                    try {
                        const msg = JSON.parse(event.data);
                        if (msg.type === 'competitor_update' && msg.competitor_id === competitorId.value && msg.data) {
                            // Merge real-time data
                            const d = msg.data;
                            if (d.latest_price && d.latest_price.price != null) {
                                const existing = priceData.value.find(p => p.recorded_at === d.latest_price.recorded_at);
                                if (!existing) {
                                    priceData.value = [...priceData.value.slice(-199), {
                                        price: d.latest_price.price,
                                        recorded_at: d.latest_price.recorded_at,
                                        product_name: d.latest_price.product_name || '',
                                    }];
                                    if (currentTab.value === 'overview' || currentTab.value === 'price') renderOverview();
                                }
                            }
                            if (d.latest_reviews && d.latest_reviews.length) {
                                const existingIds = new Set(reviews.value.map(r => r.id));
                                const newReviews = d.latest_reviews.filter(r => !existingIds.has(r.id));
                                if (newReviews.length) {
                                    reviews.value = [...newReviews, ...reviews.value].slice(0, 100);
                                }
                            }
                            if (d.sentiment_stats) {
                                sentimentDist.value = {
                                    positive: d.sentiment_stats.positive || 0,
                                    neutral: d.sentiment_stats.neutral || 0,
                                    negative: d.sentiment_stats.negative || 0,
                                };
                            }
                        }
                    } catch (e) { /* ignore malformed messages */ }
                };
                socket.onclose = () => { wsConnected.value = false; setTimeout(connectWS, 5000); };
                socket.onerror = () => { wsConnected.value = false; };
            } catch { wsConnected.value = false; }
        };

        onMounted(async () => {
            await loadData();
            connectWS();
            if (autoRefresh.value) startAutoRefresh();
        });
        onUnmounted(() => {
            if (socket) socket.close();
            stopAutoRefresh();
            if (freshnessTimer) clearInterval(freshnessTimer);
            Object.keys(charts).forEach(destroyChart);
        });

        return {
            tabs, currentTab, loading, error, competitorId, competitorName, competitors, timeRange,
            metrics, competitor, priceData, reviews, sentimentDist, sentimentTrend, changes, reports, keywords, matrixData,
            reviewFilter, filteredReviews, predictionDays, predictionLoading,
            autoRefresh, refreshInterval, wsConnected, notification,
            competitorSummaries, diffTimeline, anomalyList, correlationMatrix,
            trendArrow, trendText, sectionStatus,
            postureScores, postureVisible, postureColors,
            dataFreshness, dataVersion,
            formatNumber, formatTimestamp, trendLabel, getSentimentLabel, corrColor,
            switchTab, selectCompetitor, onCompetitorChange, setTimeRange, toggleAutoRefresh, predictPrice, loadData,
            renderPostureRadar,
        };
    }
}).mount('#app');
