<template>
  <div class="agent-board">
    <!-- 背景粒子 -->
    <div class="particles" ref="particles"></div>
    
    <div class="container">
      <header>
        <div class="logo">
          <div class="logo-icon">
            <i class="fas fa-brain"></i>
          </div>
          <div class="logo-text">MCSA 智能诊断</div>
        </div>
      </header>
      
      <div class="main-content">
        <div class="panel">
          <div class="panel-header">
            <div class="panel-title">
              <i class="fas fa-comments"></i>
              MCSA诊断助手
              <span class="message-count" v-if="messages.length > 0">
                ({{ messages.length }}条记录)
              </span>
            </div>
            <div class="panel-controls">
              <!-- RAG 功能切换选项卡 -->
              <div class="rag-tabs">
                <button 
                  :class="['tab-btn', { active: activeTab === 'chat' }]"
                  @click="activeTab = 'chat'"
                >
                  <i class="fas fa-comments"></i>
                  对话
                </button>
                <button 
                  :class="['tab-btn', { active: activeTab === 'docs' }]"
                  @click="activeTab = 'docs'"
                >
                  <i class="fas fa-file-upload"></i>
                  文档管理
                </button>
                <button 
                  :class="['tab-btn', { active: activeTab === 'graph' }]"
                  @click="activeTab = 'graph'"
                >
                  <i class="fas fa-project-diagram"></i>
                  知识图谱
                </button>
                <button 
                  :class="['tab-btn', { active: activeTab === 'health' }]"
                  @click="activeTab = 'health'; loadHealthStatus()"
                >
                  <i class="fas fa-heartbeat"></i>
                  系统状态
                </button>
              </div>
              <button 
                class="clear-chat-btn" 
                @click="resetChatHistory" 
                title="清空聊天记录"
                :disabled="isLoading"
              >
                <i class="fas fa-trash-alt"></i>
                <span>清空记录</span>
              </button>
              <button 
                class="knowledge-base-btn" 
                @click="openKnowledgeBase" 
                title="访问外部知识库"
              >
                <i class="fas fa-external-link-alt"></i>
                <span>知识库访问</span>
              </button>
              <!-- 开发环境测试按钮 -->
              <button 
                v-if="isDevelopment"
                class="test-math-btn" 
                @click="testMathRendering" 
                title="测试数学公式渲染"
                :disabled="isLoading"
              >
                <i class="fas fa-square-root-alt"></i>
                <span>测试公式</span>
              </button>
              <div class="status-indicator">
                <div :class="['status-dot', connectionStatus === 'connected' ? 'connected' : 'disconnected']"></div>
                <span>{{ connectionStatus === 'connected' ? '在线' : '离线' }}</span>
              </div>
            </div>
          </div>
          
          <!-- 对话界面 -->
          <div v-if="activeTab === 'chat'" class="chat-container">
            <div class="chat-messages" ref="chatMessages">
              <div 
                v-for="(message, index) in messages" 
                :key="index"
                :class="['message', message.type === 'user' ? 'user-message' : 'ai-message']"
              >
                <div class="message-header">
                  <div :class="['avatar', message.type === 'user' ? 'user-avatar' : 'ai-avatar']">
                    {{ message.type === 'user' ? 'U' : 'AI' }}
                  </div>
                  <div>{{ message.type === 'user' ? '用户' : 'MCSA 诊断助手' }}</div>
                </div>
                <div :class="['message-content', { typing: message.isTyping }]">
                  <div 
                    v-if="message.type === 'ai'"
                    class="markdown-content"
                    v-html="renderMarkdown(message.content)"
                  ></div>
                  <div v-else class="user-content">
                    {{ message.content }}
                  </div>
                </div>
              </div>
            </div>
            
            <div class="input-area">
              <div class="model-selector" v-if="availableModels.length > 1">
                <select v-model="selectedModel" class="model-select">
                  <option v-for="model in availableModels" :key="model.id" :value="model.id">
                    {{ model.name }} {{ model.free ? '(免费)' : '(付费)' }}
                  </option>
                </select>
              </div>

              <div class="message-controls">
                <input 
                  type="text" 
                  class="message-input" 
                  placeholder="请描述电机状况或故障现象..."
                  v-model="newMessage"
                  :disabled="isLoading"
                  @keypress.enter="sendMessage"
                >
                <button class="send-button" @click="sendMessage" :disabled="isLoading">
                  <i v-if="!isLoading" class="fas fa-paper-plane"></i>
                  <i v-else class="fas fa-spinner fa-spin"></i>
                </button>
              </div>
            </div>
          </div>

          <!-- 文档管理界面 -->
          <div v-else-if="activeTab === 'docs'" class="docs-container">
            <div class="docs-header">
              <h3><i class="fas fa-folder-open"></i> 文档与知识库管理</h3>
              <div class="docs-actions">
                <button @click="loadDocuments" class="action-btn refresh-btn" :disabled="isLoading">
                  <i class="fas fa-sync-alt" :class="{ 'fa-spin': isLoading }"></i>
                  刷新状态
                </button>
                <button @click="clearAllDocuments" class="action-btn danger-btn" :disabled="isLoading">
                  <i class="fas fa-trash"></i>
                  清空所有文档
                </button>
              </div>
            </div>

            <!-- 文件上传区域 -->
            <div class="upload-section">
              <h4><i class="fas fa-cloud-upload-alt"></i> 文件上传</h4>
              <div class="upload-area" @dragover.prevent @drop="handleFileDrop">
                <input 
                  type="file" 
                  ref="fileInput" 
                  @change="handleFileSelect" 
                  accept=".pdf,.txt,.docx,.md"
                  style="display: none"
                >
                <div class="upload-zone" @click="$refs.fileInput.click()">
                  <i class="fas fa-file-upload"></i>
                  <p>点击或拖拽文件到此处上传</p>
                  <small>支持 PDF, TXT, DOCX, MD 格式，最大 50MB</small>
                  <div class="upload-tips">
                    <div class="tip-item">
                      <i class="fas fa-info-circle"></i>
                      <span>PDF 文件请确保包含可选择的文本内容</span>
                    </div>
                    <div class="tip-item">
                      <i class="fas fa-exclamation-triangle"></i>
                      <span>扫描版 PDF 可能无法正确提取内容</span>
                    </div>
                  </div>
                </div>
                <div v-if="uploadProgress.length" class="upload-progress">
                  <div v-for="(progress, index) in uploadProgress" :key="index" class="progress-item">
                    <span>{{ progress.filename }}</span>
                    <div class="progress-bar">
                      <div class="progress-fill" :style="{ width: progress.percent + '%' }"></div>
                    </div>
                    <span :class="progress.status">{{ progress.message }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 文本直接入库 -->
            <div class="text-input-section">
              <h4><i class="fas fa-keyboard"></i> 文本直接入库</h4>
              <div class="text-input-area">
                <textarea 
                  v-model="bulkTexts" 
                  placeholder="请输入要添加到知识库的文本内容，多条文本用换行分隔..."
                  rows="5"
                  class="bulk-text-input"
                ></textarea>
                <input 
                  v-model="textSource" 
                  placeholder="文本来源 (可选)"
                  class="source-input"
                >
                <button @click="addBulkTexts" class="action-btn primary-btn" :disabled="isLoading || !bulkTexts.trim()">
                  <i class="fas fa-plus"></i>
                  批量添加文本
                </button>
              </div>
            </div>

            <!-- 文档状态显示 -->
            <div class="docs-status-section">
              <h4><i class="fas fa-list"></i> 文档状态</h4>
              <div class="status-grid">
                <div class="status-card" v-for="(group, status) in documentGroups" :key="status">
                  <div class="status-header">
                    <span class="status-name">{{ getStatusName(status) }}</span>
                    <span class="status-count">{{ Array.isArray(group) ? group.length : Object.keys(group).length }}</span>
                  </div>
                  <div class="status-items" v-if="Array.isArray(group) && group.length">
                    <div v-for="doc in group.slice(0, 3)" :key="doc.id" class="doc-item">
                      <i class="fas fa-file-alt"></i>
                      <span>{{ doc.name || doc.id }}</span>
                      <button @click="deleteDocument(doc.id)" class="delete-doc-btn">
                        <i class="fas fa-times"></i>
                      </button>
                    </div>
                    <div v-if="group.length > 3" class="more-items">
                      还有 {{ group.length - 3 }} 个文档...
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 流水线状态 -->
            <div class="pipeline-section">
              <h4><i class="fas fa-cogs"></i> 处理流水线状态</h4>
              <div class="pipeline-status">
                <div class="pipeline-info">
                  <div class="info-item">
                    <label>状态:</label>
                    <span :class="['status-badge', pipelineStatus.busy ? 'busy' : 'idle']">
                      {{ pipelineStatus.busy ? '处理中' : '空闲' }}
                    </span>
                  </div>
                  <div class="info-item" v-if="pipelineStatus.job_name">
                    <label>当前任务:</label>
                    <span>{{ pipelineStatus.job_name }}</span>
                  </div>
                  <div class="info-item" v-if="pipelineStatus.job_start">
                    <label>开始时间:</label>
                    <span>{{ formatTime(pipelineStatus.job_start) }}</span>
                  </div>
                </div>
                <div v-if="pipelineStatus.history_messages && pipelineStatus.history_messages.length" class="pipeline-logs">
                  <h5>处理日志:</h5>
                  <div class="log-messages">
                    <div v-for="(msg, index) in pipelineStatus.history_messages.slice(-5)" :key="index" class="log-message">
                      {{ msg }}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 处理建议 -->
            <div class="processing-tips">
              <h4><i class="fas fa-lightbulb"></i> 文档处理建议</h4>
              <div class="tips-grid">
                <div class="tip-card">
                  <i class="fas fa-file-pdf"></i>
                  <h5>PDF 文件</h5>
                  <ul>
                    <li>确保 PDF 包含可选择的文本</li>
                    <li>避免使用扫描版或纯图片 PDF</li>
                    <li>建议文件大小在 10MB 以内</li>
                  </ul>
                </div>
                <div class="tip-card">
                  <i class="fas fa-file-alt"></i>
                  <h5>文本文件</h5>
                  <ul>
                    <li>支持 TXT、MD 格式</li>
                    <li>使用 UTF-8 编码</li>
                    <li>内容结构化有助于提取</li>
                  </ul>
                </div>
                <div class="tip-card">
                  <i class="fas fa-file-word"></i>
                  <h5>Word 文档</h5>
                  <ul>
                    <li>支持 DOCX 格式</li>
                    <li>避免过多复杂格式</li>
                    <li>纯文本效果最佳</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          <!-- 知识图谱界面 -->
          <div v-else-if="activeTab === 'graph'" class="graph-container">
            <div class="graph-header">
              <h3><i class="fas fa-project-diagram"></i> 知识图谱管理</h3>
              <div class="graph-actions">
                <button @click="loadGraphLabels" class="action-btn refresh-btn" :disabled="isLoading">
                  <i class="fas fa-sync-alt" :class="{ 'fa-spin': isLoading }"></i>
                  刷新标签
                </button>
              </div>
            </div>

            <!-- 标签列表 -->
            <div class="labels-section">
              <h4><i class="fas fa-tags"></i> 图谱标签</h4>
              <div class="labels-grid">
                <div v-for="label in graphLabels" :key="label" class="label-item" @click="loadSubgraph(label)">
                  <i class="fas fa-tag"></i>
                  <span>{{ label }}</span>
                </div>
              </div>
            </div>

            <!-- 子图查询 -->
            <div class="subgraph-section">
              <h4><i class="fas fa-search"></i> 子图查询</h4>
              <div class="query-controls">
                <select v-model="selectedLabel" class="label-select">
                  <option value="">选择标签</option>
                  <option v-for="label in graphLabels" :key="label" :value="label">{{ label }}</option>
                </select>
                <input v-model="maxDepth" type="number" min="1" max="5" placeholder="最大深度" class="depth-input">
                <input v-model="maxNodes" type="number" min="10" max="2000" placeholder="最大节点数" class="nodes-input">
                <button @click="loadSubgraph(selectedLabel)" class="action-btn primary-btn" :disabled="!selectedLabel">
                  <i class="fas fa-search"></i>
                  查询子图
                </button>
              </div>
            </div>

            <!-- 实体搜索 -->
            <div class="entity-section">
              <h4><i class="fas fa-search-plus"></i> 实体查询</h4>
              <div class="entity-search">
                <input v-model="entityName" placeholder="输入实体名称" class="entity-input">
                <button @click="checkEntityExists" class="action-btn secondary-btn">
                  <i class="fas fa-question"></i>
                  检查存在
                </button>
              </div>
              <div v-if="entityExists !== null" class="entity-result">
                <span :class="['result-badge', entityExists ? 'exists' : 'not-exists']">
                  {{ entityExists ? '实体存在' : '实体不存在' }}
                </span>
              </div>
            </div>

            <!-- 图谱可视化区域 -->
            <div class="graph-viz-section" v-if="currentSubgraph">
              <h4><i class="fas fa-eye"></i> 图谱可视化</h4>
              <div class="graph-stats">
                <span class="stat-item">节点: {{ currentSubgraph.nodes?.length || 0 }}</span>
                <span class="stat-item">边: {{ currentSubgraph.edges?.length || 0 }}</span>
                <span class="stat-item">标签: {{ selectedLabel }}</span>
              </div>
              <div class="graph-placeholder">
                <i class="fas fa-project-diagram"></i>
                <p>图谱可视化组件位置</p>
                <small>可集成 D3.js 或 Cytoscape.js 进行可视化</small>
              </div>
            </div>
          </div>

          <!-- 系统状态界面 -->
          <div v-else-if="activeTab === 'health'" class="health-container">
            <div class="health-header">
              <h3><i class="fas fa-heartbeat"></i> 系统健康状态</h3>
              <div class="health-actions">
                <button @click="loadHealthStatus" class="action-btn refresh-btn" :disabled="isLoading">
                  <i class="fas fa-sync-alt" :class="{ 'fa-spin': isLoading }"></i>
                  刷新状态
                </button>
              </div>
            </div>

            <div v-if="healthStatus" class="health-overview">
              <!-- 系统总览 -->
              <div class="health-section">
                <h4><i class="fas fa-server"></i> 系统总览</h4>
                <div class="health-grid">
                  <div class="health-card">
                    <div class="health-label">服务状态</div>
                    <div class="health-value status-healthy">运行中</div>
                  </div>
                  <div class="health-card">
                    <div class="health-label">配置状态</div>
                    <div class="health-value">{{ healthStatus.config_status || '正常' }}</div>
                  </div>
                  <div class="health-card">
                    <div class="health-label">流水线状态</div>
                    <div class="health-value">{{ healthStatus.pipeline_status || '就绪' }}</div>
                  </div>
                </div>
              </div>

              <!-- 详细配置 -->
              <div class="health-section">
                <h4><i class="fas fa-cog"></i> 配置详情</h4>
                <div class="config-details">
                  <pre class="health-json">{{ formatHealthData(healthStatus) }}</pre>
                </div>
              </div>
            </div>

            <div v-else class="health-loading">
              <i class="fas fa-spinner fa-spin"></i>
              <p>加载系统状态中...</p>
            </div>
          </div>
        </div>
      </div>
      
      <footer>
        <p>© 2025 MCSA智能诊断系统 - 电机故障诊断专家 | 版本 1.0.0</p>
      </footer>
    </div>
  </div>
</template>

<script>
import api from '@/api/index.js'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import markedKatex from 'marked-katex-extension'

const CHAT_CACHE_KEY = 'mcsa_agent_chat_history'

export default {
  name: 'AgentBoard',
  data() {
    return {
      // 基础状态
      newMessage: '',
      isLoading: false,
      selectedModel: 'qwen',
      availableModels: [],
      connectionStatus: 'connected',
      messages: [], // 初始化为空数组，将从缓存或默认值加载
      
      // RAG 功能相关
      activeTab: 'chat', // 'chat', 'docs', 'graph', 'health'
      
      // 文档管理相关
      uploadProgress: [],
      bulkTexts: '',
      textSource: '',
      documentGroups: {},
      pipelineStatus: {},
      
      // 知识图谱相关
      graphLabels: [],
      selectedLabel: '',
      maxDepth: 3,
      maxNodes: 1000,
      entityName: '',
      entityExists: null,
      currentSubgraph: null,
      
      // 系统健康状态
      healthStatus: null,
      
      // 默认消息，用于初始化或缓存清空时
      defaultMessages: [
        {
          type: 'ai',
          content: '您好！我是MCSA智能诊断助手。我可以帮助您分析电机故障、解释诊断结果和提供维护建议。有什么问题可以咨询我？',
          isTyping: false,
          timestamp: new Date().toISOString()
        },
        {
          type: 'user',
          content: '电机出现了轴承故障，MCSA分析显示外圈频率异常，应该如何处理？',
          isTyping: false,
          timestamp: new Date().toISOString()
        },
        {
          type: 'ai',
          content: '根据MCSA分析，外圈故障频率异常表明轴承外圈存在缺陷。建议：1）立即降低负载运行；2）安排停机检修更换轴承；3）检查润滑状况；4）分析故障原因避免重复发生。',
          isTyping: false,
          timestamp: new Date().toISOString()
        }
      ]
    }
  },
  
  computed: {
    isDevelopment() {
      return process.env.NODE_ENV === 'development'
    }
  },
  
  async mounted() {
    // 配置Markdown渲染
    this.setupMarkdown()
    this.createParticles()
    this.setupPanelEffects()
    await this.loadAvailableModels()
    
    // 恢复聊天记录
    this.restoreChatHistory()
    
    // 监听页面卸载事件，保存聊天记录
    window.addEventListener('beforeunload', this.saveChatHistory)
    
    // 监听路由变化，保存聊天记录
    this.$router?.beforeEach && this.$router.beforeEach((to, from, next) => {
      if (from.path === '/agent') {
        this.saveChatHistory()
      }
      next()
    })
  },
  
  beforeUnmount() {
    // 组件卸载前保存聊天记录
    this.saveChatHistory()
    
    // 移除事件监听器
    window.removeEventListener('beforeunload', this.saveChatHistory)
  },
  
  watch: {
    // 监听messages变化，实时保存到缓存
    messages: {
      handler() {
        this.saveChatHistory()
      },
      deep: true
    }
  },

  methods: {
    /**
     * 保存聊天记录到sessionStorage
     */
    saveChatHistory() {
      try {
        const chatData = {
          messages: this.messages,
          selectedModel: this.selectedModel,
          timestamp: new Date().toISOString()
        }
        
        // 检查sessionStorage可用空间
        const dataStr = JSON.stringify(chatData)
        if (dataStr.length > 5 * 1024 * 1024) { // 5MB限制
          console.warn('[AgentBoard] 聊天记录过大，开始清理旧记录')
          // 保留最近的50条消息
          chatData.messages = this.messages.slice(-50)
          this.messages = chatData.messages
        }
        
        sessionStorage.setItem(CHAT_CACHE_KEY, JSON.stringify(chatData))
        console.log(`[AgentBoard] 聊天记录已保存到缓存 (${this.messages.length}条记录)`)
      } catch (error) {
        console.warn('[AgentBoard] 保存聊天记录失败:', error)
        
        // 如果是存储空间不足，尝试清理
        if (error.name === 'QuotaExceededError') {
          try {
            // 清理旧的聊天记录，只保留最近的30条
            const reducedMessages = this.messages.slice(-30)
            const reducedData = {
              messages: reducedMessages,
              selectedModel: this.selectedModel,
              timestamp: new Date().toISOString()
            }
            sessionStorage.setItem(CHAT_CACHE_KEY, JSON.stringify(reducedData))
            this.messages = reducedMessages
            console.log('[AgentBoard] 存储空间不足，已清理旧记录并重新保存')
          } catch (retryError) {
            console.error('[AgentBoard] 重试保存失败:', retryError)
            // 完全清空缓存
            sessionStorage.removeItem(CHAT_CACHE_KEY)
          }
        }
      }
    },
    
    /**
     * 从sessionStorage恢复聊天记录
     */
    restoreChatHistory() {
      try {
        const cachedData = sessionStorage.getItem(CHAT_CACHE_KEY)
        
        if (cachedData) {
          const chatData = JSON.parse(cachedData)
          
          // 验证数据有效性
          if (chatData.messages && Array.isArray(chatData.messages) && chatData.messages.length > 0) {
            this.messages = chatData.messages
            
            // 恢复选中的模型
            if (chatData.selectedModel) {
              this.selectedModel = chatData.selectedModel
            }
            
            console.log(`[AgentBoard] 已从缓存恢复 ${this.messages.length} 条聊天记录`)
            
            // 滚动到底部显示最新消息
            this.$nextTick(() => {
              this.scrollToBottom()
            })
            
            return
          }
        }
        
        // 如果没有缓存或缓存无效，使用默认消息
        this.messages = [...this.defaultMessages]
        console.log('[AgentBoard] 使用默认聊天记录')
        
      } catch (error) {
        console.warn('[AgentBoard] 恢复聊天记录失败，使用默认记录:', error)
        this.messages = [...this.defaultMessages]
      }
    },
    
    /**
     * 清空聊天记录缓存
     */
    clearChatHistory() {
      try {
        sessionStorage.removeItem(CHAT_CACHE_KEY)
        this.messages = [...this.defaultMessages]
        console.log('[AgentBoard] 聊天记录缓存已清空')
      } catch (error) {
        console.warn('[AgentBoard] 清空聊天记录缓存失败:', error)
      }
    },
    
    /**
     * 手动重置聊天记录（可在UI中调用）
     */
    resetChatHistory() {
      // 添加确认对话框
      if (window.confirm('确定要清空所有聊天记录吗？此操作不可恢复。')) {
        this.clearChatHistory()
        this.$nextTick(() => {
          this.scrollToBottom()
        })
        
        // 可选：显示成功提示
        if (typeof ElMessage !== 'undefined') {
          ElMessage.success('聊天记录已清空')
        }
      }
    },

    // 配置和渲染Markdown
    setupMarkdown() {
      // 配置KaTeX选项
      const katexOptions = {
        throwOnError: false,
        displayMode: false,
        strict: false,
        trust: false,
        globalGroup: true,
        fleqn: false,
        leqno: false,
        colorIsTextColor: true,
        // 允许更多数学符号和函数
        macros: {
          '\\RR': '\\mathbb{R}',
          '\\ZZ': '\\mathbb{Z}',
          '\\NN': '\\mathbb{N}',
          '\\QQ': '\\mathbb{Q}',
          '\\CC': '\\mathbb{C}',
          // 希腊字母 - 小写
          '\\alpha': '\\alpha',
          '\\beta': '\\beta',
          '\\gamma': '\\gamma',
          '\\delta': '\\delta',
          '\\epsilon': '\\epsilon',
          '\\varepsilon': '\\varepsilon',
          '\\zeta': '\\zeta',
          '\\eta': '\\eta',
          '\\theta': '\\theta',
          '\\vartheta': '\\vartheta',
          '\\iota': '\\iota',
          '\\kappa': '\\kappa',
          '\\lambda': '\\lambda',
          '\\mu': '\\mu',
          '\\nu': '\\nu',
          '\\xi': '\\xi',
          '\\pi': '\\pi',
          '\\varpi': '\\varpi',
          '\\rho': '\\rho',
          '\\varrho': '\\varrho',
          '\\sigma': '\\sigma',
          '\\varsigma': '\\varsigma',
          '\\tau': '\\tau',
          '\\upsilon': '\\upsilon',
          '\\phi': '\\phi',
          '\\varphi': '\\varphi',
          '\\chi': '\\chi',
          '\\psi': '\\psi',
          '\\omega': '\\omega',
          // 希腊字母 - 大写
          '\\Alpha': '\\Alpha',
          '\\Beta': '\\Beta',
          '\\Gamma': '\\Gamma',
          '\\Delta': '\\Delta',
          '\\Epsilon': '\\Epsilon',
          '\\Zeta': '\\Zeta',
          '\\Eta': '\\Eta',
          '\\Theta': '\\Theta',
          '\\Iota': '\\Iota',
          '\\Kappa': '\\Kappa',
          '\\Lambda': '\\Lambda',
          '\\Mu': '\\Mu',
          '\\Nu': '\\Nu',
          '\\Xi': '\\Xi',
          '\\Pi': '\\Pi',
          '\\Rho': '\\Rho',
          '\\Sigma': '\\Sigma',
          '\\Tau': '\\Tau',
          '\\Upsilon': '\\Upsilon',
          '\\Phi': '\\Phi',
          '\\Chi': '\\Chi',
          '\\Psi': '\\Psi',
          '\\Omega': '\\Omega',
          // 数学运算符和符号
          '\\partial': '\\partial',
          '\\nabla': '\\nabla',
          '\\infty': '\\infty',
          '\\pm': '\\pm',
          '\\mp': '\\mp',
          '\\times': '\\times',
          '\\div': '\\div',
          '\\cdot': '\\cdot',
          '\\ast': '\\ast',
          '\\star': '\\star',
          '\\dagger': '\\dagger',
          '\\ddagger': '\\ddagger',
          '\\cap': '\\cap',
          '\\cup': '\\cup',
          '\\uplus': '\\uplus',
          '\\sqcap': '\\sqcap',
          '\\sqcup': '\\sqcup',
          '\\vee': '\\vee',
          '\\wedge': '\\wedge',
          '\\setminus': '\\setminus',
          '\\wr': '\\wr',
          '\\diamond': '\\diamond',
          '\\bigtriangleup': '\\bigtriangleup',
          '\\bigtriangledown': '\\bigtriangledown',
          '\\triangleleft': '\\triangleleft',
          '\\triangleright': '\\triangleright',
          '\\circ': '\\circ',
          '\\bullet': '\\bullet',
          '\\oplus': '\\oplus',
          '\\ominus': '\\ominus',
          '\\otimes': '\\otimes',
          '\\oslash': '\\oslash',
          '\\odot': '\\odot',
          '\\bigcirc': '\\bigcirc',
          // 关系符号
          '\\leq': '\\leq',
          '\\geq': '\\geq',
          '\\equiv': '\\equiv',
          '\\models': '\\models',
          '\\prec': '\\prec',
          '\\succ': '\\succ',
          '\\sim': '\\sim',
          '\\perp': '\\perp',
          '\\preceq': '\\preceq',
          '\\succeq': '\\succeq',
          '\\simeq': '\\simeq',
          '\\mid': '\\mid',
          '\\ll': '\\ll',
          '\\gg': '\\gg',
          '\\asymp': '\\asymp',
          '\\parallel': '\\parallel',
          '\\subset': '\\subset',
          '\\supset': '\\supset',
          '\\approx': '\\approx',
          '\\bowtie': '\\bowtie',
          '\\subseteq': '\\subseteq',
          '\\supseteq': '\\supseteq',
          '\\cong': '\\cong',
          '\\sqsubsetex': '\\sqsubsetex',
          '\\sqsupsetex': '\\sqsupsetex',
          '\\neq': '\\neq',
          '\\smile': '\\smile',
          '\\sqsubseteq': '\\sqsubseteq',
          '\\sqsupseteq': '\\sqsupseteq',
          '\\doteq': '\\doteq',
          '\\frown': '\\frown',
          '\\in': '\\in',
          '\\ni': '\\ni',
          '\\propto': '\\propto',
          '\\vdash': '\\vdash',
          '\\dashv': '\\dashv',
          // 箭头符号
          '\\leftarrow': '\\leftarrow',
          '\\gets': '\\gets',
          '\\rightarrow': '\\rightarrow',
          '\\to': '\\to',
          '\\leftrightarrow': '\\leftrightarrow',
          '\\Leftarrow': '\\Leftarrow',
          '\\Rightarrow': '\\Rightarrow',
          '\\Leftrightarrow': '\\Leftrightarrow',
          '\\mapsto': '\\mapsto',
          '\\hookleftarrow': '\\hookleftarrow',
          '\\leftharpoonup': '\\leftharpoonup',
          '\\leftharpoondown': '\\leftharpoondown',
          '\\rightleftharpoons': '\\rightleftharpoons',
          '\\longleftarrow': '\\longleftarrow',
          '\\longrightarrow': '\\longrightarrow',
          '\\longleftrightarrow': '\\longleftrightarrow',
          '\\longmapsto': '\\longmapsto',
          '\\hookrightarrow': '\\hookrightarrow',
          '\\rightharpoonup': '\\rightharpoonup',
          '\\rightharpoondown': '\\rightharpoondown',
          '\\leadsto': '\\leadsto',
          '\\uparrow': '\\uparrow',
          '\\downarrow': '\\downarrow',
          '\\updownarrow': '\\updownarrow',
          '\\Uparrow': '\\Uparrow',
          '\\Downarrow': '\\Downarrow',
          '\\Updownarrow': '\\Updownarrow',
          '\\nearrow': '\\nearrow',
          '\\searrow': '\\searrow',
          '\\swarrow': '\\swarrow',
          '\\nwarrow': '\\nwarrow'
        }
      }

      try {
        // 使用 KaTeX 扩展
        const extension = markedKatex({
          throwOnError: false,
          nonStandard: true,
          trust: false,
          strict: 'ignore',
          output: 'html',
          displayMode: false,
          leqno: false,
          fleqn: false,
          macros: katexOptions.macros,
          // 自定义错误回调
          errorColor: '#ff6b6b',
          // 渲染失败时显示原始LaTeX
          strict: function(errorCode, errorMsg, token) {
            console.warn(`[KaTeX] ${errorCode}: ${errorMsg}`, token)
            return 'ignore'
          }
        })

        marked.use(extension)
        console.log('[AgentBoard] KaTeX扩展已加载')
        
      } catch (error) {
        console.warn('[AgentBoard] KaTeX扩展加载失败，将使用基础Markdown渲染:', error)
      }

      marked.setOptions({
        breaks: true,
        gfm: true,
        highlight: function(code, lang) {
          if (lang && hljs.getLanguage(lang)) {
            try {
              return hljs.highlight(code, { language: lang }).value
            } catch (err) {}
          }
          return hljs.highlightAuto(code).value
        }
      })
    },
    
    renderMarkdown(content) {
      if (!content) return ''
      
      try {
        // 预处理内容，确保正确的数学公式格式
        let processedContent = content
        
        // 第一步：标准化换行符
        processedContent = processedContent.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
        
        // 第二步：处理qwen可能产生的特殊格式
        // 处理被 ` 包围的数学公式
        processedContent = processedContent.replace(/`\$([^`]+)\$`/g, '$$$1$$')
        processedContent = processedContent.replace(/`\$\$([^`]+)\$\$`/g, '$$$$1$$')
        
        // 处理LaTeX环境
        processedContent = processedContent.replace(/\\begin\{equation\}([\s\S]*?)\\end\{equation\}/g, (match, content) => {
          return `$$${content.trim()}$$`
        })
        processedContent = processedContent.replace(/\\begin\{align\}([\s\S]*?)\\end\{align\}/g, (match, content) => {
          return `$$${content.trim()}$$`
        })
        processedContent = processedContent.replace(/\\begin\{array\}([\s\S]*?)\\end\{array\}/g, (match, content) => {
          return `$$${content.trim()}$$`
        })
        
        // 第三步：处理反斜杠转义问题
        // qwen可能会生成双重转义的符号
        processedContent = processedContent.replace(/\\\\([a-zA-Z]+)/g, '\\$1')
        processedContent = processedContent.replace(/\\\\\{/g, '\\{')
        processedContent = processedContent.replace(/\\\\\}/g, '\\}')
        
        // 第三步补充：处理中文字符和特殊符号
        // 移除下标中的中文零宽字符
        processedContent = processedContent.replace(/([_^])\{([^}]*?)​([^}]*?)\}/g, '$1{$2$3}')
        processedContent = processedContent.replace(/​/g, '') // 移除所有零宽字符
        
        // 处理常见的数学符号替换
        processedContent = processedContent.replace(/\bKurtosis\b/g, '\\text{Kurtosis}')
        processedContent = processedContent.replace(/\bExcess\s+Kurtosis\b/g, '\\text{Excess Kurtosis}')
        processedContent = processedContent.replace(/\bsum\b(?![a-zA-Z])/g, '\\sum')
        processedContent = processedContent.replace(/\bsqrt\b(?![a-zA-Z])/g, '\\sqrt')
        
        // 修复常见的下标问题
        processedContent = processedContent.replace(/x\s*_\s*i\s*​/g, 'x_i')
        processedContent = processedContent.replace(/x\s*_\s*(\d+)\s*​/g, 'x_$1')
        processedContent = processedContent.replace(/x\s+i\s*​/g, 'x_i')
        
        // 处理中文混合的数学表达式
        processedContent = processedContent.replace(/：第\s*i\s*个/g, ': 第 i 个')
        processedContent = processedContent.replace(/：信号的/g, ': 信号的')
        processedContent = processedContent.replace(/：(\w)/g, ': $1')
        
        // 修复求和符号的范围表示
        processedContent = processedContent.replace(/\\sum_\{i=1\}\^\{N\}/g, '\\sum_{i=1}^{N}')
        processedContent = processedContent.replace(/\\sum_\{([^}]+)\}\^\{([^}]+)\}/g, '\\sum_{$1}^{$2}')
        
        // 处理分数中的复杂表达式
        processedContent = processedContent.replace(/\\frac\{1\}\{N\}\s*\\sum/g, '\\frac{1}{N} \\sum')
        processedContent = processedContent.replace(/\\sqrt\{\\frac\{1\}\{N\}/g, '\\sqrt{\\frac{1}{N}')
        
        // 处理大括号和小括号的嵌套
        processedContent = processedContent.replace(/\\left\(\s*\\frac\{([^}]+)\}\{([^}]+)\}\s*\\right\)\^\{?(\d+)\}?/g, '\\left(\\frac{$1}{$2}\\right)^{$3}')
        
        // 处理希腊字母
        processedContent = processedContent.replace(/\\mu(?![a-zA-Z])/g, '\\mu')
        processedContent = processedContent.replace(/\\sigma(?![a-zA-Z])/g, '\\sigma')
        
        // 修复常见的文本标记
        processedContent = processedContent.replace(/\\text\{([^}]*)\s+([^}]*)\}/g, '\\text{$1 $2}')
        
        // 第四步：确保数学公式的正确格式
        // 处理行内数学公式 - 更精确的匹配
        processedContent = processedContent.replace(/\$([^$\n]*?[^$\s])\$/g, (match, formula) => {
          // 避免匹配 $$ 块级公式
          if (formula.includes('$$')) return match
          // 清理formula中的多余空格和换行
          const cleanFormula = formula.trim().replace(/\s+/g, ' ')
          return `$${cleanFormula}$`
        })
        
        // 处理块级数学公式
        processedContent = processedContent.replace(/\$\$([\s\S]*?)\$\$/g, (match, formula) => {
          // 清理formula，保留必要的换行
          const cleanFormula = formula.trim()
          return `$$${cleanFormula}$$`
        })
        
        // 第五步：处理矩阵和数组
        processedContent = processedContent.replace(/\\begin\{pmatrix\}([\s\S]*?)\\end\{pmatrix\}/g, (match, content) => {
          return `\\begin{pmatrix}${content}\\end{pmatrix}`
        })
        processedContent = processedContent.replace(/\\begin\{bmatrix\}([\s\S]*?)\\end\{bmatrix\}/g, (match, content) => {
          return `\\begin{bmatrix}${content}\\end{bmatrix}`
        })
        processedContent = processedContent.replace(/\\begin\{vmatrix\}([\s\S]*?)\\end\{vmatrix\}/g, (match, content) => {
          return `\\begin{vmatrix}${content}\\end{vmatrix}`
        })
        
        // 第六步：清理多余的空格和换行，但保留必要的格式
        processedContent = processedContent.replace(/\n\s*\n/g, '\n\n') // 保留段落分隔
        
        console.log('[AgentBoard] 数学公式预处理完成')
        
        // 使用marked渲染处理后的内容
        return marked(processedContent)
        
      } catch (error) {
        console.warn('[AgentBoard] Markdown渲染失败:', error)
        // 如果渲染失败，返回原始内容（进行HTML转义）
        return content.replace(/</g, '&lt;').replace(/>/g, '&gt;')
      }
    },
    
    // 加载可用的 AI 模型
    async loadAvailableModels() {
      try {
        const response = await api.getAvailableModels()
        this.availableModels = response.models || []
        
        // 优先选择通义千问，然后是其他可用模型
        if (this.availableModels.length > 0) {
          const qwenModel = this.availableModels.find(model => model.id === 'qwen')
          if (qwenModel) {
            this.selectedModel = 'qwen'
          } else {
            this.selectedModel = this.availableModels[0].id
          }
        }
        
        this.connectionStatus = 'connected'
      } catch (error) {
        console.error('无法加载 AI 模型:', error)
        this.connectionStatus = 'disconnected'
        this.availableModels = [
          {
            id: 'qwen',
            name: '通义千问',
            description: '使用本地 MCSA 知识库回复',
            status: 'available',
            free: true
          },
          {
            id: 'local',
            name: '本地 MCSA 知识库',
            description: '基于专业 MCSA 知识的本地模型',
            status: 'available',
            free: true
          }
        ]
        this.selectedModel = 'qwen'
      }
    },

    createParticles() {
      const particlesContainer = this.$refs.particles
      const particleCount = 15  // 减少粒子数量：从30减少到15
      
      for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div')
        particle.classList.add('particle')
        
        // 减小粒子大小范围
        const size = Math.random() * 3 + 1.5  // 从6+2改为3+1.5
        particle.style.width = `${size}px`
        particle.style.height = `${size}px`
        
        // 随机位置
        const posX = Math.random() * 100
        const posY = Math.random() * 100
        particle.style.left = `${posX}%`
        particle.style.top = `${posY}%`
        
        // 降低透明度，使粒子更加柔和
        const colors = ['#00c6ff', '#0072ff', '#6a11cb']
        const color = colors[Math.floor(Math.random() * colors.length)]
        particle.style.background = color
        particle.style.opacity = '0.15'  // 降低透明度
        
        // 增加动画延迟范围，让动画更加分散
        particle.style.animationDelay = `${Math.random() * 25}s`  // 从15s增加到25s
        
        particlesContainer.appendChild(particle)
      }
    },
    
    setupPanelEffects() {
      this.$nextTick(() => {
        const panels = document.querySelectorAll('.panel')
        panels.forEach(panel => {
          // 降低3D效果敏感度，增加节流
          let rafId = null
          
          panel.addEventListener('mousemove', (e) => {
            if (rafId) return
            
            rafId = requestAnimationFrame(() => {
              const rect = panel.getBoundingClientRect()
              const x = e.clientX - rect.left
              const y = e.clientY - rect.top
              
              // 降低旋转敏感度：从 /20 改为 /60，并限制最大旋转角度
              const rotateX = Math.max(-3, Math.min(3, (y - rect.height/2) / 60))
              const rotateY = Math.max(-3, Math.min(3, -(x - rect.width/2) / 60))
              
              panel.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`
              rafId = null
            })
          })
          
          panel.addEventListener('mouseleave', () => {
            panel.style.transform = 'perspective(1000px) rotateX(0) rotateY(0)'
          })
        })
      })
    },
    
    async sendMessage() {
      const message = this.newMessage.trim()
      if (message && !this.isLoading) {
        // 添加用户消息，包含时间戳
        this.messages.push({
          type: 'user',
          content: message,
          isTyping: false,
          timestamp: new Date().toISOString()
        })
        
        // 清空输入框
        this.newMessage = ''
        
        // 滚动到底部
        this.scrollToBottom()
        
        // 发送到后端并获取AI回复
        await this.getAIReply(message)
      }
    },
    
    async getAIReply(userMessage) {
      this.isLoading = true
      
      // 添加AI回复消息（初始状态），包含时间戳
      const aiMessage = {
        type: 'ai',
        content: '',
        isTyping: true,
        timestamp: new Date().toISOString()
      }
      
      this.messages.push(aiMessage)
      this.scrollToBottom()
      
      try {
        // 准备对话历史
        const conversationHistory = this.messages
          .slice(0, -1) // 排除刚添加的 AI 消息
          .filter(msg => !msg.isTyping) // 排除正在输入的消息
          .map(msg => ({
            role: msg.type === 'user' ? 'user' : 'assistant',
            content: msg.content
          }))
        
        // 使用主后端的 AI 聊天流式接口
        const response = await fetch('http://localhost:8000/ai/chat/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: userMessage,
            conversation_history: conversationHistory,
            model_provider: this.selectedModel
          })
        })

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() // 保留不完整的行

          for (const line of lines) {
            if (line.trim().startsWith('data: ')) {
              try {
                const jsonStr = line.trim().substring(6)
                if (jsonStr && jsonStr !== '[DONE]') {
                  const data = JSON.parse(jsonStr)
                  
                  if (data.content) {
                    // 逐字符更新消息内容
                    aiMessage.content += data.content
                    this.scrollToBottom()
                  }
                  
                  if (data.done) {
                    // 流式响应完成
                    aiMessage.isTyping = false
                    this.connectionStatus = 'connected'
                    break
                  }
                }
              } catch (e) {
                console.warn('解析流式数据失败:', e)
              }
            }
          }
        }
        
      } catch (error) {
        console.error('AI 回复失败:', error)
                // 尝试非流式后备接口
        try {
          const resp = await fetch('http://localhost:8000/ai/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              message: userMessage,
              conversation_history: conversationHistory,
              model_provider: this.selectedModel
            })
          })
          if (resp.ok) {
            const data = await resp.json()
            aiMessage.isTyping = false
            aiMessage.content = data.response || data.content || JSON.stringify(data)
            this.connectionStatus = 'connected'
          } else {
            throw new Error(`HTTP ${resp.status}: ${resp.statusText}`)
          }
        } catch (fallbackErr) {
        aiMessage.isTyping = false
        aiMessage.content = `抱歉，AI服务暂时不可用。错误信息：${error.message}。\n\n作为备选，我可以基于MCSA知识库为您提供基础的诊断建议。请重新描述您的问题。`
        this.connectionStatus = 'disconnected'
        }
      } finally {
        this.isLoading = false
        this.scrollToBottom()
      }
    },
    
    scrollToBottom() {
      this.$nextTick(() => {
        const chatMessages = this.$refs.chatMessages
        if (chatMessages) {
          chatMessages.scrollTop = chatMessages.scrollHeight
        }
      })
    },
    
    /**
     * 开发环境测试方法：验证缓存功能
     */
    testCacheFunction() {
      if (process.env.NODE_ENV === 'development') {
        console.log('=== MCSA 聊天缓存功能测试 ===')
        console.log('当前消息数量:', this.messages.length)
        console.log('缓存键:', CHAT_CACHE_KEY)
        
        const cached = sessionStorage.getItem(CHAT_CACHE_KEY)
        if (cached) {
          console.log('缓存数据:', JSON.parse(cached))
        } else {
          console.log('暂无缓存数据')
        }
        console.log('=== 测试结束 ===')
      }
    },
    
    /**
     * 开发环境测试方法：验证数学公式渲染
     */
    testMathRendering() {
      if (process.env.NODE_ENV === 'development') {
        const testFormulas = [
          '# MCSA 诊断助手数学公式渲染测试',
          '',
          '## 基础公式测试',
          '行内公式测试：$\\omega = 2\\pi f$',
          '',
          '块级公式测试：',
          '$$E = mc^2$$',
          '',
          '## 复杂公式测试',
          '偏微分方程：',
          '$$\\frac{\\partial^2 u}{\\partial t^2} = c^2 \\nabla^2 u$$',
          '',
          '## 希腊字母测试',
          '**小写希腊字母：**',
          '$\\alpha, \\beta, \\gamma, \\delta, \\epsilon, \\zeta, \\eta, \\theta, \\iota, \\kappa, \\lambda, \\mu, \\nu, \\xi, \\pi, \\rho, \\sigma, \\tau, \\upsilon, \\phi, \\chi, \\psi, \\omega$',
          '',
          '**大写希腊字母：**',
          '$\\Alpha, \\Beta, \\Gamma, \\Delta, \\Epsilon, \\Zeta, \\Eta, \\Theta, \\Iota, \\Kappa, \\Lambda, \\Mu, \\Nu, \\Xi, \\Pi, \\Rho, \\Sigma, \\Tau, \\Upsilon, \\Phi, \\Chi, \\Psi, \\Omega$',
          '',
          '## 矩阵测试',
          '括号矩阵：',
          '$$\\begin{pmatrix} a & b \\\\ c & d \\end{pmatrix}$$',
          '',
          '方括号矩阵：',
          '$$\\begin{bmatrix} \\alpha & \\beta \\\\ \\gamma & \\delta \\end{bmatrix}$$',
          '',
          '## 求和积分测试',
          '求和公式：',
          '$$\\sum_{i=1}^n x_i = \\int_0^\\infty e^{-x} dx$$',
          '',
          '多重积分：',
          '$$\\iint_D f(x,y) \\, dx \\, dy = \\int_{-\\infty}^{\\infty} \\int_{-\\infty}^{\\infty} g(x,y) \\, dx \\, dy$$',
          '',
          '## 数学运算符测试',
          '基本运算：$\\pm, \\mp, \\times, \\div, \\cdot, \\ast, \\star$',
          '',
          '关系符号：$\\leq, \\geq, \\neq, \\equiv, \\approx, \\sim, \\propto$',
          '',
          '集合运算：$\\in, \\ni, \\subset, \\supset, \\subseteq, \\supseteq, \\cup, \\cap$',
          '',
          '## 箭头符号测试',
          '基本箭头：$\\leftarrow, \\rightarrow, \\leftrightarrow, \\Leftarrow, \\Rightarrow, \\Leftrightarrow$',
          '',
          '长箭头：$\\longleftarrow, \\longrightarrow, \\longleftrightarrow$',
          '',
          '垂直箭头：$\\uparrow, \\downarrow, \\updownarrow, \\Uparrow, \\Downarrow$',
          '',
          '## 特殊符号测试',
          '微分算子：$\\partial, \\nabla, \\triangle$',
          '',
          '无穷和其他：$\\infty, \\emptyset, \\forall, \\exists, \\neg, \\angle$',
          '',
          '## MCSA 相关数学表达式',
          '频率域分析：',
          '$$X(f) = \\int_{-\\infty}^{\\infty} x(t) e^{-j2\\pi ft} dt$$',
          '',
          '功率谱密度：',
          '$$S_{xx}(f) = \\lim_{T \\to \\infty} \\frac{1}{T} \\left| X_T(f) \\right|^2$$',
          '',
          '故障特征频率：',
          '$$f_{BPFO} = \\frac{N_b}{2} f_r \\left(1 - \\frac{d}{D} \\cos \\phi \\right)$$',
          '',
          '其中：$N_b$ 是滚珠数量，$f_r$ 是转子频率，$d$ 是滚珠直径，$D$ 是节圆直径，$\\phi$ 是接触角',
          '',
          '---',
          '',
          '✅ **如果以上公式都能正确显示，说明数学公式渲染功能正常工作！**'
        ]
        
        const testMessage = {
          type: 'ai',
          content: testFormulas.join('\n'),
          isTyping: false,
          timestamp: new Date().toISOString()
        }
        
        this.messages.push(testMessage)
        this.$nextTick(() => {
          this.scrollToBottom()
        })
        
        console.log('[AgentBoard] 已添加全面的数学公式测试消息')
      }
    },

    /**
     * 打开外部知识库
     */
    openKnowledgeBase() {
      const knowledgeBaseUrl = 'http://117.72.180.197:5174/'
      window.open(knowledgeBaseUrl, '_blank', 'noopener,noreferrer')
      console.log('[AgentBoard] 已打开外部知识库:', knowledgeBaseUrl)
    },

    // ===== RAG 文档管理方法 =====
    
    /**
     * 处理文件选择
     */
    async handleFileSelect(event) {
      const files = Array.from(event.target.files)
      if (files.length) {
        await this.uploadFiles(files)
      }
    },

    /**
     * 处理文件拖拽
     */
    async handleFileDrop(event) {
      event.preventDefault()
      const files = Array.from(event.dataTransfer.files)
      if (files.length) {
        await this.uploadFiles(files)
      }
    },

    /**
     * 上传文件到 RAG 系统
     */
    async uploadFiles(files) {
      this.isLoading = true
      
      for (const file of files) {
        // 文件验证
        const maxSize = 50 * 1024 * 1024 // 50MB
        const allowedTypes = ['.pdf', '.txt', '.docx', '.md', '.doc']
        const fileExtension = '.' + file.name.split('.').pop().toLowerCase()
        
        const progressItem = {
          filename: file.name,
          percent: 0,
          status: 'uploading',
          message: '上传中...'
        }
        this.uploadProgress.push(progressItem)

        // 文件大小检查
        if (file.size > maxSize) {
          progressItem.percent = 100
          progressItem.status = 'error'
          progressItem.message = '文件过大，请选择小于50MB的文件'
          continue
        }

        // 文件类型检查
        if (!allowedTypes.includes(fileExtension)) {
          progressItem.percent = 100
          progressItem.status = 'error'
          progressItem.message = `不支持的文件类型: ${fileExtension}`
          continue
        }

        try {
          const formData = new FormData()
          formData.append('file', file)
          
          const response = await fetch('http://localhost:9621/documents/upload', {
            method: 'POST',
            body: formData
          })
          
          if (response.ok) {
            const result = await response.json()
            progressItem.percent = 100
            
            // 检查上传状态
            if (result.status === 'success') {
              progressItem.status = 'success'
              progressItem.message = result.message || '上传成功，正在后台处理...'
            } else if (result.status === 'duplicated') {
              progressItem.status = 'warning'
              progressItem.message = '文件已存在，跳过上传'
            } else {
              progressItem.status = 'warning'
              progressItem.message = result.message || '上传完成，但可能存在问题'
            }
            
            // 刷新文档列表
            await this.loadDocuments()
          } else {
            const errorData = await response.json().catch(() => ({}))
            throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`)
          }
        } catch (error) {
          progressItem.percent = 100
          progressItem.status = 'error'
          progressItem.message = `上传失败: ${error.message}`
        }
      }
      
      this.isLoading = false
      
      // 5秒后清除进度显示
      setTimeout(() => {
        this.uploadProgress = []
      }, 5000)
    },

    /**
     * 批量添加文本
     */
    async addBulkTexts() {
      if (!this.bulkTexts.trim()) return
      
      this.isLoading = true
      
      try {
        const texts = this.bulkTexts.split('\n').filter(t => t.trim()).map(t => t.trim())
        const sources = texts.map(() => this.textSource || '手动输入')
        
        const response = await fetch('http://localhost:9621/documents/texts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            texts: texts,
            file_sources: sources
          })
        })
        
        if (response.ok) {
          const result = await response.json()
          console.log('文本添加成功:', result)
          
          // 清空输入
          this.bulkTexts = ''
          this.textSource = ''
          
          // 刷新文档列表
          await this.loadDocuments()
        } else {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }
      } catch (error) {
        console.error('添加文本失败:', error)
      } finally {
        this.isLoading = false
      }
    },

    /**
     * 加载文档状态
     */
    async loadDocuments() {
      try {
        const response = await fetch('http://localhost:9621/documents')
        if (response.ok) {
          this.documentGroups = await response.json()
        }
        
        // 同时获取流水线状态
        const pipelineResp = await fetch('http://localhost:9621/documents/pipeline_status')
        if (pipelineResp.ok) {
          this.pipelineStatus = await pipelineResp.json()
        }
      } catch (error) {
        console.error('加载文档状态失败:', error)
      }
    },

    /**
     * 清空所有文档
     */
    async clearAllDocuments() {
      if (!confirm('确定要清空所有文档吗？此操作不可恢复！')) return
      
      this.isLoading = true
      
      try {
        const response = await fetch('http://localhost:9621/documents', {
          method: 'DELETE'
        })
        
        if (response.ok) {
          const result = await response.json()
          console.log('清空文档结果:', result)
          await this.loadDocuments()
        } else {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }
      } catch (error) {
        console.error('清空文档失败:', error)
      } finally {
        this.isLoading = false
      }
    },

    /**
     * 删除单个文档
     */
    async deleteDocument(docId) {
      if (!confirm('确定要删除这个文档吗？')) return
      
      try {
        const response = await fetch('http://localhost:9621/documents/delete_document', {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            doc_ids: [docId],
            delete_file: false
          })
        })
        
        if (response.ok) {
          const result = await response.json()
          console.log('删除文档结果:', result)
          await this.loadDocuments()
        } else {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }
      } catch (error) {
        console.error('删除文档失败:', error)
      }
    },

    /**
     * 获取状态显示名称
     */
    getStatusName(status) {
      const statusMap = {
        'pending': '待处理',
        'processing': '处理中', 
        'completed': '已完成',
        'failed': '失败',
        'indexed': '已索引'
      }
      return statusMap[status] || status
    },

    /**
     * 格式化时间
     */
    formatTime(timestamp) {
      if (!timestamp) return ''
      return new Date(timestamp).toLocaleString('zh-CN')
    },

    // ===== 知识图谱方法 =====

    /**
     * 加载图谱标签
     */
    async loadGraphLabels() {
      this.isLoading = true
      
      try {
        const response = await fetch('http://localhost:9621/graph/label/list')
        if (response.ok) {
          this.graphLabels = await response.json()
        } else {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }
      } catch (error) {
        console.error('加载图谱标签失败:', error)
        this.graphLabels = []
      } finally {
        this.isLoading = false
      }
    },

    /**
     * 加载子图
     */
    async loadSubgraph(label) {
      if (!label) return
      
      this.isLoading = true
      this.selectedLabel = label
      
      try {
        const params = new URLSearchParams({
          label: label,
          max_depth: this.maxDepth.toString(),
          max_nodes: this.maxNodes.toString()
        })
        
        const response = await fetch(`http://localhost:9621/graphs?${params}`)
        if (response.ok) {
          this.currentSubgraph = await response.json()
        } else {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }
      } catch (error) {
        console.error('加载子图失败:', error)
        this.currentSubgraph = null
      } finally {
        this.isLoading = false
      }
    },

    /**
     * 检查实体是否存在
     */
    async checkEntityExists() {
      if (!this.entityName.trim()) return
      
      try {
        const params = new URLSearchParams({ name: this.entityName.trim() })
        const response = await fetch(`http://localhost:9621/graph/entity/exists?${params}`)
        
        if (response.ok) {
          const result = await response.json()
          this.entityExists = result.exists || false
        } else {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }
      } catch (error) {
        console.error('检查实体失败:', error)
        this.entityExists = null
      }
    },

    // ===== 系统健康状态方法 =====

    /**
     * 加载系统健康状态
     */
    async loadHealthStatus() {
      this.isLoading = true
      
      try {
        const response = await fetch('http://localhost:9621/health')
        if (response.ok) {
          this.healthStatus = await response.json()
        } else {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }
      } catch (error) {
        console.error('加载健康状态失败:', error)
        this.healthStatus = null
      } finally {
        this.isLoading = false
      }
    },

    /**
     * 格式化健康状态数据
     */
    formatHealthData(data) {
      try {
        return JSON.stringify(data, null, 2)
      } catch (error) {
        return '数据格式化失败'
      }
    }
  }
}
</script>

