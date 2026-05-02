<!--
  情感分析饼图组件
  任务：task-009 - Week 4: 创建评论可视化组件
-->

<template>
  <div class="sentiment-pie-chart">
    <div class="chart-header">
      <h3>{{ title }}</h3>
      <div class="chart-controls">
        <select v-model="selectedTimeRange" @change="updateChart">
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

    <div v-if="!loading && !error && sentimentData" class="chart-summary">
      <div class="summary-item positive">
        <span class="label">正面评论</span>
        <span class="value">{{ sentimentData.positive || 0 }}</span>
      </div>
      <div class="summary-item neutral">
        <span class="label">中性评论</span>
        <span class="value">{{ sentimentData.neutral || 0 }}</span>
      </div>
      <div class="summary-item negative">
        <span class="label">负面评论</span>
        <span class="value">{{ sentimentData.negative || 0 }}</span>
      </div>
      <div class="summary-item score">
        <span class="label">平均情感分数</span>
        <span class="value">{{ averageScore.toFixed(2) }}</span>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, watch, computed } from 'vue';

export default {
  name: 'SentimentPieChart',
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
      default: '情感分析'
    }
  },
  setup(props) {
    const chartContainer = ref(null);
    const selectedTimeRange = ref('30d');
    const loading = ref(false);
    const error = ref(null);
    const sentimentData = ref(null);
    let plotlyChart = null;

    const averageScore = computed(() => {
      if (!sentimentData.value) return 0;
      const total = (sentimentData.value.positive || 0) +
                    (sentimentData.value.neutral || 0) +
                    (sentimentData.value.negative || 0);
      if (total === 0) return 0;

      const score = ((sentimentData.value.positive || 0) -
                     (sentimentData.value.negative || 0)) / total;
      return score;
    });

    const fetchSentimentData = async () => {
      loading.value = true;
      error.value = null;

      try {
        const params = new URLSearchParams({
          competitor_id: props.competitorId,
          days: selectedTimeRange.value === 'all' ? 365 :
                parseInt(selectedTimeRange.value)
        });

        if (props.productName) {
          params.append('product_name', props.productName);
        }

        const response = await fetch(`/api/v1/reviews/sentiment?${params}`);
        const result = await response.json();

        if (result.success) {
          sentimentData.value = result.data.sentiment_distribution;
          renderChart(result.data);
        } else {
          error.value = result.error || '获取数据失败';
        }
      } catch (err) {
        error.value = '网络请求失败: ' + err.message;
      } finally {
        loading.value = false;
      }
    };

    const renderChart = (data) => {
      if (!chartContainer.value || !window.Plotly) return;

      const sentimentDist = data.sentiment_distribution || {};
      const values = [
        sentimentDist.positive || 0,
        sentimentDist.neutral || 0,
        sentimentDist.negative || 0
      ];

      const labels = ['正面', '中性', '负面'];
      const colors = ['#10B981', '#6B7280', '#EF4444'];

      const trace = {
        values: values,
        labels: labels,
        type: 'pie',
        marker: {
          colors: colors,
          line: {
            color: '#FFFFFF',
            width: 2
          }
        },
        textinfo: 'label+percent',
        textposition: 'outside',
        hoverinfo: 'label+value+percent',
        hole: 0.4
      };

      const layout = {
        showlegend: true,
        legend: {
          orientation: 'h',
          y: -0.1
        },
        margin: { t: 20, b: 60, l: 20, r: 20 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        annotations: [{
          text: '情感分布',
          showarrow: false,
          font: {
            size: 16,
            color: '#374151'
          }
        }]
      };

      const config = {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ['lasso2d', 'select2d'],
        displaylogo: false
      };

      plotlyChart = window.Plotly.newPlot(
        chartContainer.value,
        [trace],
        layout,
        config
      );
    };

    const updateChart = () => {
      fetchSentimentData();
    };

    const exportChart = () => {
      if (!chartContainer.value || !window.Plotly) return;

      window.Plotly.downloadImage(chartContainer.value, {
        format: 'png',
        width: 800,
        height: 600,
        filename: `sentiment-analysis-${props.competitorId}-${Date.now()}`
      });
    };

    onMounted(() => {
      fetchSentimentData();
    });

    watch(() => props.competitorId, () => {
      fetchSentimentData();
    });

    watch(() => props.productName, () => {
      fetchSentimentData();
    });

    return {
      chartContainer,
      selectedTimeRange,
      loading,
      error,
      sentimentData,
      averageScore,
      updateChart,
      exportChart
    };
  }
};
</script>

<style scoped>
.sentiment-pie-chart {
  background: #FFFFFF;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.chart-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1F2937;
}

.chart-controls {
  display: flex;
  gap: 10px;
}

select {
  padding: 6px 12px;
  border: 1px solid #D1D5DB;
  border-radius: 4px;
  font-size: 14px;
  color: #374151;
  background: #FFFFFF;
  cursor: pointer;
}

select:hover {
  border-color: #9CA3AF;
}

.btn-export {
  padding: 6px 12px;
  background: #3B82F6;
  color: #FFFFFF;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-export:hover {
  background: #2563EB;
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
  color: #6B7280;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #E5E7EB;
  border-top-color: #3B82F6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 400px;
  color: #EF4444;
}

.chart-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 15px;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #E5E7EB;
}

.summary-item {
  text-align: center;
  padding: 10px;
  background: #F9FAFB;
  border-radius: 6px;
}

.summary-item .label {
  display: block;
  font-size: 12px;
  color: #6B7280;
  margin-bottom: 5px;
}

.summary-item .value {
  display: block;
  font-size: 24px;
  font-weight: 600;
  color: #1F2937;
}

.summary-item.positive .value {
  color: #10B981;
}

.summary-item.neutral .value {
  color: #6B7280;
}

.summary-item.negative .value {
  color: #EF4444;
}

.summary-item.score .value {
  color: #3B82F6;
}
</style>
