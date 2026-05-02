<!--
  自定义仪表盘页面
  任务：task-013 - Week 8: 实现自定义仪表盘
-->

<template>
  <div class="custom-dashboard">
    <div class="dashboard-header">
      <h2>自定义仪表盘</h2>
      <div class="header-controls">
        <button @click="addWidget" class="btn-add">添加组件</button>
        <button @click="saveLayout" class="btn-save">保存布局</button>
        <button @click="resetLayout" class="btn-reset">重置布局</button>
      </div>
    </div>

    <div class="dashboard-grid" ref="gridContainer">
      <div
        v-for="(widget, index) in widgets"
        :key="widget.id"
        :class="['widget', `widget-${widget.size}`]"
        :style="{ gridColumn: widget.gridColumn, gridRow: widget.gridRow }"
      >
        <div class="widget-header">
          <h3>{{ widget.title }}</h3>
          <div class="widget-controls">
            <button @click="editWidget(index)" class="btn-edit">编辑</button>
            <button @click="removeWidget(index)" class="btn-remove">删除</button>
          </div>
        </div>
        <div class="widget-content">
          <component
            :is="widget.component"
            :competitor-id="widget.competitorId"
            :product-name="widget.productName"
            :title="widget.title"
          />
        </div>
      </div>
    </div>

    <!-- 添加组件对话框 -->
    <div v-if="showAddDialog" class="dialog-overlay">
      <div class="dialog">
        <div class="dialog-header">
          <h3>添加组件</h3>
          <button @click="closeAddDialog" class="btn-close">关闭</button>
        </div>
        <div class="dialog-body">
          <div class="form-group">
            <label>组件类型</label>
            <select v-model="newWidget.type" class="form-select">
              <option value="PriceTrendChart">价格趋势图</option>
              <option value="SentimentPieChart">情感分析饼图</option>
              <option value="KeywordCloudChart">关键词云图</option>
              <option value="FilterPanel">筛选面板</option>
            </select>
          </div>
          <div class="form-group">
            <label>组件标题</label>
            <input v-model="newWidget.title" type="text" class="form-input" placeholder="组件标题">
          </div>
          <div class="form-group">
            <label>竞品ID</label>
            <input v-model.number="newWidget.competitorId" type="number" class="form-input" placeholder="竞品ID">
          </div>
          <div class="form-group">
            <label>产品名称（可选）</label>
            <input v-model="newWidget.productName" type="text" class="form-input" placeholder="产品名称">
          </div>
          <div class="form-group">
            <label>组件大小</label>
            <select v-model="newWidget.size" class="form-select">
              <option value="small">小 (1x1)</option>
              <option value="medium">中 (2x1)</option>
              <option value="large">大 (2x2)</option>
            </select>
          </div>
        </div>
        <div class="dialog-footer">
          <button @click="confirmAddWidget" class="btn-confirm">确认添加</button>
          <button @click="closeAddDialog" class="btn-cancel">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import PriceTrendChart from './PriceTrendChart.vue';
import SentimentPieChart from './SentimentPieChart.vue';
import KeywordCloudChart from './KeywordCloudChart.vue';
import FilterPanel from './FilterPanel.vue';