<style scoped>
:root {
  --primary: #00c6ff;
  --secondary: #0072ff;
  --accent: #6a11cb;
  --dark: #0f172a;
  --darker: #718ee4;
  --light: #ffffff;
  --glass: rgba(227, 234, 245, 0.5);
  --glass-light: rgba(255, 255, 255, 0.05);
  --neon-glow: 0 0 10px rgba(0, 198, 255, 0.7), 0 0 20px rgba(0, 114, 255, 0.5);
  --border: rgba(236, 218, 218, 0.2);
  --text-primary: #ffffff;
}

.agent-board {
  font-family: 'Exo 2', sans-serif;
  background: linear-gradient(135deg, var(--darker), #1e293b);
  color: var(--light);
  min-height: 100vh;
  overflow-x: hidden;
  position: relative;
}

.agent-board::before {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: radial-gradient(circle at 20% 30%, rgba(106, 17, 203, 0.1) 0%, transparent 40%),
              radial-gradient(circle at 80% 70%, rgba(0, 114, 255, 0.1) 0%, transparent 40%);
  z-index: -2;
}

.particles {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: -1;
  overflow: hidden;
}

.particle {
  position: absolute;
  border-radius: 50%;
  background: var(--primary);
  opacity: 0.2;
  animation: float 25s infinite ease-in-out;
}

@keyframes float {
  0% { transform: translateY(0) translateX(0); }
  25% { transform: translateY(-10px) translateX(5px); }
  50% { transform: translateY(0) translateX(10px); }
  75% { transform: translateY(10px) translateX(5px); }
  100% { transform: translateY(0) translateX(0); }
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 0;
  margin-bottom: 2rem;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  width: 42px;
  height: 42px;
  background: linear-gradient(135deg, var(--primary), var(--secondary));
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--neon-glow);
}

