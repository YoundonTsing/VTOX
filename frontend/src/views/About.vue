<template>
  <div class="about-container">
    <div class="card">
      <h2>关于匝间短路检测系统</h2>
      <p>本系统基于电机运行数据分析，诊断电机是否存在匝间短路故障。</p>
      
      <el-divider></el-divider>
      
      <h3>系统原理</h3>
      <p>匝间短路诊断基于以下关键特征参数：</p>
      <ul>
        <li>
          <strong>负序电流分量 I₂：</strong>
          <p>通过对称分量法计算，反映三相平衡度，是匝间短路的直接证据。</p>
          <pre>I_positive = (Ia + a*Ib + a²*Ic) / 3   (a = e^(j120°))
I_negative = (Ia + a²*Ib + a*Ic) / 3
I₂ = |I_negative|</pre>
        </li>
        
        <li>
          <strong>电流不平衡度：</strong>
          <p>反映三相电流的不平衡程度，与I₂强相关。</p>
          <pre>Unbalance = [max(Ia, Ib, Ic) - min(Ia, Ib, Ic)] / I_avg * 100%</pre>
        </li>
        
        <li>
          <strong>DQ轴电流残差的峭度：</strong>
          <p>反映电流波动特性，高峭度值表示存在瞬时异常。</p>
        </li>
        
        <li>
          <strong>效率残差：</strong>
          <p>短路导致铜损增加，效率下降。</p>
        </li>
      </ul>
      
      <h3>故障评分算法</h3>
      <p>系统采用加权评分方法计算故障概率：</p>
      <pre>P_fault = w₁ · sigmoid(I₂/I₂_ref) + w₂ · (ΔI₂/ΔI₂_ref) + w₃ · (Unbalance/Unbalance_ref) + w₄ · (Kurtosis(ΔI_q)/K_ref)</pre>
      <p>其中 w₁, w₂, w₃, w₄ 为各特征权重，根据历史数据训练确定。</p>
      
      <el-divider></el-divider>
      
      <h3>故障判断标准</h3>
      <ul>
        <li><strong>正常(NORMAL):</strong> P_fault &lt; 0.3</li>
        <li><strong>预警(WARNING):</strong> 0.3 ≤ P_fault &lt; 0.7</li>
        <li><strong>故障(FAULT):</strong> P_fault ≥ 0.7</li>
      </ul>
      
      <el-divider></el-divider>
      
      <h3>CSV文件格式要求</h3>
      <p>上传的CSV文件必须包含以下列：</p>
      <pre>timestamp, Ia, Ib, Ic, Vdc, Torque, Speed, Iq_actual, Iq_ref, I2_ref, Eta_ref</pre>
      
      <el-table :data="columnDescriptions" stripe border>
        <el-table-column prop="name" label="列名" width="120" />
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="unit" label="单位" width="100" />
      </el-table>
      
      <el-divider></el-divider>
      
      <h3>技术支持</h3>
      <p>如有问题，请联系系统管理员或查看技术文档。</p>
      <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

// CSV列描述
const columnDescriptions = ref([
  { name: 'timestamp', description: '时间戳', unit: '-' },
  { name: 'Ia, Ib, Ic', description: '三相电流', unit: 'A' },
  { name: 'Vdc', description: '母线电压', unit: 'V' },
  { name: 'Torque', description: '转矩', unit: 'Nm' },
  { name: 'Speed', description: '转速', unit: 'rpm' },
  { name: 'Iq_actual', description: '实际q轴电流', unit: 'A' },
  { name: 'Iq_ref', description: '参考q轴电流', unit: 'A' },
  { name: 'I2_ref', description: '参考负序电流', unit: 'A' },
  { name: 'Eta_ref', description: '参考效率', unit: '-' }
])
</script>

<style scoped>
.about-container {
  max-width: 900px;
  margin: 0 auto;
}

h3 {
  margin-top: 20px;
  color: #409EFF;
}

ul {
  padding-left: 20px;
}

li {
  margin-bottom: 15px;
}

pre {
  background-color: #f5f5f5;
  padding: 10px;
  border-radius: 5px;
  font-family: monospace;
  overflow-x: auto;
  margin: 10px 0;
}
</style> 