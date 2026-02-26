# XMUM Room Booking

自动预约厦门大学马来西亚分校（XMUM）图书馆自习室。支持全部 4 种房间类型，使用 Gemini AI 自动识别登录验证码。

**本项目是一个 Agent Skill**，兼容 [Claude Code](https://claude.ai/code) 与 [openclaw](https://github.com/anthropics/claude-code)。安装后 AI Agent 会掌握如何登录系统、查询空位、选择时间段并完成预约——整个流程由 AI 自主决策和操控脚本执行，无需人工介入。

> 🔥 **推荐搭配 openclaw 定时功能使用**：openclaw 支持定时自动执行 Skill，设置一次后每天固定时间由 AI 自动运行预约，完全解放双手。

---

## 支持的房间类型

| `--room-type` | 类型 | 房间 | 容量 |
|---|---|---|---|
| `silent` | Silent Study Room | N201–N214 | 2人 |
| `study` | Study Room | S221–S234 | 2人 |
| `group` *(默认)* | Group Discussion Room | E231–E236, W241–W246 | 4人 |
| `success` | Student Success Room | Room 1–3 | 4/10人 |

## 可预约时间段

| 时段 | 工作日 | 周末 |
|------|--------|------|
| 09:00 – 11:00 | ✅ | ✅ |
| 11:00 – 13:00 | ✅ | ✅ |
| 13:00 – 15:00 | ✅ | ✅ |
| 15:00 – 17:00 | ✅ | ✅ |
| 17:00 – 19:00 | ✅ | ❌ |
| 19:00 – 21:00 | ✅ | ❌ |

---

## 安装

### 方式一：一键安装（推荐）

```bash
curl -sSL https://raw.githubusercontent.com/recomby-ai/xmum-room-booking/main/install.sh | bash
```

自动完成：安装依赖 → 复制 Skill 到 openclaw → 引导配置账号

### 方式二：手动安装

```bash
git clone https://github.com/recomby-ai/xmum-room-booking.git
cd xmum-room-booking
pip install requests beautifulsoup4 google-generativeai Pillow
python3 skill/scripts/auto_booking.py --setup
```

---

## 配置（首次运行 `--setup`）

```
Campus ID:       你的学号
Password:        eServices 密码
Gemini API Key:  验证码识别用（免费申请）
```

**申请 Gemini API Key（免费）**：
1. 打开 [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. 登录 Google 账号 → **Create API key** → 复制

> ⚠️ Key 仅保存在本地 `~/.xmu_booking.json`，**不要上传到任何公开平台**，否则会被 Google 自动吊销。

---

## 使用方法

```bash
# 自动预约（2 天后，按优先级尝试多个时间段）
python3 skill/scripts/auto_booking.py

# 指定时间偏好（多个时段按顺序尝试，第一个有位置就预约）
python3 skill/scripts/auto_booking.py --time "19:00-21:00,17:00-19:00,15:00-17:00"

# 指定日期（任意空闲时段）
python3 skill/scripts/auto_booking.py --date 2026-03-01

# 指定房间类型
python3 skill/scripts/auto_booking.py --room-type silent

# 组合使用
python3 skill/scripts/auto_booking.py --room-type study --time "09:00-11:00,11:00-13:00"
```

**默认时间偏好：**
- 工作日：`19:00-21:00` → `17:00-19:00` → `15:00-17:00`（依次尝试）
- 周末：`15:00-17:00` → `13:00-15:00` → `11:00-13:00`（依次尝试）

---

## 说明

- XMUM 系统限制只能预约**今天及未来 2 天**，自动模式默认预约 2 天后
- 多时间段优先级：第一个时段没位置自动尝试下一个，找到即预约
- 登录验证码识别失败时自动重试，最多 3 次
- 每个日期每人只能预约一个房间

---

## 免责声明

1. **仅限个人使用**：本工具仅供使用者预约**自己账号**下的自习室，禁止用于代抢、转让或任何形式的商业用途（如收费帮人抢房间）。
2. **遵守学校规定**：使用前请确认符合 XMUM 图书馆及 eServices 系统的使用条款。若校方明确禁止自动化访问，请停止使用。
3. **Gemini API Key**：请自行前往 [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey) 免费申请，在 `--setup` 时填入。Key 仅保存在本地，不会上传。
4. **风险自负**：本工具按现状提供，作者不对账号封禁、预约失败或任何使用后果承担责任。