.logo-text {
  font-size: 1.8rem;
  font-weight: 700;
  background: linear-gradient(to right, var(--primary), var(--secondary));
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: 1px;
}

.main-content {
  display: flex;
  justify-content: center;
  margin-top: 2rem;
}

.panel {
  background: var(--glass);
  backdrop-filter: blur(12px);
  border-radius: 20px;
  border: 1px solid var(--glass-light);
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  position: relative;
  transition: transform 0.6s ease-out;
  max-width: 1200px;
  width: 100%;
}

.panel::before {
  content: '';
  position: absolute;
  top: -2px;
  left: -2px;
  right: -2px;
  bottom: -2px;
  background: linear-gradient(45deg, var(--primary), var(--accent), var(--secondary));
  z-index: -1;
  border-radius: 22px;
}

.panel-header {
  padding: 1.5rem;
  border-bottom: 1px solid var(--glass-light);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-title {
  font-size: 1.4rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
}

.panel-title i {
  color: var(--primary);
}

.message-count {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.6);
  font-weight: 400;
  margin-left: 8px;
}

.panel-controls {
  display: flex;
  align-items: center;
  gap: 15px;
}

.clear-chat-btn {
  background: linear-gradient(135deg, var(--secondary), var(--primary));
  border: none;
  border-radius: 10px;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--light);
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 10px rgba(194, 207, 159, 0.3);
}

