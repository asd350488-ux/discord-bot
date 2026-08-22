# ==========================
# 🎓 Moon Bot v2｜角色考試系統
# 📝 指令 2｜角色考試
# ==========================

import discord
from discord.ui import View, Button, Select, UserSelect

import sqlite3
import random
import json
import uuid
import re
from datetime import datetime
import pytz

from config import MOMMY_LIST, BOT_ADMINS
from database import DB_PATH


# ==========================
# 🌙 基本設定
# ==========================

TIMEZONE = pytz.timezone("Asia/Taipei")

# 每次最多批量設定 25 位考生
SELECT_PAGE_SIZE = 25

# 題目查看每頁數量
QUESTION_DISPLAY_PAGE_SIZE = 10

# 考試題數
EXAM_MIN_QUESTIONS = 5
EXAM_MAX_QUESTIONS = 10

# 管理層
EXAM_MANAGERS = set(BOT_ADMINS)

# 防止同一時間重複建立同一位考生的考場
ACTIVE_EXAM_USERS = set()

# 防止 setup_character_test 被 on_ready 重複註冊指令
_SETUP_DONE = False


# ==========================
# 🗄️ 資料庫
# ==========================

def get_db_connection():
    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_character_test_database():
    conn = get_db_connection()
    cursor = conn.cursor()

    # ==========================
    # 📋 本月考生 → 角色設定
    # ==========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS character_test_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round_key TEXT NOT NULL,
            user_id TEXT NOT NULL,
            mommy_id TEXT NOT NULL,
            role_id INTEGER NOT NULL,
            question_count INTEGER NOT NULL DEFAULT 5,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(round_key, user_id)
        )
    """)

    # 🔄 舊版資料庫自動補上「管理層指定題數」欄位
    assignment_columns = [
        row[1]
        for row in cursor.execute(
            "PRAGMA table_info(character_test_assignments)"
        ).fetchall()
    ]

    if "question_count" not in assignment_columns:
        cursor.execute("""
            ALTER TABLE character_test_assignments
            ADD COLUMN question_count INTEGER NOT NULL DEFAULT 5
        """)

    # ==========================
    # 🎓 進行中的考試
    # ==========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS character_test_sessions (
            session_id TEXT PRIMARY KEY,
            round_key TEXT NOT NULL,
            user_id TEXT NOT NULL,
            mommy_id TEXT NOT NULL,
            role_id INTEGER NOT NULL,
            channel_id TEXT NOT NULL,
            question_data TEXT NOT NULL,
            question_message_ids TEXT NOT NULL,
            submit_message_id TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            submitted_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def get_now():
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")


# ==========================
# 📅 每月週期
# ==========================

def get_cycle_round_key():
    """
    20 號～月底：設定下一個月的考試
    1 號～19 號：目前這個月的考試週期
    """

    now = datetime.now(TIMEZONE)

    if now.day >= 20:
        year = now.year
        month = now.month + 1

        if month == 13:
            year += 1
            month = 1

        return f"{year:04d}-{month:02d}"

    return f"{now.year:04d}-{now.month:02d}"


def is_setup_window():
    """目前不限制設定日期。"""
    return True


def format_round(round_key):
    year, month = round_key.split("-")
    return f"{year} 年 {int(month)} 月"


def cleanup_old_rounds(round_key):
    """
    每月 20 號進入新一輪時，只保留新的本月考試設定。
    不保存歷史月份報考資料。
    """

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM character_test_assignments WHERE round_key != ?",
        (round_key,)
    )

    cursor.execute(
        "DELETE FROM character_test_sessions WHERE round_key != ?",
        (round_key,)
    )

    conn.commit()
    conn.close()


# ==========================
# 👑 權限
# ==========================

def is_exam_manager(user_id: int) -> bool:
    return user_id in EXAM_MANAGERS


def get_mommy_name(user_id: int):
    return MOMMY_LIST.get(user_id, "未知媽咪")


# ==========================
# 🎭 題庫資料
# ==========================

def get_all_roles(mommy_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    if mommy_id is None:
        cursor.execute("""
            SELECT *
            FROM character_exam_roles
            ORDER BY mommy_id ASC, id ASC
        """)
    else:
        cursor.execute("""
            SELECT *
            FROM character_exam_roles
            WHERE mommy_id = ?
            ORDER BY id ASC
        """, (str(mommy_id),))

    roles = cursor.fetchall()
    conn.close()
    return roles


def get_role(role_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM character_exam_roles
        WHERE id = ?
    """, (role_id,))

    role = cursor.fetchone()
    conn.close()
    return role


