# ==========================
# 🌙 Moon Bot v2｜角色考試系統
# 📝 指令 1｜/考試角色設定
# ==========================

import discord
from discord import app_commands
from discord.ui import View, Button, Select, Modal, TextInput

import sqlite3
from datetime import datetime
import pytz

from config import MOMMY_LIST
from database import DB_PATH


# ==========================
# 🌙 基本設定
# ==========================

TIMEZONE = pytz.timezone("Asia/Taipei")

# /考試角色設定 限定頻道
CHARACTER_EXAM_CHANNEL_ID = 1540572450218320013

# Discord Select 最多 25 個選項
SELECT_PAGE_SIZE = 25

# 題庫查看時每頁顯示的題目數
QUESTION_DISPLAY_PAGE_SIZE = 10


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


def init_character_exam_database():

    conn = get_db_connection()
    cursor = conn.cursor()

    # ==========================
    # 🎭 角色資料表
    # ==========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS character_exam_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mommy_id TEXT NOT NULL,
            role_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(mommy_id, role_name)
        )
    """)

    # ==========================
    # 📝 題庫資料表
    # ==========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS character_exam_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role_id INTEGER NOT NULL,
            difficulty TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(role_id)
                REFERENCES character_exam_roles(id)
                ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


# ==========================
# 👑 權限
# ==========================

def is_mommy(user_id: int) -> bool:
    return user_id in MOMMY_LIST


def get_mommy_name(user_id: int):
    return MOMMY_LIST.get(user_id)


def is_owner(interaction: discord.Interaction, mommy_id: int) -> bool:
    return interaction.user.id == mommy_id


async def reject_not_owner(interaction: discord.Interaction):
    await interaction.response.send_message(
        "❌ 這個管理介面只屬於原本開啟它的媽咪。",
        ephemeral=True
    )


# ==========================
# 🕐 時間
# ==========================

def get_now():

    return datetime.now(
        TIMEZONE
    ).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# ==========================
# 🎭 角色資料
# ==========================

def get_mommy_roles(mommy_id: int):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM character_exam_roles
        WHERE mommy_id = ?
        ORDER BY id ASC
        """,
        (str(mommy_id),)
    )

    roles = cursor.fetchall()
    conn.close()

    return roles


def get_role(role_id: int, mommy_id: int):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM character_exam_roles
        WHERE id = ?
        AND mommy_id = ?
        """,
        (
            role_id,
            str(mommy_id)
        )
    )

    role = cursor.fetchone()
    conn.close()

    return role


# ==========================
# 📝 題目資料
# ==========================

def get_role_questions(
    role_id: int,
    difficulty: str = None
):

    conn = get_db_connection()
    cursor = conn.cursor()

    if difficulty:

        cursor.execute(
            """
            SELECT *
            FROM character_exam_questions
            WHERE role_id = ?
            AND difficulty = ?
            ORDER BY id ASC
            """,
            (
                role_id,
                difficulty
            )
        )

    else:

        cursor.execute(
            """
            SELECT *
            FROM character_exam_questions
            WHERE role_id = ?
            ORDER BY id ASC
            """,
            (role_id,)
        )

    questions = cursor.fetchall()
    conn.close()

    return questions


def get_question(
    question_id: int,
    role_id: int
):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM character_exam_questions
        WHERE id = ?
        AND role_id = ?
        """,
        (
            question_id,
            role_id
        )
    )

    question = cursor.fetchone()
    conn.close()

    return question


# ==========================
# 🌙 主畫面 Embed
# ==========================

def create_main_embed(mommy_id: int):

    mommy_name = get_mommy_name(mommy_id)
    roles = get_mommy_roles(mommy_id)

    embed = discord.Embed(
        title="🌙 角色考試設定",
        description=(
            f"👑 管理媽咪：**{mommy_name}**\n\n"
            "這裡是你的角色考試題庫管理中心。\n\n"
            "🎭 **角色管理**\n"
            "你只能管理自己建立的角色。\n\n"
            "📝 **題庫管理**\n"
            "每個角色可以建立：\n"
            "🟢 簡單題\n"
            "🔴 困難題\n\n"
            "🔐 其他媽咪的角色與題庫無法管理。"
        ),
        color=discord.Color.blurple()
    )

    total_questions = 0

    for role in roles:
        total_questions += len(get_role_questions(role["id"]))

    embed.add_field(
        name="🎭 目前角色",
        value=f"**{len(roles)}** 隻",
        inline=True
    )

    embed.add_field(
        name="📚 題庫總數",
        value=f"**{total_questions}** 題",
        inline=True
    )

    embed.set_footer(
        text="🌙 Moon Bot v2｜角色考試系統"
    )

    return embed