.clear-chat-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 15px rgba(0, 114, 255, 0.4);
}

.clear-chat-btn:active {
  transform: translateY(0);
}

.clear-chat-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.clear-chat-btn:disabled:hover {
  transform: none;
  box-shadow: 0 4px 10px rgb(187, 177, 177);
}

.knowledge-base-btn {
  background: linear-gradient(135deg, var(--accent), var(--primary));
  border: none;
  border-radius: 10px;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--light);
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 10px rgba(106, 17, 203, 0.3);
}

.knowledge-base-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 15px rgba(106, 17, 203, 0.4);
}

.knowledge-base-btn:active {
  transform: translateY(0);
}

.test-math-btn {
  background: linear-gradient(135deg, var(--accent), var(--secondary));
  border: none;
  border-radius: 10px;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--light);
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 10px rgba(106, 17, 203, 0.3);
}

.test-math-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 15px rgba(106, 17, 203, 0.4);
}

.test-math-btn:active {
  transform: translateY(0);
}

.test-math-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.test-math-btn:disabled:hover {
  transform: none;
  box-shadow: 0 4px 10px rgb(187, 177, 177);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  transition: all 0.3s ease;
}

.status-dot.connected {
  background: #4ade80;
  box-shadow: 0 0 8px #4ade80;
}

