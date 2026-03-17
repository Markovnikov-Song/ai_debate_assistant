# 🎯 多 AI 辩论决策助手

一个基于多智能体的辩论辅助决策工具，让 AI 从不同立场帮你分析问题、做出决策。

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ 功能特性

- 多智能体辩论：支持派、反对派、中立理性派、长期视角派同台辩论
- 自由辩环节：支持打断、追问、抬杠，模拟真实辩论
- 自定义角色：可自由添加、编辑、删除辩论角色及人设
- 历史记录：自动保存每次辩论，支持加载和删除
- 导出 Word：一键导出完整辩论记录为 .docx 文件
- 语速调节：控制 AI 输出节奏

## 📸 界面预览

> 启动后在浏览器中打开，左侧为控制面板，右侧为辩论内容区。

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-username/ai-debate-assistant.git
cd ai-debate-assistant
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 API Key

复制环境变量模板：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 API Key：

```env
API_KEY=your-api-key-here
BASE_URL=https://api.openai.com/v1
MODEL=gpt-4o-mini
```

> 也可以直接修改 `debate_assistant.py` 顶部的配置区。

### 4. 启动应用

```bash
streamlit run debate_assistant.py
```

浏览器会自动打开 `http://localhost:8501`

## 🔑 支持的 API

| 服务商 | BASE_URL | 模型示例 |
|--------|----------|----------|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| 豆包 (Ark) | `https://ark.cn-beijing.volces.com/api/v3` | `ep-xxxxxxxx-xxxxx` |
| SiliconFlow | `https://api.siliconflow.cn/v1` | `deepseek-ai/DeepSeek-V3` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |

## 📁 项目结构

```
ai-debate-assistant/
├── debate_assistant.py   # 主程序
├── requirements.txt      # 依赖列表
├── .env.example          # 环境变量模板
├── .gitignore            # Git 忽略规则
├── LICENSE               # MIT 许可证
└── README.md             # 项目说明
```

## 🛠️ 使用说明

1. 在左侧输入栏填写辩论议题
2. 可选填补充条件（如个人情况、约束条件等）
3. 点击「🚀 开始」启动第一轮辩论
4. 点击「🔁 继续」进行多轮辩论
5. 点击「⚡ 自由辩」触发打断/追问环节
6. 点击「📊 生成总结」获取决策建议
7. 点击「📄 导出 Word」保存辩论记录

## 📄 License

MIT © 2024
