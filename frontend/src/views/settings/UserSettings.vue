<template>
  <div class="user-settings-container">
    <h2 class="page-title">用户管理</h2>
    <p class="page-description">
      管理系统用户账号、权限和角色。
    </p>

    <div class="actions-bar">
      <el-button type="primary" @click="openAddUserDialog">
        <el-icon><plus /></el-icon> 添加用户
      </el-button>
      <el-input
        v-model="searchQuery"
        placeholder="搜索用户名或姓名"
        style="width: 300px; margin-left: auto;"
        clearable
      >
        <template #prefix>
          <el-icon><search /></el-icon>
        </template>
      </el-input>
    </div>

    <el-card class="users-table-card">
      <el-table
        v-loading="loading"
        :data="filteredUsers"
        style="width: 100%"
        border
      >
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="name" label="姓名" width="150" />
        <el-table-column prop="email" label="电子邮箱" width="200" />
        <el-table-column prop="role" label="角色" width="120">
          <template #default="scope">
            <el-tag :type="getRoleType(scope.row.role)">
              {{ getRoleText(scope.row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.status === 'active' ? 'success' : 'danger'">
              {{ scope.row.status === 'active' ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="lastLogin" label="最后登录时间" width="180">
          <template #default="scope">
            {{ formatDate(scope.row.lastLogin) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="scope">
            <el-button type="primary" link size="small" @click="editUser(scope.row)">
              编辑
            </el-button>
            <el-button type="primary" link size="small" @click="resetPassword(scope.row)">
              重置密码
            </el-button>
            <el-button
              type="primary"
              link
              size="small"
              @click="toggleUserStatus(scope.row)"
            >
              {{ scope.row.status === 'active' ? '禁用' : '启用' }}
            </el-button>
            <el-button
              type="danger"
              link
              size="small"
              @click="deleteUser(scope.row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="totalRecords"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 添加/编辑用户对话框 -->
    <el-dialog
      v-model="userDialogVisible"
      :title="isEditMode ? '编辑用户' : '添加用户'"
      width="500px"
    >
      <el-form
        ref="userFormRef"
        :model="userForm"
        :rules="userFormRules"
        label-width="100px"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="userForm.username" :disabled="isEditMode" />
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model="userForm.name" />
        </el-form-item>
        <el-form-item label="电子邮箱" prop="email">
          <el-input v-model="userForm.email" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="userForm.role" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="操作员" value="operator" />
            <el-option label="访客" value="guest" />
          </el-select>
        </el-form-item>
        <el-form-item label="密码" prop="password" v-if="!isEditMode">
          <el-input v-model="userForm.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword" v-if="!isEditMode">
          <el-input v-model="userForm.confirmPassword" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="userDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitUserForm">确定</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 重置密码对话框 -->
    <el-dialog
      v-model="resetPasswordDialogVisible"
      title="重置密码"
      width="500px"
    >
      <el-form
        ref="resetPasswordFormRef"
        :model="resetPasswordForm"
        :rules="resetPasswordRules"
        label-width="100px"
      >
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="resetPasswordForm.newPassword" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="resetPasswordForm.confirmPassword" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="resetPasswordDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitResetPassword">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus, Search } from '@element-plus/icons-vue';
import axios from 'axios'; // 引入axios

// 用户列表数据
const users = ref([]);
const loading = ref(false);
const searchQuery = ref('');
const currentPage = ref(1);
const pageSize = ref(10);
const totalRecords = ref(0); // 新增：后端返回的总记录数

// 对话框控制
const userDialogVisible = ref(false);
const resetPasswordDialogVisible = ref(false);
const isEditMode = ref(false);
const userFormRef = ref(null);
const resetPasswordFormRef = ref(null);

// 当前选中的用户ID（用于编辑和重置密码）
const currentUserId = ref(null);

// 用户表单
const userForm = reactive({
  username: '',
  name: '',
  email: '',
  role: 'operator',
  password: '',
  confirmPassword: ''
});

// 重置密码表单
const resetPasswordForm = reactive({
  newPassword: '',
  confirmPassword: ''
});

// 表单验证规则
const userFormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度应为3-20个字符', trigger: 'blur' }
  ],
  name: [
    { required: true, message: '请输入姓名', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入电子邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的电子邮箱地址', trigger: 'blur' }
  ],
  role: [
    { required: true, message: '请选择角色', trigger: 'change' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能小于6个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== userForm.password) {
          callback(new Error('两次输入的密码不一致'));
        } else {
          callback();
        }
      },
      trigger: 'blur'
    }
  ]
};

// 重置密码验证规则
const resetPasswordRules = {
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能小于6个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== resetPasswordForm.newPassword) {
          callback(new Error('两次输入的密码不一致'));
        } else {
          callback();
        }
      },
      trigger: 'blur'
    }
  ]
};

