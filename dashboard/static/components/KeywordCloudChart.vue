<!--
  关键词云图组件
  任务：task-009 - Week 4: 创建评论可视化组件
-->

<template>
  <div class="keyword-cloud-chart">
    <div class="chart-header">
      <h3>{{ title }}</h3>
      <div class="chart-controls">
        <select v-model="selectedTimeRange" @change="updateChart">
          <option value="7d">7天</option>
          <option value="30d">30天</option>
          <option value="90d">90天</option>
          <option value="all">全部</option>
        </select>
        <input
          v-model.number="topKeywords"
          type="number"
          min="10"
          max="100"
          placeholder="关键词数量"
          class="keyword-count-input"
        >
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

    <div v-if="!loading && !error && keywords.length > 0" class="keyword-list">
      <h4>热门关键词</h4>
      <div class="keywords">
        <span
          v-for="(keyword, index) in keywords"
          :key="index"
          class="keyword-tag"
          :style="{ fontSize: getFontSize(keyword.count) + 'px' }"
        >
          {{ keyword.keyword }} ({{ keyword.count }})
        </span>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, watch } from 'vue';

export default {
  name: 'KeywordCloudChart',
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
      default: '关键词云'
    }
  },
  setup(props) {
    const chartContainer = ref(null);
    const selectedTimeRange = ref('30d');
    const topKeywords = ref(30);
    const loading = ref(false);
    const error = ref(null);
    const keywords = ref([]);
    let plotlyChart = null;

    const fetchKeywordData = async () => {
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
          keywords.value = result.data.top_keywords || [];
          renderChart(result.data.top_keywords || []);
        } else {
          error.value = result.error || '获取数据失败';
        }
      } catch (err) {
        error.value = '网络请求失败: ' + err.message;
      } finally {
        loading.value = false;
      }
    };

    const renderChart = (keywordData) => {
      if (!chartContainer.value || !window.Plotly) return;

      if (keywordData.length === 0) {
        error.value = '暂无关键词数据';
        return;
      }

      // 准备词云数据
      const words = keywordData.map(k => k.keyword);
      const counts = keywordData.map(k => k.count);

      // 计算词频归一化大小
      const maxCount = Math.max(...counts);
      const minCount = Math.min(...counts);
      const sizes = counts.map(c => {
        const normalized = (c - minCount) / (maxCount - minCount || 1);
        return 20 + normalized * 60; // 字体大小范围: 20-80
      });

      // 生成随机位置（模拟词云布局）
      const n = keywordData.length;
      const x = Array.from({ length: n }, () => Math.random());
      const y = Array.from({ length: n }, () => Math.random());

      const trace = {
        x: x,
        y: y,
        text: words,
        mode: 'text',
        textfont: {
          size: sizes,
          color: counts.map(c => {
            // 根据词频设置颜色
            const ratio = c / maxCount;
            if (ratio > 0.7) return '#EF4444'; // 红色 - 高频
            if (ratio > 0.4) return '#F59E0B'; // 橙色 - 中频
            return '#3B82F6'; // 蓝色 - 低频
          })
        },
        textposition: 'middle center',
        hoverinfo: 'text',
        hovertemplate: '%{text}<br>出现次数: %{customdata}<extra></extra>',
        customdata: counts
      };

      const layout = {
        showlegend: false,
        xaxis: {
          showgrid: false,
          showticklabels: false,
          zeroline: false
        },
        yaxis: {
          showgrid: false,
          showticklabels: false,
          zeroline: false
        },
        margin: { t: 20, b: 20, l: 20, r: 20 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        hovermode: 'closest'
      };

      const config = {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ['lasso2d', 'select2d', 'zoom2d', 'pan2d'],
        displaylogo: false
      };

      plotlyChart = window.Plotly.newPlot(
        chartContainer.value,
        [trace],
        layout,
        config
      );
    };

    const getFontSize = (count) => {
      if (keywords.value.length === 0) return 14;
      const maxCount = Math.max(...keywords.value.map(k => k.count));
      const minCount = Math.min(...keywords.value.map(k => k.count));
      const normalized = (count - minCount) / (maxCount - minCount || 1);
      return 12 + normalized * 16; // 字体大小范围: 12-28
    };

    const updateChart = () => {
      fetchKeywordData();
    };

    const exportChart = () => {
      if (!chartContainer.value || !window.Plotly) return;

      window.Plotly.downloadImage(chartContainer.value, {
        format: 'png',
        width: 800,
        height: 600,
        filename: `keyword-cloud-${props.competitorId}-${Date.now()}`
      });
    };

    onMounted(() => {
      fetchKeywordData();
    });

    watch(() => props.competitorId, () => {
      fetchKeywordData();
    });

    watch(() => props.productName, () => {
      fetchKeywordData();
    });

    watch(topKeywords, () => {
      fetchKeywordData();
    });

    return {
      chartContainer,
      selectedTimeRange,
      topKeywords,
      loading,
      error,
      keywords,
      updateChart,
      exportChart,
      getFontSize
    };
  }
};
</script>

<style scoped>
.keyword-cloud-chart {
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
  align-items: center;
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

.keyword-count-input {
  width: 80px;
  padding: 6px 12px;
  border: 1px solid #D1D5DB;
  border-radius: 4px;
  font-size: 14px;
  color: #374151;
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

.keyword-list {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #E5E7EB;
}

.keyword-list h4 {
  margin: 0 0 15px 0;
  font-size: 16px;
  font-weight: 600;
  color: #1F2937;
}

.keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.keyword-tag {
  display: inline-block;
  padding: 6px 12px;
  background: #F3F4F6;
  border-radius: 4px;
  color: #374151;
  font-weight: 500;
  transition: all 0.2s;
}

.keyword-tag:hover {
  background: #E5E7EB;
  transform: scale(1.05);
}
</style>
