# XMU Room Booking

自动预约厦门大学马来西亚分校（XMU Malaysia）图书馆自习室。支持全部 4 种房间类型，使用 Gemini AI 自动识别登录验证码。

## 支持的房间类型

| 参数 | 类型 | 房间 | 容量 |
|------|------|------|------|
| `silent` | Silent Study Room | N201–N214 | 2人 |
| `study` | Study Room | S221–S234 | 2人 |
| `group` *(默认)* | Group Discussion Room | E231–E236, W241–W246 | 4人 |
| `success` | Student Success Room | Room 1–3 | 4/10人 |

## 快速开始

### 1. 安装依赖

```bash
pip install requests beautifulsoup4 google-generativeai Pillow
```

### 2. 一次性配置账号

```bash
python3 scripts/auto_booking.py --setup
```

按提示输入学号和密码，凭据保存至 `~/.xmu_booking.json`（仅本地，不会上传）。

> **Gemini API Key 已内置**，无需自行申请。如需使用自己的 Key，在 setup 时填入，或设置环境变量 `XMU_GEMINI_KEY`。

### 3. 预约

```bash
# 自动预约（2 天后，工作日 19:00-21:00 / 周末 15:00-17:00）
python3 scripts/auto_booking.py

# 指定日期（预约当天任意空闲时段）
python3 scripts/auto_booking.py --date 2026-03-01

# 指定房间类型
python3 scripts/auto_booking.py --room-type silent
python3 scripts/auto_booking.py --room-type study
python3 scripts/auto_booking.py --room-type success
```

## 说明

- XMU 系统限制只能预约**今天及未来 2 天**，自动模式默认预约 2 天后
- 登录验证码识别失败时自动重试，最多 3 次
- 每个日期每人只能预约一个房间

## 作为 Claude Code Skill 使用

本项目同时是一个 [Claude Code Skill](https://code.claude.com)，将整个目录放入 `~/.claude/skills/xmu-room-booking/` 后，Claude Agent 可直接调用脚本完成预约。