// 根据搜索条件过滤用户
const filteredUsers = computed(() => {
  const currentUsers = users.value; // 当前页的用户数据
  if (!searchQuery.value) {
    return currentUsers; 
  }
  const query = searchQuery.value.toLowerCase();
  return currentUsers.filter(
    user => user.username.toLowerCase().includes(query) || 
            user.name.toLowerCase().includes(query)
  );
});

// 分页总数应是过滤后的总数，而不是当前页的长度
// totalUsers computed属性不再需要，直接绑定totalRecords
// const totalUsers = computed(() => {
//   if (!searchQuery.value) {
//     return users.value.length;
//   }
//   const query = searchQuery.value.toLowerCase();
//   return users.value.filter(
//     user => user.username.toLowerCase().includes(query) || 
//             user.name.toLowerCase().includes(query)
//   ).length;
// });

// 获取角色文本
const getRoleText = (role) => {
  const roleMap = {
    admin: '管理员',
    operator: '操作员',
    guest: '访客'
  };
  return roleMap[role] || '未知';
};

// 获取角色标签类型
const getRoleType = (role) => {
  const typeMap = {
    admin: 'danger',
    operator: 'primary',
    guest: 'info'
  };
  return typeMap[role] || 'info';
};

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return '从未登录';
  return new Date(dateString).toLocaleString('zh-CN');
};

// 打开添加用户对话框
const openAddUserDialog = () => {
  isEditMode.value = false;
  resetUserForm();
  userDialogVisible.value = true;
};

// 编辑用户
const editUser = (user) => {
  isEditMode.value = true;
  currentUserId.value = user.id;
  
  // 填充表单
  userForm.username = user.username;
  userForm.name = user.name;
  userForm.email = user.email;
  userForm.role = user.role;
  
  userDialogVisible.value = true;
};

// 重置密码
const resetPassword = (user) => {
  currentUserId.value = user.id;
  resetPasswordForm.newPassword = '';
  resetPasswordForm.confirmPassword = '';
  resetPasswordDialogVisible.value = true;
};

// 提交用户表单
const submitUserForm = () => {
  userFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true; // 开始加载状态
      try {
        if (isEditMode.value) {
          // 编辑现有用户
          const payload = {
            name: userForm.name,
            email: userForm.email,
            role: userForm.role
          };
          const token = localStorage.getItem('access_token');
          await axios.put(`http://localhost:8000/users/${currentUserId.value}`, payload, {
            headers: {
              Authorization: `Bearer ${token}`
            }
          });
          ElMessage.success(`用户 "${userForm.username}" 已更新`);
        } else {
          // 添加新用户
          const payload = {
            username: userForm.username,
            password: userForm.password,
            name: userForm.name,
            email: userForm.email,
            role: userForm.role
          };
          await axios.post('http://localhost:8000/users/', payload);
          ElMessage.success(`用户 "${userForm.username}" 已创建`);
        }
        userDialogVisible.value = false;
        fetchUsers(); // 刷新用户列表
      } catch (error) {
        console.error('提交用户表单失败:', error);
        const errorMessage = error.response?.data?.detail || '操作失败';
        ElMessage.error(`操作失败: ${errorMessage}`);
      } finally {
        loading.value = false; // 结束加载状态
      }
    } else {
      return false;
    }
  });
};

// 提交重置密码
const submitResetPassword = () => {
  resetPasswordFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true; // 开始加载状态
      try {
        const payload = {
          password: resetPasswordForm.newPassword // 只发送密码进行更新
        };
        const token = localStorage.getItem('access_token');
        await axios.put(`http://localhost:8000/users/${currentUserId.value}`, payload, {
          headers: {
            Authorization: `Bearer ${token}`
          }
        });
        ElMessage.success('密码已重置');
        resetPasswordDialogVisible.value = false;
      } catch (error) {
        console.error('重置密码失败:', error);
        const errorMessage = error.response?.data?.detail || '重置密码失败';
        ElMessage.error(`重置密码失败: ${errorMessage}`);
      } finally {
        loading.value = false; // 结束加载状态
      }
    } else {
      return false;
    }
  });
};

// 重置用户表单
const resetUserForm = () => {
  userForm.username = '';
  userForm.name = '';
  userForm.email = '';
  userForm.role = 'operator';
  userForm.password = '';
  userForm.confirmPassword = '';
};

// 分页处理
const handleSizeChange = (size) => {
  pageSize.value = size;
  fetchUsers(); // 重新获取数据
};

const handleCurrentChange = (page) => {
  currentPage.value = page;
  fetchUsers(); // 重新获取数据
};