.status-dot.disconnected {
  background: #ef4444;
  box-shadow: 0 0 8px #ef4444;
}

.chat-container {
  height: 700px;
  display: flex;
  flex-direction: column;
}

.chat-messages {
  flex: 1;
  padding: 1.5rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.message {
  max-width: 80%;
  padding: 1rem 1.5rem;
  border-radius: 18px;
  position: relative;
  animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}

.user-message {
  background: linear-gradient(135deg, rgba(0, 114, 255, 0.2), rgba(0, 198, 255, 0.2));
  align-self: flex-end;
  border-bottom-right-radius: 5px;
}

.ai-message {
  background: linear-gradient(135deg, rgba(106, 17, 203, 0.2), rgba(0, 114, 255, 0.2));
  align-self: flex-start;
  border-bottom-left-radius: 5px;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
}

.user-avatar {
  background: linear-gradient(135deg, var(--secondary), var(--primary));
}

.ai-avatar {
  background: linear-gradient(135deg, var(--accent), var(--secondary));
}

.message-content {
  line-height: 1.6;
}

.message-content.typing::after {
  content: '▋';
  animation: blink 1s infinite;
  opacity: 1;
}

@keyframes blink {
  0% { opacity: 1; }
  50% { opacity: 0.3; }
  100% { opacity: 1; }
}

/* Markdown 内容样式 */
.markdown-content {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  line-height: 1.6;
  color: var(--text-primary);
}

/* KaTeX 数学公式样式优化 */
.markdown-content .katex {
  font-size: 1.1em !important;
  color: var(--light) !important;
}

.markdown-content .katex-display {
  margin: 16px 0 !important;
  text-align: center;
  background: rgba(0, 0, 0, 0.2);
  padding: 12px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  overflow-x: auto;
}

.markdown-content .katex-display .katex {
  font-size: 1.2em !important;
  color: #e2e8f0 !important;
}

/* 行内数学公式样式 */
.markdown-content .katex:not(.katex-display) {
  background: rgba(255, 255, 255, 0.05);
  padding: 2px 4px;
  border-radius: 3px;
  font-size: 1.05em !important;
}

/* 数学公式中的特殊符号颜色 */
.markdown-content .katex .mord {
  color: var(--light) !important;
}

.markdown-content .katex .mbin,
.markdown-content .katex .mrel {
  color: var(--primary) !important;
}

.markdown-content .katex .mop {
  color: var(--accent) !important;
}

.markdown-content .katex .mopen,
.markdown-content .katex .mclose {
  color: var(--secondary) !important;
}

/* 希腊字母和特殊符号 */
.markdown-content .katex .mathit {
  color: var(--accent) !important;
  font-style: italic;
}

/* 公式编号和标签 */
.markdown-content .katex .tag {
  color: rgba(255, 255, 255, 0.6) !important;
}

/* 响应式数学公式 */
@media (max-width: 768px) {
  .markdown-content .katex-display {
    font-size: 0.9em !important;
    padding: 8px;
    margin: 12px 0 !important;
  }
  
  .markdown-content .katex:not(.katex-display) {
    font-size: 0.95em !important;
  }
}

/* KaTeX 渲染错误处理 */
.markdown-content .katex .katex-error {
  color: #ff6b6b !important;
  background: rgba(255, 107, 107, 0.1);
  padding: 2px 4px;
  border-radius: 3px;
  font-family: monospace;
  font-size: 0.9em;
}

/* 数学公式加载状态 */
.markdown-content .katex.loading {
  background: rgba(255, 255, 255, 0.1);
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0% { opacity: 0.6; }
  50% { opacity: 1; }
  100% { opacity: 0.6; }
}

.markdown-content h1,
.markdown-content h2,
.markdown-content h3,
.markdown-content h4,
.markdown-content h5,
.markdown-content h6 {
  margin: 16px 0 8px 0;
  font-weight: 600;
  line-height: 1.4;
  color: var(--primary);
}

.markdown-content h1 { font-size: 1.8em; border-bottom: 2px solid var(--primary); padding-bottom: 8px; }
.markdown-content h2 { font-size: 1.5em; border-bottom: 1px solid var(--border); padding-bottom: 6px; }
.markdown-content h3 { font-size: 1.3em; color: var(--accent); }
.markdown-content h4 { font-size: 1.1em; }

.markdown-content p {
  margin: 12px 0;
  line-height: 1.6;
}

.markdown-content ul,
.markdown-content ol {
  margin: 12px 0;
  padding-left: 24px;
}

.markdown-content li {
  margin: 6px 0;
  line-height: 1.5;
}

.markdown-content blockquote {
  margin: 16px 0;
  padding: 12px 20px;
  border-left: 4px solid var(--primary);
  background: rgba(255, 255, 255, 0.05);
  border-radius: 0 8px 8px 0;
  font-style: italic;
}

.markdown-content code {
  background: rgba(255, 255, 255, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Fira Code', 'Consolas', 'Monaco', monospace;
  font-size: 0.9em;
  color: var(--accent);
}

.markdown-content pre {
  background: rgba(0, 0, 0, 0.3);
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 16px 0;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.markdown-content pre code {
  background: none;
  padding: 0;
  color: #e6edf3;
  font-size: 0.9em;
  line-height: 1.4;
}

.markdown-content table {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}

.markdown-content th,
.markdown-content td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid var(--border);
}

.markdown-content th {
  background: rgba(255, 255, 255, 0.05);
  font-weight: 600;
  color: var(--primary);
}

.markdown-content tr:hover {
  background: rgba(255, 255, 255, 0.02);
}

.markdown-content hr {
  border: none;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--primary), transparent);
  margin: 24px 0;
}

