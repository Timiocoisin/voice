import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router';
import LoginPage from '@/views/LoginPage.vue';
import WorkspacePage from '@/views/WorkspacePage.vue';
import RegisterPage from '@/views/RegisterPage.vue';
import ForgotPasswordPage from '@/views/ForgotPasswordPage.vue';
import ResetPasswordPage from '@/views/ResetPasswordPage.vue';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/login',
    name: 'login',
    component: LoginPage,
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'register',
    component: RegisterPage,
    meta: { requiresAuth: false }
  },
  {
    path: '/forgot-password',
    name: 'forgot-password',
    component: ForgotPasswordPage,
    meta: { requiresAuth: false }
  },
  {
    path: '/reset-password',
    name: 'reset-password',
    component: ResetPasswordPage,
    meta: { requiresAuth: false }
  },
  {
    path: '/workspace',
    name: 'workspace',
    component: WorkspacePage,
    meta: { requiresAuth: true }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/login'
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

// 路由守卫：检查登录状态
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token');
  const user = localStorage.getItem('user');
  const isAuthenticated = !!(token && user);

  // 如果访问需要认证的页面
  if (to.meta.requiresAuth) {
    if (!isAuthenticated) {
      // 未登录，跳转到登录页
      next({ name: 'login', query: { redirect: to.fullPath } });
    } else {
      // 已登录，允许访问
      next();
    }
  } else {
    // 访问登录/注册页
    if (isAuthenticated && (to.name === 'login' || to.name === 'register')) {
      // 已登录，跳转到工作台
      next({ name: 'workspace' });
    } else {
      // 未登录，允许访问登录/注册页
      next();
    }
  }
});

export default router;