def get_role_questions(role_id: int, difficulty=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    if difficulty:
        cursor.execute("""
            SELECT *
            FROM character_exam_questions
            WHERE role_id = ?
            AND difficulty = ?
            ORDER BY id ASC
        """, (role_id, difficulty))
    else:
        cursor.execute("""
            SELECT *
            FROM character_exam_questions
            WHERE role_id = ?
            ORDER BY id ASC
        """, (role_id,))

    questions = cursor.fetchall()
    conn.close()
    return questions


# ==========================
# 📋 本月考試設定資料
# ==========================

def get_assignment(round_key, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM character_test_assignments
        WHERE round_key = ?
        AND user_id = ?
    """, (round_key, str(user_id)))

    assignment = cursor.fetchone()
    conn.close()
    return assignment


def get_assignments(round_key):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM character_test_assignments
        WHERE round_key = ?
        ORDER BY id ASC
    """, (round_key,))

    assignments = cursor.fetchall()
    conn.close()
    return assignments


def get_active_session(user_id: int, round_key=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    if round_key:
        cursor.execute("""
            SELECT *
            FROM character_test_sessions
            WHERE user_id = ?
            AND round_key = ?
            AND status IN ('active', 'submitted')
            ORDER BY created_at DESC
            LIMIT 1
        """, (str(user_id), round_key))
    else:
        cursor.execute("""
            SELECT *
            FROM character_test_sessions
            WHERE user_id = ?
            AND status IN ('active', 'submitted')
            ORDER BY created_at DESC
            LIMIT 1
        """, (str(user_id),))

    session = cursor.fetchone()
    conn.close()
    return session


def save_assignment(
    round_key,
    user_id,
    mommy_id,
    role_id,
    question_count
):
    now = get_now()

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO character_test_assignments
        (
            round_key,
            user_id,
            mommy_id,
            role_id,
            question_count,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(round_key, user_id)
        DO UPDATE SET
            mommy_id = excluded.mommy_id,
            role_id = excluded.role_id,
            question_count = excluded.question_count,
            updated_at = excluded.updated_at
    """, (
        round_key,
        str(user_id),
        str(mommy_id),
        role_id,
        question_count,
        now,
        now
    ))

    conn.commit()
    conn.close()


def delete_assignment(round_key, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM character_test_assignments
        WHERE round_key = ?
        AND user_id = ?
    """, (round_key, str(user_id)))

    conn.commit()
    conn.close()


def save_session(
    session_id,
    round_key,
    user_id,
    mommy_id,
    role_id,
    channel_id,
    question_data,
    question_message_ids,
    submit_message_id
):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO character_test_sessions
        (
            session_id,
            round_key,
            user_id,
            mommy_id,
            role_id,
            channel_id,
            question_data,
            question_message_ids,
            submit_message_id,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
    """, (
        session_id,
        round_key,
        str(user_id),
        str(mommy_id),
        role_id,
        str(channel_id),
        json.dumps(question_data, ensure_ascii=False),
        json.dumps(question_message_ids),
        str(submit_message_id),
        get_now()
    ))

    conn.commit()
    conn.close()


def mark_session_submitted(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE character_test_sessions
        SET status = 'submitted',
            submitted_at = ?
        WHERE session_id = ?
    """, (get_now(), session_id))

    conn.commit()
    conn.close()


def delete_session(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM character_test_sessions WHERE session_id = ?",
        (session_id,)
    )

    conn.commit()
    conn.close()


# ==========================
# 🎯 隨機抽題
# ==========================

def draw_exam_questions(role_id: int, count: int):
    simple = list(get_role_questions(role_id, "simple"))
    hard = list(get_role_questions(role_id, "hard"))

    if len(simple) + len(hard) < count:
        return None

    simple_count = round(count * 0.6)
    hard_count = count - simple_count

    selected = []

    # -------------------------
    # 🟢 先抽簡單題
    # -------------------------

    simple_take = min(simple_count, len(simple))
    selected.extend(random.sample(simple, simple_take))

    # -------------------------
    # 🔴 再抽困難題
    # -------------------------

    hard_take = min(hard_count, len(hard))
    selected.extend(random.sample(hard, hard_take))

    # -------------------------
    # 🧩 題庫不足自動補題
    # -------------------------

    remaining = count - len(selected)
    selected_ids = {question["id"] for question in selected}

    if remaining > 0:
        extra_pool = [
            question
            for question in simple + hard
            if question["id"] not in selected_ids
        ]

        selected.extend(
            random.sample(extra_pool, remaining)
        )

    random.shuffle(selected)

    return [
        {
            "id": question["id"],
            "difficulty": question["difficulty"],
            "question": question["question"],
            "answer": question["answer"]
        }
        for question in selected
    ]


# ==========================
# 🌙 Embed
# ==========================

def create_setup_embed(round_key):
    assignments = get_assignments(round_key)
    setup_available = is_setup_window()

    embed = discord.Embed(
        title="🎓 角色考試設定中心",
        description=(
            f"📅 **本輪考試：{format_round(round_key)}**\n\n"
            "📋 每月 **20 號**開始設定下一輪考試。\n"
            "🎓 考試日期不綁定，由管理層手動安排與開始。\n"
            "⏰ 不設定倒數與考試時長。\n\n"
            f"{'🟢 目前可以設定與修改。' if setup_available else '🔒 目前不是設定期間，僅可查看。'}"
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👥 本輪考生",
        value=f"**{len(assignments)}** 人",
        inline=True
    )

    embed.add_field(
        name="👑 管理權限",
        value="六位管理層完全平權",
        inline=True
    )

    embed.add_field(
        name="🎯 綁定方式",
        value="考生 → 報考角色",
        inline=True
    )

    embed.add_field(
        name="📝 考試規則",
        value=(
            "5～10 題\n"
            "🟢 60% 簡單／🔴 40% 困難\n"
            "同一場不重複題目"
        ),
        inline=False
    )

    embed.set_footer(
        text="🌙 Moon Bot v2｜角色考試系統"
    )

    return embed


def create_assignment_list_embed(guild, round_key, page=0):
    assignments = get_assignments(round_key)

    total_pages = max(
        1,
        (len(assignments) + QUESTION_DISPLAY_PAGE_SIZE - 1)
        // QUESTION_DISPLAY_PAGE_SIZE
    )

    page = max(0, min(page, total_pages - 1))

    start = page * QUESTION_DISPLAY_PAGE_SIZE
    page_assignments = assignments[
        start:start + QUESTION_DISPLAY_PAGE_SIZE
    ]

    embed = discord.Embed(
        title="📋 本輪考生設定",
        description=(
            f"📅 **{format_round(round_key)}**\n"
            f"目前共 **{len(assignments)}** 位考生\n"
            f"第 **{page + 1} / {total_pages}** 頁"
        ),
        color=discord.Color.blurple()
    )

    if not page_assignments:
        embed.add_field(
            name="📭 目前沒有設定",
            value="尚未設定任何考生。",
            inline=False
        )
    else:
        for index, assignment in enumerate(
            page_assignments,
            start=start + 1
        ):
            member = guild.get_member(int(assignment["user_id"]))
            display_name = (
                member.display_name
                if member
                else f"使用者 {assignment['user_id']}"
            )

            mommy_name = get_mommy_name(
                int(assignment["mommy_id"])
            )

            role = get_role(
                int(assignment["role_id"])
            )

            role_name = (
                role["role_name"]
                if role
                else "未知角色"
            )

            embed.add_field(
                name=f"{index}. 👤 {display_name}",
                value=(
                    f"👩‍👧 **{mommy_name}**\n"
                    f"🎭 **{role_name}**\n"
                    f"📝 **題數：{assignment['question_count']} 題**"
                ),
                inline=False
            )

    embed.set_footer(
        text="🌙 可由六位管理層自由修改本輪設定"
    )

    return embed


# ==========================
# 👑 管理中心｜選擇媽咪
# ==========================

class ExamMommySelect(Select):

    def __init__(self, parent_view):
        self.parent_view = parent_view

        options = []

        for mommy_id, mommy_name in MOMMY_LIST.items():
            options.append(
                discord.SelectOption(
                    label=mommy_name[:100],
                    value=str(mommy_id),
                    emoji="👩‍👧"
                )
            )

        super().__init__(
            placeholder="👩‍👧 選擇媽咪",
            options=options,
            row=0
        )

    async def callback(self, interaction):
        if not is_exam_manager(interaction.user.id):
            await interaction.response.send_message(
                "❌ 只有六位管理層可以使用此設定。",
                ephemeral=True
            )
            return

        self.parent_view.selected_mommy_id = int(self.values[0])
        self.parent_view.selected_role_id = None
        self.parent_view.role_page = 0

        self.parent_view.refresh_items()

        await interaction.response.edit_message(
            embed=self.parent_view.create_embed(),
            view=self.parent_view
        )


# ==========================
# 🎭 管理中心｜選擇角色
# ==========================

class ExamRoleSelect(Select):

    def __init__(self, parent_view):
        self.parent_view = parent_view

        roles = get_all_roles(
            parent_view.selected_mommy_id
        ) if parent_view.selected_mommy_id else []

        start = parent_view.role_page * SELECT_PAGE_SIZE
        page_roles = roles[
            start:start + SELECT_PAGE_SIZE
        ]

        options = []

        for role in page_roles:
            options.append(
                discord.SelectOption(
                    label=role["role_name"][:100],
                    value=str(role["id"]),
                    emoji="🎭"
                )
            )

        if not options:
            options.append(
                discord.SelectOption(
                    label=(
                        "請先選擇媽咪"
                        if not parent_view.selected_mommy_id
                        else "目前沒有角色"
                    ),
                    value="none",
                    emoji="📭"
                )
            )

        super().__init__(
            placeholder="🎭 選擇角色",
            options=options,
            row=1
        )

    async def callback(self, interaction):
        if not is_exam_manager(interaction.user.id):
            await interaction.response.send_message(
                "❌ 只有六位管理層可以使用此設定。",
                ephemeral=True
            )
            return

        if self.values[0] == "none":
            await interaction.response.send_message(
                "📭 目前沒有可以選擇的角色。",
                ephemeral=True
            )
            return

        self.parent_view.selected_role_id = int(
            self.values[0]
        )

        await interaction.response.edit_message(
            embed=self.parent_view.create_embed(),
            view=self.parent_view
        )


# ==========================
# 👤 管理中心｜選擇考生
# ==========================

class ExamCandidateSelect(UserSelect):

    def __init__(self, parent_view):
        self.parent_view = parent_view

        super().__init__(
            placeholder="👤 選擇考生，可一次選擇多人",
            min_values=1,
            max_values=25,
            row=2
        )

    async def callback(self, interaction):
        if not is_exam_manager(interaction.user.id):
            await interaction.response.send_message(
                "❌ 只有六位管理層可以使用此設定。",
                ephemeral=True
            )
            return

        self.parent_view.selected_candidate_ids = [
            user.id for user in self.values
        ]

        await interaction.response.edit_message(
            embed=self.parent_view.create_embed(),
            view=self.parent_view
        )


# ==========================
# 📝 管理中心｜選擇考試題數
# ==========================

class ExamQuestionCountSelect(Select):

    def __init__(self, parent_view):
        self.parent_view = parent_view

        options = [
            discord.SelectOption(
                label=f"{count} 題",
                description="本次考試固定使用此題數",
                value=str(count),
                emoji="📝"
            )
            for count in range(
                EXAM_MIN_QUESTIONS,
                EXAM_MAX_QUESTIONS + 1
            )
        ]

        super().__init__(
            placeholder="📝 管理層指定本次考試題數",
            options=options,
            row=3
        )

    async def callback(self, interaction):
        if not is_exam_manager(interaction.user.id):
            await interaction.response.send_message(
                "❌ 只有六位管理層可以使用此設定。",
                ephemeral=True
            )
            return

        self.parent_view.selected_question_count = int(self.values[0])

        await interaction.response.edit_message(
            embed=self.parent_view.create_embed(),
            view=self.parent_view
        )


# ==========================
# 👑 管理中心 View
# ==========================

class ExamSetupView(View):

    def __init__(self, manager_id):
        super().__init__(timeout=None)

        self.manager_id = manager_id
        self.selected_mommy_id = None
        self.selected_role_id = None
        self.selected_candidate_ids = []
        self.selected_question_count = None
        self.role_page = 0

        self.refresh_items()

    async def check_manager(self, interaction):
        if not is_exam_manager(interaction.user.id):
            await interaction.response.send_message(
                "❌ 只有六位管理層可以使用此設定。",
                ephemeral=True
            )
            return False
        return True

    def create_embed(self):
        round_key = get_cycle_round_key()
        embed = create_setup_embed(round_key)

        selected_mommy = (
            get_mommy_name(self.selected_mommy_id)
            if self.selected_mommy_id
            else "尚未選擇"
        )

        selected_role = "尚未選擇"

        if self.selected_role_id:
            role = get_role(self.selected_role_id)
            if role:
                selected_role = role["role_name"]

        selected_candidates = (
            f"{len(self.selected_candidate_ids)} 位"
            if self.selected_candidate_ids
            else "尚未選擇"
        )

        selected_question_count = (
            f"{self.selected_question_count} 題"
            if self.selected_question_count
            else "尚未選擇"
        )

        embed.add_field(
            name="👩‍👧 本次選擇媽咪",
            value=f"**{selected_mommy}**",
            inline=True
        )

        embed.add_field(
            name="🎭 本次選擇角色",
            value=f"**{selected_role}**",
            inline=True
        )

        embed.add_field(
            name="👤 本次選擇考生",
            value=f"**{selected_candidates}**",
            inline=True
        )

        embed.add_field(
            name="📝 本次考試題數",
            value=f"**{selected_question_count}**",
            inline=True
        )

        return embed

    def refresh_items(self):
        self.clear_items()

        self.add_item(
            ExamMommySelect(self)
        )

        self.add_item(
            ExamRoleSelect(self)
        )

        self.add_item(
            ExamCandidateSelect(self)
        )

        self.add_item(
            ExamQuestionCountSelect(self)
        )

        save_button = Button(
            label="儲存設定",
            emoji="💾",
            style=discord.ButtonStyle.success,
            row=4,
            disabled=not is_setup_window()
        )

        view_button = Button(
            label="查看本輪設定",
            emoji="📋",
            style=discord.ButtonStyle.primary,
            row=4
        )

        reset_button = Button(
            label="重新選擇",
            emoji="🔄",
            style=discord.ButtonStyle.secondary,
            row=4
        )

        previous_button = Button(
            label="上一頁",
            emoji="⬅️",
            style=discord.ButtonStyle.secondary,
            row=4,
            disabled=self.role_page <= 0
        )

        next_button = Button(
            label="下一頁",
            emoji="➡️",
            style=discord.ButtonStyle.secondary,
            row=4,
            disabled=not self.has_next_role_page()
        )

        save_button.callback = self.save_settings
        view_button.callback = self.view_assignments
        reset_button.callback = self.reset_selection
        previous_button.callback = self.previous_role_page
        next_button.callback = self.next_role_page

        self.add_item(save_button)
        self.add_item(view_button)
        self.add_item(previous_button)
        self.add_item(next_button)
        self.add_item(reset_button)

    def has_next_role_page(self):
        if not self.selected_mommy_id:
            return False

        roles = get_all_roles(
            self.selected_mommy_id
        )

        return (
            self.role_page + 1
            < max(
                1,
                (len(roles) + SELECT_PAGE_SIZE - 1)
                // SELECT_PAGE_SIZE
            )
        )

    async def save_settings(self, interaction):
        if not await self.check_manager(interaction):
            return

        if not is_setup_window():
            await interaction.response.send_message(
                "🔒 目前無法修改本輪設定。",
                ephemeral=True
            )
            return

        if not self.selected_mommy_id:
            await interaction.response.send_message(
                "❌ 請先選擇媽咪。",
                ephemeral=True
            )
            return

        if not self.selected_role_id:
            await interaction.response.send_message(
                "❌ 請先選擇角色。",
                ephemeral=True
            )
            return

        if not self.selected_candidate_ids:
            await interaction.response.send_message(
                "❌ 請至少選擇一位考生。",
                ephemeral=True
            )
            return

        if not self.selected_question_count:
            await interaction.response.send_message(
                "❌ 請先指定本次考試題數（5～10 題）。",
                ephemeral=True
            )
            return

        round_key = get_cycle_round_key()
        cleanup_old_rounds(round_key)

        saved = []
        skipped = []

        for user_id in self.selected_candidate_ids:
            active_session = get_active_session(
                user_id,
                round_key
            )

            if active_session:
                skipped.append(user_id)
                continue

            save_assignment(
                round_key,
                user_id,
                self.selected_mommy_id,
                self.selected_role_id,
                self.selected_question_count
            )
            saved.append(user_id)

        role = get_role(self.selected_role_id)
        role_name = (
            role["role_name"]
            if role
            else "未知角色"
        )

        lines = [
            "💾 **本次設定完成**",
            "",
            f"👩‍👧 媽咪：**{get_mommy_name(self.selected_mommy_id)}**",
            f"🎭 角色：**{role_name}**",
            f"📝 題數：**{self.selected_question_count} 題**",
            f"📅 考試月份：**{format_round(round_key)}**",
            ""
        ]

        lines.append(
            f"✅ 成功設定：**{len(saved)}** 位"
        )

        if skipped:
            lines.append(
                f"⚠️ 因正在考試而略過：**{len(skipped)}** 位"
            )

        await interaction.response.send_message(
            "\n".join(lines),
            ephemeral=True
        )

        self.selected_candidate_ids = []
        self.selected_question_count = None
        self.refresh_items()

    async def view_assignments(self, interaction):
        if not await self.check_manager(interaction):
            return

        await interaction.response.send_message(
            embed=create_assignment_list_embed(
                interaction.guild,
                get_cycle_round_key(),
                0
            ),
            view=AssignmentListView(
                interaction.guild,
                get_cycle_round_key(),
                0
            ),
            ephemeral=True
        )

    async def reset_selection(self, interaction):
        if not await self.check_manager(interaction):
            return

        self.selected_mommy_id = None
        self.selected_role_id = None
        self.selected_candidate_ids = []
        self.selected_question_count = None
        self.role_page = 0
        self.refresh_items()

        await interaction.response.edit_message(
            embed=self.create_embed(),
            view=self
        )

    async def previous_role_page(self, interaction):
        if not await self.check_manager(interaction):
            return

        if self.role_page > 0:
            self.role_page -= 1

        self.selected_role_id = None
        self.selected_candidate_ids = []
        self.selected_question_count = None
        self.refresh_items()

        await interaction.response.edit_message(
            embed=self.create_embed(),
            view=self
        )

    async def next_role_page(self, interaction):
        if not await self.check_manager(interaction):
            return

        if self.has_next_role_page():
            self.role_page += 1

        self.selected_role_id = None
        self.selected_candidate_ids = []
        self.selected_question_count = None
        self.refresh_items()

        await interaction.response.edit_message(
            embed=self.create_embed(),
            view=self
        )


# ==========================
# 📋 本輪設定查看
# ==========================

class AssignmentSelect(Select):

    def __init__(self, parent_view):
        self.parent_view = parent_view

        assignments = get_assignments(
            parent_view.round_key
        )

        start = (
            parent_view.page
            * QUESTION_DISPLAY_PAGE_SIZE
        )

        page_assignments = assignments[
            start:start + QUESTION_DISPLAY_PAGE_SIZE
        ]

        options = []

        for assignment in page_assignments:
            member = parent_view.guild.get_member(
                int(assignment["user_id"])
            )

            display_name = (
                member.display_name
                if member
                else assignment["user_id"]
            )

            role = get_role(
                int(assignment["role_id"])
            )

            role_name = (
                role["role_name"]
                if role
                else "未知角色"
            )

            options.append(
                discord.SelectOption(
                    label=display_name[:100],
                    description=f"{role_name}｜{assignment['question_count']} 題"[:100],
                    value=str(assignment["user_id"]),
                    emoji="👤"
                )
            )

        if not options:
            options.append(
                discord.SelectOption(
                    label="目前沒有設定",
                    value="none",
                    emoji="📭"
                )
            )

        super().__init__(
            placeholder="🗑️ 選擇要移除的考生設定",
            options=options,
            row=1
        )

    async def callback(self, interaction):
        if not is_exam_manager(interaction.user.id):
            await interaction.response.send_message(
                "❌ 只有六位管理層可以使用此設定。",
                ephemeral=True
            )
            return

        if self.values[0] == "none":
            await interaction.response.send_message(
                "📭 目前沒有考生設定。",
                ephemeral=True
            )
            return

        user_id = int(self.values[0])
        assignment = get_assignment(
            self.parent_view.round_key,
            user_id
        )

        if assignment is None:
            await interaction.response.send_message(
                "❌ 找不到這位考生的設定。",
                ephemeral=True
            )
            return

        active_session = get_active_session(
            user_id,
            self.parent_view.round_key
        )

        if active_session:
            await interaction.response.send_message(
                "⚠️ 這位考生目前已有進行中的考試，\n"
                "無法移除報考設定。",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "⚠️ **確定要移除這位考生的本輪報考設定嗎？**",
            view=DeleteAssignmentView(
                self.parent_view.round_key,
                user_id,
                self.parent_view
            ),
            ephemeral=True
        )


class AssignmentListView(View):

    def __init__(self, guild, round_key, page=0):
        super().__init__(timeout=None)
        self.guild = guild
        self.round_key = round_key
        self.page = page
        self.refresh_items()

    def refresh_items(self):
        self.clear_items()

        assignments = get_assignments(
            self.round_key
        )

        total_pages = max(
            1,
            (len(assignments) + QUESTION_DISPLAY_PAGE_SIZE - 1)
            // QUESTION_DISPLAY_PAGE_SIZE
        )

        self.page = max(
            0,
            min(self.page, total_pages - 1)
        )

        self.add_item(
            AssignmentSelect(self)
        )

        previous_button = Button(
            label="上一頁",
            emoji="⬅️",
            style=discord.ButtonStyle.secondary,
            row=0,
            disabled=self.page <= 0
        )

        next_button = Button(
            label="下一頁",
            emoji="➡️",
            style=discord.ButtonStyle.secondary,
            row=0,
            disabled=self.page >= total_pages - 1
        )

        previous_button.callback = self.previous_page
        next_button.callback = self.next_page

        self.add_item(previous_button)
        self.add_item(next_button)

    async def check_manager(self, interaction):
        if not is_exam_manager(interaction.user.id):
            await interaction.response.send_message(
                "❌ 只有六位管理層可以使用此設定。",
                ephemeral=True
            )
            return False
        return True

    async def previous_page(self, interaction):
        if not await self.check_manager(interaction):
            return

        if self.page > 0:
            self.page -= 1

        self.refresh_items()

        await interaction.response.edit_message(
            embed=create_assignment_list_embed(
                self.guild,
                self.round_key,
                self.page
            ),
            view=self
        )

    async def next_page(self, interaction):
        if not await self.check_manager(interaction):
            return

        assignments = get_assignments(
            self.round_key
        )

        total_pages = max(
            1,
            (len(assignments) + QUESTION_DISPLAY_PAGE_SIZE - 1)
            // QUESTION_DISPLAY_PAGE_SIZE
        )

        if self.page < total_pages - 1:
            self.page += 1

        self.refresh_items()

        await interaction.response.edit_message(
            embed=create_assignment_list_embed(
                self.guild,
                self.round_key,
                self.page
            ),
            view=self
        )


class DeleteAssignmentView(View):

    def __init__(self, round_key, user_id, parent_view):
        super().__init__(timeout=60)
        self.round_key = round_key
        self.user_id = user_id
        self.parent_view = parent_view

    @discord.ui.button(
        label="確認移除",
        emoji="🗑️",
        style=discord.ButtonStyle.danger
    )
    async def confirm(self, interaction, button):
        if not is_exam_manager(interaction.user.id):
            await interaction.response.send_message(
                "❌ 只有六位管理層可以使用此設定。",
                ephemeral=True
            )
            return

        if not is_setup_window():
            await interaction.response.edit_message(
                content="🔒 目前不是報考設定期間。",
                view=None
            )
            return

        active_session = get_active_session(
            self.user_id,
            self.round_key
        )

        if active_session:
            await interaction.response.edit_message(
                content="⚠️ 這位考生目前已有進行中的考試，無法移除。",
                view=None
            )
            return

        delete_assignment(
            self.round_key,
            self.user_id
        )

        await interaction.response.edit_message(
            content="✅ 已移除這位考生的本輪報考設定。",
            view=None
        )

    @discord.ui.button(
        label="取消",
        emoji="↩️",
        style=discord.ButtonStyle.secondary
    )
    async def cancel(self, interaction, button):
        await interaction.response.edit_message(
            content="↩️ 已取消。",
            view=None
        )


# ==========================
# 🎓 考試確認
# ==========================

class StartExamConfirmView(View):

    def __init__(self, assignment, entry_channel):
        super().__init__(timeout=180)
        self.assignment = assignment
        self.entry_channel = entry_channel

    @discord.ui.button(
        label="確認報考資料",
        emoji="✅",
        style=discord.ButtonStyle.success,
        row=0
    )
    async def confirm(self, interaction, button):
        if interaction.user.id != int(self.assignment["user_id"]):
            await interaction.response.send_message(
                "❌ 這不是你的考試確認。",
                ephemeral=True
            )
            return

        question_count = int(self.assignment["question_count"])

        await start_assigned_exam(
            interaction,
            self.assignment,
            question_count
        )

    @discord.ui.button(
        label="取消",
        emoji="❌",
        style=discord.ButtonStyle.secondary,
        row=0
    )
    async def cancel(self, interaction, button):
        await interaction.response.edit_message(
            content="↩️ 已取消本次考試。",
            embed=None,
            view=None
        )


# ==========================
# 🎓 依管理層設定開始考試
# ==========================

async def start_assigned_exam(interaction, assignment, count):
    if interaction.user.id != int(assignment["user_id"]):
        await interaction.response.send_message(
            "❌ 這不是你的考試。",
            ephemeral=True
        )
        return

    if count < EXAM_MIN_QUESTIONS or count > EXAM_MAX_QUESTIONS:
        await interaction.response.send_message(
            "❌ 考試題數設定無效，請聯絡管理層。",
            ephemeral=True
        )
        return

    round_key = assignment["round_key"]
    user_id = int(assignment["user_id"])

    existing = get_active_session(
        user_id,
        round_key
    )

    if existing:
        channel = interaction.guild.get_channel(
            int(existing["channel_id"])
        ) if interaction.guild else None

        if channel:
            await interaction.response.edit_message(
                content=(
                    "⚠️ **你目前已有一場進行中的角色考試。**\n\n"
                    f"🎓 考場：{channel.mention}"
                ),
                embed=None,
                view=None
            )
        else:
            delete_session(existing["session_id"])
            await interaction.response.edit_message(
                content="⚠️ 原本的考場已不存在，請重新按「開始考試」。",
                embed=None,
                view=None
            )
        return

    if user_id in ACTIVE_EXAM_USERS:
        await interaction.response.edit_message(
            content="⚠️ 你的考試正在建立中，請稍候。",
            embed=None,
            view=None
        )
        return

    ACTIVE_EXAM_USERS.add(user_id)

    try:
        role = get_role(
            int(assignment["role_id"])
        )

        if role is None:
            await interaction.response.edit_message(
                content="❌ 找不到你的報考角色，請聯絡管理層。",
                embed=None,
                view=None
            )
            return

        questions = draw_exam_questions(
            int(assignment["role_id"]),
            count
        )

        if not questions:
            await interaction.response.edit_message(
                content=(
                    "❌ 題庫不足，無法建立本次考試。\n\n"
                    "請管理層補充題庫後再重新開始。"
                ),
                embed=None,
                view=None
            )
            return

        await interaction.response.defer(
            ephemeral=True
        )

        channel = await create_exam_channel(
            interaction,
            assignment,
            role,
            questions
        )

        if channel is None:
            await interaction.followup.send(
                "❌ 建立考試頻道失敗，請確認 Bot 有建立頻道與管理權限。",
                ephemeral=True
            )
            return

        await interaction.followup.edit_message(
            interaction.message.id,
            content=(
                f"✅ **考試頻道已建立！**\n\n"
                f"🎓 {channel.mention}\n"
                f"📝 本次考試：**{count} 題**\n\n"
                "請進入考試頻道開始作答。"
            ),
            view=None
        )

    finally:
        ACTIVE_EXAM_USERS.discard(user_id)


# ==========================
# 📂 建立考試頻道
# ==========================

async def create_exam_channel(
    interaction,
    assignment,
    role,
    questions
):
    guild = interaction.guild

    if guild is None:
        return None

    candidate = guild.get_member(
        int(assignment["user_id"])
    )

    if candidate is None:
        return None

    category = getattr(
        interaction.channel,
        "category",
        None
    )

    safe_name = re.sub(
        r"[^a-zA-Z0-9\u4e00-\u9fff_-]+",
        "-",
        candidate.display_name
    ).strip("-")

    if not safe_name:
        safe_name = f"user-{candidate.id}"

    channel_name = (
        f"🎓-角色考試-{safe_name}"
    )[:95]

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=False
        ),
        candidate: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True
        )
    }

    for manager_id in EXAM_MANAGERS:
        manager = guild.get_member(manager_id)

        if manager:
            overwrites[manager] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

    if guild.me:
        overwrites[guild.me] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True,
            manage_permissions=True
        )

    channel = await guild.create_text_channel(
        name=channel_name,
        category=category,
        overwrites=overwrites,
        reason="🌙 建立角色考試專屬考場"
    )

    mommy_name = get_mommy_name(
        int(assignment["mommy_id"])
    )

    # ==========================
    # 📝 題目 Embed
    # ==========================

    question_message_ids = []

    chunks = [
        questions[index:index + 5]
        for index in range(0, len(questions), 5)
    ]

    for chunk_index, chunk in enumerate(chunks):
        embed = discord.Embed(
            title=(
                f"🌙 {role['role_name']}｜角色考試"
            ),
            description=(
                f"👤 **考生：** {candidate.mention}\n"
                f"👩‍👧 **媽咪：** {mommy_name}\n"
                f"📝 **本次共：** {len(questions)} 題\n\n"
                "📌 請直接在此頻道輸入答案。"
            ),
            color=discord.Color.blurple()
        )

        start_number = chunk_index * 5 + 1

        for index, question in enumerate(
            chunk,
            start=start_number
        ):
            question_text = question["question"]

            if len(question_text) > 900:
                question_text = question_text[:897] + "..."

            difficulty_emoji = (
                "🟢"
                if question["difficulty"] == "simple"
                else "🔴"
            )

            embed.add_field(
                name=f"{difficulty_emoji} 第 {index} 題",
                value=question_text,
                inline=False
            )

        embed.set_footer(
            text="🌙 Moon Bot v2｜請完成全部題目後按下「作答完成」"
        )

        message = await channel.send(
            embed=embed
        )

        question_message_ids.append(
            message.id
        )

    submit_message = await channel.send(
        embed=discord.Embed(
            title="📝 作答完成",
            description=(
                "所有題目回答完成後，請按下下方按鈕。\n\n"
                "⚠️ 送出後將無法修改，並會立即離開本考試頻道。"
            ),
            color=discord.Color.gold()
        ),
        view=SubmitExamView()
    )

    session_id = uuid.uuid4().hex

    save_session(
        session_id,
        assignment["round_key"],
        int(assignment["user_id"]),
        int(assignment["mommy_id"]),
        int(assignment["role_id"]),
        channel.id,
        questions,
        question_message_ids,
        submit_message.id
    )

    return channel


