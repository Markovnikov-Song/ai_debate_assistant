# 🎯 多 AI 辩论决策助手

一个基于多智能体的辩论辅助决策工具，让 AI 从不同立场帮你分析问题、做出决策。

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red)
![License](https://img.shields.io/badge/License-MIT-green)

## 🌐 在线体验

直接访问，无需安装：

**[https://debate-assistant.streamlit.app/](https://debate-assistant.streamlit.app/)**

支持电脑和手机浏览器，注册账号后即可使用。

## ✨ 功能特性

- 用户注册/登录：账号密码认证，bcrypt 加密，Cookie 持久化登录，刷新不退出
- 多智能体辩论：支持派、反对派、中立理性派、长期视角派同台辩论
- 自由辩环节：打断/追问/抬杠，次数可自定义（1-6次）
- 自定义角色：可自由添加、编辑、删除辩论角色及人设
- 自动保存：每轮结束自动保存，不怕丢失
- 历史记录：每个用户独立存储，支持加载和删除
- 导出 Word：一键下载完整辩论记录含总结，兼容公网部署
- 意见反馈：用户可提交反馈，管理员后台直接查看
- 管理员面板：用户管理、使用数据统计、意见反馈查看

## 🚀 快速开始

### 前提条件

- 已安装 [Anaconda](https://www.anaconda.com/download) 或 Miniconda
- 已准备好大模型 API Key（支持 OpenAI / 豆包 / SiliconFlow / DeepSeek 等）

### 第一步：克隆项目

```bash
git clone https://github.com/your-username/ai-debate-assistant.git
cd ai-debate-assistant
```

或者直接下载 ZIP 解压到本地文件夹。

### 第二步：一键配置环境

双击运行 `setup.bat`，自动完成：

1. 检测 Anaconda 是否安装
2. 创建名为 `debate-env` 的 conda 环境（Python 3.10）
3. 安装所有依赖（使用清华镜像源）
4. 生成 `.env` 配置文件

> 如果 `setup.bat` 提示找不到 conda，请用 Anaconda Prompt 打开后手动运行。

### 第三步：填入配置

用记事本打开 `.env` 文件：

```env
API_KEY=你的API Key
BASE_URL=https://api.siliconflow.cn/v1
MODEL=deepseek-ai/DeepSeek-V3
ADMIN_USER=admin
```

### 第四步：初始化管理员账号

```bash
conda activate debate-env
python init_admin.py
```

默认创建 `admin` / `123456`，可在 `init_admin.py` 里修改。

### 第五步：启动应用

双击 `start.bat`，浏览器自动打开 `http://localhost:8501`。

## 🔑 支持的 API

| 服务商 | BASE_URL | 模型示例 |
|--------|----------|----------|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| 豆包 (Ark) | `https://ark.cn-beijing.volces.com/api/v3` | `ep-xxxxxxxx-xxxxx` |
| SiliconFlow | `https://api.siliconflow.cn/v1` | `deepseek-ai/DeepSeek-V3` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |

## 🛠️ 使用说明

1. 注册账号后登录（Cookie 保持登录，刷新不退出）
2. 输入辩论议题和补充条件
3. 点击「🚀 开始辩论」启动第一轮
4. 点击「⚡ 自由辩」触发打断/追问（次数可在侧边栏设置）
5. 点击「📊 总结」获取决策建议，可重新生成
6. 点击「📄 导出 Word」下载完整记录
7. 页面底部「💬 意见反馈」可提交建议

## 🛡️ 管理员功能

用 `ADMIN_USER` 对应的账号登录后，侧边栏出现管理员面板，包含：

- 📊 使用统计：注册用户数、总辩论场次、每日趋势图
- 👥 用户管理：重置密码、删除用户
- 💬 意见反馈：查看用户提交的反馈，标记已读

## 📁 项目结构

```
ai-debate-assistant/
├── debate_assistant.py   # 主程序
├── auth.py               # 用户认证 + 管理员面板
├── init_admin.py         # 初始化管理员账号（运行一次）
├── requirements.txt      # 依赖列表
├── setup.bat             # 一键配置环境（Anaconda）
├── start.bat             # 一键启动应用
├── .env.example          # 环境变量模板
├── .gitignore            # Git 忽略规则
├── LICENSE               # MIT 许可证
└── README.md             # 项目说明
```

## ❓ 常见问题

**Q：双击 setup.bat 闪退怎么办？**
用 Anaconda Prompt 进入项目目录手动运行，可以看到报错信息。

**Q：API 调用失败 401？**
Streamlit Cloud 部署时需在 App Settings → Secrets 里配置环境变量，不能依赖 `.env` 文件。

**Q：刷新页面退出登录？**
已通过 Cookie 解决，有效期 7 天。若仍退出，检查浏览器是否禁用了 Cookie。

**Q：用户数据存在哪里？**
账号存 `users.json`，辩论记录存 `debate_history/{用户名}/`，反馈存 `feedback.json`，均不会上传 GitHub。

## 📄 License

MIT © 2024