// 保存用户数据到本地存储 (此函数已不再使用，但保留以供参考或兼容性)
const saveUsersToLocalStorage = () => {
  localStorage.setItem('users', JSON.stringify(users.value));
};

// 从本地存储加载用户数据 (此函数已不再使用)
// const loadUsersFromLocalStorage = () => {
//   const savedUsers = localStorage.getItem('users');
//   if (savedUsers) {
//     users.value = JSON.parse(savedUsers);
//   } else {
//     generateMockUsers();
//   }
// };

// 生成模拟用户数据 (此函数已不再使用)
// const generateMockUsers = () => {
//   const mockUsers = [
//     {
//       id: 1,
//       username: 'admin',
//       name: '系统管理员',
//       email: 'admin@example.com',
//       role: 'admin',
//       status: 'active',
//       lastLogin: new Date().toISOString()
//     },
//     {
//       id: 2,
//       username: 'operator1',
//       name: '张工程师',
//       email: 'zhang@example.com',
//       role: 'operator',
//       status: 'active',
//       lastLogin: new Date(Date.now() - 86400000).toISOString()
//     },
//     {
//       id: 3,
//       username: 'operator2',
//       name: '李工程师',
//       email: 'li@example.com',
//       role: 'operator',
//       status: 'active',
//       lastLogin: new Date(Date.now() - 172800000).toISOString()
//     },
//     {
//       id: 4,
//       username: 'guest1',
//       name: '王访客',
//       email: 'wang@example.com',
//       role: 'guest',
//       status: 'disabled',
//       lastLogin: null
//     }
//   ];
  
//   users.value = mockUsers;
//   saveUsersToLocalStorage();
// };

// 切换用户状态（启用/禁用）
const toggleUserStatus = (user) => {
  const newStatus = user.status === 'active' ? 'disabled' : 'active';
  const actionText = newStatus === 'active' ? '启用' : '禁用';
  
  ElMessageBox.confirm(
    `确定要${actionText}用户 "${user.username}" 吗？`,
    `${actionText}用户`,
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  )
    .then(async () => {
      loading.value = true; // 开始加载状态
      try {
        const payload = {
          status: newStatus
        };
        const token = localStorage.getItem('access_token');
        await axios.put(`http://localhost:8000/users/${user.id}`, payload, {
          headers: {
            Authorization: `Bearer ${token}`
          }
        });
        ElMessage.success(`用户 "${user.username}" 已${actionText}`);
        fetchUsers(); // 刷新用户列表
      } catch (error) {
        console.error('切换用户状态失败:', error);
        const errorMessage = error.response?.data?.detail || '操作失败';
        ElMessage.error(`操作失败: ${errorMessage}`);
      } finally {
        loading.value = false; // 结束加载状态
      }
    })
    .catch(() => {
      // 用户取消操作
    });
};

// 删除用户
const deleteUser = (user) => {
  ElMessageBox.confirm(
    `确定要删除用户 "${user.username}" 吗？此操作不可恢复。`,
    '删除用户',
    {
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    }
  )
    .then(async () => {
      loading.value = true; // 开始加载状态
      try {
        const token = localStorage.getItem('access_token');
        await axios.delete(`http://localhost:8000/users/${user.id}`, {
          headers: {
            Authorization: `Bearer ${token}`
          }
        });
        ElMessage.success(`用户 "${user.username}" 已删除`);
        fetchUsers(); // 刷新用户列表
      } catch (error) {
        console.error('删除用户失败:', error);
        const errorMessage = error.response?.data?.detail || '删除失败';
        ElMessage.error(`删除失败: ${errorMessage}`);
      } finally {
        loading.value = false; // 结束加载状态
      }
    })
    .catch(() => {
      // 用户取消操作
    });
};

// 从后端API获取用户数据
const fetchUsers = async () => {
  loading.value = true;
  try {
    const token = localStorage.getItem('access_token');
    const response = await axios.get('http://localhost:8000/users/', {
      headers: {
        Authorization: `Bearer ${token}`
      },
      params: {
        skip: (currentPage.value - 1) * pageSize.value,
        limit: pageSize.value
      }
    });
    users.value = response.data.items.map(user => ({
      ...user,
      lastLogin: user.last_login // 保持与后端字段名一致，前端使用 formatDate 处理显示
    }));
    totalRecords.value = response.data.total; // 更新总记录数
  } catch (error) {
    console.error('获取用户列表失败:', error);
    ElMessage.error('获取用户列表失败');
  } finally {
    loading.value = false;
  }
};

// mounted 钩子中调用 fetchUsers
onMounted(() => {
  fetchUsers();
});
</script>

<style scoped>
.user-settings-container {
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

.actions-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.users-table-card {
  border-radius: 8px;
  margin-bottom: 20px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style> 