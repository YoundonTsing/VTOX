<template>
  <div class="login-container">
    <div class="brand-logo">
      <el-icon class="logo-icon"><Monitor /></el-icon>
      <span>MCSA-AI</span>
    </div>
    
    <div class="main-title">MCSA-AI电机诊断系统{{ currentMode === 'login' ? '登录' : '注册' }}</div>
    <el-card class="login-card">
      <template #header>
        <div class="card-header">
          <span>MCSA-AI电机诊断系统</span>
        </div>
      </template>

      <!-- 登录表单 -->
      <el-form
        v-if="currentMode === 'login'"
        :model="loginForm"
        :rules="loginRules"
        ref="loginFormRef"
        label-position="top"
        class="auth-form"
        @keyup.enter="handleLogin"
      >
        <el-form-item label="用户名" prop="username" class="form-item-center">
          <el-input v-model="loginForm.username" placeholder="请输入用户名"></el-input>
        </el-form-item>
        <el-form-item label="密码" prop="password" class="form-item-center">
          <el-input
            type="password"
            v-model="loginForm.password"
            placeholder="请输入密码"
            show-password
          ></el-input>
        </el-form-item>
        <el-form-item class="form-item-center">
          <el-button type="primary" @click="handleLogin" :loading="loading">登录</el-button>
        </el-form-item>
        <div class="switch-mode">
          <span>没有账号？</span>
          <span class="switch-link" @click="currentMode = 'register'">去注册</span>
        </div>
      </el-form>

      <!-- 注册表单 -->
      <el-form
        v-else
        :model="registerForm"
        :rules="registerRules"
        ref="registerFormRef"
        label-position="top"
        class="auth-form"
        @keyup.enter="handleRegister"
      >
        <el-form-item label="用户名" prop="username" class="form-item-center">
          <el-input v-model="registerForm.username" placeholder="请输入用户名"></el-input>
        </el-form-item>
        <el-form-item label="密码" prop="password" class="form-item-center">
          <el-input
            type="password"
            v-model="registerForm.password"
            placeholder="请输入密码"
            show-password
          ></el-input>
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword" class="form-item-center">
          <el-input
            type="password"
            v-model="registerForm.confirmPassword"
            placeholder="请再次输入密码"
            show-password
          ></el-input>
        </el-form-item>
        <el-form-item label="姓名" prop="name" class="form-item-center">
          <el-input v-model="registerForm.name" placeholder="请输入姓名"></el-input>
        </el-form-item>
        <el-form-item label="电子邮箱" prop="email" class="form-item-center">
          <el-input v-model="registerForm.email" placeholder="请输入电子邮箱"></el-input>
        </el-form-item>
        <el-form-item label="角色" prop="role" class="form-item-center">
          <el-select v-model="registerForm.role" placeholder="请选择角色">
            <el-option label="操作员" value="operator"></el-option>
            <el-option label="访客" value="guest"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item class="form-item-center">
          <el-button type="primary" @click="handleRegister" :loading="loading">注册</el-button>
        </el-form-item>
        <div class="switch-mode">
          <span>已有账号？</span>
          <span class="switch-link" @click="currentMode = 'login'">去登录</span>
        </div>
      </el-form>

      <div class="security-info">
        <div class="security-item">
          <el-icon><Lock /></el-icon>
          <span>安全认证</span>
        </div>
        <div class="security-item">
          <el-icon><Warning /></el-icon>
          <span>数据加密</span>
        </div>
        <div class="security-item">
          <el-icon><Connection /></el-icon>
          <span>安全连接</span>
        </div>
      </div>
    </el-card>
    
    <div class="footer-info">
      <p>© {{ currentYear }} MCSA-AI电机诊断系统（Youndon Tsing） 版权所有</p>
      <p>
        <span class="footer-item">粤ICP备2025072501号</span>
        <span class="footer-item">粤公网安备2025072501号</span>
      </p>
      <p>
        <span class="footer-item">技术支持: 电动技术开发中心</span>
        <span class="footer-item">服务热线: 400-888-8888</span>
      </p>
      <p class="certification-info">
        <span class="cert-item">ISO9001认证</span>
        <span class="cert-item">国家高新技术企业</span>
        <span class="cert-item">AAA级信用企业</span>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { 
  Lock, 
  Warning, 
  Connection, 
  Monitor 
} from '@element-plus/icons-vue'
import axios from 'axios'

