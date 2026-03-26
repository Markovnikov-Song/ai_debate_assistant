"""
轻量用户认证模块
- 用户数据存储在 users.json
- 密码使用 bcrypt 加密
- 支持注册、登录、登出、管理员面板
- 刷新页面需重新登录（无 cookie 持久化，防止串号）
"""

import json
import os
import bcrypt
import streamlit as st
from github_storage import load_users, save_users, load_feedback, save_feedback as gh_save_feedback

ADMIN_USER = os.getenv("ADMIN_USER", "admin")

try:
    ADMIN_USER = st.secrets["ADMIN_USER"]
except Exception:
    pass


def _load_users() -> dict:
    return load_users()


def _save_users(users: dict):
    save_users(users)


def register(username: str, password: str) -> tuple[bool, str]:
    username = username.strip()
    if not username or not password:
        return False, "用户名和密码不能为空"
    if len(username) < 2:
        return False, "用户名至少 2 个字符"
    if len(password) < 6:
        return False, "密码至少 6 位"
    users = _load_users()
    if username in users:
        return False, "用户名已存在"
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    users[username] = {"password": hashed}
    _save_users(users)
    return True, "注册成功"


def login(username: str, password: str) -> tuple[bool, str]:
    username = username.strip()
    users    = _load_users()
    if username not in users:
        return False, "用户名不存在"
    if bcrypt.checkpw(password.encode(), users[username]["password"].encode()):
        return True, "登录成功"
    return False, "密码错误"


def is_admin() -> bool:
    if not ADMIN_USER:
        return False
    return st.session_state.get("current_user") == ADMIN_USER


def logout():
    st.session_state.logged_in    = False
    st.session_state.current_user = ""
    st.rerun()


def _get_usage_stats() -> dict:
    from collections import defaultdict
    from github_storage import load_debate, list_debates, load_users
    stats = {
        "total_users": 0, "total_debates": 0, "total_rounds": 0,
        "user_debate_counts": {}, "daily_counts": defaultdict(int),
    }
    users = load_users()
    stats["total_users"] = len(users)
    for user in users:
        files = list_debates(user)
        count = 0
        for fname in files:
            try:
                data = load_debate(user, fname)
                if not data:
                    continue
                stats["total_rounds"] += data.get("debate_round", 0)
                date = data.get("create_time", "")[:10]
                if date:
                    stats["daily_counts"][date] += 1
                count += 1
            except Exception:
                continue
        stats["user_debate_counts"][user] = count
        stats["total_debates"] += count
    return stats


def render_admin_panel():
    if not is_admin():
        return
    with st.expander("🛡️ 管理员面板", expanded=False):
        tab_stats, tab_users, tab_feedback = st.tabs(["📊 使用统计", "👥 用户管理", "💬 意见反馈"])

        with tab_stats:
            stats = _get_usage_stats()
            m1, m2, m3 = st.columns(3)
            m1.metric("注册用户数", stats["total_users"])
            m2.metric("总辩论场次", stats["total_debates"])
            m3.metric("总辩论轮数", stats["total_rounds"])
            if stats["user_debate_counts"]:
                st.markdown("**各用户辩论场次**")
                import pandas as pd
                df_users = pd.DataFrame(
                    [(u, c) for u, c in stats["user_debate_counts"].items()],
                    columns=["用户", "场次"]
                ).sort_values("场次", ascending=False)
                st.bar_chart(df_users.set_index("用户"))
            if stats["daily_counts"]:
                st.markdown("**每日辩论场次趋势**")
                import pandas as pd
                df_daily = pd.DataFrame(
                    sorted(stats["daily_counts"].items()),
                    columns=["日期", "场次"]
                ).set_index("日期")
                st.line_chart(df_daily)

        with tab_users:
            users = _load_users()
            st.caption(f"当前注册用户数：{len(users)}")
            for uname in list(users.keys()):
                c1, c2, c3 = st.columns([4, 3, 3])
                with c1:
                    st.text(uname)
                with c2:
                    new_pw = st.text_input("新密码", key=f"reset_{uname}", placeholder="留空不改")
                    if st.button("重置", key=f"do_reset_{uname}"):
                        if new_pw and len(new_pw) >= 6:
                            users[uname]["password"] = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
                            _save_users(users)
                            st.success(f"{uname} 密码已重置")
                        else:
                            st.warning("密码至少 6 位")
                with c3:
                    if uname != ADMIN_USER:
                        if st.button("删除", key=f"del_user_{uname}"):
                            del users[uname]
                            _save_users(users)
                            st.rerun()

        with tab_feedback:
            feedbacks = load_feedback()
            if not feedbacks:
                st.info("暂无反馈")
            else:
                unread = sum(1 for x in feedbacks if not x.get("read"))
                st.caption(f"共 {len(feedbacks)} 条反馈，{unread} 条未读")
                for i, fb in enumerate(reversed(feedbacks)):
                    tag = "🔴 未读" if not fb.get("read") else "✅ 已读"
                    with st.expander(f"{tag}  {fb['user']}  {fb['time']}", expanded=not fb.get("read")):
                        st.write(fb["content"])
                        if not fb.get("read"):
                            if st.button("标为已读", key=f"read_{i}"):
                                idx = len(feedbacks) - 1 - i
                                feedbacks[idx]["read"] = True
                                gh_save_feedback(feedbacks)
                                st.rerun()


def render_auth_page() -> bool:
    """已登录返回 True，未登录渲染登录页并返回 False"""
    if st.session_state.get("logged_in"):
        return True

    st.title("🔐 多 AI 辩论决策助手")
    st.caption("请登录或注册后使用")
    st.divider()

    tab_login, tab_register = st.tabs(["登录", "注册"])

    with tab_login:
        u = st.text_input("用户名", key="login_u")
        p = st.text_input("密码", type="password", key="login_p")
        if st.button("登录", use_container_width=True, type="primary"):
            ok, msg = login(u, p)
            if ok:
                st.session_state.logged_in    = True
                st.session_state.current_user = u.strip()
                st.rerun()
            else:
                st.error(msg)

    with tab_register:
        u2 = st.text_input("用户名", key="reg_u")
        p2 = st.text_input("密码（至少6位）", type="password", key="reg_p")
        p3 = st.text_input("确认密码",        type="password", key="reg_p2")
        if st.button("注册", use_container_width=True):
            if p2 != p3:
                st.error("两次密码不一致")
            else:
                ok, msg = register(u2, p2)
                if ok:
                    st.session_state.logged_in    = True
                    st.session_state.current_user = u2.strip()
                    st.rerun()
                else:
                    st.error(msg)

    return False