# ==========================
# 📝 作答完成按鈕
# ==========================

class SubmitExamView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="作答完成",
        emoji="📝",
        style=discord.ButtonStyle.success,
        custom_id="character_test_submit"
    )
    async def submit(self, interaction, button):
        session = get_active_session(
            interaction.user.id
        )

        if session is None:
            await interaction.response.send_message(
                "❌ 找不到你的進行中考試。",
                ephemeral=True
            )
            return

        if int(session["channel_id"]) != interaction.channel.id:
            await interaction.response.send_message(
                "❌ 這不是你的考試頻道。",
                ephemeral=True
            )
            return

        if session["status"] != "active":
            await interaction.response.send_message(
                "⚠️ 這場考試已經完成作答。",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "⚠️ **交卷前請確認**\n\n"
            "📌 請確認所有題目皆已完成作答。\n"
            "✏️ **錯字、漏字、少字將不視為正確答案。**\n"
            "📝 答案需符合題目要求，角色名稱及專有名詞請確認拼寫。\n"
            "🚫 **確認交卷後將無法修改答案。**\n"
            "🔍 交卷後將由管理層進行人工核對。\n\n"
            "⚠️ **確定要交卷嗎？**",
            view=ConfirmSubmitView(
                session["session_id"]
            ),
            ephemeral=True
        )