.markdown-content strong {
  color: var(--accent);
  font-weight: 600;
}

.markdown-content em {
  color: var(--secondary);
  font-style: italic;
}

.input-area {
  padding: 1.5rem;
  border-top: 1px solid var(--glass-light);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.model-selector {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  opacity: 0.8;
}

.model-select {
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid var(--glass-light);
  border-radius: 8px;
  color: var(--light);
  padding: 0.5rem;
  font-family: inherit;
  font-size: 0.85rem;
  transition: all 0.3s ease;
}

.model-select:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 2px rgba(0, 198, 255, 0.2);
}

.message-controls {
  display: flex;
  gap: 1rem;
}

.message-input {
  flex: 1;
  padding: 1rem 1.5rem;
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid var(--glass-light);
  border-radius: 15px;
  color: var(--light);
  font-family: inherit;
  font-size: 1rem;
  transition: all 0.3s ease;
}

.message-input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(248, 246, 244, 0.61);
}

.message-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.send-button {
  width: 50px;
  height: 50px;
  border-radius: 15px;
  background: linear-gradient(135deg, var(--primary), var(--secondary));
  border: none;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.4s ease-out;
  box-shadow: 0 4px 15px rgba(0, 114, 255, 0.4);
}

.send-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(0, 114, 255, 0.5);
}

