# XMUM Room Booking

自动预约厦门大学马来西亚分校（XMUM）图书馆自习室。支持全部 4 种房间类型，使用 Gemini AI 自动识别登录验证码。

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

### 2. 申请 Gemini API Key（免费）

本工具使用 Gemini AI 识别登录验证码，需要自行申请 Key：

1. 打开 [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. 登录 Google 账号 → 点击 **Create API key** → 复制

> ⚠️ Key 只保存在你本地，**不要粘贴到任何代码文件或公开上传**，否则 Google 会自动检测并吊销。

### 3. 一次性配置账号

```bash
python3 scripts/auto_booking.py --setup
```

会依次提示输入：
- Campus ID（学号，如 `CYS2309205`）
- 密码
- Gemini API Key（粘贴上一步申请的 Key）

所有信息保存至 `~/.xmu_booking.json`（仅本地可读），之后无需再输入。

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

- XMUM 系统限制只能预约**今天及未来 2 天**，自动模式默认预约 2 天后
- 登录验证码识别失败时自动重试，最多 3 次
- 每个日期每人只能预约一个房间

## 作为 Claude Code Skill 使用

本项目同时是一个 [Claude Code Skill](https://code.claude.com)，将整个目录放入 `~/.claude/skills/xmu-room-booking/` 后，Claude Agent 可直接调用脚本完成预约。

---

## 免责声明

1. **仅限个人使用**：本工具仅供使用者预约**自己账号**下的自习室，禁止用于代抢、转让或任何形式的商业用途（如收费帮人抢房间）。
2. **遵守学校规定**：使用前请确认符合 XMUM 图书馆及 eServices 系统的使用条款。若校方明确禁止自动化访问，请停止使用。
3. **Gemini API Key**：请自行前往 [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey) 免费申请，在 `--setup` 时填入。Key 仅保存在本地，不会上传。
4. **风险自负**：本工具按现状提供，作者不对账号封禁、预约失败或任何使用后果承担责任。