# ==========================
# ⚠️ 交卷確認
# ==========================

class ConfirmSubmitView(View):

    def __init__(self, session_id):
        super().__init__(timeout=60)
        self.session_id = session_id

    @discord.ui.button(
        label="確認交卷",
        emoji="✅",
        style=discord.ButtonStyle.danger
    )
    async def confirm(self, interaction, button):
        session = get_active_session(
            interaction.user.id
        )

        if session is None or session["session_id"] != self.session_id:
            await interaction.response.edit_message(
                content="❌ 找不到這場考試。",
                view=None
            )
            return

        channel = interaction.guild.get_channel(
            int(session["channel_id"])
        )

        if channel is None:
            delete_session(self.session_id)
            await interaction.response.edit_message(
                content="❌ 考試頻道已不存在。",
                view=None
            )
            return

        mark_session_submitted(
            self.session_id
        )

        question_data = json.loads(
            session["question_data"]
        )

        message_ids = json.loads(
            session["question_message_ids"]
        )

        # -------------------------
        # 🚪 先移除考生權限
        # -------------------------

        candidate = interaction.guild.get_member(
            interaction.user.id
        )

        if candidate:
            await channel.set_permissions(
                candidate,
                view_channel=False,
                send_messages=False,
                read_message_history=False
            )

        # -------------------------
        # 📖 自動顯示標準答案
        # -------------------------

        for message_id in message_ids:
            try:
                message = await channel.fetch_message(
                    int(message_id)
                )

                embed = message.embeds[0]
                embed.clear_fields()

                # 重新依照原本每 5 題一則訊息分組
                message_index = message_ids.index(
                    message_id
                )

                chunk = question_data[
                    message_index * 5:
                    message_index * 5 + 5
                ]

                start_number = message_index * 5 + 1

                for index, question in enumerate(
                    chunk,
                    start=start_number
                ):
                    embed.add_field(
                        name=(
                            f"{'🟢' if question['difficulty'] == 'simple' else '🔴'} "
                            f"第 {index} 題"
                        ),
                        value=(
                            f"📝 **問題：**\n"
                            f"{question['question']}\n\n"
                            f"📖 **標準答案：**\n"
                            f"{question['answer']}"
                        ),
                        inline=False
                    )

                embed.description = (
                    "👑 **考生已完成作答**\n\n"
                    "🔍 請管理層人工核對考生答案。"
                )
                embed.color = discord.Color.green()
                embed.set_footer(
                    text="🌙 Moon Bot v2｜人工核對完成後可關閉考試頻道"
                )

                await message.edit(
                    embed=embed
                )

            except discord.NotFound:
                continue

        # -------------------------
        # 🗑️ 管理層關閉考場
        # -------------------------

        await channel.send(
            embed=discord.Embed(
                title="🔍 人工核對",
                description=(
                    "考生已完成作答並離開考試頻道。\n\n"
                    "👑 請管理層核對考生答案。\n"
                    "確認完成後即可關閉本考試頻道。"
                ),
                color=discord.Color.orange()
            ),
            view=CloseExamView(
                self.session_id
            )
        )

        await interaction.response.edit_message(
            content="✅ **作答完成！**\n\n"
                    "你已離開本次考試頻道。",
            view=None
        )

    @discord.ui.button(
        label="返回考試",
        emoji="↩️",
        style=discord.ButtonStyle.secondary
    )
    async def cancel(self, interaction, button):
        await interaction.response.edit_message(
            content="↩️ 已取消交卷，你可以繼續修改答案。",
            view=None
        )


