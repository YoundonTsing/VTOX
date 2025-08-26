<template>
  <div class="fleet-distributed-monitor">
    <!-- 🎯 顶部控制面板 -->
    <div class="control-header">
      <div class="header-left">
        <h2>🚗 车队分布式实时监控</h2>
        <el-tag :type="getConnectionStatusType(connectionStatus)" size="large">
          {{ getConnectionStatusText(connectionStatus) }}
        </el-tag>
      </div>
      <div class="header-right">
        <!-- 用户信息和认证状态 -->
        <div class="user-info">
          <el-icon class="user-icon"><User /></el-icon>
          <span class="username">{{ currentUser }}</span>
          <el-dropdown @command="handleUserCommand" class="user-dropdown">
            <el-button text type="primary" size="small">
              <el-icon><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        
        <el-divider direction="vertical" />
        
        <el-button 
          :type="connectionStatus === 'connected' ? 'danger' : 'primary'" 
          @click="connectionStatus === 'connected' ? stopMonitoring() : startMonitoring()"
          :loading="connectionStatus === 'connecting'"
          :disabled="connectionStatus === 'connecting'"
          size="large"
        >
          {{ connectionStatus === 'connected' ? '🛑 停止监控' : 
             connectionStatus === 'connecting' ? '正在连接...' : '▶️ 开始监控' }}
        </el-button>
        <el-button 
          v-if="connectionStatus === 'connected'" 
          type="warning" 
          @click="resetAllData"
          size="large"
        >
          🔄 重置
        </el-button>
      </div>
    </div>

    <!-- 📊 车队概览统计 -->
    <div v-if="connectionStatus === 'connected'" class="fleet-overview">
      <div class="overview-card">
        <div class="stat-item">
          <div class="stat-icon">🚗</div>
          <div class="stat-content">
            <div class="stat-value">{{ Object.keys(vehicleData).length }}</div>
            <div class="stat-label">在线车辆</div>
          </div>
        </div>
        <div class="stat-item">
          <div class="stat-icon" :style="{ color: getOverallHealthColor() }">❤️</div>
          <div class="stat-content">
            <div class="stat-value" :style="{ color: getOverallHealthColor() }">
              {{ getOverallHealthScore().toFixed(1) }}%
            </div>
            <div class="stat-label">车队健康度</div>
          </div>
        </div>
        <div class="stat-item">
          <div class="stat-icon" :style="{ color: getAlertColor() }">⚠️</div>
          <div class="stat-content">
            <div class="stat-value" :style="{ color: getAlertColor() }">
              {{ getTotalAlerts() }}
            </div>
            <div class="stat-label">活跃警报</div>
          </div>
        </div>
        <div class="stat-item">
          <div class="stat-icon">📡</div>
          <div class="stat-content">
            <div class="stat-value">{{ detailedStats.actualProcessRate }}</div>
            <div class="stat-label">实际处理 msg/s</div>
            <div class="stat-sub-label">原始接收: {{ detailedStats.rawReceiveRate }} msg/s</div>
          </div>
        </div>
        <div class="stat-item">
          <div class="stat-icon">⏱️</div>
          <div class="stat-content">
            <div class="stat-value">{{ monitoringDuration }}</div>
            <div class="stat-label">监控时间</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 🚀 详细性能监控面板 -->
    <div v-if="connectionStatus === 'connected'" class="performance-detail-panel">
      <div class="performance-header">
        <h3>📊 实时性能监控</h3>
        <div class="performance-actions">
          <el-button 
            size="small" 
            type="primary" 
            @click="updateDetailedStats"
          >
            🔄 刷新
          </el-button>
          <el-button 
            size="small" 
            type="warning" 
            @click="resetPerformanceData"
          >
            🗑️ 重置
          </el-button>
          <!-- 缓存优化开关 -->
          <el-button 
            size="small" 
            :type="cacheOptimizationEnabled ? 'success' : 'info'"
            @click="toggleCacheOptimization"
            :loading="cacheOptimizationLoading"
          >
            {{ cacheOptimizationEnabled ? '🚀 缓存优化已启用' : '⚡ 启用缓存优化' }}
          </el-button>
        </div>
      </div>

      <div class="performance-cards">
        <!-- 实时传输指标 -->
        <div class="performance-card transmission-metrics">
          <div class="card-header">
            <div class="card-title">🚀 传输性能</div>
            <div class="card-status" :class="detailedStats.processingEfficiency >= 95 ? 'status-excellent' : detailedStats.processingEfficiency >= 80 ? 'status-good' : 'status-warning'">
              {{ detailedStats.processingEfficiency }}% 效率
            </div>
          </div>
          <div class="metrics-grid">
            <div class="metric-item">
              <div class="metric-value">{{ detailedStats.rawReceiveRate }}</div>
              <div class="metric-label">WebSocket接收 msg/s</div>
            </div>
            <div class="metric-item">
              <div class="metric-value">{{ detailedStats.actualProcessRate }}</div>
              <div class="metric-label">实际处理 msg/s</div>
            </div>
            <div class="metric-item">
              <div class="metric-value">{{ detailedStats.latencyMs }}</div>
              <div class="metric-label">处理延迟 ms</div>
            </div>
          </div>
        </div>

        <!-- 🚀 缓存优化指标 (新增) -->
        <div v-if="cacheOptimizationEnabled" class="performance-card cache-optimization-metrics">
          <div class="card-header">
            <div class="card-title">🚀 缓存优化</div>
            <div class="card-status" :class="cacheStats.loss_rate < 0.05 ? 'status-excellent' : cacheStats.loss_rate < 0.15 ? 'status-good' : 'status-warning'">
              {{ (cacheStats.loss_rate * 100).toFixed(1) }}% 丢失率
            </div>
          </div>
          <div class="metrics-grid">
            <div class="metric-item">
              <div class="metric-value">{{ (cacheStats.cache_hit_rate * 100).toFixed(1) }}%</div>
              <div class="metric-label">缓存命中率</div>
            </div>
            <div class="metric-item">
              <div class="metric-value">{{ cacheStats.active_vehicles || 0 }}</div>
              <div class="metric-label">活跃车辆缓存</div>
            </div>
            <div class="metric-item">
              <div class="metric-value">{{ cacheStats.retry_count || 0 }}</div>
              <div class="metric-label">重试次数</div>
            </div>
          </div>
        </div>

        <!-- 峰值性能指标 -->
        <div class="performance-card peak-metrics">
          <div class="card-header">
            <div class="card-title">📈 峰值性能</div>
            <div class="card-status status-info">历史最高</div>
          </div>
          <div class="metrics-grid">
            <div class="metric-item">
              <div class="metric-value">{{ detailedStats.peakReceiveRate }}</div>
              <div class="metric-label">峰值接收 msg/s</div>
            </div>
            <div class="metric-item">
              <div class="metric-value">{{ detailedStats.peakProcessRate }}</div>
              <div class="metric-label">峰值处理 msg/s</div>
            </div>
            <div class="metric-item">
              <div class="metric-value">{{ Math.round((detailedStats.peakReceiveRate / 2500) * 100) }}</div>
              <div class="metric-label">理论性能利用率 %</div>
            </div>
          </div>
        </div>

        <!-- 缓冲区状态 -->
        <div class="performance-card buffer-metrics">
          <div class="card-header">
            <div class="card-title">💾 缓冲区状态</div>
            <div class="card-status" :class="detailedStats.bufferUtilization >= 80 ? 'status-warning' : detailedStats.bufferUtilization >= 60 ? 'status-good' : 'status-excellent'">
              {{ detailedStats.bufferUtilization }}% 使用率
            </div>
          </div>
          <div class="metrics-grid">
            <div class="metric-item">
              <div class="metric-value">{{ detailedStats.bufferSize }}</div>
              <div class="metric-label">当前缓冲区</div>
            </div>
            <div class="metric-item">
              <div class="metric-value">{{ detailedStats.bufferCapacity }}</div>
              <div class="metric-label">最大容量</div>
            </div>
            <div class="metric-item">
              <div class="metric-value">{{ detailedStats.bufferOverflows }}</div>
              <div class="metric-label">溢出次数</div>
            </div>
          </div>
        </div>

        <!-- 累计统计 -->
        <div class="performance-card cumulative-metrics">
          <div class="card-header">
            <div class="card-title">📊 累计统计</div>
            <div class="card-status status-info">总计</div>
          </div>
          <div class="metrics-grid">
            <div class="metric-item">
              <div class="metric-value">{{ (detailedStats.messagesReceived || 0).toLocaleString() }}</div>
              <div class="metric-label">总接收消息</div>
            </div>
            <div class="metric-item">
              <div class="metric-value">{{ (detailedStats.messagesProcessed || 0).toLocaleString() }}</div>
              <div class="metric-label">总处理消息</div>
            </div>
            <div class="metric-item">
              <div class="metric-value">{{ (detailedStats.messagesDropped || 0).toLocaleString() }}</div>
              <div class="metric-label">丢弃消息</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 性能提示 -->
      <div v-if="detailedStats.processingEfficiency < 90" class="performance-tips">
        <el-alert
          :title="getPerformanceTip()"
          type="warning"
          :closable="false"
          show-icon
        />
      </div>

      <!-- 🚀 缓存优化建议 (新增) -->
      <div v-if="shouldShowCacheOptimizationSuggestion" class="cache-optimization-suggestion">
        <el-alert
          title="💡 建议启用缓存优化模式"
          :description="getCacheOptimizationSuggestion()"
          type="info"
          show-icon
          :closable="false"
        >
          <template #default>
            <div class="suggestion-actions">
              <el-button 
                type="primary" 
                size="small"
                @click="enableCacheOptimization"
                :loading="cacheOptimizationLoading"
              >
                🚀 立即启用
              </el-button>
            </div>
          </template>
        </el-alert>
      </div>
    </div>

    <!-- 🔍 智能搜索功能 -->
    <div v-if="connectionStatus === 'connected'" class="search-section">
      <div class="search-container">
        <div class="search-header">
          <h3>🔍 车辆智能搜索</h3>
          <div class="search-stats">
            <span class="search-stat">总计: {{ Object.keys(vehicleData).length }}辆</span>
            <span class="search-stat">已筛选: {{ filteredVehicles.length }}辆</span>
          </div>
        </div>
        
        <!-- 搜索输入框和过滤器（横向排列） -->
        <div class="search-input-section">
          <div class="search-row">
            <el-input
              v-model="searchQuery"
              placeholder="🔍 搜索车辆ID、车型、位置..."
              class="search-input-horizontal"
              clearable
              @input="handleSearchInput"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            
            <el-select 
              v-model="searchFilter.vehicleType" 
              placeholder="车型"
              clearable
              @change="applyFilters"
              class="filter-select-horizontal"
            >
              <el-option
                v-for="type in availableVehicleTypes"
                :key="type.value"
                :label="type.icon + ' ' + type.label"
                :value="type.value"
              >
                <span>{{ type.icon }} {{ type.label }}</span>
              </el-option>
            </el-select>
            
            <el-select 
              v-model="searchFilter.location" 
              placeholder="地区"
              clearable
              @change="applyFilters"
              class="filter-select-horizontal"
            >
              <el-option
                v-for="location in availableLocations"
                :key="location.value"
                :label="location.label"
                :value="location.value"
              >
                <span>📍 {{ location.label }}</span>
              </el-option>
            </el-select>
            
            <el-select 
              v-model="searchFilter.healthStatus" 
              placeholder="状态"
              clearable
              @change="applyFilters"
              class="filter-select-horizontal"
            >
              <el-option label="🟢 健康" value="healthy"></el-option>
              <el-option label="🟡 预警" value="warning"></el-option>
              <el-option label="🔴 故障" value="danger"></el-option>
            </el-select>
            
            <el-button type="primary" @click="clearFilters" class="clear-filters-btn-horizontal">
              清除
            </el-button>
          </div>
        </div>

        <!-- 搜索结果快速访问 -->
        <div v-if="searchQuery || hasActiveFilters" class="search-results">
          <div class="results-header">
            <span class="results-title">🎯 搜索结果 ({{ searchResults.length }})</span>
            <span v-if="searchResults.length === 0" class="no-results">未找到匹配的车辆</span>
          </div>
          
          <div v-if="searchResults.length > 0" class="results-grid">
            <div 
              v-for="vehicle in searchResults" 
              :key="vehicle.vehicleId"
              class="result-item"
              @click="quickAccessVehicle(vehicle.vehicleId)"
            >
              <div class="result-header">
                <span class="result-icon">{{ getVehicleIcon(vehicle.vehicleId) }}</span>
                <span class="result-name">{{ getVehicleName(vehicle.vehicleId) }}</span>
                <el-tag :type="getVehicleStatusType(vehicle)" size="small">
                  {{ getVehicleStatusText(vehicle) }}
                </el-tag>
              </div>
              <div class="result-details">
                <div class="result-detail">
                  <span class="detail-label">型号:</span>
                  <span class="detail-value">{{ getVehicleModel(vehicle.vehicleId) }}</span>
                </div>
                <div class="result-detail">
                  <span class="detail-label">位置:</span>
                  <span class="detail-value">{{ getLocationFromVehicleId(vehicle.vehicleId) }}</span>
                </div>
                <div class="result-detail">
                  <span class="detail-label">健康度:</span>
                  <span class="detail-value" :style="{ color: getHealthColor(vehicle.overall?.health_score) }">
                    {{ (vehicle.overall?.health_score || 0).toFixed(1) }}%
                  </span>
                </div>
              </div>
              <div class="result-actions">
                <el-button 
                  type="primary" 
                  size="small" 
                  @click.stop="viewVehicleDetails(vehicle.vehicleId)"
                  class="quick-access-btn"
                >
                  💻 监控界面
                </el-button>
                <el-button 
                  type="success" 
                  size="small" 
                  @click.stop="scrollToVehicleCard(vehicle.vehicleId)"
                  class="locate-btn"
                >
                  🎯 定位
                </el-button>
              </div>
            </div>
          </div>
        </div>

        <!-- 常用车辆快速访问 -->
        <div v-if="!searchQuery && !hasActiveFilters" class="quick-access-section">
          <div class="quick-access-header">
            <h4>⭐ 常用车辆快速访问</h4>
            <el-button link size="small" @click="refreshFavorites">刷新</el-button>
          </div>
          <div class="favorites-grid">
            <div 
              v-for="vehicleId in favoriteVehicles" 
              :key="vehicleId"
              class="favorite-item"
              @click="quickAccessVehicle(vehicleId)"
            >
              <div class="favorite-icon">{{ getVehicleIcon(vehicleId) }}</div>
              <div class="favorite-info">
                <div class="favorite-name">{{ getVehicleName(vehicleId) }}</div>
                <div class="favorite-model">{{ getVehicleModel(vehicleId) }}</div>
              </div>
              <div class="favorite-status">
                <div 
                  class="status-dot" 
                  :class="vehicleData[vehicleId] ? getVehicleCardClass(vehicleData[vehicleId]) : 'offline'"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 🚗 车辆列表展示 -->
    <div v-if="connectionStatus === 'connected'" class="vehicle-grid">
      <div 
        v-for="(vehicle, vehicleId) in vehicleData" 
        :key="vehicleId"
        :data-vehicle-id="vehicleId"
        class="vehicle-card"
        :class="getVehicleCardClass(vehicle)"
        @click="toggleVehicleDetails(vehicleId)"
      >
        <!-- 车辆基本信息头部 -->
        <div class="vehicle-header">
          <div class="vehicle-info">
            <div class="vehicle-title">
              <span class="vehicle-icon">{{ getVehicleIcon(vehicleId) }}</span>
              <span class="vehicle-name">{{ getVehicleName(vehicleId) }}</span>
              <el-tag :type="getVehicleStatusType(vehicle)" size="small">
                {{ getVehicleStatusText(vehicle) }}
              </el-tag>
            </div>
            <div class="vehicle-location">
              📍 {{ getLocationFromVehicleId(vehicleId) }}
            </div>
          </div>
          <div class="vehicle-actions">
            <el-button 
              type="primary" 
              link 
              @click.stop="viewVehicleDetails(vehicleId)"
              class="detail-btn"
            >
              详情 →
            </el-button>
            <div class="expand-indicator" :class="{ expanded: expandedVehicles.has(vehicleId) }">
              {{ expandedVehicles.has(vehicleId) ? '▼' : '▶️' }}
            </div>
          </div>
        </div>

        <!-- 车辆快速状态指标 -->
        <div class="vehicle-status-bar">
          <div class="status-metrics">
            <div class="metric-item">
              <div class="metric-icon">❤️</div>
              <div class="metric-value" :style="{ color: getHealthColor(vehicle.overall?.health_score) }">
                {{ (vehicle.overall?.health_score || 0).toFixed(1) }}%
              </div>
              <div class="metric-label">健康度</div>
            </div>
            <div class="metric-item">
              <div class="metric-icon">⚡</div>
              <div class="metric-value">
                {{ getFaultCount(vehicle) }}
              </div>
              <div class="metric-label">故障项</div>
            </div>
            <div class="metric-item">
              <div class="metric-icon">🕐</div>
              <div class="metric-value">
                {{ getLastUpdateTime(vehicle) }}
              </div>
              <div class="metric-label">更新</div>
            </div>
            <div class="metric-item">
              <div class="metric-icon">📊</div>
              <div class="metric-value">
                {{ vehicle.messageCount || 0 }}
              </div>
              <div class="metric-label">消息数</div>
            </div>
          </div>
        </div>

        <!-- 故障类型快速状态 -->
        <div class="fault-status-grid">
          <div 
            v-for="faultType in faultTypes" 
            :key="faultType.type"
            class="fault-status-item"
            :class="getFaultStatusClass(vehicle[faultType.type])"
            @click.stop="viewFaultDetails(vehicleId, faultType.type)"
          >
            <div class="fault-icon">{{ getFaultIcon(faultType.type) }}</div>
            <div class="fault-name">{{ getFaultShortName(faultType.name) }}</div>
            <div class="fault-score">
              {{ getFaultScore(vehicle[faultType.type]).toFixed(1) }}
            </div>
          </div>
        </div>

        <!-- 展开的详细信息 -->
        <div v-if="expandedVehicles.has(vehicleId)" class="vehicle-details">
          <el-divider content-position="left">实时数据</el-divider>
          
          <!-- 实时图表预览 -->
          <div class="mini-charts-grid">
            <div 
              v-for="faultType in faultTypes" 
              :key="`${vehicleId}-${faultType.type}`"
              class="mini-chart-container"
            >
              <div class="mini-chart-header">
                <span>{{ getFaultShortName(faultType.name) }}</span>
                <el-tag :type="getFaultTagType(vehicle[faultType.type])" size="mini">
                  {{ getFaultStatusText(vehicle[faultType.type]) }}
                </el-tag>
              </div>
              <div class="mini-chart" :id="`mini-chart-${vehicleId}-${faultType.type}`">
                <!-- 小型图表将在这里渲染 -->
                <div class="chart-placeholder">
                  <div class="chart-value">
                    {{ getFaultScore(vehicle[faultType.type]).toFixed(1) }}
                  </div>
                  <div class="chart-trend" :class="getTrendClass(vehicle[faultType.type])">
                    {{ getTrendIcon(vehicle[faultType.type]) }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 车辆特征信息 -->
          <div class="vehicle-features">
            <div class="feature-row">
              <span class="feature-label">车辆型号:</span>
              <span class="feature-value">{{ getVehicleModel(vehicleId) }}</span>
            </div>
            <div class="feature-row">
              <span class="feature-label">注册时间:</span>
              <span class="feature-value">{{ formatTime(vehicle.firstSeen) }}</span>
            </div>
            <div class="feature-row">
              <span class="feature-label">运行时长:</span>
              <span class="feature-value">{{ getRunningDuration(vehicle) }}</span>
            </div>
            <div class="feature-row">
              <span class="feature-label">数据频率:</span>
              <span class="feature-value">{{ getDataFrequency(vehicle) }}</span>
            </div>
            <div class="feature-row">
              <span class="feature-label">最后更新:</span>
              <span class="feature-value">{{ formatDetailedTime(vehicle.lastUpdate) }}</span>
            </div>
            <div class="feature-row">
              <span class="feature-label">监控状态:</span>
              <span class="feature-value" :style="{ color: getMonitoringStatusColor(vehicle) }">
                {{ getMonitoringStatusText(vehicle) }}
              </span>
            </div>
          </div>

          <!-- 时间记录详情 -->
          <el-divider content-position="left">⏰ 时间记录</el-divider>
          <div class="time-records">
            <div class="time-record-grid">
              <div class="time-record-item">
                <div class="time-record-label">🚀 首次连接</div>
                <div class="time-record-value">{{ formatDetailedTime(vehicle.firstSeen) }}</div>
                <div class="time-record-duration">{{ getTimeSince(vehicle.firstSeen) }}前</div>
              </div>
              <div class="time-record-item">
                <div class="time-record-label">📡 最新数据</div>
                <div class="time-record-value">{{ formatDetailedTime(vehicle.lastUpdate) }}</div>
                <div class="time-record-duration">{{ getTimeSince(vehicle.lastUpdate) }}前</div>
              </div>
              <div class="time-record-item">
                <div class="time-record-label">⚡ 累计在线</div>
                <div class="time-record-value">{{ getRunningDuration(vehicle) }}</div>
                <div class="time-record-duration">持续监控中</div>
              </div>
              <div class="time-record-item">
                <div class="time-record-label">📊 数据统计</div>
                <div class="time-record-value">{{ vehicle.messageCount || 0 }} 条消息</div>
                <div class="time-record-duration">{{ getDataFrequency(vehicle) }}</div>
              </div>
            </div>
          </div>

          <!-- 故障时间记录 -->
          <el-divider content-position="left">🔍 故障时间记录</el-divider>
          <div class="fault-time-records">
            <div 
              v-for="faultType in faultTypes" 
              :key="`time-${vehicleId}-${faultType.type}`"
              class="fault-time-item"
              :class="getFaultTimeItemClass(vehicle[faultType.type])"
            >
              <div class="fault-time-header">
                <span class="fault-time-icon">{{ getFaultIcon(faultType.type) }}</span>
                <span class="fault-time-name">{{ getFaultShortName(faultType.name) }}</span>
                <el-tag :type="getFaultTagType(vehicle[faultType.type])" size="mini">
                  {{ getFaultStatusText(vehicle[faultType.type]) }}
                </el-tag>
              </div>
              <div class="fault-time-details">
                <div class="fault-time-detail">
                  <span class="detail-label">当前评分:</span>
                  <span class="detail-value">{{ getFaultScore(vehicle[faultType.type]).toFixed(2) }}</span>
                </div>
                <div class="fault-time-detail">
                  <span class="detail-label">最后检测:</span>
                  <span class="detail-value">{{ formatDetailedTime(vehicle[faultType.type]?.lastUpdate) }}</span>
                </div>
                <div class="fault-time-detail">
                  <span class="detail-label">状态持续:</span>
                  <span class="detail-value">{{ getTimeSince(vehicle[faultType.type]?.lastUpdate) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="connectionStatus === 'connected' && Object.keys(vehicleData).length === 0" class="empty-state">
      <div class="empty-icon">🚗💨</div>
      <div class="empty-text">暂无车辆数据</div>
      <div class="empty-hint">请启动车辆模拟器或检查数据连接</div>
    </div>

    <!-- 断开连接状态 -->
    <div v-else class="disconnected-state">
      <div class="disconnected-icon">📡❌</div>
      <div class="disconnected-text">未连接到数据源</div>
      <div class="disconnected-hint">点击"开始监控"按钮连接到实时数据流</div>
      <div class="disconnected-note">只有点击开始监控按钮后，系统才会开始处理数据</div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Search, User, ArrowDown, SwitchButton } from '@element-plus/icons-vue';
import { ensureConnected, subscribe, getState, onMessage } from '@/stores/realtimeStore.js';
import api from '@/api/index.js';
import { globalOptimizer, VehicleDataManager, HistoryDataManager } from '@/utils/performanceOptimizer.js';

const router = useRouter();

// ==========================================
// 响应式数据
// ==========================================

// 用户相关
const currentUser = ref('管理员');

// 连接状态
const connectionStatus = ref('disconnected');
const isMonitoring = ref(false);
const expandedVehicles = ref(new Set());

// 监控时间追踪
const monitoringStartTime = ref(null);
const monitoringTimer = ref(null);
const currentTime = ref(Date.now()); // 添加当前时间追踪，用于触发计算属性更新

// 🚀 性能优化：使用车辆数据管理器
const vehicleDataManager = new VehicleDataManager(globalOptimizer);
const vehicleData = reactive({});

// 性能监控
const performanceMetrics = ref({
  messageRate: 0,
  memoryUsage: '0 MB',
  updateTime: '0 ms',
  lastUpdate: null,
  lastMessageCount: 0
});

// 🚀 详细WebSocket性能统计
const detailedStats = ref({
  // 实时指标
  rawReceiveRate: 0,
  actualProcessRate: 0,
  bufferUtilization: 0,
  latencyMs: 0,
  
  // 峰值指标
  peakReceiveRate: 0,
  peakProcessRate: 0,
  
  // 平均指标
  avgReceiveRate: 0,
  avgProcessRate: 0,
  
  // 累计统计
  messagesReceived: 0,
  messagesProcessed: 0,
  messagesDropped: 0,
  bufferOverflows: 0,
  
  // 缓冲区状态
  bufferSize: 0,
  bufferCapacity: 500,
  
  // 处理效率
  processingEfficiency: 100,
  
  // 连接状态
  isConnected: false,
  reconnectAttempts: 0
});

// 性能监控定时器
let performanceUpdateTimer = null;

// 🚀 批量处理相关变量
let batchUpdateQueue = new Set(); // 需要更新健康评分的车辆ID队列
let batchUpdateTimer = null;
const BATCH_UPDATE_INTERVAL = 100; // 100ms批量更新一次健康评分

// 🚀 消息缓存优化
const messageCache = {
  lastUpdate: 0,
  updateInterval: 50, // 50ms内的重复更新将被忽略
};

// 故障类型定义
const faultTypes = ref([
  { type: 'turn_fault', name: '匝间短路故障', icon: '🎯' },
  { type: 'insulation', name: '绝缘失效故障', icon: '🔌' },
  { type: 'bearing', name: '轴承故障', icon: '⚙️' },
  { type: 'eccentricity', name: '偏心故障', icon: '🔄' },
  { type: 'broken_bar', name: '断条故障', icon: '🔗' }
]);

// 🔍 搜索功能相关数据
const searchQuery = ref('');
const searchFilter = reactive({
  vehicleType: '',
  location: '',
  healthStatus: ''
});

// 常用车辆（这里可以从localStorage读取或基于访问频率）
const favoriteVehicles = ref([
  'SEAL_粤B_001',
  'QIN_陕A_002', 
  'HAN_陕A_003',
  'TANG_粤A_004',
  'SONG_沪A_005'
]);

// 辅助函数：获取故障评分（兼容新旧字段名）
const getFaultScore = (faultData) => {
  if (!faultData) return 0;
  return faultData.fault_score !== undefined ? faultData.fault_score : (faultData.score || 0);
};

// 可用的搜索选项
const availableVehicleTypes = computed(() => [
  { value: 'SEAL', label: '海豹', icon: '🦭' },
  { value: 'QIN', label: '比亚迪秦', icon: '🏮' },
  { value: 'HAN', label: '比亚迪汉', icon: '🏛️' },
  { value: 'TANG', label: '比亚迪唐', icon: '🏯' },
  { value: 'SONG', label: '比亚迪宋', icon: '🎵' },
  { value: 'YUAN', label: '比亚迪元', icon: '💰' },
  { value: 'DOLPHIN', label: '比亚迪海豚', icon: '🐬' },
  { value: 'SEAGULL', label: '比亚迪海鸥', icon: '🕊️' },
  { value: 'FRIGATE', label: '护卫舰07', icon: '🚢' },
  { value: 'DESTROYER', label: '驱逐舰05', icon: '⚓' }
]);

const availableLocations = computed(() => [
  { value: '深圳', label: '深圳福田区' },
  { value: '西安', label: '西安高新区' },
  { value: '广州', label: '广州天河区' },
  { value: '上海', label: '上海浦东区' },
  { value: '北京', label: '北京海淀区' },
  { value: '南京', label: '南京鼓楼区' },
  { value: '杭州', label: '杭州滨江区' },
  { value: '成都', label: '成都高新区' },
  { value: '重庆', label: '重庆渝中区' }
]);

// 计算属性：是否有活跃的过滤器
const hasActiveFilters = computed(() => {
  return searchFilter.vehicleType || searchFilter.location || searchFilter.healthStatus;
});

// 计算属性：过滤后的车辆列表
const filteredVehicles = computed(() => {
  let vehicles = Object.values(vehicleData);
  
  // 应用搜索查询
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    vehicles = vehicles.filter(vehicle => {
      const vehicleId = vehicle.vehicleId?.toLowerCase() || '';
      const vehicleName = getVehicleName(vehicle.vehicleId).toLowerCase();
      const vehicleModel = getVehicleModel(vehicle.vehicleId).toLowerCase();
      const location = getLocationFromVehicleId(vehicle.vehicleId).toLowerCase();
      
      return vehicleId.includes(query) || 
             vehicleName.includes(query) || 
             vehicleModel.includes(query) || 
             location.includes(query);
    });
  }
  
  // 应用车型过滤器
  if (searchFilter.vehicleType) {
    vehicles = vehicles.filter(vehicle => 
      vehicle.vehicleId?.includes(searchFilter.vehicleType)
    );
  }
  
  // 应用位置过滤器
  if (searchFilter.location) {
    vehicles = vehicles.filter(vehicle => 
      getLocationFromVehicleId(vehicle.vehicleId).includes(searchFilter.location)
    );
  }
  
  // 应用健康状态过滤器
  if (searchFilter.healthStatus) {
    vehicles = vehicles.filter(vehicle => {
      const healthScore = vehicle.overall?.health_score || 0;
      switch (searchFilter.healthStatus) {
        case 'healthy':
          return healthScore >= 90;
        case 'warning':
          return healthScore >= 70 && healthScore < 90;
        case 'danger':
          return healthScore < 70;
        default:
          return true;
      }
    });
  }
  
  return vehicles;
});

// 搜索结果（限制显示数量以提高性能）
const searchResults = computed(() => {
  return filteredVehicles.value.slice(0, 20); // 最多显示20个结果
});

// ==========================================
// 数据处理和管理
// ==========================================

// 🚀 高性能消息处理
const handleMessage = (message) => {
  try {
    const data = typeof message === 'string' ? JSON.parse(message) : message;
    
    // 快速验证：检查必要字段
    if (!data.vehicle_id || !data.fault_type) {
      return; // 静默跳过无效消息，减少console输出
    }
    
    // 快速检查是否有有效的评分数据
    const score = data.fault_score ?? data.score ?? data.fault_severity;
    if (score === undefined) {
      return; // 跳过无评分数据的消息
    }
    
    // 🚀 高效更新车辆数据（避免频繁计算）
    updateVehicleDataFast(data);
    
    // 🚀 节流更新性能指标（避免过度频繁更新）
    const now = Date.now();
    if (now - messageCache.lastUpdate > messageCache.updateInterval) {
    updatePerformanceMetrics();
      messageCache.lastUpdate = now;
    }
  } catch (error) {
    // 减少错误日志频率，避免影响性能
    if (Math.random() < 0.01) { // 只记录1%的错误
    console.error('处理消息失败:', error);
    }
  }
};

// 🚀 高性能车辆数据更新（使用性能优化器）
const updateVehicleDataFast = (data) => {
  const vehicleId = data.vehicle_id;
  
  // 使用性能优化的车辆数据管理器
  const success = vehicleDataManager.updateVehicle(vehicleId, data);
  if (!success) return; // 被节流跳过
  
  // 节流更新UI数据
  globalOptimizer.throttleUpdate(`ui_${vehicleId}`, () => {
    const optimizedData = vehicleDataManager.getVehicleData();
    // 限制车辆数量，防止内存溢出
    globalOptimizer.limitObjectSize(optimizedData, 50);
    
    // 批量更新reactive数据
    Object.assign(vehicleData, optimizedData);
    
    // 批量更新健康评分
    batchUpdateQueue.add(vehicleId);
    scheduleBatchHealthUpdate();
  }, 100);
};

// 🚀 批量健康评分更新调度器
const scheduleBatchHealthUpdate = () => {
  if (batchUpdateTimer) return; // 已有定时器，不重复创建
  
  batchUpdateTimer = setTimeout(() => {
    // 批量处理所有需要更新的车辆
    for (const vehicleId of batchUpdateQueue) {
      updateOverallHealthFast(vehicleId);
    }
    
    // 清空队列和定时器
    batchUpdateQueue.clear();
    batchUpdateTimer = null;
  }, BATCH_UPDATE_INTERVAL);
};

// 🚀 高性能健康评分更新
const updateOverallHealthFast = (vehicleId) => {
  const vehicle = vehicleData[vehicleId];
  if (!vehicle) return;
  
  let totalScore = 0;
  let faultCount = 0;
  
  // 🚀 优化：使用for循环替代forEach，减少函数调用开销
  const faultTypesList = faultTypes.value;
  for (let i = 0; i < faultTypesList.length; i++) {
    const faultData = vehicle[faultTypesList[i].type];
    if (faultData && faultData.score !== undefined) {
      // 🚀 直接使用score字段，避免函数调用
      const score = faultData.score;
      if (typeof score === 'number' && score >= 0) {
        totalScore += Math.max(0, 100 - score);
        faultCount++;
      }
    }
  }
  
  // 🚀 只在有变化时更新，减少Vue响应式触发
  const newHealthScore = faultCount > 0 ? totalScore / faultCount : 100;
  if (vehicle.overall.health_score !== newHealthScore) {
  vehicle.overall.health_score = newHealthScore;
  }
};

// ==========================================
// WebSocket 连接管理
// ==========================================

// 开始监控
const startMonitoring = async () => {
  try {
    connectionStatus.value = 'connecting';
    
    // 1. 首先启动桥接器
    ElMessage.info('🔌 正在启动数据桥接器...');
    await api.startStreamBridge();
    
    // 2. 全局存储负责WS连接，这里订阅状态
    const unsubscribe = subscribe(() => {
      const snap = getState();
      if (snap.isConnected) {
        connectionStatus.value = 'connected';
        isMonitoring.value = true;
        ElMessage.success('📡 已连接到车队数据流 - 数据将实时处理并显示');
        if (!monitoringStartTime.value) {
          monitoringStartTime.value = new Date();
          startMonitoringTimer();
          startPerformanceMonitoring();
        }
      }
    });
    // 记录在本地，组件卸载时移除订阅（不影响全局会话）
    if (!window.__vtox_fleet_unsubs) window.__vtox_fleet_unsubs = [];
    window.__vtox_fleet_unsubs.push(unsubscribe);
    
    // 3. 订阅全局原始消息，驱动本地数据更新
    const offMessage = onMessage((raw) => {
      handleMessage(raw);
    });
    window.__vtox_fleet_unsubs.push(offMessage);

    // 4. 连接由全局 store 保证
    ElMessage.info('📡 正在建立WebSocket连接...');
    await ensureConnected();
    
  } catch (error) {
    connectionStatus.value = 'error';
    ElMessage.error(`启动监控失败: ${error.message || '未知错误'}`);
  }
};

// 停止监控
const stopMonitoring = async () => {
  try {
    // 1. 全局持久化：不主动断开全局WS，仅更新本地状态
    ElMessage.info('📡 已停止本地监控展示（全局会话保持）');
    connectionStatus.value = 'disconnected';
    isMonitoring.value = false;
    
    // 2. 然后停止桥接器
    ElMessage.info('🔌 正在停止数据桥接器...');
    await api.stopStreamBridge();
    
    // 重置监控时间
    monitoringStartTime.value = null;
    currentTime.value = Date.now();
    
    stopMonitoringTimer();
    stopPerformanceMonitoring(); // 🚀 停止详细性能监控
    ElMessage.success('🛑 监控系统已停止 - 数据处理暂停');
  } catch (error) {
    ElMessage.error(`停止监控失败: ${error.message || '未知错误'}`);
  }
};

// 启动定时器
const startMonitoringTimer = () => {
  if (monitoringTimer.value) {
    clearInterval(monitoringTimer.value);
  }
  monitoringTimer.value = setInterval(() => {
    // 更新当前时间以触发监控时间计算
    currentTime.value = Date.now();
    // 更新性能指标
    updatePerformanceMetrics();
  }, 1000); // 每秒更新一次
};

// 停止定时器
const stopMonitoringTimer = () => {
  if (monitoringTimer.value) {
    clearInterval(monitoringTimer.value);
    monitoringTimer.value = null;
  }
};

// ==========================================
// 界面交互
// ==========================================

// 处理用户下拉菜单命令
const handleUserCommand = (command) => {
  switch (command) {
    case 'logout':
      handleLogout();
      break;
    default:
      // console.log('未知命令:', command);
  }
};

// 处理用户登出
const handleLogout = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要退出登录吗？',
      '退出确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    );
    
    // 停止监控
    if (connectionStatus.value === 'connected') {
      stopMonitoring();
    }
    
    // 清除登录信息
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_info');
    
    // 跳转到登录页
    router.push('/auth/login');
    
    ElMessage.success('已退出登录');
  } catch {
    // 用户取消
  }
};

