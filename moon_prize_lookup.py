# -*- coding: utf-8 -*-
"""🌙 Moon Bot｜玩家盲盒中獎紀錄查詢（唯讀獨立模組）"""

import discord
from discord import app_commands
from discord.ext import commands

from database import c
from config import BOT_ADMINS


ACHIEVEMENT_STATUS = {
    "awaiting_image": "⏳ 等待玩家提交圖片",
    "image_received": "📩 已收到圖片，尚待轉交",
    "forwarded": "🎨 已轉交製作者",
    "completed": "✅ 已完成",
    "expired": "⌛ 已逾期放棄",
    "cancelled": "🚫 已取消",
}

HALLOWEEN_IMAGE_STATUS = {
    "not_required": "不需要提交圖片",
    "awaiting_image": "⏳ 等待玩家提交圖片",
    "forwarded": "🎨 已轉交媽咪",
    "completed": "✅ 已完成",
    "cancelled": "🚫 已取消",
}

HALLOWEEN_PRIZES = {
    "money": "努努幣",
    "sticker": "🎨 角色 Q 版貼圖 ×1",
    "couple": "💕 角色合照 ×1",
}


def _table_exists(table_name):
    c.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    )
    return c.fetchone() is not None


def _fmt_time(value):
    if not value:
        return "未記錄"
    return str(value).replace("T", " ")[:19]


def _fetch_player_records(user_id):
    """只執行 SELECT，不建立資料表、不更新或刪除任何資料。"""
    records = []

    if _table_exists("moon_achievement_redemptions"):
        c.execute(
            """
            SELECT redemption_id, reward, mommy_name, character_name,
                   status, created_at, submitted_at, completed_at
            FROM moon_achievement_redemptions
            WHERE user_id=?
            ORDER BY redemption_id DESC
            """,
            (int(user_id),),
        )
        for row in c.fetchall():
            records.append({
                "system": "🌙 成就盲盒",
                "sort_time": row["created_at"] or "",
                "number": row["redemption_id"],
                "prize": row["reward"] or "未記錄獎品",
                "detail": (
                    f"負責媽咪／製作者：{row['mommy_name'] or '未指定'}\n"
                    f"角色名稱：{row['character_name'] or '未指定'}\n"
                    f"圖片狀態：{ACHIEVEMENT_STATUS.get(row['status'], row['status'] or '未知')}\n"
                    f"兌換時間：{_fmt_time(row['created_at'])}\n"
                    f"提交時間：{_fmt_time(row['submitted_at'])}\n"
                    f"完成時間：{_fmt_time(row['completed_at'])}"
                ),
            })

    if _table_exists("halloween_lottery_entries"):
        c.execute(
            """
            SELECT id, draw_number, price, prize_type, prize_value, is_test,
                   created_at, claim_status, mommy_name, character_name,
                   claimed_at, image_status
            FROM halloween_lottery_entries
            WHERE user_id=?
            ORDER BY id DESC
            """,
            (str(user_id),),
        )
        for row in c.fetchall():
            prize_type = row["prize_type"] or "未知獎品"
            if prize_type == "money":
                prize = f"💰 努努幣 {int(row['prize_value'] or 0):,}"
            else:
                prize = HALLOWEEN_PRIZES.get(
                    prize_type, f"{prize_type}（{row['prize_value']}）"
                )

            test_label = "🧪 管理員測試紀錄" if int(row["is_test"] or 0) else "正式抽獎"
            if prize_type in ("sticker", "couple"):
                claim_text = (
                    "已填寫領獎資料"
                    if int(row["claim_status"] or 0) == 1
                    else "尚未填寫領獎資料"
                )
            else:
                claim_text = "不需要填寫角色資料"

            records.append({
                "system": "🎃 萬聖節盲盒",
                "sort_time": row["created_at"] or "",
                "number": row["id"],
                "prize": prize,
                "detail": (
                    f"紀錄類型：{test_label}\n"
                    f"抽獎序號：第 {row['draw_number']} 次\n"
                    f"抽獎費用：{int(row['price'] or 0):,} 努努幣\n"
                    f"領獎資料：{claim_text}\n"
                    f"負責媽咪：{row['mommy_name'] or '未指定'}\n"
                    f"角色名稱：{row['character_name'] or '未指定'}\n"
                    f"圖片狀態：{HALLOWEEN_IMAGE_STATUS.get(row['image_status'], row['image_status'] or '未知')}\n"
                    f"中獎時間：{_fmt_time(row['created_at'])}\n"
                    f"填寫領獎資料時間：{_fmt_time(row['claimed_at'])}"
                ),
            })

    records.sort(key=lambda item: item["sort_time"], reverse=True)
    return records


