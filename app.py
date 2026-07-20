import html
import json
import math
import os
import uuid
from datetime import datetime

import streamlit as st

CATEGORIES = ["업무", "개인", "공부", "육아"]
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "todos.json")

CATEGORY_COLORS = {
    "업무": ("#dbeafe", "#2563eb"),
    "개인": ("#ede9fe", "#7c3aed"),
    "공부": ("#fef3c7", "#d97706"),
    "육아": ("#d1fae5", "#059669"),
}

st.set_page_config(page_title="마이 투두", page_icon="✅", layout="centered")


# ---- persistence (JSON file on disk = localStorage 대체) ----

def load_todos():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_todos(todos):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)


def find_todo(todo_id):
    return next((t for t in st.session_state.todos if t["id"] == todo_id), None)


def round_half_up(value):
    # python's round() uses banker's rounding (round(12.5) == 12), which would show a
    # different percentage than the web version's Math.round (Math.round(12.5) === 13)
    # for the same data. This matches Math.round's behavior for our always-non-negative inputs.
    return math.floor(value + 0.5)


# ---- session state init ----

if "todos" not in st.session_state:
    st.session_state.todos = load_todos()
if "editing_id" not in st.session_state:
    st.session_state.editing_id = None
if "input_error" not in st.session_state:
    st.session_state.input_error = None
if "edit_error" not in st.session_state:
    st.session_state.edit_error = None
if "new_todo_category" not in st.session_state:
    st.session_state.new_todo_category = "개인"


# ---- callbacks (mutate state, run before the script reruns) ----

def handle_add():
    title = st.session_state.new_todo_title
    category = st.session_state.new_todo_category
    if not title.strip():
        st.session_state.input_error = "할 일 제목을 입력해주세요."
        return
    st.session_state.input_error = None
    st.session_state.todos.append({
        "id": str(uuid.uuid4()),
        "title": title.strip(),
        "category": category,
        "completed": False,
        "createdAt": datetime.now().isoformat(),
    })
    save_todos(st.session_state.todos)
    st.session_state.new_todo_title = ""


def toggle_todo(todo_id):
    checked = st.session_state[f"chk_{todo_id}"]
    todo = find_todo(todo_id)
    if todo:
        todo["completed"] = checked
        save_todos(st.session_state.todos)


def start_edit(todo_id):
    todo = find_todo(todo_id)
    if not todo:
        return
    st.session_state.editing_id = todo_id
    st.session_state.edit_error = None
    # 위젯 key를 항상 최신 데이터로 덮어써서, 이전 편집 시도의 잔여 값이
    # 남아있다가 다시 표시되는 것을 방지한다.
    st.session_state[f"edit_title_{todo_id}"] = todo["title"]
    st.session_state[f"edit_cat_{todo_id}"] = todo["category"]


def save_edit(todo_id):
    title_val = st.session_state.get(f"edit_title_{todo_id}", "")
    if not title_val.strip():
        st.session_state.edit_error = "할 일 제목을 입력해주세요."
        return
    todo = find_todo(todo_id)
    if todo:
        todo["title"] = title_val.strip()
        todo["category"] = st.session_state.get(f"edit_cat_{todo_id}", todo["category"])
        save_todos(st.session_state.todos)
    st.session_state.editing_id = None
    st.session_state.edit_error = None


def cancel_edit(todo_id):
    st.session_state.editing_id = None
    st.session_state.edit_error = None


def reset_editing_on_filter_change():
    st.session_state.editing_id = None
    st.session_state.edit_error = None


def delete_todo(todo_id):
    st.session_state.todos = [t for t in st.session_state.todos if t["id"] != todo_id]
    save_todos(st.session_state.todos)
    if st.session_state.editing_id == todo_id:
        st.session_state.editing_id = None
        st.session_state.edit_error = None


def render_category_badge(category: str) -> str:
    bg, fg = CATEGORY_COLORS.get(category, ("#f3f4f6", "#6b7280"))
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 10px;'
        f'border-radius:999px;font-size:0.78rem;white-space:nowrap;">{html.escape(category)}</span>'
    )


# ---- UI ----

