import streamlit as st
from openai import OpenAI
import json
import os
from datetime import datetime
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from auth import render_auth_page

# ===================== 登录拦截 =====================
if not render_auth_page():
    st.stop()

# ===================== 基础配置 =====================
API_KEY = "sk-dwydkdynhxcrnajjpzvbjpyyfinzecaqfyxpszbexrohoqzg"
BASE_URL = "https://api.siliconflow.cn/v1"
MODEL = "deepseek-ai/DeepSeek-V3.2"

# 存储配置：每个用户独立文件夹
CURRENT_USER = st.session_state.get("current_user", "guest")
HISTORY_FOLDER = os.path.join("debate_history", CURRENT_USER)
if not os.path.exists(HISTORY_FOLDER):
    os.makedirs(HISTORY_FOLDER)

# 初始化AI客户端
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# Streamlit页面配置
st.set_page_config(page_title="超级辩论助手", page_icon="🎯", layout="centered")

# 手机端适配样式
st.markdown("""
<style>
/* 正文字体在手机上稍大一点 */
@media (max-width: 768px) {
    .block-container { padding: 1rem 0.75rem; }
    h1 { font-size: 1.4rem !important; }
    h2 { font-size: 1.2rem !important; }
    h3 { font-size: 1rem !important; }
    p, li { font-size: 0.95rem !important; line-height: 1.6; }
    /* 按钮撑满宽度更好点击 */
    .stButton > button { width: 100%; }
}
</style>
""", unsafe_allow_html=True)

st.title("🎯 超级多智能体辩论决策助手")
st.divider()

# ===================== 主页面：议题输入区 =====================
topic_input = st.text_area(
    "💬 输入你的辩论议题",
    value=st.session_state.get("topic", ""),
    placeholder="例如：大学生是否应该考研？  /  远程办公利大于弊吗？",
    height=100,
)
st.session_state.topic = topic_input.strip()

ctx_input = st.text_area(
    "📌 补充条件（可选）",
    value=st.session_state.get("user_context", ""),
    placeholder="例如：我是大三学生，目标985，家庭条件一般……",
    height=80,
)
if st.button("✅ 确认补充条件", use_container_width=True):
    st.session_state.user_context = ctx_input.strip()
    if st.session_state.user_context:
        st.session_state.debate_history.append({
            "type": "user_context",
            "content": f"用户补充：{st.session_state.user_context}",
            "round": st.session_state.debate_round + 1
        })
    st.success("已更新")

st.divider()

# ===================== 会话状态初始化 =====================
if "topic" not in st.session_state:
    st.session_state.topic = ""
if "user_context" not in st.session_state:
    st.session_state.user_context = ""
if "debate_history" not in st.session_state:
    st.session_state.debate_history = []
if "debate_round" not in st.session_state:
    st.session_state.debate_round = 0
if "current_history_id" not in st.session_state:
    st.session_state.current_history_id = None
if "custom_agents" not in st.session_state:
    st.session_state.custom_agents = []
if "speed" not in st.session_state:
    st.session_state.speed = 0.0  # 保留兼容，不再使用


