---
name: xmu-room-booking
description: Books XMUM library study rooms automatically via the eServices portal. Uses Gemini AI to solve login captchas. Supports Group Discussion Rooms (E/W block). Use when the user wants to book, reserve, or check availability of a study room or library space at XMUM (Xiamen University Malaysia).
---

# XMUM Room Booking

自动登录 XMUM eServices，用 Gemini AI 破解验证码，查询并预约自习室。

---

## 使用前需要准备

**第一步：安装依赖（只需一次）**

```bash
pip install requests beautifulsoup4 google-generativeai Pillow
```

**第二步：运行配置向导（只需一次）**

```bash
python3 scripts/auto_booking.py --setup
```

按提示输入学号和密码，凭据会加密保存到 `~/.xmu_booking.json`，之后无需再输入。

> **Gemini API Key 需自行申请（免费）**：前往 [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey) 生成后在 `--setup` 时填入，或设置环境变量 `XMUM_GEMINI_KEY`。

---

## 这个 Skill 能做什么

| 功能 | 说明 |
|------|------|
| 自动预约自习室 | 登录 → 识别验证码 → 查询空位 → 一键预约 |
| 自动模式 | 预约 **2 天后** 的自习室（XMUM 系统最多只允许提前 2 天） |
| 指定日期模式 | 预约任意指定日期的任意空闲时段 |
| 多自习室类型 | 目前支持 Group Discussion Room，可扩展其他类型 |
| 失败自动重试 | 验证码识别失败时最多重试 3 次 |

**可预约的房间：**

| `--room-type` | 类型 | 房间 | 容量 |
|---|---|---|---|
| `silent` | Silent Study Room | N201–N214 | 2人 |
| `study` | Study Room | S221–S234 | 2人 |
| `group` *(默认)* | Group Discussion Room | E231–E236, W241–W246 | 4人 |
| `success` | Student Success Room | Room 1–3 | 4/10人 |

**默认预约时间：**
- 工作日：19:00 – 21:00
- 周末：15:00 – 17:00

---

## 使用方法

```bash
# 自动预约（2 天后，按默认时间）
python3 scripts/auto_booking.py

# 指定日期预约（预约当天任意空闲时段）
python3 scripts/auto_booking.py --date 2026-03-01

# 指定房间类型（silent / study / group / success）
python3 scripts/auto_booking.py --room-type silent
```

---

## 常见错误

| 错误信息 | 原因 | 解决 |
|----------|------|------|
| `Missing environment variables` | 环境变量未配置 | 按上方步骤配置并 `source` |
| `Students can only book for today and next 2 days` | 日期超出范围 | 改用自动模式或选更近的日期 |
| `You have already made a booking for the selected date` | 当天已有预约 | 无需重复预约 |
| `Captcha recognition error` | Gemini Key 无效 | 检查 `XMUM_GEMINI_KEY` |
| `Incorrect username or password` | 账号密码错误 | 检查 `XMUM_USERNAME` / `XMUM_PASSWORD` |
