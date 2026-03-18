import streamlit as st
from openai import OpenAI
import json
import os
import random
from datetime import datetime
from docx import Document
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from dotenv import load_dotenv
from auth import render_auth_page, render_admin_panel

load_dotenv()

# ===================== 登录拦截 =====================
if not render_auth_page():
    st.stop()

# ===================== 基础配置（从 .env 读取） =====================
API_KEY  = os.getenv("API_KEY",  "your-api-key-here")
BASE_URL = os.getenv("BASE_URL", "https://api.siliconflow.cn/v1")
MODEL    = os.getenv("MODEL",    "deepseek-ai/DeepSeek-V3.2")

CURRENT_USER   = st.session_state.get("current_user", "guest")
HISTORY_FOLDER = os.path.join("debate_history", CURRENT_USER)
if not os.path.exists(HISTORY_FOLDER):
    os.makedirs(HISTORY_FOLDER)

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# ===================== 页面配置 =====================
st.set_page_config(page_title="超级辩论助手", page_icon="🎯", layout="centered")
st.markdown("""
<style>
@media (max-width: 768px) {
    .block-container { padding: 1rem 0.75rem; }
    h1 { font-size: 1.4rem !important; }
    h2 { font-size: 1.2rem !important; }
    h3 { font-size: 1rem !important; }
    p, li { font-size: 0.95rem !important; line-height: 1.6; }
    .stButton > button { width: 100%; }
}
</style>
""", unsafe_allow_html=True)