const router = useRouter()
const loginFormRef = ref(null)
const registerFormRef = ref(null) // 新增注册表单引用
const loading = ref(false)
const currentYear = computed(() => new Date().getFullYear())
const currentMode = ref('login') // 'login' 或 'register'

const loginForm = reactive({
  username: '',
  password: ''
})

const registerForm = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  name: '',
  email: '',
  role: 'operator' // 默认角色
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('请再次输入密码'))
  } else if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致!'))
  } else {
    callback()
  }
}

const loginRules = reactive({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度在3到50个字符之间', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 50, message: '密码长度至少为6个字符', trigger: 'blur' }
  ]
})

const registerRules = reactive({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度在3到50个字符之间', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 50, message: '密码长度至少为6个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ],
  name: [
    { required: true, message: '请输入姓名', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入电子邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的电子邮箱格式', trigger: 'blur' }
  ],
  role: [
    { required: true, message: '请选择角色', trigger: 'change' }
  ]
})

const handleLogin = () => {
  loginFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        console.log('发送登录请求:', {
          username: loginForm.username,
          password: '******' // 隐藏密码
        })
        
        // 尝试简化请求
        const response = await axios.post('http://localhost:8000/auth/token', 
          { 
            username: loginForm.username,
            password: loginForm.password
          },
          { 
            headers: { 'Content-Type': 'application/json' }
            // 移除 withCredentials 选项
          }
        )

        console.log('登录响应:', response.data)
        const { access_token, token_type } = response.data
        localStorage.setItem('access_token', access_token)
        localStorage.setItem('token_type', token_type)
        localStorage.setItem('username', loginForm.username) // 保存用户名
        
        ElMessage.success('登录成功！')
        
        // 使用replace而不是push，防止用户通过返回按钮回到登录页
        // 添加更多参数确保页面完全刷新
        router.replace({
          path: '/dashboard',
          query: { 
            t: Date.now(),
            refresh: 'true',
            auth: 'true'
          }
        })
        
        // 强制刷新整个页面，确保所有组件重新加载
        setTimeout(() => {
          window.location.href = '/dashboard?forceReload=' + Date.now()
        }, 100)
      } catch (error) {
        console.error('登录失败:', error)
        let errorMessage = '登录失败'
        
        if (error.response) {
          // 服务器返回了错误响应
          console.error('错误响应:', error.response)
          errorMessage += `: ${error.response.status} - ${error.response.data?.detail || '未知错误'}`
        } else if (error.request) {
          // 请求已发送但没有收到响应
          console.error('无响应:', error.request)
          errorMessage += ': 服务器无响应，请检查网络连接和后端服务'
        } else {
          // 设置请求时发生错误
          console.error('请求错误:', error.message)
          errorMessage += `: ${error.message}`
        }
        
        ElMessage.error(errorMessage)
      } finally {
        loading.value = false
      }
    }
  })
}