st.title("마이 투두")

# 진행률 (전체 + 카테고리별)
todos = st.session_state.todos
total = len(todos)
completed_count = sum(1 for t in todos if t["completed"])
percent = round_half_up(completed_count / total * 100) if total else 0

with st.container(border=True):
    st.progress(percent / 100 if total else 0.0)
    st.caption(f"{completed_count}/{total} 완료 ({percent}%)" if total else "할 일 없음")

    for cat in CATEGORIES:
        cat_todos = [t for t in todos if t["category"] == cat]
        cat_completed = sum(1 for t in cat_todos if t["completed"])
        cat_percent = round_half_up(cat_completed / len(cat_todos) * 100) if cat_todos else 0

        label_col, bar_col, count_col = st.columns([1, 4, 2])
        label_col.write(cat)
        with bar_col:
            st.progress(cat_percent / 100 if cat_todos else 0.0)
        count_col.write(f"{cat_completed}/{len(cat_todos)} ({cat_percent}%)")

# 입력 영역 (Enter 또는 버튼으로 추가)
with st.form("add_form", clear_on_submit=False):
    title_col, category_col, button_col = st.columns([3, 1, 1])
    title_col.text_input(
        "할 일", key="new_todo_title", placeholder="할 일을 입력하세요",
        label_visibility="collapsed",
    )
    category_col.selectbox(
        "카테고리", CATEGORIES, key="new_todo_category", label_visibility="collapsed",
    )
    button_col.form_submit_button("추가", on_click=handle_add, use_container_width=True)

if st.session_state.input_error:
    st.error(st.session_state.input_error)

# 카테고리 필터
current_filter = st.radio(
    "필터", ["전체"] + CATEGORIES, key="filter_radio", horizontal=True,
    label_visibility="collapsed", on_change=reset_editing_on_filter_change,
)

# 할 일 목록
if current_filter == "전체":
    filtered = todos
else:
    filtered = [t for t in todos if t["category"] == current_filter]

if not filtered:
    st.info("할 일이 없습니다." if total == 0 else "해당 카테고리에 할 일이 없습니다.")
else:
    for todo in filtered:
        with st.container(border=True):
            if st.session_state.editing_id == todo["id"]:
                title_col, category_col, save_col, cancel_col = st.columns([3, 1.4, 1, 1])
                title_col.text_input(
                    "제목", key=f"edit_title_{todo['id']}", label_visibility="collapsed",
                )
                category_col.selectbox(
                    "카테고리", CATEGORIES, key=f"edit_cat_{todo['id']}",
                    label_visibility="collapsed",
                )
                save_col.button(
                    "저장", key=f"save_btn_{todo['id']}",
                    on_click=save_edit, args=(todo["id"],), use_container_width=True,
                )
                cancel_col.button(
                    "취소", key=f"cancel_btn_{todo['id']}",
                    on_click=cancel_edit, args=(todo["id"],), use_container_width=True,
                )
                if st.session_state.edit_error:
                    st.error(st.session_state.edit_error)
            else:
                check_col, title_col, badge_col, edit_col, delete_col = st.columns(
                    [0.6, 3, 1.2, 1, 1]
                )
                check_col.checkbox(
                    "완료", value=todo["completed"], key=f"chk_{todo['id']}",
                    on_change=toggle_todo, args=(todo["id"],), label_visibility="collapsed",
                )

                safe_title = html.escape(todo["title"])
                if todo["completed"]:
                    title_html = (
                        f'<span style="text-decoration:line-through;color:#9ca3af;">'
                        f'{safe_title}</span>'
                    )
                else:
                    title_html = safe_title
                title_col.markdown(title_html, unsafe_allow_html=True)

                badge_col.markdown(render_category_badge(todo["category"]), unsafe_allow_html=True)

                edit_col.button(
                    "수정", key=f"edit_btn_{todo['id']}",
                    on_click=start_edit, args=(todo["id"],), use_container_width=True,
                )
                delete_col.button(
                    "삭제", key=f"del_btn_{todo['id']}",
                    on_click=delete_todo, args=(todo["id"],), use_container_width=True,
                )
