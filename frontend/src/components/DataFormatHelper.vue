<template>
  <div class="data-format-helper">
    <div v-if="formatType === 'turn-to-turn'">
      <h3>匝间短路诊断数据格式</h3>
      <p>系统支持以下格式的CSV文件：</p>
      
      <h4>必需列：</h4>
      <ul>
        <li><code>timestamp</code>: 时间戳</li>
        <li><code>Ia</code>, <code>Ib</code>, <code>Ic</code>: 三相电流</li>
        <li><code>Vdc</code>: 直流母线电压</li>
      </ul>
      
      <h4>可选列（提高诊断准确性）：</h4>
      <ul>
        <li><code>Torque</code>: 电机转矩</li>
        <li><code>Speed</code>: 电机转速</li>
        <li><code>Iq_actual</code>, <code>Iq_ref</code>: q轴电流实际值和参考值</li>
        <li><code>Id_actual</code>: d轴电流实际值</li>
        <li><code>I2_ref</code>: 负序电流参考值</li>
        <li><code>Eta_ref</code>: 参考效率</li>
      </ul>
      
      <h4>示例数据：</h4>
      <pre>timestamp,Ia,Ib,Ic,Vdc,Torque,Speed,Iq_actual,Iq_ref,I2_ref,Eta_ref,Id_actual
1267.575,257,258,258,707,-1602.2,1.21,,,,,
1267.575,257,258,258,706,-1602.2,1.21,,,,,
1267.575,257,258,258,705,-1602.2,1.21,,,,,</pre>
    </div>

    <div v-else-if="formatType === 'insulation'">
      <h3>绝缘失效检测数据格式</h3>
      <p>系统支持以下格式的CSV文件：</p>
      
      <h4>必需列：</h4>
      <ul>
        <li><code>timestamp</code>: 时间戳</li>
        <li><code>Ia</code>, <code>Ib</code>, <code>Ic</code>: 三相电流</li>
        <li><code>Vdc</code>: 直流母线电压</li>
      </ul>
      
      <h4>可选列（提高诊断准确性）：</h4>
      <ul>
        <li><code>T_winding</code>: 绕组温度</li>
        <li><code>Torque</code>: 电机转矩</li>
        <li><code>Speed</code>: 电机转速</li>
        <li><code>Iq_actual</code>, <code>Iq_ref</code>: q轴电流实际值和参考值</li>
        <li><code>Id_actual</code>: d轴电流实际值</li>
        <li><code>Eta_ref</code>: 参考效率</li>
      </ul>
      
      <h4>示例数据：</h4>
      <pre>timestamp,Ia,Ib,Ic,Vdc,T_winding,Torque,Speed,Iq_actual,Iq_ref,Eta_ref,Id_actual
1267.575,257,258,258,707,85.2,-1602.2,1.21,,,0.93,
1267.576,257,258,258,706,85.3,-1602.2,1.21,,,0.93,
1267.577,257,258,258,705,85.5,-1602.2,1.21,,,0.93,</pre>
    </div>

    <div v-else>
      <h3>数据格式说明</h3>
      <p>请上传CSV格式的电机数据文件，具体格式要求请参考对应诊断类型的说明。</p>
    </div>
  </div>
</template>

<script setup>
import { defineProps } from 'vue'

const props = defineProps({
  formatType: {
    type: String,
    default: 'turn-to-turn'
  }
})
</script>

<style scoped>
.data-format-helper {
  padding: 10px;
}

h3 {
  margin-top: 0;
  color: #303133;
}

h4 {
  margin-top: 20px;
  margin-bottom: 10px;
  color: #606266;
}

ul {
  padding-left: 20px;
}

li {
  margin-bottom: 5px;
}

code {
  background-color: #f5f7fa;
  padding: 2px 5px;
  border-radius: 3px;
  color: #409EFF;
  font-family: monospace;
}

pre {
  background-color: #f5f7fa;
  padding: 15px;
  border-radius: 5px;
  overflow-x: auto;
  font-family: monospace;
  margin-top: 10px;
  white-space: pre-wrap;
}
</style> 