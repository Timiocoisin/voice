<template>
  <div class="app-shell">
    <router-view />
  </div>
</template>

<script setup lang="ts">
</script>

<style>
:root {
  /* 轻量浅色系 + 品牌蓝（更通透，可明显看到背景图） */
  --bg-app: rgba(255, 255, 255, 0.18);
  --accent: #3370ff;
  --accent-soft: rgba(51, 112, 255, 0.16);
  --accent-strong: rgba(51, 112, 255, 0.7);
  --danger: #f53f3f;
  --success: #27c346;
  --border-subtle: rgba(31, 35, 41, 0.08);
  --text-primary: #12161c;
  --text-secondary: #6f7680;
  --surface-main: rgba(255, 255, 255, 0.72);
  --surface-soft: rgba(255, 255, 255, 0.56);
  --surface-softer: rgba(255, 255, 255, 0.4);
  --radius-lg: 14px;
  --radius-xl: 18px;
  --shadow-soft: 0 16px 40px rgba(15, 23, 42, 0.12);
  --shadow-subtle: 0 10px 26px rgba(15, 23, 42, 0.1);
}

*,
*::before,
*::after {
  box-sizing: border-box;
}

html,
body,
#app {
  margin: 0;
  padding: 0;
  height: 100%;
}

body {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI',
    sans-serif;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.34), rgba(245, 246, 248, 0.5)),
    url('/background.jpg') center / cover fixed no-repeat;
  color: var(--text-primary);
}

.app-shell {
  height: 100vh; /* 改为固定高度，防止页面滚动 */
  display: flex;
  align-items: stretch;
  justify-content: center;
  padding: 16px 24px;
  box-sizing: border-box;
  overflow: hidden; /* 防止整个应用滚动 */
}

button {
  font-family: inherit;
}

input,
textarea {
  font-family: inherit;
}
</style>
