# 🎯 多 AI 辩论决策助手

一个基于多智能体的辩论辅助决策工具，让 AI 从不同立场帮你分析问题、做出决策。

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ 功能特性

- 用户注册/登录：账号密码认证，密码 bcrypt 加密，数据按用户隔离
- 多智能体辩论：支持派、反对派、中立理性派、长期视角派同台辩论
- 自由辩环节：支持打断、追问、抬杠，模拟真实辩论
- 自定义角色：可自由添加、编辑、删除辩论角色及人设
- 历史记录：每个用户独立保存，支持加载和删除
- 导出 Word：一键下载完整辩论记录（浏览器直接下载，兼容公网部署）
- 语速调节：控制 AI 输出节奏

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

### 第三步：填入 API Key

用记事本打开项目目录下的 `.env` 文件：

```env
API_KEY=你的API Key
BASE_URL=https://api.siliconflow.cn/v1
MODEL=deepseek-ai/DeepSeek-V3
```

### 第四步：启动应用

双击 `start.bat`，浏览器自动打开 `http://localhost:8501`，注册账号后即可使用。

以后每次使用只需双击 `start.bat`。

## 🔑 支持的 API

| 服务商 | BASE_URL | 模型示例 |
|--------|----------|----------|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| 豆包 (Ark) | `https://ark.cn-beijing.volces.com/api/v3` | `ep-xxxxxxxx-xxxxx` |
| SiliconFlow | `https://api.siliconflow.cn/v1` | `deepseek-ai/DeepSeek-V3` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |

## 🛠️ 使用说明

1. 首次使用先注册账号，之后登录
2. 在左侧输入栏填写辩论议题
3. 可选填补充条件（个人情况、约束条件等）
4. 点击「🚀 开始」启动第一轮辩论
5. 点击「🔁 继续」进行多轮辩论
6. 点击「⚡ 自由辩」触发打断/追问环节
7. 点击「📊 生成总结」获取决策建议
8. 点击「📄 导出 Word」下载辩论记录

## 📁 项目结构

```
ai-debate-assistant/
├── debate_assistant.py   # 主程序
├── auth.py               # 用户注册/登录模块
├── requirements.txt      # 依赖列表
├── setup.bat             # 一键配置环境（Anaconda）
├── start.bat             # 一键启动应用
├── .env.example          # 环境变量模板
├── .gitignore            # Git 忽略规则（含 .env 和 users.json）
├── LICENSE               # MIT 许可证
└── README.md             # 项目说明
```

## ❓ 常见问题

**Q：双击 setup.bat 闪退怎么办？**
用 Anaconda Prompt 进入项目目录手动运行，可以看到报错信息。

**Q：conda 命令找不到？**
确认 Anaconda 已安装，安装时勾选"Add to PATH"，或改用 Anaconda Prompt 运行。

**Q：依赖安装很慢？**
setup.bat 已默认使用清华镜像源，仍慢可换阿里源：
`pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple`

**Q：API 调用失败？**
检查 `.env` 中的 `API_KEY`、`BASE_URL`、`MODEL` 是否正确，不同服务商的 BASE_URL 不同。

**Q：用户数据存在哪里？**
账号信息存在 `users.json`，辩论记录存在 `debate_history/{用户名}/`，均在本地，不会上传 GitHub。

## 📄 License

MIT © 2024