.send-button:active {
  transform: translateY(0);
}

.send-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.send-button:disabled:hover {
  transform: none;
  box-shadow: 0 4px 15px rgb(187, 177, 177);
}

footer {
  text-align: center;
  padding: 2rem 0;
  margin-top: 3rem;
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.6);
  opacity: 1;
  border-top: 1px solid var(--glass-light);
}

/* RAG 功能样式 */

/* 选项卡样式 */
.rag-tabs {
  display: flex;
  gap: 8px;
  margin-right: 15px;
}

.tab-btn {
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid var(--glass-light);
  border-radius: 8px;
  padding: 6px 12px;
  color: rgba(255, 255, 255, 0.8);
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 6px;
}

.tab-btn:hover {
  background: rgba(0, 114, 255, 0.2);
  border-color: var(--secondary);
}

.tab-btn.active {
  background: linear-gradient(135deg, var(--primary), var(--secondary));
  border-color: var(--primary);
  color: var(--light);
  font-weight: 600;
}

/* 查询模式选择 */
.rag-query-mode {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
  opacity: 0.9;
}

.mode-select {
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid var(--glass-light);
  border-radius: 6px;
  color: var(--light);
  padding: 4px 8px;
  font-size: 0.85rem;
  transition: all 0.3s ease;
}

