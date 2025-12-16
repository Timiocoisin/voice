# 资源文件说明

此目录存放应用程序所需的所有图标和背景图片资源。

## 需要的文件

请将以下文件放置在此目录中：

### 图标文件 (SVG格式)
- `close.svg` - 关闭图标 (icon_id: 1)
- `diamond.svg` - 钻石图标 (icon_id: 2)
- `email.svg` - 邮箱图标 (icon_id: 3)
- `minimize.svg` - 最小化图标 (icon_id: 7)
- `password.svg` - 密码图标 (icon_id: 8)
- `headset.svg` - 耳机图标 (icon_id: 9)
- `speaker.svg` - 喇叭图标/注册密码图标 (icon_id: 10)
- `username.svg` - 用户名图标 (icon_id: 11)
- `code.svg` - 验证码图标 (icon_id: 12)
- `vip.svg` - VIP图标 (icon_id: 13)

### 图片文件
- `default_avatar.png` - 默认头像 (icon_id: 4)
- `app_icon.png` - 应用图标 (icon_id: 5)
- `logo.png` - Logo (icon_id: 6)
- `background.jpg` - 背景图片 (icon_id: 14)

## 注意事项

- 所有 SVG 图标文件应该使用 SVG 格式
- 图片文件可以使用 PNG 或 JPG 格式
- 如果某个文件不存在，应用程序会记录警告日志，但不会崩溃
- 文件路径映射定义在 `backend/resources/resource_loader.py` 中的 `ICON_MAPPING` 字典