export default {
  name: 'CustomDashboard',
  components: {
    PriceTrendChart,
    SentimentPieChart,
    KeywordCloudChart,
    FilterPanel
  },
  setup() {
    const widgets = ref([]);
    const showAddDialog = ref(false);
    const newWidget = ref({
      type: 'PriceTrendChart',
      title: '',
      competitorId: 1,
      productName: null,
      size: 'medium'
    });

    const defaultWidgets = [
      {
        id: 1,
        type: 'PriceTrendChart',
        component: 'PriceTrendChart',
        title: '价格趋势',
        competitorId: 1,
        productName: null,
        size: 'large',
        gridColumn: 'span 2',
        gridRow: 'span 2'
      },
      {
        id: 2,
        type: 'SentimentPieChart',
        component: 'SentimentPieChart',
        title: '情感分析',
        competitorId: 1,
        productName: null,
        size: 'medium',
        gridColumn: 'span 2',
        gridRow: 'span 1'
      },
      {
        id: 3,
        type: 'KeywordCloudChart',
        component: 'KeywordCloudChart',
        title: '关键词云',
        competitorId: 1,
        productName: null,
        size: 'medium',
        gridColumn: 'span 2',
        gridRow: 'span 1'
      }
    ];

    const addWidget = () => {
      showAddDialog.value = true;
      newWidget.value = {
        type: 'PriceTrendChart',
        title: '',
        competitorId: 1,
        productName: null,
        size: 'medium'
      };
    };

    const closeAddDialog = () => {
      showAddDialog.value = false;
    };

    const confirmAddWidget = () => {
      const sizeConfig = {
        small: { gridColumn: 'span 1', gridRow: 'span 1' },
        medium: { gridColumn: 'span 2', gridRow: 'span 1' },
        large: { gridColumn: 'span 2', gridRow: 'span 2' }
      };

      const widget = {
        id: Date.now(),
        type: newWidget.value.type,
        component: newWidget.value.type,
        title: newWidget.value.title || getDefaultTitle(newWidget.value.type),
        competitorId: newWidget.value.competitorId,
        productName: newWidget.value.productName,
        size: newWidget.value.size,
        gridColumn: sizeConfig[newWidget.value.size].gridColumn,
        gridRow: sizeConfig[newWidget.value.size].gridRow
      };

      widgets.value.push(widget);
      closeAddDialog();
    };

    const getDefaultTitle = (type) => {
      const titles = {
        PriceTrendChart: '价格趋势',
        SentimentPieChart: '情感分析',
        KeywordCloudChart: '关键词云',
        FilterPanel: '筛选面板'
      };
      return titles[type] || '组件';
    };

    const editWidget = (index) => {
      // 编辑功能可以扩展
      console.log('Edit widget:', index);
    };

    const removeWidget = (index) => {
      widgets.value.splice(index, 1);
    };

    const saveLayout = () => {
      localStorage.setItem('dashboardLayout', JSON.stringify(widgets.value));
      alert('布局已保存');
    };

    const resetLayout = () => {
      widgets.value = [...defaultWidgets];
      localStorage.removeItem('dashboardLayout');
      alert('布局已重置');
    };

    const loadLayout = () => {
      const saved = localStorage.getItem('dashboardLayout');
      if (saved) {
        widgets.value = JSON.parse(saved);
      } else {
        widgets.value = [...defaultWidgets];
      }
    };

    onMounted(() => {
      loadLayout();
    });

    return {
      widgets,
      showAddDialog,
      newWidget,
      addWidget,
      closeAddDialog,
      confirmAddWidget,
      editWidget,
      removeWidget,
      saveLayout,
      resetLayout
    };
  }
};
</script>

<style scoped>
.custom-dashboard {
  padding: 20px;
  background: #F9FAFB;
  min-height: 100vh;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding: 20px;
  background: #FFFFFF;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.dashboard-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #1F2937;
}

.header-controls {
  display: flex;
  gap: 10px;
}

.btn-add {
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

.btn-add:hover {
  background: #2563EB;
}

.btn-save {
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

.btn-save:hover {
  background: #059669;
}

.btn-reset {
  padding: 10px 20px;
  background: #F3F4F6;
  color: #374151;
  border: 1px solid #D1D5DB;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-reset:hover {
  background: #E5E7EB;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  grid-auto-rows: minmax(200px, auto);
}

.widget {
  background: #FFFFFF;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.widget-small {
  grid-column: span 1;
  grid-row: span 1;
}

.widget-medium {
  grid-column: span 2;
  grid-row: span 1;
}

.widget-large {
  grid-column: span 2;
  grid-row: span 2;
}

.widget-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  background: #F9FAFB;
  border-bottom: 1px solid #E5E7EB;
}

.widget-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1F2937;
}

.widget-controls {
  display: flex;
  gap: 8px;
}

.btn-edit {
  padding: 4px 8px;
  background: #3B82F6;
  color: #FFFFFF;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}

.btn-remove {
  padding: 4px 8px;
  background: #EF4444;
  color: #FFFFFF;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}

.widget-content {
  padding: 20px;
  height: calc(100% - 60px);
  overflow: auto;
}

.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  background: #FFFFFF;
  border-radius: 8px;
  width: 500px;
  max-width: 90%;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #E5E7EB;
}

.dialog-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1F2937;
}

.btn-close {
  padding: 4px 8px;
  background: #F3F4F6;
  color: #374151;
  border: 1px solid #D1D5DB;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}

.dialog-body {
  padding: 20px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.form-input,
.form-select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #D1D5DB;
  border-radius: 4px;
  font-size: 14px;
  color: #374151;
}

.dialog-footer {
  display: flex;
  gap: 10px;
  padding: 20px;
  border-top: 1px solid #E5E7EB;
}

.btn-confirm {
  flex: 1;
  padding: 10px 20px;
  background: #3B82F6;
  color: #FFFFFF;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
}

.btn-cancel {
  padding: 10px 20px;
  background: #F3F4F6;
  color: #374151;
  border: 1px solid #D1D5DB;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
}
</style>