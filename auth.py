"""
轻量用户认证模块
- 用户数据存储在 users.json
- 密码使用 bcrypt 加密
- 支持注册、登录、登出、管理员面板
- 使用 cookie 持久化登录状态，刷新不退出
"""

import json
import os
import bcrypt
import streamlit as st
from streamlit_cookies_controller import CookieController

USERS_FILE = "users.json"
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
COOKIE_KEY = "debate_user"

# 全局 cookie 控制器（每次页面加载只初始化一次）
_cookie = CookieController()


def _load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_users(users: dict):
    tmp = USERS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    os.replace(tmp, USERS_FILE)


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
    return st.session_state.get("current_user") == ADMIN_USER


def _restore_from_cookie():
    """页面加载时尝试从 cookie 恢复登录状态"""
    if st.session_state.get("logged_in"):
        return
    try:
        username = _cookie.get(COOKIE_KEY)
        if username and username in _load_users():
            st.session_state.logged_in    = True
            st.session_state.current_user = username
    except Exception:
        pass


def _get_usage_stats() -> dict:
    """
    聚合统计所有用户的使用数据，不读取辩论具体内容。
    返回：用户数、总辩论场次、总轮数、活跃用户、最近7天活跃数
    """
    import glob
    from collections import defaultdict

    base = "debate_history"
    stats = {
        "total_users": 0,
        "total_debates": 0,
        "total_rounds": 0,
        "user_debate_counts": {},   # {username: 场次}
        "daily_counts": defaultdict(int),  # {日期: 场次}
    }

    if not os.path.exists(base):
        return stats

    user_dirs = [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))]
    stats["total_users"] = len(user_dirs)

    for user in user_dirs:
        user_path = os.path.join(base, user)
        files = glob.glob(os.path.join(user_path, "*.json"))
        count = 0
        for fp in files:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
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

            # 核心指标
            m1, m2, m3 = st.columns(3)
            m1.metric("注册用户数", stats["total_users"])
            m2.metric("总辩论场次", stats["total_debates"])
            m3.metric("总辩论轮数", stats["total_rounds"])

            # 各用户场次（不显示内容）
            if stats["user_debate_counts"]:
                st.markdown("**各用户辩论场次**")
                import pandas as pd
                df_users = pd.DataFrame(
                    [(u, c) for u, c in stats["user_debate_counts"].items()],
                    columns=["用户", "场次"]
                ).sort_values("场次", ascending=False)
                st.bar_chart(df_users.set_index("用户"))

            # 每日活跃趋势
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
            FEEDBACK_FILE = "feedback.json"
            if not os.path.exists(FEEDBACK_FILE):
                st.info("暂无反馈")
            else:
                with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                    feedbacks = json.load(f)
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
                                tmp = FEEDBACK_FILE + ".tmp"
                                with open(tmp, "w", encoding="utf-8") as f:
                                    json.dump(feedbacks, f, ensure_ascii=False, indent=2)
                                os.replace(tmp, FEEDBACK_FILE)
                                st.rerun()


def logout():
    """登出：清除 session 和 cookie"""
    st.session_state.logged_in    = False
    st.session_state.current_user = ""
    try:
        _cookie.remove(COOKIE_KEY)
    except Exception:
        pass
    st.rerun()


def render_auth_page() -> bool:
    """已登录返回 True，未登录渲染登录页并返回 False"""
    _restore_from_cookie()

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
                # 写入 cookie，有效期 7 天
                _cookie.set(COOKIE_KEY, u.strip(), max_age=7 * 24 * 3600)
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
                    st.success(msg + "，请切换到登录标签")
                else:
                    st.error(msg)

    return False
