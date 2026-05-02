<!--
  多维度筛选面板组件
  任务：task-012 - Week 7: 实现多维度下钻分析
-->

<template>
  <div class="filter-panel">
    <div class="panel-header">
      <h3>多维度筛选</h3>
      <button @click="resetFilters" class="btn-reset">重置</button>
    </div>

    <div class="filter-section">
      <!-- 时间范围筛选 -->
      <div class="filter-group">
        <label class="filter-label">时间范围</label>
        <div class="date-range-picker">
          <input
            v-model="filters.startDate"
            type="date"
            class="date-input"
          >
          <span class="date-separator">至</span>
          <input
            v-model="filters.endDate"
            type="date"
            class="date-input"
          >
        </div>
        <div class="quick-select">
          <button
            v-for="range in quickRanges"
            :key="range.value"
            @click="setQuickRange(range.value)"
            :class="['quick-btn', { active: selectedQuickRange === range.value }]"
          >
            {{ range.label }}
          </button>
        </div>
      </div>

      <!-- 竞品筛选 -->
      <div class="filter-group">
        <label class="filter-label">竞品选择</label>
        <select v-model="filters.competitorId" @change="onCompetitorChange" class="filter-select">
          <option :value="null">全部竞品</option>
          <option
            v-for="competitor in competitors"
            :key="competitor.id"
            :value="competitor.id"
          >
            {{ competitor.name }}
          </option>
        </select>
      </div>

      <!-- 产品筛选 -->
      <div class="filter-group">
        <label class="filter-label">产品选择</label>
        <select v-model="filters.productName" class="filter-select">
          <option :value="null">全部产品</option>
          <option
            v-for="product in products"
            :key="product"
            :value="product"
          >
            {{ product }}
          </option>
        </select>
      </div>

      <!-- 价格范围筛选 -->
      <div class="filter-group">
        <label class="filter-label">价格范围</label>
        <div class="range-inputs">
          <input
            v-model.number="filters.minPrice"
            type="number"
            placeholder="最低价"
            class="range-input"
          >
          <span class="range-separator">-</span>
          <input
            v-model.number="filters.maxPrice"
            type="number"
            placeholder="最高价"
            class="range-input"
          >
        </div>
      </div>

      <!-- 情感筛选 -->
      <div class="filter-group">
        <label class="filter-label">情感分类</label>
        <div class="checkbox-group">
          <label class="checkbox-label">
            <input
              v-model="filters.sentiments"
              type="checkbox"
              value="positive"
            >
            <span class="checkbox-text positive">正面</span>
          </label>
          <label class="checkbox-label">
            <input
              v-model="filters.sentiments"
              type="checkbox"
              value="neutral"
            >
            <span class="checkbox-text neutral">中性</span>
          </label>
          <label class="checkbox-label">
            <input
              v-model="filters.sentiments"
              type="checkbox"
              value="negative"
            >
            <span class="checkbox-text negative">负面</span>
          </label>
        </div>
      </div>

      <!-- 评分范围筛选 -->
      <div class="filter-group">
        <label class="filter-label">评分范围</label>
        <div class="rating-slider">
          <input
            v-model.number="filters.minRating"
            type="range"
            min="1"
            max="5"
            step="0.5"
            class="slider"
          >
          <span class="rating-value">{{ filters.minRating }} - 5</span>
        </div>
      </div>

      <!-- 产品分类筛选 -->
      <div class="filter-group">
        <label class="filter-label">产品分类</label>
        <select v-model="filters.categoryLevel1" @change="onCategoryChange" class="filter-select">
          <option :value="null">全部分类</option>
          <option
            v-for="category in categories"
            :key="category"
            :value="category"
          >
            {{ category }}
          </option>
        </select>
      </div>

      <!-- 数据来源筛选 -->
      <div class="filter-group">
        <label class="filter-label">数据来源</label>
        <div class="checkbox-group">
          <label class="checkbox-label">
            <input
              v-model="filters.sources"
              type="checkbox"
              value="website"
            >
            <span class="checkbox-text">官网</span>
          </label>
          <label class="checkbox-label">
            <input
              v-model="filters.sources"
              type="checkbox"
              value="api"
            >
            <span class="checkbox-text">API</span>
          </label>
          <label class="checkbox-label">
            <input
              v-model="filters.sources"
              type="checkbox"
              value="social"
            >
            <span class="checkbox-text">社交媒体</span>
          </label>
        </div>
      </div>
    </div>

    <div class="panel-footer">
      <button @click="applyFilters" class="btn-apply">应用筛选</button>
      <button @click="exportData" class="btn-export">导出数据</button>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, watch } from 'vue';