# ===================== 加载/保存自定义角色配置 =====================
def load_agent_config():
    # 每次动态获取当前用户的配置文件路径，避免 guest 路径污染
    user = st.session_state.get("current_user", "guest")
    cfg_file = f"agent_config_{user}.json"
    if os.path.exists(cfg_file):
        with open(cfg_file, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return [
            {"name": "支持派",
             "prompt": "你是立场鲜明的支持派，说话像真实大学生一样自然、有逻辑、有情绪，但不偏激。先承接上一轮内容，针对性反驳对方，再讲自己的观点。核心理由、关键结论必须加粗。"},
            {"name": "反对派",
             "prompt": "你是清醒理性的反对派，说话像认真思考的学生，指出问题一针见血。先针对性反驳对方上一轮观点，再提出自己的看法。核心理由、风险、弊端必须加粗。"},
            {"name": "中立理性派",
             "prompt": "你是中立理性派，像客观分析的学长，不站队、只讲事实。指出双方合理与不合理的地方，语气温和自然。关键判断、核心差异必须加粗。"},
            {"name": "长期视角派",
             "prompt": "你是长期视角观察者，站在未来、考研、就业、成长角度说话，像过来人给建议。结合长远发展点评当前辩论。长期影响、未来收益必须加粗。"}
        ]


def save_agent_config(agents):
    user = st.session_state.get("current_user", "guest")
    cfg_file = f"agent_config_{user}.json"
    with open(cfg_file, "w", encoding="utf-8") as f:
        json.dump(agents, f, ensure_ascii=False, indent=2)


# 初始化角色
if not st.session_state.custom_agents:
    st.session_state.custom_agents = load_agent_config()


# ===================== 🔥 超级辩论提示词（含打断/追问/抬杠） =====================
def get_debate_prompt(agent_prompt):
    return agent_prompt + """
【辩论规则】
1. 先直接回应上一轮的内容，**必须反驳或承接**，不能自说自话。
2. 可以质疑对方的逻辑、数据、前提，像真实辩论一样。
3. 核心理由、关键结论、反驳点必须用Markdown加粗。
4. 语言自然、像真人，不要机器腔。
5. 控制在150字以内，简明扼要，不要废话。
"""


def get_interrupt_prompt(agent_prompt, target_name, target_content):
    """打断专用 prompt：明确指定被打断的人和内容"""
    return agent_prompt + f"""
【自由辩规则】
现在是自由辩环节，你要打断并反驳"{target_name}"刚才说的这段话：

"{target_content}"

要求：
1. 直接针对上面这段话的漏洞、矛盾或不合理之处发起反驳或追问
2. 不需要完整阐述自己的立场，只需要一针见血地指出问题
3. 语气可以尖锐，像真实辩论赛的自由辩环节
4. 控制在100字以内，简短有力
"""


# ===================== 优化后的总结提示词 =====================
SUMMARIZER_PROMPT = """
你是专业的最终决策总结者，需要基于完整的辩论历史（包括用户补充条件、自定义角色的观点、打断/追问内容），输出一份清晰、可落地的总结。
要求：
1. **核心争议点**：提炼2-3个最核心的分歧，不要罗列所有细节。
2. **各方核心观点**：简要总结每个角色的核心立场（包括自定义角色）。
3. **最终综合建议**：给出明确的决策方向（支持/反对/折中），必须贴合用户的具体场景和补充条件。
4. **决策依据**：列出3-5条支持该建议的最核心论据。
格式要求：
- 用中文数字分点，结构清晰。
- **最重要的结论、建议必须加粗**。
- 语言简洁，不要废话。
"""


# ===================== 核心存储函数 =====================
def save_debate_history():
    if not st.session_state.topic or len(st.session_state.debate_history) == 0:
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    topic_key = st.session_state.topic[:12].replace(" ", "_").replace("？", "_").replace("?", "_")
    filename = f"{timestamp}_{topic_key}.json"
    path = os.path.join(HISTORY_FOLDER, filename)
    data = {
        "id": filename,
        "topic": st.session_state.topic,
        "user_context": st.session_state.user_context,
        "debate_round": st.session_state.debate_round,
        "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "debate_content": st.session_state.debate_history,
        "agents_used": st.session_state.custom_agents
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filename


def load_debate_history(filename):
    path = os.path.join(HISTORY_FOLDER, filename)
    if not os.path.exists(path):
        st.error("记录不存在")
        return False
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    st.session_state.topic = data["topic"]
    st.session_state.user_context = data["user_context"]
    st.session_state.debate_round = data["debate_round"]
    st.session_state.debate_history = data["debate_content"]
    st.session_state.current_history_id = filename
    if "agents_used" in data:
        st.session_state.custom_agents = data["agents_used"]
    st.rerun()  # 刷新页面让内容显示出来


def get_all_history():
    files = [f for f in os.listdir(HISTORY_FOLDER) if f.endswith(".json")]
    files.sort(reverse=True)
    return files


def delete_history(filename):
    path = os.path.join(HISTORY_FOLDER, filename)
    if os.path.exists(path):
        os.remove(path)
        st.success("已删除")
        if st.session_state.current_history_id == filename:
            st.session_state.topic = ""
            st.session_state.user_context = ""
            st.session_state.debate_round = 0
            st.session_state.debate_history = []
            st.session_state.current_history_id = None
        st.rerun()


# ===================== 导出Word函数（返回字节流，支持浏览器下载） =====================
def export_to_word():
    """生成 Word 文档并返回 (bytes, filename)，不写磁盘，兼容公网部署。"""
    import io
    if not st.session_state.topic or len(st.session_state.debate_history) == 0:
        return None, None

    doc = Document()

    # 标题
    title = doc.add_heading(f"辩论记录：{st.session_state.topic}", 0)
    title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

    # 基本信息
    doc.add_heading("一、基本信息", level=1)
    doc.add_paragraph(f"创建时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    doc.add_paragraph(f"辩论轮数：{st.session_state.debate_round}")
    if st.session_state.user_context:
        doc.add_paragraph(f"用户补充条件：{st.session_state.user_context}")

    # 辩论记录
    doc.add_heading("二、完整辩论记录", level=1)
    for r in range(1, st.session_state.debate_round + 1):
        doc.add_heading(f"第{r}轮", level=2)
        for item in [x for x in st.session_state.debate_history if x["round"] == r]:
            if item["type"] == "user_context":
                p = doc.add_paragraph()
                p.add_run("💬 用户补充：").bold = True
                p.add_run(item["content"].replace("用户补充：", ""))
            elif item["type"] == "agent_speech":
                p = doc.add_paragraph()
                p.add_run(f"{item['name']}：").bold = True
                p.add_run(item["content"].replace("**", ""))
            doc.add_paragraph()

    # 写入内存，不落磁盘
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    filename = f"辩论记录_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    return buf.getvalue(), filename


# ===================== AI调用函数 =====================
def call_llm(prompt, history_context="", max_tokens=400):
    context = f"核心辩论议题：{st.session_state.topic}\n"
    if st.session_state.user_context:
        context += f"用户补充条件/场景：{st.session_state.user_context}\n"
    if history_context:
        context += f"历史辩论内容：\n{history_context}\n"
    context += f"你的任务：{prompt}"

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": context}],
            temperature=0.8,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"AI调用失败：{str(e)}")
        return "调用失败"


def format_history(hist):
    out = ""
    for item in hist:
        if item["type"] == "agent_speech":
            out += f"第{item['round']}轮 - {item['name']}：{item['content']}\n\n"
        elif item["type"] == "user_context":
            out += f"{item['content']}\n\n"
    return out


# ===================== 左侧UI（整合所有功能） =====================
with st.sidebar:
    st.header("⚙️ 核心设置")

    # 当前用户 & 登出
    st.caption(f"👤 当前用户：{CURRENT_USER}")
    if st.button("登出", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.current_user = ""
        st.rerun()

    st.markdown("---")

    # 1. 语速调节已移除（原为无效延迟）

    st.markdown("---")

    # 3. 自定义角色（新增）
    st.markdown("### 🎭 角色管理")
    with st.expander("点击展开/编辑角色"):
        for i, agent in enumerate(st.session_state.custom_agents):
            col1, col2, col3 = st.columns([3, 6, 1])
            with col1:
                new_name = st.text_input(f"角色{i + 1}名", value=agent["name"], key=f"name_{i}")
            with col2:
                new_prompt = st.text_area(f"角色{i + 1}人设", value=agent["prompt"], key=f"prompt_{i}", height=80)
            with col3:
                if st.button("🗑️", key=f"del_{i}"):
                    st.session_state.custom_agents.pop(i)
                    save_agent_config(st.session_state.custom_agents)
                    st.rerun()
            # 更新角色
            st.session_state.custom_agents[i]["name"] = new_name
            st.session_state.custom_agents[i]["prompt"] = new_prompt

        # 添加新角色
        st.markdown("---")
        if st.button("➕ 添加新角色", use_container_width=True):
            st.session_state.custom_agents.append({"name": "新角色", "prompt": "请输入这个人设的性格、立场、说话风格"})
            save_agent_config(st.session_state.custom_agents)
            st.rerun()

        # 保存角色配置
        if st.button("💾 保存角色配置", use_container_width=True):
            save_agent_config(st.session_state.custom_agents)
            st.success("角色配置已保存")

    st.markdown("---")

    # 4. 辩论操作
    st.markdown("### 🎯 辩论操作")
    col1, col2 = st.columns(2)
    with col1:
        start = st.button("🚀 开始", use_container_width=True, disabled=not st.session_state.topic)
    with col2:
        cont = st.button("🔁 继续", use_container_width=True, disabled=len(st.session_state.debate_history) == 0)

    interrupt = st.button("⚡ 自由辩（打断/追问）", use_container_width=True,
                          disabled=len(st.session_state.debate_history) == 0)
    summary = st.button("📊 生成总结", use_container_width=True)

    st.markdown("---")

    # 5. 导出与历史
    st.markdown("### 💾 导出与历史")
    word_bytes, word_filename = export_to_word()
    if word_bytes:
        st.download_button(
            label="📄 导出 Word",
            data=word_bytes,
            file_name=word_filename,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )
    else:
        st.button("📄 导出 Word", disabled=True, use_container_width=True)

    if st.button("💾 保存辩论", use_container_width=True):
        f = save_debate_history()
        if f: st.success(f"已保存：{f}")

    clear = st.button("🧹 清空当前", use_container_width=True)
    if clear:
        st.session_state.topic = ""
        st.session_state.user_context = ""
        st.session_state.debate_history = []
        st.session_state.debate_round = 0
        st.session_state.current_history_id = None
        st.rerun()

    st.markdown("---")
    st.markdown("### 📜 加载历史")
    histories = get_all_history()
    if histories:
        selected = st.selectbox("选择记录", histories)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 加载", use_container_width=True):
                load_debate_history(selected)
        with c2:
            if st.button("🗑️ 删除", use_container_width=True):
                delete_history(selected)
    else:
        st.info("暂无历史记录")

# ===================== 辩论逻辑（含自由辩） =====================
hist_str = format_history(st.session_state.debate_history)

if start:
    st.session_state.debate_round += 1
    r = st.session_state.debate_round
    st.subheader(f"📢 第{r}轮辩论")
    batch = []
    for agent in st.session_state.custom_agents:
        st.markdown(f"### 🗣 {agent['name']}")
        with st.spinner("思考中..."):
            content = call_llm(get_debate_prompt(agent["prompt"]), hist_str)
            st.markdown(content)
            batch.append({
                "type": "agent_speech",
                "round": r,
                "name": agent["name"],
                "content": content
            })
            st.divider()
    st.session_state.debate_history.extend(batch)
    st.success(f"✅ 第{r}轮完成")

if cont:
    st.session_state.debate_round += 1
    r = st.session_state.debate_round
    st.subheader(f"📢 第{r}轮（继续辩论）")
    h = format_history(st.session_state.debate_history)
    batch = []
    for agent in st.session_state.custom_agents:
        st.markdown(f"### 🗣 {agent['name']}")
        with st.spinner("思考中..."):
            content = call_llm(get_debate_prompt(agent["prompt"]), h)
            st.markdown(content)
            batch.append({
                "type": "agent_speech",
                "round": r,
                "name": agent["name"],
                "content": content
            })
            st.divider()
    st.session_state.debate_history.extend(batch)
    st.success(f"✅ 第{r}轮完成")

if interrupt:
    st.session_state.debate_round += 1
    r = st.session_state.debate_round
    st.subheader(f"⚡ 第{r}轮（自由辩·打断/追问）")
    h = format_history(st.session_state.debate_history)

    # 取上一轮最后几条发言作为"被打断"的候选
    last_speeches = [
        x for x in st.session_state.debate_history
        if x["type"] == "agent_speech"
    ][-len(st.session_state.custom_agents):]  # 上一轮所有发言

    batch = []
    import random

    # 模拟 3 次交替打断：每次随机选一个打断者，打断上一条发言
    current_target = last_speeches[-1] if last_speeches else None
    for _ in range(3):
        if not current_target:
            break

        # 选一个不是被打断者的角色来发起打断
        other_agents = [
            a for a in st.session_state.custom_agents
            if a["name"] != current_target["name"]
        ]
        if not other_agents:
            break
        attacker = random.choice(other_agents)

        st.markdown(f"### ⚡ {attacker['name']} 打断 {current_target['name']}")
        with st.spinner("组织语言中..."):
            content = call_llm(
                get_interrupt_prompt(
                    attacker["prompt"],
                    current_target["name"],
                    current_target["content"][:300]  # 只取前300字避免 token 过多
                ),
                h
            )
            st.markdown(content)
        st.divider()

        entry = {
            "type": "agent_speech",
            "round": r,
            "name": attacker["name"],
            "content": f"（打断{current_target['name']}）{content}"
        }
        batch.append(entry)
        # 下一次打断的目标变成刚才的攻击者
        current_target = {"name": attacker["name"], "content": content}

    st.session_state.debate_history.extend(batch)
    st.success(f"✅ 自由辩环节完成")

if summary:
    st.subheader("📊 最终决策总结")
    with st.spinner("生成总结中..."):
        h = format_history(st.session_state.debate_history)
        res = call_llm(SUMMARIZER_PROMPT, h, max_tokens=800)
        st.markdown(res)

# ===================== 历史展示 =====================
st.divider()
st.subheader("📜 完整辩论记录")
if st.session_state.debate_history:
    max_r = st.session_state.debate_round
    for r in range(1, max_r + 1):
        items = [x for x in st.session_state.debate_history if x["round"] == r]
        with st.expander(f"第{r}轮", expanded=r == max_r):
            for it in items:
                if it["type"] == "user_context":
                    st.write(f"💬 {it['content']}")
                else:
                    st.markdown(f"**{it['name']}**")
                    st.markdown(it["content"])
                st.markdown("---")
else:
    st.info("还未开始辩论，请在左侧输入议题并点击「开始」")