# ==========================
# ➕ 新增角色 Modal
# ==========================

class AddCharacterModal(
    Modal,
    title="➕ 新增角色"
):

    role_name = TextInput(
        label="🎭 角色名稱",
        placeholder="例如：小月牙",
        required=True,
        max_length=50
    )

    def __init__(self, mommy_id: int):

        super().__init__()
        self.mommy_id = mommy_id

    async def on_submit(self, interaction: discord.Interaction):

        if not is_owner(interaction, self.mommy_id):
            await reject_not_owner(interaction)
            return

        role_name = self.role_name.value.strip()

        if not role_name:
            await interaction.response.send_message(
                "❌ 角色名稱不能為空。",
                ephemeral=True
            )
            return

        conn = get_db_connection()
        cursor = conn.cursor()

        try:

            now = get_now()

            cursor.execute(
                """
                INSERT INTO character_exam_roles
                (
                    mommy_id,
                    role_name,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    str(self.mommy_id),
                    role_name,
                    now,
                    now
                )
            )

            conn.commit()

        except sqlite3.IntegrityError:

            conn.close()

            await interaction.response.send_message(
                f"❌ 你已經有一隻名為 **{role_name}** 的角色。",
                ephemeral=True
            )
            return

        conn.close()

        embed = discord.Embed(
            title="🎭 角色建立成功",
            description=(
                f"✨ 已成功建立角色：\n\n"
                f"🎭 **{role_name}**\n\n"
                "接下來可以開始建立這隻角色的考試題庫。"
            ),
            color=discord.Color.green()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


# ==========================
# 🎭 角色選擇 Select
# ==========================

class CharacterSelect(Select):

    def __init__(
        self,
        mommy_id: int,
        page: int = 0
    ):

        self.mommy_id = mommy_id
        self.page = page

        roles = get_mommy_roles(mommy_id)
        start = page * SELECT_PAGE_SIZE
        page_roles = roles[start:start + SELECT_PAGE_SIZE]

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
                    label="目前沒有角色",
                    value="none",
                    emoji="📭"
                )
            )

        super().__init__(
            placeholder="🎭 選擇要管理的角色",
            options=options,
            row=0
        )

    async def callback(self, interaction: discord.Interaction):

        if not is_owner(interaction, self.mommy_id):
            await reject_not_owner(interaction)
            return

        if self.values[0] == "none":
            await interaction.response.send_message(
                "📭 目前還沒有建立任何角色。",
                ephemeral=True
            )
            return

        role_id = int(self.values[0])

        role = get_role(
            role_id,
            self.mommy_id
        )

        if role is None:
            await interaction.response.send_message(
                "❌ 找不到這隻角色，或你沒有管理權限。",
                ephemeral=True
            )
            return

        embed = create_role_manage_embed(role)

        await interaction.response.send_message(
            embed=embed,
            view=RoleManageView(
                self.mommy_id,
                role_id
            ),
            ephemeral=True
        )


# ==========================
# 🎭 角色選擇 View
# ==========================

class CharacterSelectView(View):

    def __init__(
        self,
        mommy_id: int,
        page: int = 0
    ):

        super().__init__(timeout=300)

        self.mommy_id = mommy_id
        self.page = page
        self.refresh_items()

    def refresh_items(self):

        self.clear_items()

        roles = get_mommy_roles(self.mommy_id)
        total_pages = max(
            1,
            (len(roles) + SELECT_PAGE_SIZE - 1)
            // SELECT_PAGE_SIZE
        )

        if self.page >= total_pages:
            self.page = total_pages - 1

        self.add_item(
            CharacterSelect(
                self.mommy_id,
                self.page
            )
        )

        previous_button = Button(
            label="上一頁",
            emoji="⬅️",
            style=discord.ButtonStyle.secondary,
            disabled=self.page <= 0,
            row=1
        )

        next_button = Button(
            label="下一頁",
            emoji="➡️",
            style=discord.ButtonStyle.secondary,
            disabled=self.page >= total_pages - 1,
            row=1
        )

        previous_button.callback = self.previous_page
        next_button.callback = self.next_page

        self.add_item(previous_button)
        self.add_item(next_button)

    async def previous_page(self, interaction: discord.Interaction):

        if not is_owner(interaction, self.mommy_id):
            await reject_not_owner(interaction)
            return

        if self.page > 0:
            self.page -= 1

        self.refresh_items()

        await interaction.response.edit_message(
            content="🎭 請選擇要管理的角色：",
            view=self
        )

    async def next_page(self, interaction: discord.Interaction):

        if not is_owner(interaction, self.mommy_id):
            await reject_not_owner(interaction)
            return

        roles = get_mommy_roles(self.mommy_id)
        total_pages = max(
            1,
            (len(roles) + SELECT_PAGE_SIZE - 1)
            // SELECT_PAGE_SIZE
        )

        if self.page < total_pages - 1:
            self.page += 1

        self.refresh_items()

        await interaction.response.edit_message(
            content="🎭 請選擇要管理的角色：",
            view=self
        )


# ==========================
# 🎭 角色管理 Embed
# ==========================

def create_role_manage_embed(role):

    simple_questions = get_role_questions(
        role["id"],
        "simple"
    )

    hard_questions = get_role_questions(
        role["id"],
        "hard"
    )

    embed = discord.Embed(
        title="🎭 角色題庫管理",
        description=(
            f"目前角色：**{role['role_name']}**\n\n"
            "請選擇要進行的操作。"
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🟢 簡單題",
        value=f"目前 **{len(simple_questions)}** 題",
        inline=True
    )

    embed.add_field(
        name="🔴 困難題",
        value=f"目前 **{len(hard_questions)}** 題",
        inline=True
    )

    embed.add_field(
        name="📚 題庫說明",
        value=(
            "每道題目皆為簡答題，並保存標準答案。\n"
            "🔴 困難題不是必要項目。"
        ),
        inline=False
    )

    embed.set_footer(
        text="🌙 Moon Bot v2｜角色考試系統"
    )

    return embed


# ==========================
# 🎭 角色管理 View
# ==========================

class RoleManageView(View):

    def __init__(
        self,
        mommy_id: int,
        role_id: int
    ):

        super().__init__(timeout=300)
        self.mommy_id = mommy_id
        self.role_id = role_id

    async def check_owner(self, interaction):
        if not is_owner(interaction, self.mommy_id):
            await reject_not_owner(interaction)
            return False
        return True

    # ==========================
    # 🟢 簡單題
    # ==========================

    @discord.ui.button(
        label="簡單題",
        emoji="🟢",
        style=discord.ButtonStyle.success,
        row=0
    )
    async def simple_questions(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        if not await self.check_owner(interaction):
            return

        await interaction.response.send_message(
            embed=discord.Embed(
                title="🟢 簡單題",
                description="請選擇要進行的操作。",
                color=discord.Color.green()
            ),
            view=QuestionManageView(
                self.mommy_id,
                self.role_id,
                "simple"
            ),
            ephemeral=True
        )

    # ==========================
    # 🔴 困難題
    # ==========================

    @discord.ui.button(
        label="困難題",
        emoji="🔴",
        style=discord.ButtonStyle.danger,
        row=0
    )
    async def hard_questions(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        if not await self.check_owner(interaction):
            return

        await interaction.response.send_message(
            embed=discord.Embed(
                title="🔴 困難題",
                description=(
                    "請選擇要進行的操作。\n\n"
                    "⚠️ 困難題不是必要項目。"
                ),
                color=discord.Color.red()
            ),
            view=QuestionManageView(
                self.mommy_id,
                self.role_id,
                "hard"
            ),
            ephemeral=True
        )

    # ==========================
    # 📋 查看題庫
    # ==========================

    @discord.ui.button(
        label="查看全部題目",
        emoji="📋",
        style=discord.ButtonStyle.primary,
        row=1
    )
    async def view_all_questions(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        if not await self.check_owner(interaction):
            return

        await show_question_list(
            interaction,
            self.mommy_id,
            self.role_id
        )


# ==========================
# 📝 題庫管理 View
# ==========================

class QuestionManageView(View):

    def __init__(
        self,
        mommy_id: int,
        role_id: int,
        difficulty: str
    ):

        super().__init__(timeout=300)
        self.mommy_id = mommy_id
        self.role_id = role_id
        self.difficulty = difficulty

    async def check_owner(self, interaction):
        if not is_owner(interaction, self.mommy_id):
            await reject_not_owner(interaction)
            return False
        return True

    # ==========================
    # ➕ 批量新增
    # ==========================

    @discord.ui.button(
        label="批量新增題目",
        emoji="➕",
        style=discord.ButtonStyle.success,
        row=0
    )
    async def add_questions(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        if not await self.check_owner(interaction):
            return

        await interaction.response.send_modal(
            AddQuestionsModal(
                self.mommy_id,
                self.role_id,
                self.difficulty
            )
        )

    # ==========================
    # 📋 查看
    # ==========================

    @discord.ui.button(
        label="查看題目",
        emoji="📋",
        style=discord.ButtonStyle.primary,
        row=0
    )
    async def view_questions(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        if not await self.check_owner(interaction):
            return

        await show_question_list(
            interaction,
            self.mommy_id,
            self.role_id,
            self.difficulty
        )

    # ==========================
    # ✏️ 修改
    # ==========================

    @discord.ui.button(
        label="修改題目",
        emoji="✏️",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def edit_questions(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        if not await self.check_owner(interaction):
            return

        questions = get_role_questions(
            self.role_id,
            self.difficulty
        )

        if not questions:
            await interaction.response.send_message(
                "📭 目前沒有題目可以修改。",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "✏️ 請選擇要修改的題目：",
            view=QuestionSelectView(
                self.mommy_id,
                self.role_id,
                self.difficulty,
                "edit"
            ),
            ephemeral=True
        )

    # ==========================
    # 🗑️ 刪除
    # ==========================

    @discord.ui.button(
        label="刪除題目",
        emoji="🗑️",
        style=discord.ButtonStyle.danger,
        row=1
    )
    async def delete_questions(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        if not await self.check_owner(interaction):
            return

        questions = get_role_questions(
            self.role_id,
            self.difficulty
        )

        if not questions:
            await interaction.response.send_message(
                "📭 目前沒有題目可以刪除。",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🗑️ 請選擇要刪除的題目：",
            view=QuestionSelectView(
                self.mommy_id,
                self.role_id,
                self.difficulty,
                "delete"
            ),
            ephemeral=True
        )


# ==========================
# ➕ 批量新增題目 Modal
# ==========================

class AddQuestionsModal(
    Modal,
    title="➕ 批量新增簡答題"
):

    questions = TextInput(
        label="📝 題目與標準答案",
        placeholder=(
            "每一行一題，格式：\n"
            "問題｜標準答案\n"
            "例如：小月牙的生日？｜6月16日\n"
        ),
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=4000
    )

    def __init__(
        self,
        mommy_id: int,
        role_id: int,
        difficulty: str
    ):

        super().__init__()
        self.mommy_id = mommy_id
        self.role_id = role_id
        self.difficulty = difficulty

    async def on_submit(self, interaction: discord.Interaction):

        if not is_owner(interaction, self.mommy_id):
            await reject_not_owner(interaction)
            return

        if get_role(self.role_id, self.mommy_id) is None:
            await interaction.response.send_message(
                "❌ 找不到這隻角色，或你沒有管理權限。",
                ephemeral=True
            )
            return

        raw_text = self.questions.value.strip()

        lines = [
            line.strip()
            for line in raw_text.splitlines()
            if line.strip()
        ]

        if not lines:
            await interaction.response.send_message(
                "❌ 沒有偵測到任何題目。",
                ephemeral=True
            )
            return

        parsed_questions = []
        invalid_lines = []

        for index, line in enumerate(lines, start=1):

            if "｜" not in line:
                invalid_lines.append(f"第 {index} 行")
                continue

            question, answer = line.split("｜", 1)
            question = question.strip()
            answer = answer.strip()

            if not question or not answer:
                invalid_lines.append(f"第 {index} 行")
                continue

            parsed_questions.append((question, answer))

        if invalid_lines:
            await interaction.response.send_message(
                "❌ 以下內容格式錯誤：\n\n"
                + "\n".join(invalid_lines)
                + "\n\n"
                "請使用：\n"
                "**問題｜標準答案**",
                ephemeral=True
            )
            return

        if not parsed_questions:
            await interaction.response.send_message(
                "❌ 沒有可以儲存的有效題目。",
                ephemeral=True
            )
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        now = get_now()

        for question, answer in parsed_questions:
            cursor.execute(
                """
                INSERT INTO character_exam_questions
                (
                    role_id,
                    difficulty,
                    question,
                    answer,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    self.role_id,
                    self.difficulty,
                    question,
                    answer,
                    now,
                    now
                )
            )

        cursor.execute(
            """
            UPDATE character_exam_roles
            SET updated_at = ?
            WHERE id = ?
            AND mommy_id = ?
            """,
            (
                now,
                self.role_id,
                str(self.mommy_id)
            )
        )

        conn.commit()
        conn.close()

        difficulty_name = (
            "🟢 簡單題"
            if self.difficulty == "simple"
            else "🔴 困難題"
        )

        embed = discord.Embed(
            title="✅ 題庫新增成功",
            description=(
                f"{difficulty_name}\n\n"
                f"本次成功新增 **{len(parsed_questions)}** 題。"
            ),
            color=discord.Color.green()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


# ==========================
# 📋 題目選擇 Select
# ==========================

class QuestionSelect(Select):

    def __init__(
        self,
        mommy_id: int,
        role_id: int,
        difficulty: str,
        action: str,
        page: int = 0
    ):

        self.mommy_id = mommy_id
        self.role_id = role_id
        self.difficulty = difficulty
        self.action = action
        self.page = page

        questions = get_role_questions(
            role_id,
            difficulty
        )

        start = page * SELECT_PAGE_SIZE
        page_questions = questions[
            start:start + SELECT_PAGE_SIZE
        ]

        options = []

        for question in page_questions:

            question_text = question["question"]

            if len(question_text) > 90:
                question_text = question_text[:87] + "..."

            options.append(
                discord.SelectOption(
                    label=question_text,
                    value=str(question["id"]),
                    emoji="📝"
                )
            )

        if not options:
            options.append(
                discord.SelectOption(
                    label="目前沒有題目",
                    value="none",
                    emoji="📭"
                )
            )

        super().__init__(
            placeholder="📝 選擇題目",
            options=options,
            row=0
        )

    async def callback(self, interaction: discord.Interaction):

        if not is_owner(interaction, self.mommy_id):
            await reject_not_owner(interaction)
            return

        if self.values[0] == "none":
            await interaction.response.send_message(
                "📭 目前沒有題目。",
                ephemeral=True
            )
            return

        question_id = int(self.values[0])

        question = get_question(
            question_id,
            self.role_id
        )

        if question is None:
            await interaction.response.send_message(
                "❌ 找不到這道題目。",
                ephemeral=True
            )
            return

        if self.action == "edit":

            await interaction.response.send_modal(
                EditQuestionModal(
                    self.mommy_id,
                    self.role_id,
                    question
                )
            )

        elif self.action == "delete":

            await interaction.response.send_message(
                embed=discord.Embed(
                    title="🗑️ 確認刪除題目",
                    description=(
                        f"📝 **題目：**\n"
                        f"{question['question']}\n\n"
                        f"📖 **標準答案：**\n"
                        f"{question['answer']}\n\n"
                        "⚠️ 確定要永久刪除這道題目嗎？"
                    ),
                    color=discord.Color.red()
                ),
                view=DeleteQuestionConfirmView(
                    self.mommy_id,
                    self.role_id,
                    question_id
                ),
                ephemeral=True
            )


# ==========================
# 📝 題目選擇 View
# ==========================

class QuestionSelectView(View):

    def __init__(
        self,
        mommy_id: int,
        role_id: int,
        difficulty: str,
        action: str,
        page: int = 0
    ):

        super().__init__(timeout=300)
        self.mommy_id = mommy_id
        self.role_id = role_id
        self.difficulty = difficulty
        self.action = action
        self.page = page
        self.refresh_items()

    def refresh_items(self):

        self.clear_items()

        questions = get_role_questions(
            self.role_id,
            self.difficulty
        )

        total_pages = max(
            1,
            (len(questions) + SELECT_PAGE_SIZE - 1)
            // SELECT_PAGE_SIZE
        )

        if self.page >= total_pages:
            self.page = total_pages - 1

        self.add_item(
            QuestionSelect(
                self.mommy_id,
                self.role_id,
                self.difficulty,
                self.action,
                self.page
            )
        )

        previous_button = Button(
            label="上一頁",
            emoji="⬅️",
            style=discord.ButtonStyle.secondary,
            disabled=self.page <= 0,
            row=1
        )

        next_button = Button(
            label="下一頁",
            emoji="➡️",
            style=discord.ButtonStyle.secondary,
            disabled=self.page >= total_pages - 1,
            row=1
        )

        previous_button.callback = self.previous_page
        next_button.callback = self.next_page

        self.add_item(previous_button)
        self.add_item(next_button)

    async def previous_page(self, interaction: discord.Interaction):

        if not is_owner(interaction, self.mommy_id):
            await reject_not_owner(interaction)
            return

        if self.page > 0:
            self.page -= 1

        self.refresh_items()

        await interaction.response.edit_message(
            content="📝 請選擇題目：",
            view=self
        )

    async def next_page(self, interaction: discord.Interaction):

        if not is_owner(interaction, self.mommy_id):
            await reject_not_owner(interaction)
            return

        questions = get_role_questions(
            self.role_id,
            self.difficulty
        )

        total_pages = max(
            1,
            (len(questions) + SELECT_PAGE_SIZE - 1)
            // SELECT_PAGE_SIZE
        )

        if self.page < total_pages - 1:
            self.page += 1

        self.refresh_items()

        await interaction.response.edit_message(
            content="📝 請選擇題目：",
            view=self
        )


# ==========================
# ✏️ 修改題目 Modal
# ==========================

class EditQuestionModal(
    Modal,
    title="✏️ 修改考試題目"
):

    question_text = TextInput(
        label="📝 題目",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )

    answer_text = TextInput(
        label="📖 標準答案",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    def __init__(
        self,
        mommy_id: int,
        role_id: int,
        question
    ):

        super().__init__()
        self.mommy_id = mommy_id
        self.role_id = role_id
        self.question_id = question["id"]

        self.question_text.default = question["question"]
        self.answer_text.default = question["answer"]

    async def on_submit(self, interaction: discord.Interaction):

        if not is_owner(interaction, self.mommy_id):
            await reject_not_owner(interaction)
            return

        question = get_question(
            self.question_id,
            self.role_id
        )

        if question is None:
            await interaction.response.send_message(
                "❌ 找不到這道題目。",
                ephemeral=True
            )
            return

        new_question = self.question_text.value.strip()
        new_answer = self.answer_text.value.strip()

        if not new_question or not new_answer:
            await interaction.response.send_message(
                "❌ 題目與標準答案都不能為空。",
                ephemeral=True
            )
            return

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE character_exam_questions
            SET question = ?,
                answer = ?,
                updated_at = ?
            WHERE id = ?
            AND role_id = ?
            """,
            (
                new_question,
                new_answer,
                get_now(),
                self.question_id,
                self.role_id
            )
        )

        conn.commit()
        conn.close()

        await interaction.response.send_message(
            embed=discord.Embed(
                title="✏️ 題目內容已更新",
                description=(
                    "題目與標準答案已成功修改。\n\n"
                    "接下來可以選擇是否修改題目難度。"
                ),
                color=discord.Color.blurple()
            ),
            view=EditQuestionDifficultyView(
                self.mommy_id,
                self.role_id,
                self.question_id
            ),
            ephemeral=True
        )


# ==========================
# ✏️ 修改難度
# ==========================

class EditQuestionDifficultySelect(Select):

    def __init__(
        self,
        mommy_id: int,
        role_id: int,
        question_id: int
    ):

        self.mommy_id = mommy_id
        self.role_id = role_id
        self.question_id = question_id

        super().__init__(
            placeholder="🧩 選擇新的題目難度",
            options=[
                discord.SelectOption(
                    label="簡單題",
                    value="simple",
                    emoji="🟢"
                ),
                discord.SelectOption(
                    label="困難題",
                    value="hard",
                    emoji="🔴"
                )
            ]
        )

    async def callback(self, interaction: discord.Interaction):

        if not is_owner(interaction, self.mommy_id):
            await reject_not_owner(interaction)
            return

        new_difficulty = self.values[0]

        question = get_question(
            self.question_id,
            self.role_id
        )

        if question is None:
            await interaction.response.send_message(
                "❌ 找不到這道題目。",
                ephemeral=True
            )
            return

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE character_exam_questions
            SET difficulty = ?,
                updated_at = ?
            WHERE id = ?
            AND role_id = ?
            """,
            (
                new_difficulty,
                get_now(),
                self.question_id,
                self.role_id
            )
        )

        conn.commit()
        conn.close()

        difficulty_name = (
            "🟢 簡單題"
            if new_difficulty == "simple"
            else "🔴 困難題"
        )

        await interaction.response.edit_message(
            content=f"✅ 題目難度已修改為 **{difficulty_name}**。",
            embed=None,
            view=None
        )


class EditQuestionDifficultyView(View):

    def __init__(
        self,
        mommy_id: int,
        role_id: int,
        question_id: int
    ):

        super().__init__(timeout=120)

        self.mommy_id = mommy_id
        self.role_id = role_id
        self.question_id = question_id

        self.add_item(
            EditQuestionDifficultySelect(
                mommy_id,
                role_id,
                question_id
            )
        )


# ==========================
# 🗑️ 刪除確認
# ==========================

class DeleteQuestionConfirmView(View):

    def __init__(
        self,
        mommy_id: int,
        role_id: int,
        question_id: int
    ):

        super().__init__(timeout=60)
        self.mommy_id = mommy_id
        self.role_id = role_id
        self.question_id = question_id

    @discord.ui.button(
        label="確認刪除",
        emoji="🗑️",
        style=discord.ButtonStyle.danger
    )
    async def confirm_delete(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        if not is_owner(interaction, self.mommy_id):
            await reject_not_owner(interaction)
            return

        question = get_question(
            self.question_id,
            self.role_id
        )

        if question is None:
            await interaction.response.send_message(
                "❌ 這道題目已不存在。",
                ephemeral=True
            )
            return

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM character_exam_questions
            WHERE id = ?
            AND role_id = ?
            """,
            (
                self.question_id,
                self.role_id
            )
        )

        cursor.execute(
            """
            UPDATE character_exam_roles
            SET updated_at = ?
            WHERE id = ?
            AND mommy_id = ?
            """,
            (
                get_now(),
                self.role_id,
                str(self.mommy_id)
            )
        )

        conn.commit()
        conn.close()

        await interaction.response.edit_message(
            content="✅ 題目已永久刪除。",
            embed=None,
            view=None
        )

    @discord.ui.button(
        label="取消",
        emoji="↩️",
        style=discord.ButtonStyle.secondary
    )
    async def cancel_delete(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        if not is_owner(interaction, self.mommy_id):
            await reject_not_owner(interaction)
            return

        await interaction.response.edit_message(
            content="↩️ 已取消刪除。",
            embed=None,
            view=None
        )


# ==========================
# 📋 題庫查看分頁
# ==========================

class QuestionListView(View):

    def __init__(
        self,
        mommy_id: int,
        role_id: int,
        difficulty: str = None,
        page: int = 0
    ):

        super().__init__(timeout=300)
        self.mommy_id = mommy_id
        self.role_id = role_id
        self.difficulty = difficulty
        self.page = page
        self.refresh_items()

    def refresh_items(self):

        self.clear_items()

        questions = get_role_questions(
            self.role_id,
            self.difficulty
        )

        total_pages = max(
            1,
            (len(questions) + QUESTION_DISPLAY_PAGE_SIZE - 1)
            // QUESTION_DISPLAY_PAGE_SIZE
        )

        if self.page >= total_pages:
            self.page = total_pages - 1

        previous_button = Button(
            label="上一頁",
            emoji="⬅️",
            style=discord.ButtonStyle.secondary,
            disabled=self.page <= 0,
            row=0
        )

        next_button = Button(
            label="下一頁",
            emoji="➡️",
            style=discord.ButtonStyle.secondary,
            disabled=self.page >= total_pages - 1,
            row=0
        )

        previous_button.callback = self.previous_page
        next_button.callback = self.next_page

        self.add_item(previous_button)
        self.add_item(next_button)

    async def previous_page(self, interaction: discord.Interaction):

        if not is_owner(interaction, self.mommy_id):
            await reject_not_owner(interaction)
            return

        if self.page > 0:
            self.page -= 1

        self.refresh_items()

        embed = create_question_list_embed(
            self.mommy_id,
            self.role_id,
            self.difficulty,
            self.page
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

    async def next_page(self, interaction: discord.Interaction):

        if not is_owner(interaction, self.mommy_id):
            await reject_not_owner(interaction)
            return

        questions = get_role_questions(
            self.role_id,
            self.difficulty
        )

        total_pages = max(
            1,
            (len(questions) + QUESTION_DISPLAY_PAGE_SIZE - 1)
            // QUESTION_DISPLAY_PAGE_SIZE
        )

        if self.page < total_pages - 1:
            self.page += 1

        self.refresh_items()

        embed = create_question_list_embed(
            self.mommy_id,
            self.role_id,
            self.difficulty,
            self.page
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )


# ==========================
# 📋 題庫查看 Embed
# ==========================

def create_question_list_embed(
    mommy_id: int,
    role_id: int,
    difficulty: str,
    page: int
):

    role = get_role(
        role_id,
        mommy_id
    )

    questions = get_role_questions(
        role_id,
        difficulty
    )

    if difficulty == "simple":
        difficulty_title = "🟢 簡單題"
    elif difficulty == "hard":
        difficulty_title = "🔴 困難題"
    else:
        difficulty_title = "📚 全部題目"

    total_pages = max(
        1,
        (len(questions) + QUESTION_DISPLAY_PAGE_SIZE - 1)
        // QUESTION_DISPLAY_PAGE_SIZE
    )

    start = page * QUESTION_DISPLAY_PAGE_SIZE
    page_questions = questions[
        start:start + QUESTION_DISPLAY_PAGE_SIZE
    ]

    embed = discord.Embed(
        title=(
            f"📋 {role['role_name']}｜"
            f"{difficulty_title}"
        ),
        description=(
            f"目前共 **{len(questions)}** 題\n"
            f"第 **{page + 1} / {total_pages}** 頁\n\n"
            "以下為目前保存的題目與標準答案。"
        ),
        color=discord.Color.blurple()
    )

    for index, question in enumerate(
        page_questions,
        start=start + 1
    ):

        difficulty_emoji = (
            "🟢"
            if question["difficulty"] == "simple"
            else "🔴"
        )

        embed.add_field(
            name=f"{difficulty_emoji} 第 {index} 題",
            value=(
                f"📝 **問題：**\n"
                f"{question['question']}\n\n"
                f"📖 **標準答案：**\n"
                f"{question['answer']}"
            ),
            inline=False
        )

    embed.set_footer(
        text="🌙 Moon Bot v2｜角色考試系統"
    )

    return embed


# ==========================
# 📋 顯示題目
# ==========================

async def show_question_list(
    interaction: discord.Interaction,
    mommy_id: int,
    role_id: int,
    difficulty: str = None
):

    if not is_owner(interaction, mommy_id):
        await reject_not_owner(interaction)
        return

    role = get_role(
        role_id,
        mommy_id
    )

    if role is None:
        await interaction.response.send_message(
            "❌ 找不到這隻角色，或你沒有管理權限。",
            ephemeral=True
        )
        return

    questions = get_role_questions(
        role_id,
        difficulty
    )

    if not questions:
        await interaction.response.send_message(
            "📭 目前沒有符合條件的題目。",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        embed=create_question_list_embed(
            mommy_id,
            role_id,
            difficulty,
            0
        ),
        view=QuestionListView(
            mommy_id,
            role_id,
            difficulty,
            0
        ),
        ephemeral=True
    )


# ==========================
# 🌙 主選單 View
# ==========================

class CharacterExamMainView(View):

    def __init__(self, mommy_id: int):

        super().__init__(timeout=300)
        self.mommy_id = mommy_id

    async def check_owner(self, interaction):
        if not is_owner(interaction, self.mommy_id):
            await reject_not_owner(interaction)
            return False
        return True

    # ==========================
    # ➕ 新增角色
    # ==========================

    @discord.ui.button(
        label="新增角色",
        emoji="➕",
        style=discord.ButtonStyle.success,
        row=0
    )
    async def add_role(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        if not await self.check_owner(interaction):
            return

        await interaction.response.send_modal(
            AddCharacterModal(
                self.mommy_id
            )
        )

    # ==========================
    # 🎭 我的角色
    # ==========================

    @discord.ui.button(
        label="我的角色",
        emoji="🎭",
        style=discord.ButtonStyle.primary,
        row=0
    )
    async def my_roles(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        if not await self.check_owner(interaction):
            return

        roles = get_mommy_roles(
            self.mommy_id
        )

        if not roles:
            await interaction.response.send_message(
                "📭 你目前還沒有建立任何角色。",
                ephemeral=True
            )
            return

        total_pages = max(
            1,
            (len(roles) + SELECT_PAGE_SIZE - 1)
            // SELECT_PAGE_SIZE
        )

        await interaction.response.send_message(
            content=(
                f"🎭 請選擇要管理的角色：\n"
                f"第 **1 / {total_pages}** 頁"
            ),
            view=CharacterSelectView(
                self.mommy_id
            ),
            ephemeral=True
        )

    # ==========================
    # 🔄 重新整理
    # ==========================

    @discord.ui.button(
        label="重新整理",
        emoji="🔄",
        style=discord.ButtonStyle.secondary,
        row=0
    )
    async def refresh(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        if not await self.check_owner(interaction):
            return

        await interaction.response.edit_message(
            embed=create_main_embed(
                self.mommy_id
            ),
            view=CharacterExamMainView(
                self.mommy_id
            )
        )


# ==========================
# 📝 指令 1
# ==========================

def setup_character_exam(bot):

    # ==========================
    # 🗄️ 初始化資料庫
    # ==========================

    init_character_exam_database()

    # ==========================
    # 📝 /考試角色設定
    # ==========================

    @bot.tree.command(
        name="考試角色設定",
        description="🌙 管理自己的角色與考試題庫"
    )
    async def character_exam_setup(
        interaction: discord.Interaction
    ):

        # ==========================
        # 📍 頻道限制
        # ==========================

        if interaction.channel_id != CHARACTER_EXAM_CHANNEL_ID:

            await interaction.response.send_message(
                "❌ 此指令只能在指定頻道使用。",
                ephemeral=True
            )
            return

        # ==========================
        # 👑 媽咪權限
        # ==========================

        if not is_mommy(interaction.user.id):

            await interaction.response.send_message(
                "❌ 只有四位媽咪可以使用此指令。",
                ephemeral=True
            )
            return

        # ==========================
        # 🌙 顯示管理中心
        # ==========================

        embed = create_main_embed(
            interaction.user.id
        )

        await interaction.response.send_message(
            embed=embed,
            view=CharacterExamMainView(
                interaction.user.id
            ),
            ephemeral=True
        )