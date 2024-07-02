import discord
from cogs.premium import SLOTM_PANEL, RequirePremiumView
from discord.ext import commands
from lib import plural
from models import Scrim, ScrimsSlotManager

from .. import ScrimsView
from ..utility.selectors import prompt_scrims_selector


class SlotmMainPanel(ScrimsView):
    def __init__(self, ctx: commands.Context):
        super().__init__(ctx, timeout=100)

    async def initial_msg(self) -> discord.Embed:
        slotm_records = await ScrimsSlotManager.filter(guild_id=self.ctx.guild.id).prefetch_related("scrims")

        e = discord.Embed(
            color=self.bot.color,
            title="Scrims Slot Cancel / Claim Manager",
            description=(
                "Slot-Manager is a way to ease-up scrims slot management process. "
                "With Quotient's slotm users can - cancel their slot, claim an empty slot "
                "and also set reminder for vacant slots, All without bugging any mod."
            ),
        )

        e.description += "\n\n**Current Cancel / Claim Panels:**\n"
        if not slotm_records:
            e.description += "```No slot manager records found```"

        for idx, slotm in enumerate(slotm_records, start=1):
            e.description += f"`{idx:02}.` <#{slotm.channel_id}> - ({plural(slotm.scrims):scrim|scrims})"

        e.set_footer(text="Don't forget to set the match times for scrims.")
        return e

    @discord.ui.button(label="Setup Cancel / Claim", style=discord.ButtonStyle.primary)
    async def setup_cancel_claim(self, inter: discord.Interaction, btn: discord.ui.Button):
        await inter.response.defer()

        if not inter.guild.me.guild_permissions.manage_channels:
            return await inter.followup.send(
                embed=self.bot.error_embed("I need `Manage Channels` permission to setup `cancel / claim`."),
                view=self.bot.contact_support_view(),
                ephemeral=True,
            )

        if not await self.bot.is_pro_guild(inter.guild_id):
            if await ScrimsSlotManager.filter(guild_id=inter.guild_id).count() >= SLOTM_PANEL:
                v = RequirePremiumView(
                    f"You have reached the maximum limit of '{SLOTM_PANEL} slot manager panels', Upgrade to Quotient Pro to unlock more."
                )
                return await inter.followup.send(embed=v.premium_embed, view=v)

        self.stop()

        scrims = await prompt_scrims_selector(
            inter,
            inter.user,
            await Scrim.filter(guild_id=inter.guild_id),
            "Select scrims to setup slot manager for.",
        )
        if not scrims:
            return

        prompt = await self.bot.prompt(
            inter,
            inter.user,
            "A new channel will be created for the selected scrims slot manager.\n\n`Do you want to continue?`",
            ephemeral=True,
        )
        if not prompt:
            return

        overwrites = {
            inter.guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True),
            inter.guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_channels=True,
                manage_messages=True,
                read_message_history=True,
                embed_links=True,
                manage_permissions=True,
            ),
        }

        channel = await inter.guild.create_text_channel(
            name="cancel-claim-slot", overwrites=overwrites, reason=f"Created for scrims slotm by {inter.user}"
        )

        record = ScrimsSlotManager(channel_id=channel.id, guild_id=inter.guild_id)
        await record.setup(scrims)
        msg = await channel.send("Setting up cancel claim panel ...")

        slotm = await ScrimsSlotManager.create(channel_id=channel.id, guild_id=inter.guild_id, message_id=msg.id)
        await Scrim.filter(pk__in=[s.pk for s in scrims]).update(slotm=slotm)

        await slotm.refresh_public_message()

        self.stop()
        v = SlotmMainPanel(self.ctx)
        v.message = await self.message.edit(content="", embed=await v.initial_msg(), view=v)

    @discord.ui.button(label="Edit Settings", style=discord.ButtonStyle.primary)
    async def edit_settings(self, inter: discord.Interaction, btn: discord.ui.Button):
        await inter.response.defer()

    @discord.ui.button(label="Set Match Time")
    async def set_match_times(self, inter: discord.Interaction, btn: discord.ui.Button):
        await inter.response.defer()