export default {
  name: 'FilterPanel',
  props: {
    initialFilters: {
      type: Object,
      default: () => ({})
    }
  },
  setup(props, { emit }) {
    const filters = ref({
      startDate: null,
      endDate: null,
      competitorId: null,
      productName: null,
      minPrice: null,
      maxPrice: null,
      sentiments: ['positive', 'neutral', 'negative'],
      minRating: 1,
      categoryLevel1: null,
      sources: ['website', 'api', 'social']
    });

    const competitors = ref([]);
    const products = ref([]);
    const categories = ref([]);
    const selectedQuickRange = ref('30d');

    const quickRanges = [
      { label: '7天', value: '7d' },
      { label: '30天', value: '30d' },
      { label: '90天', value: '90d' },
      { label: '全部', value: 'all' }
    ];

    const fetchCompetitors = async () => {
      try {
        const response = await fetch('/api/v1/competitors');
        const result = await response.json();
        if (result.success) {
          competitors.value = result.data;
        }
      } catch (err) {
        console.error('Failed to fetch competitors:', err);
      }
    };

    const fetchProducts = async (competitorId) => {
      if (!competitorId) {
        products.value = [];
        return;
      }

      try {
        const response = await fetch(`/api/v1/products?competitor_id=${competitorId}`);
        const result = await response.json();
        if (result.success) {
          products.value = result.data;
        }
      } catch (err) {
        console.error('Failed to fetch products:', err);
      }
    };

    const fetchCategories = async () => {
      try {
        const response = await fetch('/api/v1/categories');
        const result = await response.json();
        if (result.success) {
          categories.value = result.data;
        }
      } catch (err) {
        console.error('Failed to fetch categories:', err);
      }
    };

    const setQuickRange = (range) => {
      selectedQuickRange.value = range;
      const now = new Date();
      let startDate;

      switch (range) {
        case '7d':
          startDate = new Date(now - 7 * 24 * 60 * 60 * 1000);
          break;
        case '30d':
          startDate = new Date(now - 30 * 24 * 60 * 60 * 1000);
          break;
        case '90d':
          startDate = new Date(now - 90 * 24 * 60 * 60 * 1000);
          break;
        case 'all':
          filters.value.startDate = null;
          filters.value.endDate = null;
          return;
      }

      filters.value.startDate = startDate.toISOString().split('T')[0];
      filters.value.endDate = now.toISOString().split('T')[0];
    };

    const onCompetitorChange = () => {
      filters.value.productName = null;
      fetchProducts(filters.value.competitorId);
    };

    const onCategoryChange = () => {
      // 可以添加二级分类逻辑
    };

    const applyFilters = () => {
      emit('filter-change', filters.value);
    };

    const resetFilters = () => {
      filters.value = {
        startDate: null,
        endDate: null,
        competitorId: null,
        productName: null,
        minPrice: null,
        maxPrice: null,
        sentiments: ['positive', 'neutral', 'negative'],
        minRating: 1,
        categoryLevel1: null,
        sources: ['website', 'api', 'social']
      };
      selectedQuickRange.value = '30d';
      products.value = [];
      emit('filter-change', filters.value);
    };

    const exportData = () => {
      emit('export', filters.value);
    };

    onMounted(() => {
      fetchCompetitors();
      fetchCategories();

      // 设置默认时间范围
      setQuickRange('30d');
    });

    watch(() => props.initialFilters, (newFilters) => {
      if (newFilters) {
        filters.value = { ...filters.value, ...newFilters };
      }
    }, { immediate: true });

    return {
      filters,
      competitors,
      products,
      categories,
      quickRanges,
      selectedQuickRange,
      setQuickRange,
      onCompetitorChange,
      onCategoryChange,
      applyFilters,
      resetFilters,
      exportData
    };
  }
};
</script>

<style scoped>
.filter-panel {
  background: #FFFFFF;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #E5E7EB;
}

.panel-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1F2937;
}

.btn-reset {
  padding: 6px 12px;
  background: #F3F4F6;
  color: #374151;
  border: 1px solid #D1D5DB;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-reset:hover {
  background: #E5E7EB;
}

.filter-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-label {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.date-range-picker {
  display: flex;
  align-items: center;
  gap: 10px;
}

.date-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #D1D5DB;
  border-radius: 4px;
  font-size: 14px;
  color: #374151;
}

.date-separator {
  color: #6B7280;
  font-size: 14px;
}

.quick-select {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.quick-btn {
  padding: 4px 12px;
  background: #F3F4F6;
  color: #6B7280;
  border: 1px solid #D1D5DB;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.quick-btn:hover {
  background: #E5E7EB;
}

.quick-btn.active {
  background: #3B82F6;
  color: #FFFFFF;
  border-color: #3B82F6;
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid #D1D5DB;
  border-radius: 4px;
  font-size: 14px;
  color: #374151;
  background: #FFFFFF;
  cursor: pointer;
}

.filter-select:hover {
  border-color: #9CA3AF;
}

.range-inputs {
  display: flex;
  align-items: center;
  gap: 10px;
}

.range-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #D1D5DB;
  border-radius: 4px;
  font-size: 14px;
  color: #374151;
}

.range-separator {
  color: #6B7280;
  font-size: 14px;
}

.checkbox-group {
  display: flex;
  gap: 15px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.checkbox-text {
  font-size: 14px;
  color: #374151;
}

.checkbox-text.positive {
  color: #10B981;
}

.checkbox-text.neutral {
  color: #6B7280;
}

.checkbox-text.negative {
  color: #EF4444;
}

.rating-slider {
  display: flex;
  align-items: center;
  gap: 15px;
}

.slider {
  flex: 1;
  height: 6px;
  border-radius: 3px;
  background: #E5E7EB;
  outline: none;
  -webkit-appearance: none;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #3B82F6;
  cursor: pointer;
}

.rating-value {
  font-size: 14px;
  color: #374151;
  font-weight: 500;
}

.panel-footer {
  display: flex;
  gap: 10px;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #E5E7EB;
}

.btn-apply {
  flex: 1;
  padding: 10px 20px;
  background: #3B82F6;
  color: #FFFFFF;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-apply:hover {
  background: #2563EB;
}

.btn-export {
  padding: 10px 20px;
  background: #10B981;
  color: #FFFFFF;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-export:hover {
  background: #059669;
}
</style>
