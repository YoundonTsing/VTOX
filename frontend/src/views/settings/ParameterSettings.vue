<template>
  <div class="parameter-settings-container">
    <h2 class="page-title">参数配置</h2>
    <p class="page-description">
      配置系统运行的各项参数，包括数据采集、算法和系统设置。
    </p>

    <el-card class="settings-card">
      <el-tabs v-model="activeTab" type="border-card" class="settings-tabs">
        <!-- 数据采集参数 -->
        <el-tab-pane label="数据采集参数" name="acquisition">
          <div class="tab-content">
            <h3>数据采集参数配置</h3>
            <p class="tab-description">配置数据采集的采样率、通道数量等参数。</p>

            <el-form :model="acquisitionParams" label-width="180px">
              <el-form-item label="采样率 (Hz)">
                <el-select v-model="acquisitionParams.samplingRate" style="width: 200px">
                  <el-option v-for="rate in samplingRates" :key="rate" :label="`${rate} Hz`" :value="rate" />
                </el-select>
              </el-form-item>

              <el-form-item label="采样点数">
                <el-input-number v-model="acquisitionParams.samplingPoints" :min="128" :max="16384" :step="128" />
              </el-form-item>

              <el-form-item label="电流通道使能">
                <el-switch v-model="acquisitionParams.currentChannelEnabled" />
              </el-form-item>

              <el-form-item label="电压通道使能">
                <el-switch v-model="acquisitionParams.voltageChannelEnabled" />
              </el-form-item>

              <el-form-item label="振动通道使能">
                <el-switch v-model="acquisitionParams.vibrationChannelEnabled" />
              </el-form-item>

              <el-form-item label="温度通道使能">
                <el-switch v-model="acquisitionParams.temperatureChannelEnabled" />
              </el-form-item>

              <el-form-item label="数据缓冲区大小 (MB)">
                <el-slider v-model="acquisitionParams.bufferSize" :min="1" :max="100" :step="1" show-input />
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>

        <!-- 算法参数 -->
        <el-tab-pane label="算法参数" name="algorithm">
          <div class="tab-content">
            <h3>算法参数配置</h3>
            <p class="tab-description">配置故障诊断算法的参数。</p>

            <el-form :model="algorithmParams" label-width="180px">
              <el-form-item label="FFT窗口长度">
                <el-select v-model="algorithmParams.fftWindowLength" style="width: 200px">
                  <el-option v-for="len in fftWindowLengths" :key="len" :label="`${len}`" :value="len" />
                </el-select>
              </el-form-item>

              <el-form-item label="FFT窗口类型">
                <el-select v-model="algorithmParams.fftWindowType" style="width: 200px">
                  <el-option label="矩形窗" value="rectangular" />
                  <el-option label="汉宁窗" value="hanning" />
                  <el-option label="汉明窗" value="hamming" />
                  <el-option label="布莱克曼窗" value="blackman" />
                </el-select>
              </el-form-item>

              <el-form-item label="特征提取间隔 (ms)">
                <el-input-number v-model="algorithmParams.featureExtractionInterval" :min="100" :max="10000" :step="100" />
              </el-form-item>

              <el-form-item label="诊断算法模式">
                <el-radio-group v-model="algorithmParams.diagnosisMode">
                  <el-radio label="standard">标准模式</el-radio>
                  <el-radio label="advanced">高级模式</el-radio>
                  <el-radio label="expert">专家模式</el-radio>
                </el-radio-group>
              </el-form-item>

              <el-form-item label="使用神经网络">
                <el-switch v-model="algorithmParams.useNeuralNetwork" />
              </el-form-item>

              <el-form-item label="神经网络模型" v-if="algorithmParams.useNeuralNetwork">
                <el-select v-model="algorithmParams.neuralNetworkModel" style="width: 200px">
                  <el-option label="CNN" value="cnn" />
                  <el-option label="LSTM" value="lstm" />
                  <el-option label="混合模型" value="hybrid" />
                </el-select>
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>

        <!-- 系统参数 -->
        <el-tab-pane label="系统参数" name="system">
          <div class="tab-content">
            <h3>系统参数配置</h3>
            <p class="tab-description">配置系统运行的基本参数。</p>

            <el-form :model="systemParams" label-width="180px">
              <el-form-item label="数据存储路径">
                <el-input v-model="systemParams.dataStoragePath" placeholder="/data/storage" />
              </el-form-item>

              <el-form-item label="数据保留天数">
                <el-input-number v-model="systemParams.dataRetentionDays" :min="1" :max="365" :step="1" />
              </el-form-item>

              <el-form-item label="日志级别">
                <el-select v-model="systemParams.logLevel" style="width: 200px">
                  <el-option label="调试" value="debug" />
                  <el-option label="信息" value="info" />
                  <el-option label="警告" value="warning" />
                  <el-option label="错误" value="error" />
                </el-select>
              </el-form-item>

              <el-form-item label="系统启动时自动开始监控">
                <el-switch v-model="systemParams.autoStartMonitoring" />
              </el-form-item>

              <el-form-item label="告警通知方式">
                <el-checkbox-group v-model="systemParams.notificationMethods">
                  <el-checkbox label="email">电子邮件</el-checkbox>
                  <el-checkbox label="sms">短信</el-checkbox>
                  <el-checkbox label="wechat">微信</el-checkbox>
                  <el-checkbox label="app">App推送</el-checkbox>
                </el-checkbox-group>
              </el-form-item>

              <el-form-item label="告警接收邮箱" v-if="systemParams.notificationMethods.includes('email')">
                <el-input v-model="systemParams.emailRecipients" placeholder="example@company.com" />
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>
      </el-tabs>

      <div class="actions">
        <el-button type="primary" @click="saveSettings">保存设置</el-button>
        <el-button @click="resetSettings">恢复默认</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { ElMessage } from 'element-plus';

