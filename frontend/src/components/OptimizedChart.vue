<template>
  <div class="optimized-chart" :style="{ width: width, height: height }">
    <canvas 
      ref="canvasRef" 
      :width="canvasWidth" 
      :height="canvasHeight"
      @mousedown="onMouseDown"
      @mousemove="onMouseMove"
      @mouseup="onMouseUp"
      @wheel="onWheel"
    ></canvas>
    
    <!-- 性能统计信息 -->
    <div v-if="showStats" class="chart-stats">
      <div>FPS: {{ fps }}</div>
      <div>Points: {{ dataPoints }}</div>
      <div>Rendered: {{ renderedPoints }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import { globalChartOptimizer } from '@/mixins/diagnosisOptimization.js';

const props = defineProps({
  data: {
    type: Array,
    default: () => []
  },
  width: {
    type: String,
    default: '100%'
  },
  height: {
    type: String,
    default: '300px'
  },
  lineColor: {
    type: String,
    default: '#00c6ff'
  },
  backgroundColor: {
    type: String,
    default: 'transparent'
  },
  showGrid: {
    type: Boolean,
    default: true
  },
  showStats: {
    type: Boolean,
    default: false
  },
  maxDataPoints: {
    type: Number,
    default: 200
  },
  autoScale: {
    type: Boolean,
    default: true
  }
});

const canvasRef = ref(null);
const canvasWidth = ref(800);
const canvasHeight = ref(300);

// 性能统计
const fps = ref(0);
const dataPoints = ref(0);
const renderedPoints = ref(0);

// 图表状态
const viewBox = ref({ x: 0, y: 0, width: 1, height: 1 });
const isDragging = ref(false);
const lastMousePos = ref({ x: 0, y: 0 });

// 性能监控
let lastFrameTime = 0;
let frameCount = 0;
let animationFrame = null;

onMounted(() => {
  setupCanvas();
  startRendering();
  window.addEventListener('resize', handleResize);
});

onBeforeUnmount(() => {
  stopRendering();
  window.removeEventListener('resize', handleResize);
});

// 监听数据变化
watch(() => props.data, (newData) => {
  dataPoints.value = newData.length;
  globalChartOptimizer.throttleChartUpdate('optimized-chart', () => {
    render();
  });
}, { deep: true });

// 设置画布
const setupCanvas = () => {
  nextTick(() => {
    if (!canvasRef.value) return;
    
    const container = canvasRef.value.parentElement;
    const rect = container.getBoundingClientRect();
    
    canvasWidth.value = rect.width * window.devicePixelRatio;
    canvasHeight.value = rect.height * window.devicePixelRatio;
    
    const ctx = canvasRef.value.getContext('2d');
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    
    render();
  });
};

// 处理窗口大小变化
const handleResize = () => {
  globalChartOptimizer.throttleChartUpdate('resize', setupCanvas);
};

// 开始渲染循环
const startRendering = () => {
  const renderLoop = (timestamp) => {
    // 计算FPS
    if (timestamp - lastFrameTime >= 1000) {
      fps.value = Math.round(frameCount * 1000 / (timestamp - lastFrameTime));
      frameCount = 0;
      lastFrameTime = timestamp;
    }
    frameCount++;
    
    animationFrame = requestAnimationFrame(renderLoop);
  };
  
  animationFrame = requestAnimationFrame(renderLoop);
};

// 停止渲染循环
const stopRendering = () => {
  if (animationFrame) {
    cancelAnimationFrame(animationFrame);
    animationFrame = null;
  }
};

// 主渲染函数
const render = () => {
  if (!canvasRef.value) return;
  
  const ctx = canvasRef.value.getContext('2d');
  const width = canvasRef.value.width / window.devicePixelRatio;
  const height = canvasRef.value.height / window.devicePixelRatio;
  
  // 清空画布
  ctx.clearRect(0, 0, width, height);
  
  // 设置背景
  if (props.backgroundColor !== 'transparent') {
    ctx.fillStyle = props.backgroundColor;
    ctx.fillRect(0, 0, width, height);
  }
  
  // 优化数据
  const optimizedData = globalChartOptimizer.optimizeChartData(props.data);
  renderedPoints.value = optimizedData.length;
  
  if (optimizedData.length === 0) return;
  
  // 绘制网格
  if (props.showGrid) {
    drawGrid(ctx, width, height);
  }
  
  // 绘制数据线
  drawDataLine(ctx, optimizedData, width, height);
};

// 绘制网格
const drawGrid = (ctx, width, height) => {
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
  ctx.lineWidth = 1;
  
  // 垂直线
  for (let i = 0; i <= 10; i++) {
    const x = (width / 10) * i;
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }
  
  // 水平线
  for (let i = 0; i <= 5; i++) {
    const y = (height / 5) * i;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }
};

// 绘制数据线
const drawDataLine = (ctx, data, width, height) => {
  if (data.length < 2) return;
  
  // 计算数据范围
  let minValue = Infinity;
  let maxValue = -Infinity;
  
  for (const point of data) {
    const value = typeof point === 'object' ? point.y || point.value || 0 : point;
    minValue = Math.min(minValue, value);
    maxValue = Math.max(maxValue, value);
  }
  
  const range = maxValue - minValue || 1;
  
  // 绘制线条
  ctx.strokeStyle = props.lineColor;
  ctx.lineWidth = 2;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  
  ctx.beginPath();
  
  for (let i = 0; i < data.length; i++) {
    const point = data[i];
    const value = typeof point === 'object' ? point.y || point.value || 0 : point;
    
    const x = (width / (data.length - 1)) * i;
    const y = height - ((value - minValue) / range) * height;
    
    if (i === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  }
  
  ctx.stroke();
  
  // 绘制填充区域
  ctx.globalAlpha = 0.3;
  ctx.fillStyle = props.lineColor;
  ctx.lineTo(width, height);
  ctx.lineTo(0, height);
  ctx.closePath();
  ctx.fill();
  ctx.globalAlpha = 1.0;
};

// 鼠标事件处理
const onMouseDown = (event) => {
  isDragging.value = true;
  lastMousePos.value = { x: event.clientX, y: event.clientY };
};

const onMouseMove = (event) => {
  if (!isDragging.value) return;
  
  const deltaX = event.clientX - lastMousePos.value.x;
  const deltaY = event.clientY - lastMousePos.value.y;
  
  // 实现平移功能
  viewBox.value.x -= deltaX / canvasWidth.value;
  viewBox.value.y -= deltaY / canvasHeight.value;
  
  lastMousePos.value = { x: event.clientX, y: event.clientY };
  render();
};

const onMouseUp = () => {
  isDragging.value = false;
};

const onWheel = (event) => {
  event.preventDefault();
  
  // 实现缩放功能
  const zoomFactor = event.deltaY > 0 ? 1.1 : 0.9;
  viewBox.value.width *= zoomFactor;
  viewBox.value.height *= zoomFactor;
  
  render();
};

// 导出方法供外部调用
defineExpose({
  render,
  clearChart: () => {
    if (canvasRef.value) {
      const ctx = canvasRef.value.getContext('2d');
      ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height);
    }
  },
  exportImage: () => {
    return canvasRef.value ? canvasRef.value.toDataURL() : null;
  }
});
</script>

<style scoped>
.optimized-chart {
  position: relative;
  overflow: hidden;
  border-radius: 8px;
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.8), rgba(30, 41, 59, 0.8));
}

canvas {
  width: 100%;
  height: 100%;
  cursor: crosshair;
}

.chart-stats {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 5px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-family: monospace;
}

.chart-stats div {
  margin: 2px 0;
}
</style>