# ==========================
# 🗑️ 關閉考試頻道
# ==========================

class CloseExamView(View):

    def __init__(self, session_id):
        super().__init__(timeout=None)
        self.session_id = session_id

    @discord.ui.button(
        label="關閉考試頻道",
        emoji="🗑️",
        style=discord.ButtonStyle.danger,
        custom_id="character_test_close"
    )
    async def close(self, interaction, button):
        if not is_exam_manager(interaction.user.id):
            await interaction.response.send_message(
                "❌ 只有六位管理層可以關閉考試頻道。",
                ephemeral=True
            )
            return

        session = get_session_by_id(
            self.session_id
        )

        if session is None:
            await interaction.response.send_message(
                "❌ 找不到這場考試。",
                ephemeral=True
            )
            return

        if session["status"] != "submitted":
            await interaction.response.send_message(
                "⚠️ 考生尚未完成作答，暫時不能關閉考試頻道。",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "⚠️ **確定要關閉本次考試頻道嗎？**\n\n"
            "關閉後頻道將永久刪除。",
            view=ConfirmCloseExamView(
                self.session_id
            ),
            ephemeral=True
        )


class ConfirmCloseExamView(View):

    def __init__(self, session_id):
        super().__init__(timeout=60)
        self.session_id = session_id

    @discord.ui.button(
        label="確認關閉",
        emoji="🗑️",
        style=discord.ButtonStyle.danger
    )
    async def confirm(self, interaction, button):
        if not is_exam_manager(interaction.user.id):
            await interaction.response.send_message(
                "❌ 只有六位管理層可以關閉考試頻道。",
                ephemeral=True
            )
            return

        session = get_session_by_id(
            self.session_id
        )

        if session is None:
            await interaction.response.edit_message(
                content="❌ 這場考試已不存在。",
                view=None
            )
            return

        channel = interaction.guild.get_channel(
            int(session["channel_id"])
        )

        delete_session(
            self.session_id
        )

        if channel:
            await channel.delete(
                reason="🌙 角色考試人工核對完成，關閉考場"
            )

        await interaction.response.edit_message(
            content="✅ 考試頻道已關閉並永久刪除。",
            view=None
        )

    @discord.ui.button(
        label="取消",
        emoji="↩️",
        style=discord.ButtonStyle.secondary
    )
    async def cancel(self, interaction, button):
        await interaction.response.edit_message(
            content="↩️ 已取消關閉。",
            view=None
        )


