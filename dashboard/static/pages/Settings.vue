<!--
  个性化设置页面
  任务：task-014 - Week 9: 实现个性化设置和报告中心
-->

<template>
  <div class="settings-page">
    <div class="settings-header">
      <h2>个性化设置</h2>
    </div>

    <div class="settings-content">
      <!-- 用户信息设置 -->
      <div class="settings-section">
        <h3>用户信息</h3>
        <div class="form-group">
          <label>用户名</label>
          <input v-model="settings.username" type="text" class="form-input" placeholder="用户名">
        </div>
        <div class="form-group">
          <label>邮箱</label>
          <input v-model="settings.email" type="email" class="form-input" placeholder="邮箱">
        </div>
      </div>

      <!-- 通知设置 -->
      <div class="settings-section">
        <h3>通知设置</h3>
        <div class="checkbox-group">
          <label class="checkbox-label">
            <input v-model="settings.notifications.email" type="checkbox">
            <span>邮件通知</span>
          </label>
          <label class="checkbox-label">
            <input v-model="settings.notifications.browser" type="checkbox">
            <span>浏览器通知</span>
          </label>
          <label class="checkbox-label">
            <input v-model="settings.notifications.websocket" type="checkbox">
            <span>实时推送</span>
          </label>
        </div>
      </div>

      <!-- 监控设置 -->
      <div class="settings-section">
        <h3>监控设置</h3>
        <div class="form-group">
          <label>默认监控间隔（分钟）</label>
          <input v-model.number="settings.monitoringInterval" type="number" class="form-input" min="1" max="1440">
        </div>
        <div class="form-group">
          <label>价格变化阈值（%）</label>
          <input v-model.number="settings.priceChangeThreshold" type="number" class="form-input" min="0" max="100" step="0.1">
        </div>
        <div class="form-group">
          <label>情感分析灵敏度</label>
          <select v-model="settings.sentimentSensitivity" class="form-select">
            <option value="low">低</option>
            <option value="medium">中</option>
            <option value="high">高</option>
          </select>
        </div>
      </div>

      <!-- 显示设置 -->
      <div class="settings-section">
        <h3>显示设置</h3>
        <div class="form-group">
          <label>主题</label>
          <select v-model="settings.theme" class="form-select">
            <option value="light">浅色</option>
            <option value="dark">深色</option>
            <option value="auto">自动</option>
          </select>
        </div>
        <div class="form-group">
          <label>语言</label>
          <select v-model="settings.language" class="form-select">
            <option value="zh-CN">简体中文</option>
            <option value="en-US">English</option>
          </select>
        </div>
        <div class="form-group">
          <label>时区</label>
          <select v-model="settings.timezone" class="form-select">
            <option value="Asia/Shanghai">Asia/Shanghai (UTC+8)</option>
            <option value="UTC">UTC</option>
          </select>
        </div>
      </div>

      <!-- 数据导出设置 -->
      <div class="settings-section">
        <h3>数据导出</h3>
        <div class="form-group">
          <label>导出格式</label>
          <select v-model="settings.exportFormat" class="form-select">
            <option value="csv">CSV</option>
            <option value="json">JSON</option>
            <option value="excel">Excel</option>
          </select>
        </div>
        <div class="form-group">
          <label>日期格式</label>
          <select v-model="settings.dateFormat" class="form-select">
            <option value="YYYY-MM-DD">YYYY-MM-DD</option>
            <option value="DD/MM/YYYY">DD/MM/YYYY</option>
            <option value="MM/DD/YYYY">MM/DD/YYYY</option>
          </select>
        </div>
      </div>

      <div class="settings-footer">
        <button @click="saveSettings" class="btn-save">保存设置</button>
        <button @click="resetSettings" class="btn-reset">重置默认</button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';

export default {
  name: 'Settings',
  setup() {
    const settings = ref({
      username: '',
      email: '',
      notifications: {
        email: true,
        browser: true,
        websocket: true
      },
      monitoringInterval: 60,
      priceChangeThreshold: 5.0,
      sentimentSensitivity: 'medium',
      theme: 'light',
      language: 'zh-CN',
      timezone: 'Asia/Shanghai',
      exportFormat: 'csv',
      dateFormat: 'YYYY-MM-DD'
    });

    const defaultSettings = { ...settings.value };

    const loadSettings = () => {
      const saved = localStorage.getItem('userSettings');
      if (saved) {
        settings.value = { ...defaultSettings, ...JSON.parse(saved) };
      }
    };

    const saveSettings = () => {
      localStorage.setItem('userSettings', JSON.stringify(settings.value));
      alert('设置已保存');
    };

    const resetSettings = () => {
      settings.value = { ...defaultSettings };
      localStorage.removeItem('userSettings');
      alert('设置已重置');
    };

    onMounted(() => {
      loadSettings();
    });

    return {
      settings,
      saveSettings,
      resetSettings
    };
  }
};
</script>

<style scoped>
.settings-page {
  padding: 20px;
  background: #F9FAFB;
  min-height: 100vh;
}

.settings-header {
  margin-bottom: 30px;
  padding: 20px;
  background: #FFFFFF;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.settings-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #1F2937;
}

.settings-content {
  background: #FFFFFF;
  border-radius: 8px;
  padding: 30px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.settings-section {
  margin-bottom: 30px;
  padding-bottom: 30px;
  border-bottom: 1px solid #E5E7EB;
}

.settings-section:last-of-type {
  border-bottom: none;
}

.settings-section h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  font-weight: 600;
  color: #1F2937;
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
  max-width: 400px;
  padding: 8px 12px;
  border: 1px solid #D1D5DB;
  border-radius: 4px;
  font-size: 14px;
  color: #374151;
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 14px;
  color: #374151;
}

.settings-footer {
  display: flex;
  gap: 10px;
  margin-top: 30px;
  padding-top: 30px;
  border-top: 1px solid #E5E7EB;
}

.btn-save {
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

.btn-save:hover {
  background: #2563EB;
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
</style>