class PrizeRecordView(discord.ui.View):
    def __init__(self, owner_id, member, records, page=0):
        super().__init__(timeout=180)
        self.owner_id = int(owner_id)
        self.member = member
        self.records = records
        self.page = page
        self.page_size = 5
        self._update_buttons()

    def _update_buttons(self):
        total_pages = max(1, (len(self.records) + self.page_size - 1) // self.page_size)
        self.previous.disabled = self.page <= 0
        self.next.disabled = self.page >= total_pages - 1

    def make_embed(self):
        total_pages = max(1, (len(self.records) + self.page_size - 1) // self.page_size)
        start = self.page * self.page_size
        current = self.records[start:start + self.page_size]

        achievement_count = sum(x["system"] == "🌙 成就盲盒" for x in self.records)
        halloween_count = sum(x["system"] == "🎃 萬聖節盲盒" for x in self.records)

        embed = discord.Embed(
            title="📜 玩家盲盒中獎紀錄",
            description=(
                f"玩家：{self.member.mention}\n"
                f"玩家 ID：`{self.member.id}`\n\n"
                f"🌙 成就盲盒：**{achievement_count}** 筆\n"
                f"🎃 萬聖節盲盒：**{halloween_count}** 筆\n"
                f"📦 總紀錄：**{len(self.records)}** 筆"
            ),
            color=discord.Color.gold(),
        )

        if not current:
            embed.add_field(name="查詢結果", value="目前沒有找到這位玩家的中獎紀錄。", inline=False)
        else:
            for item in current:
                embed.add_field(
                    name=f"{item['system']}｜#{item['number']}｜{item['prize']}",
                    value=item["detail"],
                    inline=False,
                )

        embed.set_footer(text=f"第 {self.page + 1}/{total_pages} 頁｜此查詢為唯讀，不會修改任何紀錄")
        return embed

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id and interaction.user.id not in BOT_ADMINS:
            await interaction.response.send_message("❌ 只有發起查詢的管理員可以操作這份紀錄。", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="◀ 上一頁", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction, button):
        self.page = max(0, self.page - 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="下一頁 ▶", style=discord.ButtonStyle.secondary)
    async def next(self, interaction, button):
        total_pages = max(1, (len(self.records) + self.page_size - 1) // self.page_size)
        self.page = min(total_pages - 1, self.page + 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)


def setup_moon_prize_lookup(bot):
    """註冊唯讀查詢指令；不碰原本兩套盲盒模組。"""

    async def query_player_prizes(
        interaction: discord.Interaction,
        玩家: discord.Member,
    ):
        if interaction.user.id not in BOT_ADMINS:
            await interaction.response.send_message("❌ 只有機器人管理員可以查詢玩家中獎紀錄。", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            records = _fetch_player_records(玩家.id)
        except Exception as exc:
            await interaction.followup.send(
                f"⚠️ 查詢資料時發生錯誤：`{type(exc).__name__}`\n"
                "沒有執行任何資料修改，請檢查資料庫連線與資料表欄位。",
                ephemeral=True,
            )
            return

        view = PrizeRecordView(interaction.user.id, 玩家, records)
        await interaction.followup.send(
            embed=view.make_embed(),
            view=view if records else None,
            ephemeral=True,
        )

    command = app_commands.Command(
        name="查詢玩家中獎資料",
        description="查詢玩家的成就盲盒與萬聖節盲盒中獎紀錄（唯讀）",
        callback=query_player_prizes,
    )

    if bot.tree.get_command(command.name) is None:
        bot.tree.add_command(command)
    else:
        print(f"⚠️ 指令「{command.name}」已存在，略過重複註冊。")