const handleRegister = () => {
  registerFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        console.log('发送注册请求:', registerForm)
        const response = await axios.post('http://localhost:8000/users/', registerForm)
        console.log('注册响应:', response.data)
        ElMessage.success('注册成功！请登录')
        currentMode.value = 'login' // 注册成功后切换回登录模式
        // 清空注册表单
        Object.assign(registerForm, { 
          username: '', 
          password: '', 
          confirmPassword: '', 
          name: '', 
          email: '', 
          role: 'operator' 
        })
      } catch (error) {
        console.error('注册失败:', error)
        let errorMessage = '注册失败'
        if (error.response) {
          errorMessage += `: ${error.response.status} - ${error.response.data?.detail || '未知错误'}`
        } else if (error.request) {
          errorMessage += ': 服务器无响应，请检查网络连接和后端服务'
        } else {
          errorMessage += `: ${error.message}`
        }
        ElMessage.error(errorMessage)
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  position: relative;
  overflow: hidden;
  /* 动态渐变背景 */
  background: linear-gradient(-45deg, #1e3a8a, #0f172a, #2563eb, #1e40af);
  background-size: 400% 400%;
  animation: gradient 15s ease infinite;
}

@keyframes gradient {
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
}

.main-title {
  position: absolute;
  top: 15%;
  left: 50%;
  transform: translateX(-50%);
  font-size: 48px; /* 增大字体 */
  font-weight: bold;
  color: white;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.6);
  z-index: 2;
  text-align: center;
  width: 100%;
  letter-spacing: 2px; /* 增加字间距 */
}

.login-card {
  width: 400px;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(10px);
  background-color: rgba(255, 255, 255, 0.25); /* 更透明的背景 */
  border: 1px solid rgba(255, 255, 255, 0.18);
  z-index: 1;
  margin-top: 40px; /* 为大标题腾出空间 */
}

.card-header {
  text-align: center;
  font-size: 24px;
  font-weight: bold;
  color: #ffffff; /* 将标题文字颜色改为白色 */
  margin-bottom: 10px; /* 从20px减少到10px */
}

.auth-form {
  margin-top: 10px; /* 从20px减少到10px */
}

/* 居中表单项 */
.form-item-center {
  text-align: center;
}

:deep(.el-form-item__label) {
  text-align: center;
  width: 100% !important;
  justify-content: center;
}

.el-button {
  width: 100%;
}

/* 修改登录按钮为红色背景 */
:deep(.el-button--primary) {
  background-color: #ff0000;
  border-color: #ff0000;
}

:deep(.el-button--primary:hover),
:deep(.el-button--primary:focus) {
  background-color: #d40000;
  border-color: #d40000;
}

/* 确保密码字段的星号与用户名输入框对齐 */
:deep(.el-input__inner) {
  text-align: center;
  box-sizing: border-box;
  height: 40px;
  line-height: 40px;
  padding: 0 15px;
}

:deep(.el-input__suffix) {
  right: 5px;
}

.footer-info {
  position: absolute;
  bottom: 20px;
  left: 0;
  width: 100%;
  text-align: center;
  color: rgba(255, 255, 255, 0.8);
  font-size: 12px;
  z-index: 2;
}

.footer-info p {
  margin: 5px 0;
}

.footer-item {
  margin: 0 10px;
  position: relative;
}

.footer-item:not(:last-child)::after {
  content: '|';
  position: absolute;
  right: -12px;
  color: rgba(255, 255, 255, 0.5);
}

.security-info {
  display: flex;
  justify-content: space-around;
  margin-top: 20px;
  padding-top: 15px;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
}

.security-item {
  display: flex;
  align-items: center;
  color: rgba(255, 255, 255, 0.9);
  font-size: 12px;
}

.security-item .el-icon {
  margin-right: 5px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.9);
}

.brand-logo {
  position: absolute;
  top: 20px;
  left: 30px;
  display: flex;
  align-items: center;
  color: white;
  font-size: 24px;
  font-weight: bold;
  z-index: 10;
}

.brand-logo .logo-icon {
  font-size: 28px;
  margin-right: 10px;
  color: #ff0000;
}

.certification-info {
  margin-top: 10px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
}

.cert-item {
  margin: 0 8px;
  position: relative;
}

.cert-item:not(:last-child)::after {
  content: '•';
  position: absolute;
  right: -10px;
  color: rgba(255, 255, 255, 0.4);
}

.switch-mode {
  text-align: center;
  margin-top: 15px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.8);
}

.switch-link {
  color: #409eff; /* Element Plus 默认链接蓝色 */
  cursor: pointer;
  margin-left: 5px; /* 与前一个span保持一定距离 */
  font-weight: bold;
}

.switch-link:hover {
  text-decoration: underline;
}

</style> 