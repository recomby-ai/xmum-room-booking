---
name: xmum-room-booking
description: Books XMUM (Xiamen University Malaysia) library study rooms automatically. Controls the booking script to login, solve captchas with Gemini AI, query available rooms, and complete reservations. Use when the user asks to book, reserve, or check study rooms at XMUM library, or when running scheduled automatic daily booking.
---

# XMUM Room Booking Skill

这个 Skill 让 AI Agent 掌握完整的预约流程，通过操控 `scripts/auto_booking.py` 自主完成：登录 → 验证码识别 → 查询空位 → 选择时间段 → 提交预约。

---

## 首次使用前（人工操作一次）

```bash
# 安装依赖
pip install requests beautifulsoup4 google-generativeai Pillow

# 配置账号（保存到 ~/.xmu_booking.json）
python3 scripts/auto_booking.py --setup
```

setup 会依次询问：学号、密码、Gemini API Key（免费申请：https://aistudio.google.com/apikey）

---

## AI 如何操控脚本

### 日常自动预约（最常用）

```bash
# 预约 2 天后，工作日优先 19:00-21:00，周末优先 15:00-17:00
# 若首选时段无位，自动尝试下一个
python3 scripts/auto_booking.py
```

### 指定时间偏好（多个按顺序尝试，找到即预约）

```bash
python3 scripts/auto_booking.py --time "19:00-21:00,17:00-19:00,15:00-17:00"
```

### 指定日期

```bash
python3 scripts/auto_booking.py --date 2026-03-01
```

### 指定房间类型

```bash
python3 scripts/auto_booking.py --room-type silent   # 安静自习室
python3 scripts/auto_booking.py --room-type study    # 学习室
python3 scripts/auto_booking.py --room-type group    # 小组讨论室（默认）
python3 scripts/auto_booking.py --room-type success  # Student Success Room
```

---

## 可预约房间与时间

| `--room-type` | 房间 | 容量 |
|---|---|---|
| `silent` | N201–N214 | 2人 |
| `study` | S221–S234 | 2人 |
| `group` *(默认)* | E231–E236, W241–W246 | 4人 |
| `success` | Room 1–3 | 4/10人 |

| 时段 | 工作日 | 周末 |
|------|--------|------|
| 09:00–11:00 | ✅ | ✅ |
| 11:00–13:00 | ✅ | ✅ |
| 13:00–15:00 | ✅ | ✅ |
| 15:00–17:00 | ✅ | ✅ |
| 17:00–19:00 | ✅ | ❌ |
| 19:00–21:00 | ✅ | ❌ |

---

## 常见错误处理

| 错误 | 原因 | 处理 |
|------|------|------|
| `Missing credentials` | 未配置账号 | 运行 `--setup` |
| `Students can only book for today and next 2 days` | 日期超限 | 改用自动模式 |
| `You have already made a booking for the selected date` | 已预约 | 无需重复操作 |
| `Captcha recognition error: 403` | Gemini Key 失效 | 重新申请 Key，运行 `--setup` 更新 |
| `Incorrect username or password` | 账号密码错误 | 运行 `--setup` 重新配置 |