# ===================== 会话状态初始化 =====================
defaults = {
    "topic": "", "user_context": "", "debate_history": [],
    "debate_round": 0, "current_history_id": None,
    "custom_agents": [], "interrupt_rounds": 3,
    "last_summary": "",   # 存最新一次总结
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ===================== 角色配置 =====================
def load_agent_config():
    cfg = f"agent_config_{st.session_state.get('current_user','guest')}.json"
    if os.path.exists(cfg):
        with open(cfg, "r", encoding="utf-8") as f:
            return json.load(f)
    return [
        {"name": "支持派",     "prompt": "你是立场鲜明的支持派，说话像真实大学生一样自然、有逻辑、有情绪，但不偏激。先承接上一轮内容，针对性反驳对方，再讲自己的观点。核心理由、关键结论必须加粗。"},
        {"name": "反对派",     "prompt": "你是清醒理性的反对派，说话像认真思考的学生，指出问题一针见血。先针对性反驳对方上一轮观点，再提出自己的看法。核心理由、风险、弊端必须加粗。"},
        {"name": "中立理性派", "prompt": "你是中立理性派，像客观分析的学长，不站队、只讲事实。指出双方合理与不合理的地方，语气温和自然。关键判断、核心差异必须加粗。"},
        {"name": "长期视角派", "prompt": "你是长期视角观察者，站在未来、考研、就业、成长角度说话，像过来人给建议。结合长远发展点评当前辩论。长期影响、未来收益必须加粗。"},
    ]

def save_agent_config(agents):
    cfg = f"agent_config_{st.session_state.get('current_user','guest')}.json"
    with open(cfg, "w", encoding="utf-8") as f:
        json.dump(agents, f, ensure_ascii=False, indent=2)

if not st.session_state.custom_agents:
    st.session_state.custom_agents = load_agent_config()

# ===================== Prompt =====================
def get_debate_prompt(agent_prompt):
    return agent_prompt + """
【辩论规则】
1. 先直接回应上一轮的内容，必须反驳或承接，不能自说自话。
2. 可以质疑对方的逻辑、数据、前提，像真实辩论一样。
3. 核心理由、关键结论、反驳点必须用Markdown加粗。
4. 语言自然、像真人，不要机器腔。
5. 控制在150字以内，简明扼要，不要废话。
"""

def get_interrupt_prompt(agent_prompt, target_name, target_content):
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

SUMMARIZER_PROMPT = """
你是专业的最终决策总结者，基于完整辩论历史输出清晰可落地的总结。
要求：
1. **核心争议点**：提炼2-3个最核心的分歧。
2. **各方核心观点**：简要总结每个角色的核心立场。
3. **最终综合建议**：给出明确的决策方向（支持/反对/折中），贴合用户的具体场景。
4. **决策依据**：列出3-5条支持该建议的核心论据。
格式：用中文数字分点，最重要的结论必须加粗，语言简洁。
"""

# ===================== 存储函数 =====================
def auto_save():
    """每轮结束后静默自动保存，覆盖同一议题的上次记录"""
    if not st.session_state.topic or not st.session_state.debate_history:
        return
    # 用固定文件名（议题key），每次覆盖，不产生重复文件
    topic_key = st.session_state.topic[:20].replace(" ","_").replace("？","_").replace("?","_")
    filename  = f"auto_{topic_key}.json"
    data = {
        "id": filename, "topic": st.session_state.topic,
        "user_context": st.session_state.user_context,
        "debate_round": st.session_state.debate_round,
        "create_time":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "debate_content": st.session_state.debate_history,
        "agents_used":  st.session_state.custom_agents,
    }
    with open(os.path.join(HISTORY_FOLDER, filename), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_debate_history():
    if not st.session_state.topic or not st.session_state.debate_history:
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    topic_key = st.session_state.topic[:12].replace(" ","_").replace("？","_").replace("?","_")
    filename  = f"{timestamp}_{topic_key}.json"
    data = {
        "id": filename, "topic": st.session_state.topic,
        "user_context": st.session_state.user_context,
        "debate_round": st.session_state.debate_round,
        "create_time":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "debate_content": st.session_state.debate_history,
        "agents_used":  st.session_state.custom_agents,
    }
    with open(os.path.join(HISTORY_FOLDER, filename), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filename

def load_debate_history(filename):
    path = os.path.join(HISTORY_FOLDER, filename)
    if not os.path.exists(path):
        st.error("记录不存在")
        return
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    st.session_state.topic              = data["topic"]
    st.session_state.user_context       = data["user_context"]
    st.session_state.debate_round       = data["debate_round"]
    st.session_state.debate_history     = data["debate_content"]
    st.session_state.current_history_id = filename
    st.session_state.last_summary       = ""
    if "agents_used" in data:
        st.session_state.custom_agents = data["agents_used"]
    st.rerun()

def get_all_history():
    files = [f for f in os.listdir(HISTORY_FOLDER) if f.endswith(".json")]
    files.sort(reverse=True)
    return files

def get_history_label(filename):
    path = os.path.join(HISTORY_FOLDER, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        prefix = "🔄 " if filename.startswith("auto_") else ""
        return f"{prefix}{data.get('topic','未知议题')[:16]}  [{data.get('create_time','')[:16]}]"
    except Exception:
        return filename

def delete_history(filename):
    path = os.path.join(HISTORY_FOLDER, filename)
    if os.path.exists(path):
        os.remove(path)
        if st.session_state.current_history_id == filename:
            for k, v in {"topic":"","user_context":"","debate_history":[],"debate_round":0,"current_history_id":None}.items():
                st.session_state[k] = v
        st.rerun()

# ===================== 导出 Word =====================
def export_to_word():
    import io
    if not st.session_state.topic or not st.session_state.debate_history:
        return None, None
    doc   = Document()
    title = doc.add_heading(f"辩论记录：{st.session_state.topic}", 0)
    title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    doc.add_heading("一、基本信息", level=1)
    doc.add_paragraph(f"创建时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    doc.add_paragraph(f"辩论轮数：{st.session_state.debate_round}")
    if st.session_state.user_context:
        doc.add_paragraph(f"补充条件：{st.session_state.user_context}")
    doc.add_heading("二、完整辩论记录", level=1)
    for r in range(1, st.session_state.debate_round + 1):
        doc.add_heading(f"第{r}轮", level=2)
        for item in [x for x in st.session_state.debate_history if x["round"] == r]:
            p = doc.add_paragraph()
            p.add_run(f"{item['name']}：").bold = True
            p.add_run(item["content"].replace("**", ""))
            doc.add_paragraph()
    if st.session_state.last_summary:
        doc.add_heading("三、决策总结", level=1)
        doc.add_paragraph(st.session_state.last_summary.replace("**", ""))
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue(), f"辩论记录_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"

# ===================== AI 调用 =====================
def format_history_recent(hist, last_n_rounds=2):
    if not hist: return ""
    max_r  = max(x["round"] for x in hist)
    cutoff = max(1, max_r - last_n_rounds + 1)
    return "".join(
        f"第{x['round']}轮 - {x['name']}：{x['content']}\n\n"
        for x in hist if x["round"] >= cutoff and x["type"] == "agent_speech"
    )

def format_history_full(hist):
    return "".join(
        f"第{x['round']}轮 - {x['name']}：{x['content']}\n\n"
        for x in hist if x["type"] == "agent_speech"
    )

def call_llm(prompt, history_context="", max_tokens=400):
    context = f"核心辩论议题：{st.session_state.topic}\n"
    if st.session_state.user_context:
        context += f"用户补充条件：{st.session_state.user_context}\n"
    if history_context:
        context += f"近期辩论内容：\n{history_context}\n"
    context += f"你的任务：{prompt}"
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": context}],
            temperature=0.8,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"AI调用失败：{str(e)}")
        return "调用失败"

# ===================== 主页面 =====================
st.title("🎯 超级多智能体辩论决策助手")
st.divider()

st.session_state.topic = st.text_area(
    "💬 输入你的辩论议题",
    value=st.session_state.topic,
    placeholder="例如：大学生是否应该考研？  /  远程办公利大于弊吗？",
    height=100,
).strip()

st.session_state.user_context = st.text_area(
    "📌 补充条件（可选）",
    value=st.session_state.user_context,
    placeholder="例如：我是大三学生，目标985，家庭条件一般……",
    height=80,
).strip()

# 操作按钮
has_topic   = bool(st.session_state.topic)
has_history = bool(st.session_state.debate_history)

# 开始/继续合并为一个按钮
btn_label = "🚀 开始辩论" if st.session_state.debate_round == 0 else "🔁 继续辩论"
c1, c2, c3 = st.columns(3)
with c1: run_debate = st.button(btn_label,   use_container_width=True, disabled=not has_topic)
with c2: interrupt  = st.button("⚡ 自由辩", use_container_width=True, disabled=not has_history)
with c3: do_summary = st.button("📊 总结",   use_container_width=True, disabled=not has_history)

st.divider()

# ===================== 侧边栏 =====================
with st.sidebar:
    st.header("⚙️ 设置")
    st.caption(f"👤 {CURRENT_USER}")
    if st.button("登出", use_container_width=True):
        st.session_state.logged_in    = False
        st.session_state.current_user = ""
        st.rerun()

    # 管理员面板（仅管理员可见）
    render_admin_panel()

    st.markdown("---")
    st.markdown("### 🎭 角色管理")
    with st.expander("展开编辑角色"):
        for i, agent in enumerate(st.session_state.custom_agents):
            c1, c2, c3 = st.columns([3, 6, 1])
            with c1: new_name   = st.text_input(f"角色{i+1}名", value=agent["name"],   key=f"name_{i}")
            with c2: new_prompt = st.text_area(f"角色{i+1}人设", value=agent["prompt"], key=f"prompt_{i}", height=80)
            with c3:
                if st.button("🗑️", key=f"del_{i}"):
                    st.session_state.custom_agents.pop(i)
                    save_agent_config(st.session_state.custom_agents)
                    st.rerun()
            st.session_state.custom_agents[i]["name"]   = new_name
            st.session_state.custom_agents[i]["prompt"] = new_prompt
        st.markdown("---")
        if st.button("➕ 添加角色", use_container_width=True):
            st.session_state.custom_agents.append({"name": "新角色", "prompt": "请输入人设"})
            save_agent_config(st.session_state.custom_agents)
            st.rerun()
        if st.button("💾 保存角色配置", use_container_width=True):
            save_agent_config(st.session_state.custom_agents)
            st.success("已保存")

    st.markdown("---")
    st.markdown("### ⚡ 自由辩设置")
    st.session_state.interrupt_rounds = st.slider(
        "打断次数", min_value=1, max_value=6,
        value=st.session_state.interrupt_rounds
    )

    st.markdown("---")
    st.markdown("### 💾 导出与历史")
    word_bytes, word_filename = export_to_word()
    if word_bytes:
        st.download_button("📄 导出 Word", data=word_bytes, file_name=word_filename,
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                           use_container_width=True)
    else:
        st.button("📄 导出 Word", disabled=True, use_container_width=True)

    if st.button("💾 手动保存", use_container_width=True):
        f = save_debate_history()
        if f: st.success("已保存")

    if st.button("🧹 清空当前", use_container_width=True):
        for k, v in {"topic":"","user_context":"","debate_history":[],"debate_round":0,
                     "current_history_id":None,"last_summary":""}.items():
            st.session_state[k] = v
        st.rerun()

    st.markdown("---")
    st.markdown("### 📜 历史记录")
    histories = get_all_history()
    if histories:
        labels   = {f: get_history_label(f) for f in histories}
        selected = st.selectbox("选择记录", histories, format_func=lambda f: labels[f])
        hc1, hc2 = st.columns(2)
        with hc1:
            if st.button("🔄 加载", use_container_width=True):
                load_debate_history(selected)
        with hc2:
            if st.button("🗑️ 删除", use_container_width=True):
                delete_history(selected)
    else:
        st.info("暂无历史记录")

# ===================== 辩论逻辑 =====================
if run_debate:
    st.session_state.debate_round += 1
    r        = st.session_state.debate_round
    hist_ctx = format_history_recent(st.session_state.debate_history)
    st.subheader(f"📢 第{r}轮辩论")
    batch = []
    for agent in st.session_state.custom_agents:
        st.markdown(f"### 🗣 {agent['name']}")
        with st.spinner("思考中..."):
            content = call_llm(get_debate_prompt(agent["prompt"]), hist_ctx)
        st.markdown(content)
        st.divider()
        batch.append({"type": "agent_speech", "round": r, "name": agent["name"], "content": content})
    st.session_state.debate_history.extend(batch)
    auto_save()  # 自动保存
    st.success(f"✅ 第{r}轮完成（已自动保存）")

if interrupt:
    st.session_state.debate_round += 1
    r             = st.session_state.debate_round
    hist_ctx      = format_history_recent(st.session_state.debate_history)
    last_speeches = [x for x in st.session_state.debate_history if x["type"] == "agent_speech"]
    st.subheader(f"⚡ 第{r}轮（自由辩·打断/追问）")
    batch          = []
    current_target = last_speeches[-1] if last_speeches else None
    for _ in range(st.session_state.interrupt_rounds):
        if not current_target:
            break
        other_agents = [a for a in st.session_state.custom_agents if a["name"] != current_target["name"]]
        if not other_agents:
            break
        attacker = random.choice(other_agents)
        st.markdown(f"### ⚡ {attacker['name']} 打断 {current_target['name']}")
        with st.spinner("组织语言中..."):
            content = call_llm(
                get_interrupt_prompt(attacker["prompt"], current_target["name"], current_target["content"][:300]),
                hist_ctx
            )
        st.markdown(content)
        st.divider()
        batch.append({"type": "agent_speech", "round": r, "name": attacker["name"],
                      "content": f"（打断{current_target['name']}）{content}"})
        current_target = {"name": attacker["name"], "content": content}
    st.session_state.debate_history.extend(batch)
    auto_save()
    st.success("✅ 自由辩环节完成（已自动保存）")

if do_summary:
    st.subheader("📊 最终决策总结")
    with st.spinner("生成总结中..."):
        res = call_llm(SUMMARIZER_PROMPT, format_history_full(st.session_state.debate_history), max_tokens=800)
    st.session_state.last_summary = res  # 存起来，导出 Word 时一并写入
    st.markdown(res)
    if st.button("🔄 重新生成总结"):
        st.session_state.last_summary = ""
        st.rerun()

# 如果已有总结但没有触发按钮，也展示出来
elif st.session_state.last_summary:
    st.subheader("📊 最终决策总结")
    st.markdown(st.session_state.last_summary)
    if st.button("🔄 重新生成总结"):
        st.session_state.last_summary = ""
        st.rerun()

# ===================== 辩论记录展示 =====================
st.divider()
st.subheader("📜 完整辩论记录")
if st.session_state.debate_history:
    for r in range(1, st.session_state.debate_round + 1):
        items = [x for x in st.session_state.debate_history if x["round"] == r]
        with st.expander(f"第{r}轮", expanded=(r == st.session_state.debate_round)):
            for it in items:
                st.markdown(f"**{it['name']}**")
                st.markdown(it["content"])
                st.markdown("---")
else:
    st.info("还未开始辩论，输入议题后点击「🚀 开始辩论」")