// 切换车辆详情展开/收缩
const toggleVehicleDetails = (vehicleId) => {
  if (expandedVehicles.value.has(vehicleId)) {
    expandedVehicles.value.delete(vehicleId);
  } else {
    expandedVehicles.value.add(vehicleId);
  }
};

// 查看车辆详情页面
const viewVehicleDetails = (vehicleId) => {
  router.push({
    name: 'VehicleDetail',
    params: { vehicleId },
    query: { from: 'fleet-monitor' }
  });
};

// 查看故障详情
const viewFaultDetails = (vehicleId, faultType) => {
  router.push({
    name: 'FaultDetail',
    params: { vehicleId, faultType },
    query: { from: 'fleet-monitor' }
  });
};

// 重置所有数据
const resetAllData = async () => {
  try {
    await ElMessageBox.confirm(
      '这将清空所有车辆的历史数据，确定要继续吗？',
      '重置确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    );
    
    // 清空车辆数据
    Object.keys(vehicleData).forEach(key => {
      delete vehicleData[key];
    });
    
    // 重置展开状态
    expandedVehicles.value.clear();
    
    // 重置监控时间
    if (isMonitoring.value) {
      monitoringStartTime.value = new Date();
    }
    
    // 重置性能指标（保留lastUpdate以确保消息速率计算正常）
    const currentLastUpdate = performanceMetrics.value.lastUpdate;
    performanceMetrics.value = {
      messageRate: 0,
      memoryUsage: '0 MB',
      updateTime: '0 ms',
      lastUpdate: currentLastUpdate // 保留当前时间戳
    };
    
    // 🚀 重置详细性能数据
    resetPerformanceData();
    
    ElMessage.success('✅ 数据已重置');
  } catch {
    // 用户取消
  }
};

// ==========================================
// 🔍 搜索功能方法
// ==========================================

// 处理搜索输入
const handleSearchInput = (value) => {
  // 实时搜索，可以添加防抖以提高性能
  // 这里简化处理，直接使用计算属性
};

// 应用过滤器
const applyFilters = () => {
  // 过滤器变化时的处理逻辑
  // 由于使用了计算属性，这里主要用于触发重新计算
};

// 清除所有过滤器
const clearFilters = () => {
  searchQuery.value = '';
  searchFilter.vehicleType = '';
  searchFilter.location = '';
  searchFilter.healthStatus = '';
};

// 快速访问车辆（跳转到详情页面）
const quickAccessVehicle = (vehicleId) => {
  // 记录访问历史（可以用于更新常用车辆列表）
  addToAccessHistory(vehicleId);
  
  // 跳转到车辆详情页面
  router.push({
    name: 'VehicleDetail',
    params: { vehicleId },
    query: { from: 'fleet-monitor', source: 'search' }
  });
};

// 滚动到车辆卡片
const scrollToVehicleCard = (vehicleId) => {
  // 如果搜索结果中有该车辆，先清除搜索以显示所有车辆
  if (searchQuery.value || hasActiveFilters.value) {
    clearFilters();
    
    // 等待DOM更新后再滚动
    nextTick(() => {
      scrollToVehicleElement(vehicleId);
    });
  } else {
    scrollToVehicleElement(vehicleId);
  }
};

// 滚动到车辆元素
const scrollToVehicleElement = (vehicleId) => {
  // 查找车辆卡片元素并滚动到它
  const vehicleCard = document.querySelector(`[data-vehicle-id="${vehicleId}"]`);
  if (vehicleCard) {
    vehicleCard.scrollIntoView({ 
      behavior: 'smooth', 
      block: 'center' 
    });
    
    // 高亮显示车辆卡片
    vehicleCard.classList.add('highlight');
    setTimeout(() => {
      vehicleCard.classList.remove('highlight');
    }, 3000);
  } else {
    ElMessage.warning(`车辆 ${vehicleId} 暂未在线`);
  }
};

// 添加到访问历史
const addToAccessHistory = (vehicleId) => {
  // 这里可以实现访问历史记录功能
      // console.log(`访问车辆: ${vehicleId}`);
  
  // 更新常用车辆列表（移动到前面）
  const index = favoriteVehicles.value.indexOf(vehicleId);
  if (index > -1) {
    favoriteVehicles.value.splice(index, 1);
  }
  favoriteVehicles.value.unshift(vehicleId);
  
  // 限制常用车辆数量
  if (favoriteVehicles.value.length > 8) {
    favoriteVehicles.value = favoriteVehicles.value.slice(0, 8);
  }
  
  // 可以保存到localStorage
  try {
    localStorage.setItem('favoriteVehicles', JSON.stringify(favoriteVehicles.value));
  } catch (error) {
    console.warn('无法保存常用车辆列表:', error);
  }
};

// 刷新常用车辆
const refreshFavorites = () => {
  // 基于当前在线车辆更新常用列表
  const onlineVehicles = Object.keys(vehicleData);
  favoriteVehicles.value = favoriteVehicles.value.filter(vehicleId => 
    onlineVehicles.includes(vehicleId)
  );
  
  // 如果常用车辆少于5个，添加一些在线车辆
  if (favoriteVehicles.value.length < 5) {
    const additionalVehicles = onlineVehicles
      .filter(vehicleId => !favoriteVehicles.value.includes(vehicleId))
      .slice(0, 5 - favoriteVehicles.value.length);
    
    favoriteVehicles.value.push(...additionalVehicles);
  }
  
  ElMessage.success('已刷新常用车辆列表');
};

// 获取搜索建议（可选功能）
const getSearchSuggestions = (query) => {
  if (!query) return [];
  
  const suggestions = [];
  const vehicles = Object.values(vehicleData);
  
  vehicles.forEach(vehicle => {
    const vehicleId = vehicle.vehicleId;
    const vehicleName = getVehicleName(vehicleId);
    const vehicleModel = getVehicleModel(vehicleId);
    const location = getLocationFromVehicleId(vehicleId);
    
    if (vehicleId.toLowerCase().includes(query.toLowerCase())) {
      suggestions.push({
        type: 'vehicle_id',
        value: vehicleId,
        label: `车辆ID: ${vehicleId}`,
        icon: '🔍'
      });
    }
    
    if (vehicleModel.toLowerCase().includes(query.toLowerCase())) {
      suggestions.push({
        type: 'model',
        value: vehicleModel,
        label: `车型: ${vehicleModel}`,
        icon: '🚗'
      });
    }
    
    if (location.toLowerCase().includes(query.toLowerCase())) {
      suggestions.push({
        type: 'location',
        value: location,
        label: `位置: ${location}`,
        icon: '📍'
      });
    }
  });
  
  // 去重并限制数量
  const uniqueSuggestions = suggestions.filter((item, index, self) => 
    index === self.findIndex(t => t.value === item.value && t.type === item.type)
  );
  
  return uniqueSuggestions.slice(0, 10);
};

// ==========================================
// 工具函数
// ==========================================

// 获取车辆图标
const getVehicleIcon = (vehicleId) => {
  if (vehicleId.includes('SEAL')) return '🦭';
  if (vehicleId.includes('QIN')) return '🏮';
  if (vehicleId.includes('HAN')) return '🏛️';
  if (vehicleId.includes('TANG')) return '🏯';
  if (vehicleId.includes('SONG')) return '🎵';
  if (vehicleId.includes('YUAN')) return '💰';
  if (vehicleId.includes('DOLPHIN')) return '🐬';
  if (vehicleId.includes('SEAGULL')) return '🕊️';
  if (vehicleId.includes('FRIGATE')) return '🚢';
  if (vehicleId.includes('DESTROYER')) return '⚓';
  return '🚗';
};

// 获取车辆名称
const getVehicleName = (vehicleId) => {
  const parts = vehicleId.split('_');
  return parts.length > 1 ? parts.slice(0, -1).join('_') : vehicleId;
};

// 获取车辆型号
const getVehicleModel = (vehicleId) => {
  if (vehicleId.includes('SEAL')) return '比亚迪海豹';
  if (vehicleId.includes('QIN')) return '比亚迪秦';
  if (vehicleId.includes('HAN')) return '比亚迪汉';
  if (vehicleId.includes('TANG')) return '比亚迪唐';
  if (vehicleId.includes('SONG')) return '比亚迪宋';
  if (vehicleId.includes('YUAN')) return '比亚迪元';
  if (vehicleId.includes('DOLPHIN')) return '比亚迪海豚';
  if (vehicleId.includes('SEAGULL')) return '比亚迪海鸥';
  if (vehicleId.includes('FRIGATE')) return '比亚迪护卫舰07';
  if (vehicleId.includes('DESTROYER')) return '比亚迪驱逐舰05';
  return '未知型号';
};

// 从车辆ID获取位置信息
const getLocationFromVehicleId = (vehicleId) => {
  if (!vehicleId) return '未知位置';
  if (vehicleId.includes('粤B') || vehicleId.includes('SEAL')) return '深圳福田区';
  if (vehicleId.includes('陕A') && vehicleId.includes('QIN')) return '西安高新区';
  if (vehicleId.includes('陕A') && vehicleId.includes('HAN')) return '西安雁塔区';
  if (vehicleId.includes('粤A') && vehicleId.includes('TANG')) return '广州天河区';
  if (vehicleId.includes('沪A') && vehicleId.includes('SONG')) return '上海浦东区';
  if (vehicleId.includes('京A') && vehicleId.includes('YUAN')) return '北京海淀区';
  if (vehicleId.includes('苏A') && vehicleId.includes('DOLPHIN')) return '南京鼓楼区';
  if (vehicleId.includes('浙A') && vehicleId.includes('SEAGULL')) return '杭州滨江区';
  if (vehicleId.includes('川A') && vehicleId.includes('FRIGATE')) return '成都高新区';
  if (vehicleId.includes('渝A') && vehicleId.includes('DESTROYER')) return '重庆渝中区';
  return '未知位置';
};

// 获取故障图标
const getFaultIcon = (faultType) => {
  const iconMap = {
    'turn_fault': '🎯',
    'insulation': '🔌',
    'bearing': '⚙️',
    'eccentricity': '🔄',
    'broken_bar': '🔗'
  };
  return iconMap[faultType] || '❓';
};

// 获取故障简短名称
const getFaultShortName = (fullName) => {
  return fullName.replace('故障', '').substring(0, 4);
};

// 获取健康度颜色
const getHealthColor = (score) => {
  if (score >= 90) return '#67c23a';
  if (score >= 70) return '#e6a23c';
  if (score >= 50) return '#f56c6c';
  return '#909399';
};

// 获取连接状态文本
const getConnectionStatusText = (status) => {
  const statusMap = {
    'disconnected': '离线',
    'connecting': '连接中',
    'connected': '在线',
    'error': '错误'
  };
  return statusMap[status] || status;
};

// 获取连接状态类型
const getConnectionStatusType = (status) => {
  const typeMap = {
    'disconnected': 'info',
    'connecting': 'warning',
    'connected': 'success',
    'error': 'danger'
  };
  return typeMap[status] || 'info';
};

// 获取车辆状态
const getVehicleStatusText = (vehicle) => {
  const healthScore = vehicle.overall?.health_score || 0;
  if (healthScore >= 90) return '健康';
  if (healthScore >= 70) return '预警';
  if (healthScore >= 50) return '故障';
  return '严重';
};

const getVehicleStatusType = (vehicle) => {
  const healthScore = vehicle.overall?.health_score || 0;
  if (healthScore >= 90) return 'success';
  if (healthScore >= 70) return 'warning';
  return 'danger';
};

// 获取车辆卡片样式
const getVehicleCardClass = (vehicle) => {
  const healthScore = vehicle.overall?.health_score || 0;
  if (healthScore >= 90) return 'vehicle-healthy';
  if (healthScore >= 70) return 'vehicle-warning';
  return 'vehicle-danger';
};

// 获取故障状态样式
const getFaultStatusClass = (faultData) => {
  if (!faultData) return 'fault-unknown';
  const score = faultData.fault_score || 0;
  if (score < 30) return 'fault-normal';
  if (score < 70) return 'fault-warning';
  return 'fault-danger';
};

// 获取故障状态文本
const getFaultStatusText = (faultData) => {
  if (!faultData) return '未知';
  const score = faultData.fault_score || 0;
  if (score < 30) return '正常';
  if (score < 70) return '预警';
  return '故障';
};

// 获取故障标签类型
const getFaultTagType = (faultData) => {
  if (!faultData) return 'info';
  const score = faultData.fault_score || 0;
  if (score < 30) return 'success';
  if (score < 70) return 'warning';
  return 'danger';
};

// 获取故障数量
const getFaultCount = (vehicle) => {
  let count = 0;
  faultTypes.value.forEach(faultType => {
    const faultData = vehicle[faultType.type];
    if (faultData && faultData.fault_score > 30) {
      count++;
    }
  });
  return count;
};

// 获取最后更新时间
const getLastUpdateTime = (vehicle) => {
  if (!vehicle.lastUpdate) return '--';
  // 🚀 修复：直接使用时间戳计算，不再调用.getTime()
  const lastUpdate = typeof vehicle.lastUpdate === 'number' ? vehicle.lastUpdate : vehicle.lastUpdate.getTime();
  const diff = Date.now() - lastUpdate;
  if (diff < 60000) return `${Math.floor(diff / 1000)}s`;
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m`;
  return `${Math.floor(diff / 3600000)}h`;
};

// 获取运行时长
const getRunningDuration = (vehicle) => {
  if (!vehicle.firstSeen) return '--';
  // 🚀 修复：直接使用时间戳计算，不再调用.getTime()
  const firstSeen = typeof vehicle.firstSeen === 'number' ? vehicle.firstSeen : vehicle.firstSeen.getTime();
  const diff = Date.now() - firstSeen;
  const hours = Math.floor(diff / 3600000);
  const minutes = Math.floor((diff % 3600000) / 60000);
  return `${hours}h${minutes}m`;
};

// 获取数据频率
const getDataFrequency = (vehicle) => {
  if (!vehicle.firstSeen || !vehicle.messageCount) return '--';
  // 🚀 修复：直接使用时间戳计算，不再调用.getTime()
  const firstSeen = typeof vehicle.firstSeen === 'number' ? vehicle.firstSeen : vehicle.firstSeen.getTime();
  const diff = (Date.now() - firstSeen) / 1000;
  const frequency = vehicle.messageCount / diff;
  return `${frequency.toFixed(1)}/s`;
};

// 获取趋势图标
const getTrendIcon = (faultData) => {
  // 这里可以根据历史数据计算趋势
  return '📈'; // 简化显示
};

const getTrendClass = (faultData) => {
  return 'trend-stable'; // 简化显示
};

// 格式化时间
const formatTime = (date) => {
  if (!date) return '--';
  return date.toLocaleTimeString();
};

// 格式化详细时间
const formatDetailedTime = (date) => {
  if (!date) return '--';
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
};

// 计算时间间隔（多久之前）
const getTimeSince = (date) => {
  if (!date) return '--';
  const now = Date.now();
  // 🚀 修复：兼容时间戳和Date对象
  const timestamp = typeof date === 'number' ? date : date.getTime();
  const diff = now - timestamp;
  
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  
  if (days > 0) return `${days}天`;
  if (hours > 0) return `${hours}小时`;
  if (minutes > 0) return `${minutes}分钟`;
  return `${seconds}秒`;
};

// 获取监控状态文本
const getMonitoringStatusText = (vehicle) => {
  if (!vehicle.lastUpdate) return '离线';
  // 🚀 修复：兼容时间戳和Date对象
  const lastUpdate = typeof vehicle.lastUpdate === 'number' ? vehicle.lastUpdate : vehicle.lastUpdate.getTime();
  const diff = Date.now() - lastUpdate;
  if (diff < 30000) return '在线'; // 30秒内为在线
  if (diff < 300000) return '延迟'; // 5分钟内为延迟
  return '离线';
};

// 获取监控状态颜色
const getMonitoringStatusColor = (vehicle) => {
  const status = getMonitoringStatusText(vehicle);
  switch (status) {
    case '在线': return '#67c23a';
    case '延迟': return '#e6a23c';
    case '离线': return '#f56c6c';
    default: return '#909399';
  }
};

// 获取故障时间项样式类
const getFaultTimeItemClass = (faultData) => {
  if (!faultData) return 'fault-time-unknown';
  const score = getFaultScore(faultData);
  if (score < 30) return 'fault-time-normal';
  if (score < 70) return 'fault-time-warning';
  return 'fault-time-danger';
};

// 计算整体健康度
const getOverallHealthScore = () => {
  const vehicles = Object.values(vehicleData);
  if (vehicles.length === 0) return 100;
  
  const totalScore = vehicles.reduce((sum, vehicle) => 
    sum + (vehicle.overall?.health_score || 0), 0);
  return totalScore / vehicles.length;
};

// 获取整体健康颜色
const getOverallHealthColor = () => {
  return getHealthColor(getOverallHealthScore());
};

// 获取总警报数
const getTotalAlerts = () => {
  return Object.values(vehicleData).reduce((sum, vehicle) => 
    sum + getFaultCount(vehicle), 0);
};

// 获取警报颜色
const getAlertColor = () => {
  const totalAlerts = getTotalAlerts();
  if (totalAlerts === 0) return '#67c23a';
  if (totalAlerts < 5) return '#e6a23c';
  return '#f56c6c';
};

// 更新性能指标
const updatePerformanceMetrics = () => {
  const now = Date.now();
  if (!performanceMetrics.value.lastUpdate) {
    performanceMetrics.value.lastUpdate = now;
    performanceMetrics.value.lastMessageCount = getTotalMessageCount();
    return;
  }
  
  const timeDiff = (now - performanceMetrics.value.lastUpdate) / 1000;
  if (timeDiff >= 1) {
    const currentTotalMessages = getTotalMessageCount();
    const newMessages = currentTotalMessages - (performanceMetrics.value.lastMessageCount || 0);
    
    // 🔧 修复：计算每秒新增消息数，而不是累计消息数
    performanceMetrics.value.messageRate = Math.round(newMessages / timeDiff);
    performanceMetrics.value.lastUpdate = now;
    performanceMetrics.value.lastMessageCount = currentTotalMessages;
  }
};

// 获取总消息数的辅助函数
const getTotalMessageCount = () => {
  return Object.values(vehicleData).reduce((sum, vehicle) => 
    sum + (vehicle.messageCount || 0), 0);
};

// 计算监控持续时间
const monitoringDuration = computed(() => {
  if (!monitoringStartTime.value || !isMonitoring.value) {
    return '0s';
  }
  
  // 使用currentTime触发响应式更新
  const now = currentTime.value;
  // 🚀 修复：兼容时间戳和Date对象
  const startTime = typeof monitoringStartTime.value === 'number' 
    ? monitoringStartTime.value 
    : monitoringStartTime.value.getTime();
  const diff = now - startTime;
  const hours = Math.floor(diff / 3600000);
  const minutes = Math.floor((diff % 3600000) / 60000);
  const seconds = Math.floor((diff % 60000) / 1000);
  
  if (hours > 0) {
    return `${hours}h${minutes}m`;
  } else if (minutes > 0) {
    return `${minutes}m${seconds}s`;
  } else {
    return `${seconds}s`;
  }
});

// ==========================================
// 生命周期
// ==========================================

onMounted(() => {
      // console.log('🚗 车队分布式监控界面已加载');
  
  // 🚀 启动性能监控和内存管理
  startPerformanceOptimization();
  
  // 初始化用户信息
  try {
    const userInfo = localStorage.getItem('user_info');
    if (userInfo) {
      const user = JSON.parse(userInfo);
      currentUser.value = user.username || user.name || '管理员';
    }
  } catch (error) {
    console.warn('无法加载用户信息:', error);
    currentUser.value = '管理员';
  }
  
  // 从localStorage加载常用车辆列表
  try {
    const savedFavorites = localStorage.getItem('favoriteVehicles');
    if (savedFavorites) {
      favoriteVehicles.value = JSON.parse(savedFavorites);
    }
  } catch (error) {
    console.warn('无法加载常用车辆列表:', error);
  }
  
  // 检查WebSocket连接状态，如果已连接则自动启动监控
  ensureConnected().finally(() => {
    const snap = getState();
    if (snap.isConnected) {
      console.log('🚗 WebSocket已连接，自动启动监控');
      connectionStatus.value = 'connected';
      isMonitoring.value = true;
      monitoringStartTime.value = new Date();
      currentTime.value = Date.now();
      startMonitoringTimer();
      startPerformanceMonitoring();
      
      // 🚀 订阅全局原始消息，驱动本地数据更新
      const offMessage = onMessage((raw) => {
        handleMessage(raw);
      });
      if (!window.__vtox_fleet_unsubs) window.__vtox_fleet_unsubs = [];
      window.__vtox_fleet_unsubs.push(offMessage);
      
      // 🚀 自动启动桥接器，确保数据流正常
      api.startStreamBridge().then(() => {
        console.log('🚀 桥接器已自动启动');
      }).catch(err => {
        console.warn('⚠️ 桥接器自动启动失败:', err);
      });
    } else {
      console.warn('⚠️ WebSocket连接失败，无法自动启动监控');
    }
  })
});

// 保持会话级持久化：路由切换不主动断开，避免中断监控
onBeforeUnmount(() => {
  // 仅清理本组件UI定时器
  stopMonitoringTimer();
  // 🚀 清理性能优化器资源
  cleanupPerformanceOptimization();
});

// 🚀 启动性能优化和内存管理
const startPerformanceOptimization = () => {
  console.log('🚀 启动性能优化器...');
  
  // 启动内存监控
  globalOptimizer.startMemoryMonitoring(() => {
    console.log('🧹 执行自动内存清理...');
    
    // 清理车辆数据管理器
    vehicleDataManager.cleanup();
    
    // 清理过期的车辆数据
    globalOptimizer.deepCleanup(vehicleData, 300000); // 5分钟
    
    // 强制垃圾回收提示
    if (window.gc) {
      window.gc();
    }
    
    console.log(`📊 清理后车辆数量: ${vehicleDataManager.getVehicleCount()}`);
  });
  
  // 监控性能指标
  setInterval(() => {
    const vehicleCount = Object.keys(vehicleData).length;
    const managerCount = vehicleDataManager.getVehicleCount();
    
    if (vehicleCount > 100) {
      console.warn(`⚠️ 车辆数量过多: ${vehicleCount}, 执行清理`);
      globalOptimizer.limitObjectSize(vehicleData, 50);
    }
    
    // 检查WebSocket队列性能
    import('@/mixins/diagnosisOptimization.js').then(({ globalWebSocketOptimizer }) => {
      const queueStats = globalWebSocketOptimizer.getStats();
      const snap = getState();
      
      // 计算消息处理率
      const totalHandled = snap.detailedStats.messagesProcessed + snap.detailedStats.messagesDropped;
      const lossRate = snap.detailedStats.messagesReceived > 0 ? 
        (snap.detailedStats.messagesReceived - totalHandled) / snap.detailedStats.messagesReceived : 0;
      
      if (lossRate > 0.1) { // 如果丢失率超过10%
        console.warn(`⚠️ 消息丢失率过高: ${(lossRate * 100).toFixed(1)}%`, {
          received: snap.detailedStats.messagesReceived,
          processed: snap.detailedStats.messagesProcessed,
          dropped: snap.detailedStats.messagesDropped,
          queueSize: queueStats.queued,
          queueDropped: queueStats.dropped
        });
      }
    });
    
    // 检查内存使用情况
    if (performance.memory) {
      const memoryUsage = (performance.memory.usedJSHeapSize / 1024 / 1024).toFixed(2);
      const memoryLimit = (performance.memory.jsHeapSizeLimit / 1024 / 1024).toFixed(2);
      
      if (vehicleCount % 20 === 0 && vehicleCount > 0) { // 每20个车辆输出一次
        console.log(`📈 内存使用: ${memoryUsage}MB / ${memoryLimit}MB, 车辆: ${vehicleCount}/${managerCount}`);
      }
    }
  }, 10000); // 每10秒检查一次
};

// 🚀 清理性能优化器资源
const cleanupPerformanceOptimization = () => {
  console.log('🧹 清理性能优化器资源...');
  globalOptimizer.destroy();
};

// 🚀 更新详细性能统计
const updateDetailedStats = () => {
  const snap = getState();
  if (snap && snap.detailedStats) {
    // 🔧 性能数据更新
    
    // 更新峰值统计
    const currentReceiveRate = snap.detailedStats.rawReceiveRate || 0;
    const currentProcessRate = snap.detailedStats.actualProcessRate || 0;
    
    // 保持峰值记录
    if (!detailedStats.value.peakReceiveRate) detailedStats.value.peakReceiveRate = 0;
    if (!detailedStats.value.peakProcessRate) detailedStats.value.peakProcessRate = 0;
    
    if (currentReceiveRate > detailedStats.value.peakReceiveRate) {
      detailedStats.value.peakReceiveRate = currentReceiveRate;
    }
    if (currentProcessRate > detailedStats.value.peakProcessRate) {
      detailedStats.value.peakProcessRate = currentProcessRate;
    }
    
    detailedStats.value = {
      rawReceiveRate: currentReceiveRate,
      actualProcessRate: currentProcessRate,
      latencyMs: snap.detailedStats.latencyMs || 0,
      messagesReceived: snap.detailedStats.messagesReceived || 0,
      messagesProcessed: snap.detailedStats.messagesProcessed || 0,
      messagesDropped: snap.detailedStats.messagesDropped || 0,
      bufferOverflows: 0,
      peakReceiveRate: detailedStats.value.peakReceiveRate,
      peakProcessRate: detailedStats.value.peakProcessRate,
      avgReceiveRate: 0,
      avgProcessRate: 0,
      bufferUtilization: 0,
      bufferSize: 0,
      bufferCapacity: 500,
      processingEfficiency: snap.detailedStats.messagesReceived > 0 ? 
        Math.round((snap.detailedStats.messagesProcessed / snap.detailedStats.messagesReceived) * 100) : 100,
      concurrentBatches: 0,
      queuedBatches: 0,
      totalBatchesProcessed: 0,
      avgBatchSize: 0,
      isConnected: snap.isConnected || false,
      reconnectAttempts: snap.reconnectAttempts || 0
    };
  } else {
    // 🔧 确保即使没有数据也有默认值
    console.warn('⚠️ [DEBUG] snap 或 snap.detailedStats 为空，使用默认值');
    detailedStats.value = {
      rawReceiveRate: 0,
      actualProcessRate: 0,
      latencyMs: 0,
      messagesReceived: 0,
      messagesProcessed: 0,
      messagesDropped: 0,
      bufferOverflows: 0,
      peakReceiveRate: 0,
      peakProcessRate: 0,
      avgReceiveRate: 0,
      avgProcessRate: 0,
      bufferUtilization: 0,
      bufferSize: 0,
      bufferCapacity: 500,
      processingEfficiency: 100,
      concurrentBatches: 0,
      queuedBatches: 0,
      totalBatchesProcessed: 0,
      avgBatchSize: 0,
      isConnected: false,
      reconnectAttempts: 0
    };
  }
};

// 🚀 启动性能监控定时器
const startPerformanceMonitoring = () => {
  if (performanceUpdateTimer) {
    clearInterval(performanceUpdateTimer);
  }
  
  performanceUpdateTimer = setInterval(() => {
    updateDetailedStats();
    // 🚀 更新缓存统计
    if (cacheOptimizationEnabled.value) {
      updateCacheStats();
    }
  }, 1000); // 每秒更新一次详细统计
};

// 🚀 停止性能监控定时器
const stopPerformanceMonitoring = () => {
  if (performanceUpdateTimer) {
    clearInterval(performanceUpdateTimer);
    performanceUpdateTimer = null;
  }
  
  // 🚀 清理批量更新定时器
  if (batchUpdateTimer) {
    clearTimeout(batchUpdateTimer);
    batchUpdateTimer = null;
  }
  
  // 🚀 清空更新队列
  batchUpdateQueue.clear();
};

// 🚀 重置所有性能数据
const resetPerformanceData = () => {
  // 重置基本性能指标
  performanceMetrics.value = {
    messageRate: 0,
    memoryUsage: '0 MB',
    updateTime: '0 ms',
    lastUpdate: null,
    lastMessageCount: 0
  };
  
  // 重置全局统计（简单清零）：实际会由全局 store 周期更新
  // 这里不直接操作全局连接，避免中断会话
  
  // 更新详细统计显示
  updateDetailedStats();
};

// 🚀 获取性能优化提示
const getPerformanceTip = () => {
  const stats = detailedStats.value;
  
  if (stats.bufferUtilization > 80) {
    return '⚠️ 缓冲区使用率过高，建议启用缓存优化模式或检查后端处理能力';
  }
  
  if (stats.messagesDropped > stats.messagesProcessed * 0.1) {
    return '⚠️ 消息丢失率较高，强烈建议启用Redis Stream缓存优化模式，可显著减少消息丢失';
  }
  
  if (stats.latencyMs > 1000) {
    return '⚠️ 消息处理延迟过高，可能影响实时性，建议启用缓存优化并检查网络连接';
  }
  
  if (stats.processingEfficiency < 80) {
    return '⚠️ 处理效率偏低，建议启用缓存优化模式，优化批处理大小或减少处理间隔';
  }
  
  if (!cacheOptimizationEnabled.value && stats.messagesReceived > 1000) {
    return '💡 检测到高消息吞吐量，建议启用Redis Stream缓存优化模式以获得最佳性能';
  }
  
  return '💡 系统运行良好，可考虑启用缓存优化模式进一步提升性能';
};

// 🚀 缓存优化建议 (新增)
const getCacheOptimizationSuggestion = () => {
  const messageDropRate = detailedStats.value.messagesDropped > 0 ? 
    (detailedStats.value.messagesDropped / detailedStats.value.messagesReceived * 100).toFixed(1) : 0;
  
  return `当前消息丢失率: ${messageDropRate}%。Redis Stream缓存优化模式采用智能降采样、批量处理和消息重试机制，可将丢失率降低至5%以下，显著提升系统性能和数据完整性。`;
};

// 🚀 缓存优化开关
const cacheOptimizationEnabled = ref(false);
const cacheOptimizationLoading = ref(false);

// 🚀 缓存优化建议显示条件
const shouldShowCacheOptimizationSuggestion = computed(() => {
  return !cacheOptimizationEnabled.value && detailedStats.value.bufferUtilization > 70;
});

// 🚀 启用缓存优化
const enableCacheOptimization = async () => {
  cacheOptimizationLoading.value = true;
  try {
    const response = await api.enableCacheOptimization();
    if (response.status === 'success') {
      cacheOptimizationEnabled.value = true;
      ElMessage.success('🚀 缓存优化已启用，消息丢失率将显著降低');
      // 立即更新缓存统计
      updateCacheStats();
    } else {
      throw new Error(response.message || '启用缓存优化失败');
    }
  } catch (error) {
    ElMessage.error(`启用缓存优化失败: ${error.message || error}`);
  } finally {
    cacheOptimizationLoading.value = false;
  }
};

// 🚀 禁用缓存优化
const disableCacheOptimization = async () => {
  cacheOptimizationLoading.value = true;
  try {
    const response = await api.disableCacheOptimization();
    if (response.status === 'success') {
      cacheOptimizationEnabled.value = false;
      ElMessage.info('🔄 缓存优化已禁用，切换回标准模式');
      // 重置缓存统计
      cacheStats.value = {
        loss_rate: 0,
        cache_hit_rate: 0,
        active_vehicles: 0,
        retry_count: 0
      };
    } else {
      throw new Error(response.message || '禁用缓存优化失败');
    }
  } catch (error) {
    ElMessage.error(`禁用缓存优化失败: ${error.message || error}`);
  } finally {
    cacheOptimizationLoading.value = false;
  }
};

// 🚀 切换缓存优化开关
const toggleCacheOptimization = async () => {
  if (cacheOptimizationEnabled.value) {
    await disableCacheOptimization();
  } else {
    await enableCacheOptimization();
  }
};

// 🚀 更新缓存统计
const updateCacheStats = async () => {
  if (!cacheOptimizationEnabled.value) return;
  
  try {
    const response = await api.getCacheOptimizationStats();
    if (response.status === 'success' && response.data) {
      cacheStats.value = {
        loss_rate: response.data.loss_rate || 0,
        cache_hit_rate: response.data.cache_hit_rate || 0,
        active_vehicles: response.data.active_vehicles || 0,
        retry_count: response.data.retry_count || 0,
        cached_messages: response.data.cached_messages || 0,
        total_received: response.data.total_received || 0,
        total_processed: response.data.total_processed || 0
      };
    }
  } catch (error) {
    console.warn('获取缓存统计失败:', error);
  }
};

// 🚀 缓存优化指标 (新增)
const cacheStats = ref({
  loss_rate: 0,
  cache_hit_rate: 0,
  active_vehicles: 0,
  retry_count: 0
});
</script>

<style scoped>
/* ==========================================
   车队分布式监控样式
   ========================================== */

.fleet-distributed-monitor {
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: calc(100vh - 60px);
}

/* 控制头部 */
.control-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 15px;
  padding: 20px 30px;
  margin-bottom: 25px;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.header-left h2 {
  margin: 0 0 8px 0;
  color: white;
  font-size: 24px;
  font-weight: 600;
}

.header-right {
  display: flex;
  gap: 15px;
}

/* 车队概览统计 */
.fleet-overview {
  margin-bottom: 25px;
}

.overview-card {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); /* 减小最小宽度以适应5个统计项 */
  gap: 20px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 15px;
  padding: 25px;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 15px;
}

.stat-icon {
  font-size: 32px;
  line-height: 1;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: white;
  line-height: 1;
  margin-bottom: 5px;
}

.stat-label {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.8);
  font-weight: 500;
}

.stat-sub-label {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.6);
  font-weight: 400;
  margin-top: 2px;
  font-style: italic;
}

/* 智能搜索功能 */
.search-section {
  margin-bottom: 25px;
}

.search-container {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 15px;
  padding: 25px;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.search-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.search-header h3 {
  margin: 0;
  color: white;
  font-size: 18px;
  font-weight: 600;
}

.search-stats {
  display: flex;
  gap: 15px;
}

.search-stat {
  color: rgba(255, 255, 255, 0.8);
  font-size: 14px;
  background: rgba(255, 255, 255, 0.1);
  padding: 4px 8px;
  border-radius: 12px;
}

.search-input-section {
  margin-bottom: 20px;
}

/* 横向搜索行 - 增加优先级 */
.search-section .search-container .search-input-section .search-row {
  display: flex !important;
  gap: 12px !important;
  align-items: center !important;
  flex-wrap: wrap !important;
  width: 100% !important;
}

.search-section .search-container .search-input-section .search-row .search-input-horizontal {
  flex: 2 !important;
  min-width: 250px !important;
  max-width: 450px !important;
}

.search-input-horizontal :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.9) !important;
  border-radius: 8px !important;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1) !important;
}

.search-section .search-container .search-input-section .search-row .filter-select-horizontal {
  min-width: 120px !important;
  max-width: 200px !important;
  flex: 0 0 auto !important;
}

.filter-select-horizontal :deep(.el-select__wrapper) {
  background: rgba(255, 255, 255, 0.9) !important;
  border-radius: 8px !important;
}

.search-section .search-container .search-input-section .search-row .clear-filters-btn-horizontal {
  background: rgba(255, 255, 255, 0.2) !important;
  border: 1px solid rgba(255, 255, 255, 0.3) !important;
  color: white !important;
  border-radius: 8px !important;
  flex: 0 0 auto !important;
  padding: 8px 12px !important;
  white-space: nowrap !important;
}

/* 响应式设计 - 小屏幕适配 */
@media (max-width: 1200px) {
  .search-section .search-container .search-input-section .search-row {
    gap: 10px !important;
  }
  
  .search-section .search-container .search-input-section .search-row .search-input-horizontal {
    min-width: 200px !important;
    max-width: 400px !important;
  }
  
  .search-section .search-container .search-input-section .search-row .filter-select-horizontal {
    min-width: 100px !important;
    max-width: 150px !important;
  }
}

@media (max-width: 900px) {
  .search-section .search-container .search-input-section .search-row {
    gap: 8px !important;
  }
  
  .search-section .search-container .search-input-section .search-row .search-input-horizontal {
    min-width: 180px !important;
    max-width: 320px !important;
  }
  
  .search-section .search-container .search-input-section .search-row .filter-select-horizontal {
    min-width: 90px !important;
    max-width: 130px !important;
  }
}

@media (max-width: 768px) {
  .search-section .search-container .search-input-section .search-row {
    flex-direction: column !important;
    gap: 15px !important;
  }
  
  .search-section .search-container .search-input-section .search-row .search-input-horizontal {
    width: 100% !important;
    min-width: unset !important;
  }
  
  .search-section .search-container .search-input-section .search-row .filter-select-horizontal {
    width: 100% !important;
    min-width: unset !important;
  }
  
  .search-section .search-container .search-input-section .search-row .clear-filters-btn-horizontal {
    width: 100% !important;
  }
}

.clear-filters-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* 搜索结果样式 */
.search-results {
  margin-bottom: 20px;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.results-title {
  color: white;
  font-weight: 600;
  font-size: 16px;
}

.no-results {
  color: rgba(255, 255, 255, 0.7);
  font-style: italic;
}

.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 15px;
}

.result-item {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 10px;
  padding: 15px;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid transparent;
}

.result-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
  border-color: rgba(64, 158, 255, 0.5);
}

.result-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.result-icon {
  font-size: 20px;
}

.result-name {
  font-weight: 600;
  color: #2c3e50;
  flex: 1;
}

.result-details {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}

.result-detail {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.detail-label {
  font-size: 12px;
  color: #7f8c8d;
  margin-bottom: 2px;
}

.detail-value {
  font-size: 14px;
  font-weight: 600;
  color: #2c3e50;
}

.result-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.quick-access-btn, .locate-btn {
  flex: 1;
  border-radius: 6px;
  font-size: 12px;
  padding: 6px 12px;
}

/* 常用车辆快速访问样式 */
.quick-access-section {
  margin-top: 20px;
}

.quick-access-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.quick-access-header h4 {
  margin: 0;
  color: white;
  font-size: 16px;
  font-weight: 600;
}

.favorites-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.favorite-item {
  background: rgba(255, 255, 255, 0.9);
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 12px;
}

.favorite-item:hover {
  background: rgba(255, 255, 255, 1);
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.favorite-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.favorite-info {
  flex: 1;
  min-width: 0;
}

.favorite-name {
  font-weight: 600;
  color: #2c3e50;
  font-size: 14px;
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.favorite-model {
  font-size: 12px;
  color: #7f8c8d;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.favorite-status {
  flex-shrink: 0;
}

.status-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #909399;
}

.status-dot.vehicle-healthy {
  background: #67c23a;
}

.status-dot.vehicle-warning {
  background: #e6a23c;
}

.status-dot.vehicle-danger {
  background: #f56c6c;
}

.status-dot.offline {
  background: #909399;
}

/* 车辆卡片高亮样式 */
.vehicle-card.highlight {
  animation: highlight-pulse 1s ease-in-out 3;
  border-color: #409eff !important;
  box-shadow: 0 0 20px rgba(64, 158, 255, 0.4) !important;
}

@keyframes highlight-pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.02);
  }
}

/* 车辆网格布局 */
.vehicle-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 25px;
}

/* 车辆卡片 */
.vehicle-card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 15px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid transparent;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.vehicle-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.2);
}

.vehicle-card.vehicle-healthy {
  border-color: #67c23a;
}

.vehicle-card.vehicle-warning {
  border-color: #e6a23c;
}

.vehicle-card.vehicle-danger {
  border-color: #f56c6c;
}

/* 车辆头部信息 */
.vehicle-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 15px;
}

.vehicle-info {
  flex: 1;
}

.vehicle-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.vehicle-icon {
  font-size: 24px;
}

.vehicle-name {
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
}

.vehicle-location {
  font-size: 14px;
  color: #7f8c8d;
}

.vehicle-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.detail-btn {
  font-weight: 600;
}

.expand-indicator {
  font-size: 16px;
  transition: transform 0.3s ease;
}

.expand-indicator.expanded {
  transform: rotate(180deg);
}

/* 车辆状态栏 */
.vehicle-status-bar {
  margin-bottom: 15px;
}

.status-metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 15px;
}

.metric-item {
  text-align: center;
  padding: 10px;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 8px;
}

.metric-icon {
  font-size: 20px;
  margin-bottom: 5px;
}

.metric-value {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 3px;
}

.metric-label {
  font-size: 12px;
  color: #7f8c8d;
}

/* 故障状态网格 */
.fault-status-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
  margin-bottom: 15px;
}

.fault-status-item {
  padding: 12px 8px;
  border-radius: 8px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}

.fault-status-item:hover {
  transform: scale(1.05);
}

.fault-status-item.fault-normal {
  background: rgba(103, 194, 58, 0.1);
  border-color: #67c23a;
}

.fault-status-item.fault-warning {
  background: rgba(230, 162, 60, 0.1);
  border-color: #e6a23c;
}

.fault-status-item.fault-danger {
  background: rgba(245, 108, 108, 0.1);
  border-color: #f56c6c;
}

.fault-status-item.fault-unknown {
  background: rgba(144, 147, 153, 0.1);
  border-color: #909399;
}

.fault-icon {
  font-size: 18px;
  margin-bottom: 5px;
}

.fault-name {
  font-size: 12px;
  color: #2c3e50;
  margin-bottom: 3px;
  font-weight: 500;
}

.fault-score {
  font-size: 14px;
  font-weight: 600;
  color: #2c3e50;
}

/* 车辆详细信息 */
.vehicle-details {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
}

/* 小型图表网格 */
.mini-charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 15px;
  margin-bottom: 20px;
}

.mini-chart-container {
  background: rgba(0, 0, 0, 0.05);
  border-radius: 8px;
  padding: 12px;
}

.mini-chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  font-size: 12px;
  font-weight: 600;
}

.mini-chart {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chart-placeholder {
  text-align: center;
}

.chart-value {
  font-size: 20px;
  font-weight: 700;
  color: #2c3e50;
}

.chart-trend {
  font-size: 16px;
  margin-top: 5px;
}

/* 车辆特征信息 */
.vehicle-features {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.feature-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.feature-label {
  font-weight: 600;
  color: #2c3e50;
}

.feature-value {
  color: #7f8c8d;
}

/* 空状态 */
.empty-state, .disconnected-state {
  text-align: center;
  padding: 60px 20px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 15px;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.empty-icon, .disconnected-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.empty-text, .disconnected-text {
  font-size: 24px;
  color: white;
  margin-bottom: 10px;
  font-weight: 600;
}

.empty-hint, .disconnected-hint {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.8);
}

.disconnected-note {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  font-style: italic;
  margin-top: 10px;
  padding: 8px 15px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  display: inline-block;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .vehicle-grid {
    grid-template-columns: 1fr;
  }
  
  .overview-card {
    grid-template-columns: repeat(2, 1fr);
  }
  
  /* 在移动设备上，最后一个统计项单独占一行居中显示 */
  .overview-card .stat-item:last-child {
    grid-column: 1 / -1;
    justify-self: center;
    max-width: 200px;
  }
  
  .control-header {
    flex-direction: column;
    gap: 15px;
    text-align: center;
  }
  
  .status-metrics {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .fault-status-grid {
    grid-template-columns: repeat(3, 1fr);
  }
  
  .vehicle-features {
    grid-template-columns: 1fr;
  }

  .search-input-section {
    flex-direction: column;
    gap: 10px;
  }

  .search-filters {
    flex-direction: column;
    gap: 10px;
  }

  .filter-select {
    width: 100%;
  }

  .results-grid {
    grid-template-columns: 1fr;
  }

  .result-details {
    grid-template-columns: 1fr;
    gap: 4px;
  }
  
  .result-detail {
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
    text-align: left;
  }
  
  .favorites-grid {
    grid-template-columns: 1fr;
  }
  
  .search-stats {
    flex-direction: column;
    gap: 8px;
  }
  
  /* 时间记录移动端适配 */
  .time-record-grid {
    grid-template-columns: 1fr;
    gap: 10px;
  }
  
  .fault-time-details {
    grid-template-columns: 1fr;
    gap: 8px;
  }
  
  .fault-time-detail {
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
    text-align: left;
  }
}

/* Element Plus 组件覆写 */
:deep(.el-button) {
  border-radius: 8px;
  font-weight: 600;
}

:deep(.el-tag) {
  border-radius: 6px;
  font-weight: 500;
}

:deep(.el-divider__text) {
  background-color: white;
  color: #2c3e50;
  font-weight: 600;
}

/* 时间记录样式 */
.time-records {
  margin: 15px 0;
}

.time-record-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
}

.time-record-item {
  background: rgba(0, 0, 0, 0.03);
  border-radius: 8px;
  padding: 12px;
  text-align: center;
  border: 1px solid rgba(0, 0, 0, 0.1);
}

.time-record-label {
  font-size: 14px;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 8px;
}

.time-record-value {
  font-size: 16px;
  font-weight: 700;
  color: #409EFF;
  margin-bottom: 4px;
}

.time-record-duration {
  font-size: 12px;
  color: #7f8c8d;
  font-style: italic;
}

/* 故障时间记录样式 */
.fault-time-records {
  margin: 15px 0;
}

.fault-time-item {
  background: rgba(0, 0, 0, 0.03);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 10px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.fault-time-item:hover {
  background: rgba(0, 0, 0, 0.05);
  transform: translateY(-1px);
}

.fault-time-item.fault-time-normal {
  border-left: 4px solid #67c23a;
}

.fault-time-item.fault-time-warning {
  border-left: 4px solid #e6a23c;
}

.fault-time-item.fault-time-danger {
  border-left: 4px solid #f56c6c;
}

.fault-time-item.fault-time-unknown {
  border-left: 4px solid #909399;
}

.fault-time-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.fault-time-icon {
  font-size: 18px;
}

.fault-time-name {
  font-weight: 600;
  color: #2c3e50;
  flex: 1;
}

.fault-time-details {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.fault-time-detail {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.fault-time-detail .detail-label {
  font-size: 12px;
  color: #7f8c8d;
  margin-bottom: 4px;
}

.fault-time-detail .detail-value {
  font-size: 14px;
  font-weight: 600;
  color: #2c3e50;
}

/* 🚀 详细性能面板样式 */
.performance-detail-panel {
  margin: 20px 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
}

.performance-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  color: white;
}

.performance-header h3 {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.performance-actions {
  display: flex;
  gap: 10px;
}

.performance-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.performance-card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  transition: all 0.3s ease;
}

.performance-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 35px rgba(0, 0, 0, 0.15);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 2px solid #f0f0f0;
}

.card-title {
  font-size: 18px;
  font-weight: 700;
  color: #2c3e50;
}

.card-status {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
}

.status-excellent {
  background: linear-gradient(45deg, #4CAF50, #8BC34A);
  color: white;
}

.status-good {
  background: linear-gradient(45deg, #2196F3, #03A9F4);
  color: white;
}

.status-warning {
  background: linear-gradient(45deg, #FF9800, #FFC107);
  color: white;
}

.status-info {
  background: linear-gradient(45deg, #9C27B0, #E91E63);
  color: white;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 15px;
}

.metric-item {
  text-align: center;
  padding: 15px 10px;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border-radius: 10px;
  transition: all 0.3s ease;
}

.metric-item:hover {
  transform: scale(1.05);
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.metric-value {
  font-size: 24px;
  font-weight: 800;
  color: #2c3e50;
  margin-bottom: 5px;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.metric-label {
  font-size: 12px;
  color: #7f8c8d;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.performance-tips {
  margin-top: 15px;
}

.performance-tips .el-alert {
  border-radius: 10px;
  border: none;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .performance-cards {
    grid-template-columns: 1fr;
  }
  
  .metrics-grid {
    grid-template-columns: 1fr;
  }
  
  .performance-header {
    flex-direction: column;
    gap: 15px;
    text-align: center;
  }
  
  .performance-actions {
    justify-content: center;
  }
}

/* 🚀 缓存优化指标 (新增) */
.performance-card.cache-optimization-metrics {
  background: linear-gradient(135deg, #FFD700, #FFA500);
  border-color: #FFA500;
}

.cache-optimization-metrics .card-header {
  border-bottom: 2px solid #FFA500;
}

.cache-optimization-metrics .card-title {
  color: #FFA500;
}

.cache-optimization-metrics .card-status {
  background: linear-gradient(45deg, #FFA500, #FF8C00);
  color: white;
}

.cache-optimization-metrics .metric-item {
  background: linear-gradient(135deg, #FFD700, #FFA500);
}

.cache-optimization-metrics .metric-value {
  color: #FFA500;
}

.cache-optimization-metrics .metric-label {
  color: #FF8C00;
}

/* 🚀 缓存优化建议 (新增) */
.cache-optimization-suggestion {
  margin-top: 15px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.cache-optimization-suggestion .el-alert {
  border: none;
  box-shadow: none;
}

.cache-optimization-suggestion .el-alert .el-alert__content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.cache-optimization-suggestion .el-alert .el-alert__icon {
  margin-right: 10px;
}

.cache-optimization-suggestion .suggestion-actions {
  display: flex;
  gap: 10px;
}

.cache-optimization-suggestion .el-button {
  flex: 1;
}
</style> 