# ==========================
# 🔎 Session 查詢
# ==========================

def get_session_by_id(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM character_test_sessions
        WHERE session_id = ?
    """, (session_id,))

    session = cursor.fetchone()
    conn.close()
    return session


# ==========================
# 🎓 考試入口 Embed
# ==========================

def create_exam_entry_embed():
    return discord.Embed(
        title="🎓 角色考試入口",
        description=(
            "歡迎來到 **Moon Bot｜角色考試**。\n\n"
            "🎭 系統會自動取得管理層事前綁定的報考角色。\n"
            "📝 考試題數由管理層事前指定（5～10 題）。\n"
            "🎲 題目由系統隨機抽取。\n"
            "✏️ 所有題目皆為簡答題，請直接在考試頻道作答。\n\n"
            "⚠️ 考生不能自行選擇角色。\n"
            "⚠️ 同一時間只能有一場進行中的考試。"
        ),
        color=discord.Color.blurple()
    )


# ==========================
# 🎓 考試入口 View
# ==========================

class ExamEntryView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="開始考試",
        emoji="🎓",
        style=discord.ButtonStyle.success,
        custom_id="character_test_start_exam"
    )
    async def start(self, interaction, button):
        round_key = get_cycle_round_key()

        assignment = get_assignment(
            round_key,
            interaction.user.id
        )

        if assignment is None:
            await interaction.response.send_message(
                "❌ 目前找不到你的本月報考資料。\n\n"
                "請聯絡六位管理層確認你是否已完成報考設定。",
                ephemeral=True
            )
            return

        existing = get_active_session(
            interaction.user.id,
            round_key
        )

        if existing:
            channel = interaction.guild.get_channel(
                int(existing["channel_id"])
            )

            if channel:
                await interaction.response.send_message(
                    "⚠️ 你目前已有一場進行中的角色考試。\n\n"
                    f"🎓 考場：{channel.mention}",
                    ephemeral=True
                )
                return

            delete_session(
                existing["session_id"]
            )

        role = get_role(
            int(assignment["role_id"])
        )

        if role is None:
            await interaction.response.send_message(
                "❌ 找不到你的報考角色，請聯絡管理層。",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            embed=discord.Embed(
                title="🎓 角色考試｜報考資料確認",
                description=(
                    "📋 系統已取得你的報考資料。\n\n"
                    f"👤 **考生：** {interaction.user.display_name}\n"
                    f"👩‍👧 **媽咪：** {get_mommy_name(int(assignment['mommy_id']))}\n"
                    f"🎭 **報考角色：** {role['role_name']}\n\n"
                    "⚠️ 請確認以上資料正確。\n"
                    "確認後才會建立你的專屬考試頻道。"
                ),
                color=discord.Color.blurple()
            ),
            view=StartExamConfirmView(
                assignment,
                interaction.channel
            ),
            ephemeral=True
        )


# ==========================
# 📝 啟動系統
# ==========================

def setup_character_test(bot):
    global _SETUP_DONE

    init_character_test_database()

    if _SETUP_DONE:
        return

    _SETUP_DONE = True
    
    # 🎓 永久註冊角色考試入口按鈕
    bot.add_view(ExamEntryView())

    # ==========================
    # 🎓 /角色考試設定
    # ==========================

    @bot.tree.command(
        name="考試設定",
        description="🎓 管理本輪媽咪、角色、考生與考試題數"
    )
    async def character_test_setup(interaction: discord.Interaction):
        if not is_exam_manager(interaction.user.id):
            await interaction.response.send_message(
                "❌ 只有六位管理層可以使用此指令。",
                ephemeral=True
            )
            return

        round_key = get_cycle_round_key()

        # 20 號開始新一輪時清除舊月份資料
        if datetime.now(TIMEZONE).day >= 20:
            cleanup_old_rounds(round_key)

        await interaction.response.send_message(
            embed=create_setup_embed(round_key),
            view=ExamSetupView(
                interaction.user.id
            ),
            ephemeral=True
        )

    # ==========================
    # 🎓 /角色考試
    # ==========================

    @bot.tree.command(
        name="角色考試",
        description="🎓 開啟角色考試入口"
    )
    async def character_test_entry(interaction: discord.Interaction):

        # 🔐 只有 6 位管理層可以使用
        if not is_exam_manager(interaction.user.id):
            await interaction.response.send_message(
                "❌ 你沒有權限使用此指令。",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            embed=create_exam_entry_embed(),
            view=ExamEntryView()
        )
 