.mode-select:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 2px rgba(0, 198, 255, 0.2);
}

/* 文档管理容器 */
.docs-container,
.graph-container,
.health-container {
  padding: 1.5rem;
  height: 700px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.docs-header,
.graph-header,
.health-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--glass-light);
  padding-bottom: 1rem;
}

.docs-header h3,
.graph-header h3,
.health-header h3 {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--primary);
  margin: 0;
  font-size: 1.3rem;
}

.docs-actions,
.graph-actions,
.health-actions {
  display: flex;
  gap: 10px;
}

/* 通用按钮样式 */
.action-btn {
  border: none;
  border-radius: 8px;
  padding: 8px 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
}

.refresh-btn {
  background: linear-gradient(135deg, var(--secondary), var(--primary));
  color: white;
}

.primary-btn {
  background: linear-gradient(135deg, var(--primary), var(--secondary));
  color: white;
}

.secondary-btn {
  background: linear-gradient(135deg, var(--accent), var(--secondary));
  color: white;
}

.danger-btn {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
}

.action-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

/* 文件上传区域 */
.upload-section {
  background: rgba(255, 255, 255, 0.02);
  border-radius: 12px;
  padding: 1.5rem;
  border: 1px solid var(--glass-light);
}

.upload-section h4 {
  margin: 0 0 1rem 0;
  color: var(--accent);
  display: flex;
  align-items: center;
  gap: 8px;
}

.upload-zone {
  border: 2px dashed var(--glass-light);
  border-radius: 12px;
  padding: 2rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: rgba(255, 255, 255, 0.02);
}

.upload-zone:hover {
  border-color: var(--primary);
  background: rgba(0, 198, 255, 0.05);
}

.upload-zone i {
  font-size: 2rem;
  color: var(--primary);
  margin-bottom: 1rem;
}

.upload-progress {
  margin-top: 1rem;
}

.progress-item {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  padding: 8px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
}

.progress-bar {
  flex: 1;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary), var(--secondary));
  transition: width 0.3s ease;
}

.progress-item .success {
  color: #4ade80;
}

.progress-item .error {
  color: #ef4444;
}

.progress-item .warning {
  color: #f59e0b;
}

/* 上传提示样式 */
.upload-tips {
  margin-top: 1rem;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.tip-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.7);
  opacity: 0.8;
}

.tip-item i {
  font-size: 0.7rem;
  color: var(--accent);
}

/* 文本输入区域 */
.text-input-section {
  background: rgba(255, 255, 255, 0.02);
  border-radius: 12px;
  padding: 1.5rem;
  border: 1px solid var(--glass-light);
}

.text-input-section h4 {
  margin: 0 0 1rem 0;
  color: var(--accent);
  display: flex;
  align-items: center;
  gap: 8px;
}

.text-input-area {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.bulk-text-input {
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid var(--glass-light);
  border-radius: 8px;
  padding: 12px;
  color: var(--light);
  font-family: inherit;
  resize: vertical;
  min-height: 120px;
}

.bulk-text-input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 2px rgba(0, 198, 255, 0.2);
}

.source-input {
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid var(--glass-light);
  border-radius: 8px;
  padding: 10px 12px;
  color: var(--light);
  font-family: inherit;
}

.source-input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 2px rgba(0, 198, 255, 0.2);
}

/* 文档状态网格 */
.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.status-card {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 1rem;
  border: 1px solid var(--glass-light);
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.status-name {
  font-weight: 600;
  color: var(--primary);
}

.status-count {
  background: var(--accent);
  color: white;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 600;
}

.status-items {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.doc-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85rem;
  padding: 4px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.02);
}

.doc-item i {
  color: var(--secondary);
}

.doc-item span {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.delete-doc-btn {
  background: none;
  border: none;
  color: #ef4444;
  cursor: pointer;
  padding: 2px;
  border-radius: 2px;
  opacity: 0.7;
  transition: opacity 0.2s ease;
}

.delete-doc-btn:hover {
  opacity: 1;
}

.more-items {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.6);
  font-style: italic;
}

/* 流水线状态 */
.pipeline-section {
  background: rgba(255, 255, 255, 0.02);
  border-radius: 12px;
  padding: 1.5rem;
  border: 1px solid var(--glass-light);
}

.pipeline-section h4 {
  margin: 0 0 1rem 0;
  color: var(--accent);
  display: flex;
  align-items: center;
  gap: 8px;
}

.pipeline-info {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 1rem;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-item label {
  font-weight: 600;
  color: rgba(255, 255, 255, 0.8);
}

.status-badge {
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 600;
}

.status-badge.busy {
  background: #f59e0b;
  color: white;
}

.status-badge.idle {
  background: #10b981;
  color: white;
}

.pipeline-logs h5 {
  margin: 0 0 0.5rem 0;
  color: var(--secondary);
}

.log-messages {
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  padding: 1rem;
  max-height: 150px;
  overflow-y: auto;
  font-family: monospace;
  font-size: 0.85rem;
}

.log-message {
  padding: 2px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.9);
}

/* 处理建议样式 */
.processing-tips {
  background: rgba(255, 255, 255, 0.02);
  border-radius: 12px;
  padding: 1.5rem;
  border: 1px solid var(--glass-light);
}

.processing-tips h4 {
  margin: 0 0 1rem 0;
  color: var(--accent);
  display: flex;
  align-items: center;
  gap: 8px;
}

.tips-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.tip-card {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  padding: 1rem;
  border: 1px solid var(--glass-light);
  transition: all 0.3s ease;
}

.tip-card:hover {
  background: rgba(255, 255, 255, 0.08);
  transform: translateY(-2px);
}

.tip-card i {
  font-size: 1.5rem;
  color: var(--primary);
  margin-bottom: 0.5rem;
  display: block;
}

.tip-card h5 {
  margin: 0 0 0.5rem 0;
  color: var(--secondary);
  font-size: 1rem;
}

.tip-card ul {
  margin: 0;
  padding-left: 1rem;
  list-style: none;
}

.tip-card li {
  margin: 0.3rem 0;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.8);
  position: relative;
}

.tip-card li::before {
  content: '•';
  color: var(--accent);
  position: absolute;
  left: -0.8rem;
}

/* 知识图谱样式 */
.labels-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.label-item {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--glass-light);
  border-radius: 20px;
  padding: 6px 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.9rem;
}

.label-item:hover {
  background: rgba(0, 198, 255, 0.1);
  border-color: var(--primary);
}

.label-item i {
  color: var(--accent);
}

.query-controls {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.label-select,
.depth-input,
.nodes-input,
.entity-input {
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid var(--glass-light);
  border-radius: 6px;
  padding: 8px 12px;
  color: var(--light);
  font-family: inherit;
}

.label-select:focus,
.depth-input:focus,
.nodes-input:focus,
.entity-input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 2px rgba(0, 198, 255, 0.2);
}

.entity-search {
  display: flex;
  gap: 10px;
  align-items: center;
}

.entity-result {
  margin-top: 10px;
}

.result-badge {
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 600;
}

.result-badge.exists {
  background: #10b981;
  color: white;
}

.result-badge.not-exists {
  background: #ef4444;
  color: white;
}

.graph-stats {
  display: flex;
  gap: 15px;
  margin-bottom: 1rem;
}

.stat-item {
  background: rgba(255, 255, 255, 0.05);
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 600;
}

.graph-placeholder {
  background: rgba(255, 255, 255, 0.02);
  border: 2px dashed var(--glass-light);
  border-radius: 12px;
  padding: 2rem;
  text-align: center;
  color: rgba(255, 255, 255, 0.6);
}

.graph-placeholder i {
  font-size: 3rem;
  margin-bottom: 1rem;
  color: var(--accent);
}

/* 健康状态样式 */
.health-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
}

.health-card {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 1rem;
  text-align: center;
  border: 1px solid var(--glass-light);
}

.health-label {
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.8);
  margin-bottom: 0.5rem;
}

.health-value {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--primary);
}

.status-healthy {
  color: #10b981 !important;
}

.config-details {
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  padding: 1rem;
  max-height: 400px;
  overflow-y: auto;
}

.health-json {
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 0.8rem;
  line-height: 1.4;
  color: #e6edf3;
  margin: 0;
  white-space: pre-wrap;
}

.health-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  color: rgba(255, 255, 255, 0.6);
  height: 200px;
}

.health-loading i {
  font-size: 2rem;
  color: var(--primary);
}

/* 响应式设计 */
@media (max-width: 900px) {
  .message {
    max-width: 90%;
  }
  
  .rag-tabs {
    flex-wrap: wrap;
  }
  
  .query-controls {
    flex-direction: column;
    align-items: stretch;
  }
  
  .status-grid {
    grid-template-columns: 1fr;
  }
  
  .health-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 600px) {
  header {
    flex-direction: column;
    gap: 1rem;
  }
  
  .logo-text {
    font-size: 1.5rem;
  }
  
  .docs-header,
  .graph-header,
  .health-header {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }
  
  .docs-actions,
  .graph-actions,
  .health-actions {
    justify-content: center;
  }
}
</style> 