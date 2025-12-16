# 资源文件说明

此目录存放应用程序所需的所有图标和背景图片资源。

## 目录结构

```
resources/
├── icons/          # SVG 图标文件
│   ├── close.svg
│   ├── diamond.svg
│   ├── email.svg
│   ├── minimize.svg
│   ├── password.svg
│   ├── headset.svg
│   ├── speaker.svg
│   ├── username.svg
│   ├── code.svg
│   └── vip.svg
└── images/         # 图片文件（PNG/JPG）
    ├── default_avatar.png
    ├── app_icon.png
    ├── logo.png
    └── background.jpg
```

## 需要的文件

### icons/ 目录下的图标文件 (SVG格式)
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

### images/ 目录下的图片文件
- `default_avatar.png` - 默认头像 (icon_id: 4)
- `app_icon.png` - 应用图标 (icon_id: 5)
- `logo.png` - Logo (icon_id: 6)
- `background.jpg` - 背景图片 (icon_id: 14)

## 注意事项

- 所有 SVG 图标文件应放置在 `icons/` 目录下
- 所有图片文件（PNG/JPG）应放置在 `images/` 目录下
- 如果某个文件不存在，应用程序会记录警告日志，但不会崩溃
- 文件路径映射定义在 `backend/resources/resource_loader.py` 中的 `ICON_MAPPING` 字典
- 请确保文件名与映射表中定义的文件名完全一致