const activeTab = ref('acquisition');

// 采样率选项
const samplingRates = [1000, 2000, 5000, 10000, 20000, 50000];

// FFT窗口长度选项
const fftWindowLengths = [128, 256, 512, 1024, 2048, 4096, 8192];

// 数据采集参数
const acquisitionParams = reactive({
  samplingRate: 10000,
  samplingPoints: 1024,
  currentChannelEnabled: true,
  voltageChannelEnabled: true,
  vibrationChannelEnabled: true,
  temperatureChannelEnabled: false,
  bufferSize: 10
});

// 算法参数
const algorithmParams = reactive({
  fftWindowLength: 1024,
  fftWindowType: 'hanning',
  featureExtractionInterval: 1000,
  diagnosisMode: 'standard',
  useNeuralNetwork: false,
  neuralNetworkModel: 'cnn'
});

// 系统参数
const systemParams = reactive({
  dataStoragePath: '/data/storage',
  dataRetentionDays: 30,
  logLevel: 'info',
  autoStartMonitoring: false,
  notificationMethods: ['email'],
  emailRecipients: 'admin@example.com'
});

// 加载设置
const loadSettings = () => {
  try {
    // 加载数据采集参数
    const savedAcquisitionParams = localStorage.getItem('acquisition_params');
    if (savedAcquisitionParams) {
      Object.assign(acquisitionParams, JSON.parse(savedAcquisitionParams));
    }

    // 加载算法参数
    const savedAlgorithmParams = localStorage.getItem('algorithm_params');
    if (savedAlgorithmParams) {
      Object.assign(algorithmParams, JSON.parse(savedAlgorithmParams));
    }

    // 加载系统参数
    const savedSystemParams = localStorage.getItem('system_params');
    if (savedSystemParams) {
      Object.assign(systemParams, JSON.parse(savedSystemParams));
    }

    ElMessage.success('参数配置已加载');
  } catch (error) {
    console.error('加载参数配置失败:', error);
    ElMessage.error('加载参数配置失败');
  }
};

// 保存设置
const saveSettings = () => {
  try {
    // 保存数据采集参数
    localStorage.setItem('acquisition_params', JSON.stringify(acquisitionParams));

    // 保存算法参数
    localStorage.setItem('algorithm_params', JSON.stringify(algorithmParams));

    // 保存系统参数
    localStorage.setItem('system_params', JSON.stringify(systemParams));

    ElMessage.success('参数配置已保存');
  } catch (error) {
    console.error('保存参数配置失败:', error);
    ElMessage.error('保存参数配置失败');
  }
};

// 重置为默认设置
const resetSettings = () => {
  ElMessage.info('恢复默认功能将在后续版本中实现');
};

onMounted(() => {
  loadSettings();
});
</script>

<style scoped>
.parameter-settings-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  margin-bottom: 10px;
  color: #303133;
}

.page-description {
  color: #606266;
  margin-bottom: 20px;
}

.settings-card {
  border-radius: 8px;
}

.settings-tabs {
  border-radius: 8px;
}

.tab-content {
  padding: 20px;
}

.tab-content h3 {
  font-size: 18px;
  margin-bottom: 10px;
}

.tab-description {
  color: #909399;
  margin-bottom: 30px;
  font-size: 14px;
}

.actions {
  margin-top: 30px;
  padding: 0 20px 20px;
  display: flex;
  justify-content: flex-start;
  gap: 15px;
}
</style> 