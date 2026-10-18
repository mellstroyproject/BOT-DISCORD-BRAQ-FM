import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from aiohttp import web

TOKEN = os.getenv("DISCORD_TOKEN")
# ID ролей через запятую, например: 123,456,789
ROLE_IDS = [int(x) for x in os.getenv("ROLE_IDS", "").replace(" ", "").split(",") if x]
RANK_PREFIX = os.getenv("RANK_PREFIX", "(1) ")  # приписка к нику
PORT = int(os.getenv("PORT", "10000"))          # Render сам передаёт PORT

intents = discord.Intents.default()
intents.members = True  # нужно для изменения ников и ролей
intents.message_content = True  # нужно для команды !panel


class NickModal(discord.ui.Modal, title="Получение роли"):
    nick = discord.ui.TextInput(
        label="Ваш ник из игры",
        placeholder="Иван Иванов",
        min_length=3,
        max_length=20,
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user

        roles = [guild.get_role(rid) for rid in ROLE_IDS]
        roles = [r for r in roles if r is not None]

        if not roles:
            await interaction.response.send_message(
                "Роли не найдены. Сообщите администрации.", ephemeral=True
            )
            return

        new_nick = f"{RANK_PREFIX}{self.nick.value.strip()}"[:32]  # лимит Discord — 32 символа

        try:
            await member.add_roles(*roles, reason="Получение роли через панель")
        except discord.Forbidden:
            await interaction.response.send_message(
                "У бота нет прав выдать эти роли. Проверьте, что роль бота выше выдаваемых.",
                ephemeral=True,
            )
            return

        try:
            await member.edit(nick=new_nick, reason="Ник из игры")
            nick_info = f"Ваш ник: **{new_nick}**"
        except discord.Forbidden:
            nick_info = "Не удалось сменить ник (у владельца сервера или выше роли ник не меняется)."

        await interaction.response.send_message(
            f"Роли выданы! {nick_info}", ephemeral=True
        )


class RoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # кнопка работает всегда, даже после перезапуска

    @discord.ui.button(
        label="Получить роль",
        style=discord.ButtonStyle.success,
        emoji="🎭",
        custom_id="get_role_button",
    )
    async def get_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NickModal())


class RoleBot(commands.Bot):
    async def setup_hook(self):
        self.add_view(RoleView())  # регистрируем постоянную кнопку
        await self.tree.sync()


bot = RoleBot(command_prefix="!", intents=intents)


@bot.tree.command(name="panel", description="Отправить панель получения роли в этот канал")
@app_commands.default_permissions(administrator=True)
async def panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Получение роли",
        description="Нажмите кнопку ниже и введите ваш ник из игры.\nПосле этого вы получите роли, а ник будет обновлён.",
        color=0x2B2D31,
    )
    await interaction.channel.send(embed=embed, view=RoleView())
    await interaction.response.send_message("Панель отправлена.", ephemeral=True)


@bot.command(name="panel")
@commands.has_permissions(administrator=True)
async def panel_prefix(ctx: commands.Context):
    embed = discord.Embed(
        title="Получение роли",
        description="Нажмите кнопку ниже и введите ваш ник из игры.\nПосле этого вы получите роли, а ник будет обновлён.",
        color=0x2B2D31,
    )
    await ctx.send(embed=embed, view=RoleView())
    try:
        await ctx.message.delete()
    except discord.HTTPException:
        pass


@bot.event
async def on_ready():
    print(f"Бот запущен как {bot.user}")


# ---- Мини-сервер, чтобы Render не усыплял сервис ----
async def health(request):
    return web.Response(text="OK")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()


async def main():
    await start_web_server()
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
