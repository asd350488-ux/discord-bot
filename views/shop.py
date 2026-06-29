import discord

from database import c, conn
from config import *

class BuyButton(discord.ui.Button):
    def __init__(self, item_id, price, name):
        super().__init__(
            label=f"購買 {name}",
            style=discord.ButtonStyle.green
        )
        self.item_id = item_id
        self.price = price
        self.name = name

    async def callback(self, interaction: discord.Interaction):

        user_id = str(interaction.user.id)

        # 💰 查錢
        c.execute("SELECT money FROM users WHERE user_id=?", (user_id,))
        data = c.fetchone()

        if not data or data[0] < self.price:
            await interaction.response.send_message("❌ 努努幣不足", ephemeral=True)
            return

        # 📦 查庫存
        c.execute("SELECT stock FROM shop WHERE item_id=?", (self.item_id,))
        stock = c.fetchone()

        if not stock or stock[0] <= 0:
            await interaction.response.send_message("❌ 商品已售完", ephemeral=True)
            return

        # 💰 扣錢
        c.execute("UPDATE users SET money = money - ? WHERE user_id=?", (self.price, user_id))

        # 📦 扣庫存
        c.execute("UPDATE shop SET stock = stock - 1 WHERE item_id=?", (self.item_id,))

        # 🎒 加入背包
        c.execute("SELECT amount FROM inventory WHERE user_id=? AND item_id=?", (user_id, self.item_id))
        inv = c.fetchone()

        if inv:
            c.execute("UPDATE inventory SET amount = amount + 1 WHERE user_id=? AND item_id=?", (user_id, self.item_id))
        else:
            c.execute("INSERT INTO inventory (user_id, item_id, amount) VALUES (?, ?, 1)", (user_id, self.item_id))

        conn.commit()

        await interaction.response.send_message(
            f"🛍️ 購買成功！**{self.name}**\n<a:emoji40:1510362334026268713> -{self.price}"
        )

class ShopView(discord.ui.View):
    def __init__(self, items, page=0):
        super().__init__(timeout=60)
        self.items = items
        self.page = page
        self.per_page = 3

    def get_page_items(self):
        start = self.page * self.per_page
        end = start + self.per_page
        return self.items[start:end]

    async def update(self, interaction):

        self.clear_items()

        embed = discord.Embed(
            title="🛒 商店",
            color=discord.Color.gold()
        )

        page_items = self.get_page_items()

        for item_id, name, price, stock, desc, img in page_items:

            embed.add_field(
                name=f"🆔 {item_id}｜{name}",
                value=f"{desc}\n<a:emoji40:1510362334026268713> {price}｜庫存:{stock}",
                inline=False
            )

            self.add_item(BuyButton(item_id, price, name))

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

    @discord.ui.button(
        label="⬅ 上一頁",
        style=discord.ButtonStyle.gray
    )
    async def prev(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if self.page > 0:
            self.page -= 1

        await self.update(interaction)

    @discord.ui.button(
        label="➡ 下一頁",
        style=discord.ButtonStyle.gray
    )
    async def next(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if (self.page + 1) * self.per_page < len(self.items):
            self.page += 1

        await self.update(interaction)

async def get_wanted_level(user_id):

    c.execute(
        "SELECT level FROM wanted WHERE user_id=?",
        (user_id,)
    )

    data = c.fetchone()

    return data[0] if data else 0


async def add_wanted(user_id):

    c.execute(
        "SELECT level FROM wanted WHERE user_id=?",
        (user_id,)
    )

    data = c.fetchone()

    if data:

        c.execute(
            """
            UPDATE wanted
            SET level = level + 1
            WHERE user_id=?
            """,
            (user_id,)
        )

    else:

        c.execute(
            """
            INSERT INTO wanted
            (user_id, level)
            VALUES (?, 1)
            """,
            (user_id,)
        )

    conn.commit()

    async def update(self, interaction):

        self.clear_items()

        embed = discord.Embed(
            title="🛒 商店",
            color=discord.Color.gold()
        )

        page_items = self.get_page_items()

        for item_id, name, price, stock, desc, img in page_items:

            embed.add_field(
                name=f"🆔 {item_id}｜{name}",
                value=f"{desc}\n<a:emoji40:1510362334026268713> {price}｜庫存:{stock}",
                inline=False
            )

            self.add_item(BuyButton(item_id, price, name))

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="⬅ 上一頁", style=discord.ButtonStyle.gray)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        await self.update(interaction)

    @discord.ui.button(label="➡ 下一頁", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if (self.page + 1) * self.per_page < len(self.items):
            self.page += 1
        await self.update(interaction)
