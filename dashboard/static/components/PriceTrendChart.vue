<!--
  价格趋势图组件
  任务：task-004 - Week 1: 创建价格趋势图组件
-->

<template>
  <div class="price-trend-chart">
    <div class="chart-header">
      <h3>{{ title }}</h3>
      <div class="chart-controls">
        <select v-model="selectedTimeRange" @change="updateChart">
          <option value="24h">24小时</option>
          <option value="7d">7天</option>
          <option value="30d">30天</option>
          <option value="90d">90天</option>
          <option value="all">全部</option>
        </select>
        <button @click="exportChart" class="btn-export">导出</button>
      </div>
    </div>

    <div ref="chartContainer" class="chart-container"></div>

    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <div v-if="error" class="error">
      <p>{{ error }}</p>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, watch } from 'vue';

export default {
  name: 'PriceTrendChart',
  props: {
    competitorId: {
      type: Number,
      required: true
    },
    productName: {
      type: String,
      default: null
    },
    title: {
      type: String,
      default: '价格趋势'
    },
    showPrediction: {
      type: Boolean,
      default: false
    }
  },
  setup(props) {
    const chartContainer = ref(null);
    const selectedTimeRange = ref('30d');
    const loading = ref(false);
    const error = ref(null);
    let plotlyChart = null;

    const fetchPriceData = async () => {
      loading.value = true;
      error.value = null;

      try {
        const params = new URLSearchParams({
          competitor_id: props.competitorId,
          interval: 'day'
        });

        if (props.productName) {
          params.append('product_name', props.productName);
        }

        // 计算时间范围
        const now = new Date();
        let startDate;
        switch (selectedTimeRange.value) {
          case '24h':
            startDate = new Date(now - 24 * 60 * 60 * 1000);
            break;
          case '7d':
            startDate = new Date(now - 7 * 24 * 60 * 60 * 1000);
            break;
          case '30d':
            startDate = new Date(now - 30 * 24 * 60 * 60 * 1000);
            break;
          case '90d':
            startDate = new Date(now - 90 * 24 * 60 * 60 * 1000);
            break;
          default:
            startDate = null;
        }

        if (startDate) {
          params.append('start_date', startDate.toISOString().split('T')[0]);
        }

        const response = await fetch(`/api/v1/prices/history?${params}`);
        const data = await response.json();

        if (data.success) {
          return data.data;
        } else {
          throw new Error(data.error?.message || 'Failed to fetch price data');
        }
      } catch (err) {
        error.value = err.message;
        console.error('Error fetching price data:', err);
        return null;
      } finally {
        loading.value = false;
      }
    };

    const renderChart = async () => {
      const data = await fetchPriceData();
      if (!data || !data.prices || data.prices.length === 0) {
        error.value = '暂无价格数据';
        return;
      }

      // 准备数据
      const prices = data.prices.reverse(); // 按时间升序
      const trace = {
        x: prices.map(p => p.timestamp),
        y: prices.map(p => p.price),
        type: 'scatter',
        mode: 'lines+markers',
        name: data.product_name || '价格',
        line: {
          color: '#3b82f6',
          width: 2
        },
        marker: {
          size: 6,
          color: '#3b82f6'
        }
      };

      const layout = {
        title: {
          text: '',
          font: { size: 16, color: '#f1f5f9' }
        },
        xaxis: {
          title: '时间',
          type: 'date',
          gridcolor: '#334155',
          tickfont: { color: '#94a3b8' }
        },
        yaxis: {
          title: '价格 (CNY)',
          tickprefix: '¥',
          gridcolor: '#334155',
          tickfont: { color: '#94a3b8' }
        },
        hovermode: 'x unified',
        plot_bgcolor: 'transparent',
        paper_bgcolor: 'transparent',
        margin: { l: 60, r: 20, t: 20, b: 60 },
        showlegend: true,
        legend: {
          orientation: 'h',
          y: -0.2,
          font: { color: '#94a3b8' }
        }
      };

      const config = {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ['lasso2d', 'select2d'],
        displaylogo: false
      };

      // 使用Plotly渲染图表
      if (window.Plotly) {
        plotlyChart = window.Plotly.newPlot(
          chartContainer.value,
          [trace],
          layout,
          config
        );
      } else {
        console.error('Plotly.js not loaded');
        error.value = '图表库未加载';
      }
    };

    const updateChart = () => {
      renderChart();
    };

    const exportChart = () => {
      if (plotlyChart && window.Plotly) {
        window.Plotly.downloadImage(chartContainer.value, {
          format: 'png',
          width: 1200,
          height: 600,
          filename: 'price-trend-chart'
        });
      }
    };

    onMounted(() => {
      renderChart();
    });

    watch([() => props.competitorId, () => props.productName], () => {
      renderChart();
    });

    return {
      chartContainer,
      selectedTimeRange,
      loading,
      error,
      updateChart,
      exportChart
    };
  }
};
</script>

<style scoped>
.price-trend-chart {
  background: #1e293b;
  border-radius: 8px;
  padding: 20px;
  border: 1px solid #334155;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.chart-header h3 {
  margin: 0;
  color: #f1f5f9;
  font-size: 18px;
}

.chart-controls {
  display: flex;
  gap: 10px;
}

select {
  background: #0f172a;
  color: #f1f5f9;
  border: 1px solid #334155;
  padding: 8px 12px;
  border-radius: 4px;
  cursor: pointer;
}

.btn-export {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-export:hover {
  background: #2563eb;
}

.chart-container {
  width: 100%;
  height: 400px;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 400px;
  color: #94a3b8;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #334155;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 400px;
  color: #ef4444;
}
</style>
