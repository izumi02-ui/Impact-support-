import discord
import os
from flask import Flask
from threading import Thread
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View, Select

app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True  # User info ke liye zaroori hai
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"Synced slash commands for {self.user}")

bot = MyBot()

# --- 1. /help Command (Custom Message & Button) ---
class HelpContactView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="Contact Support", url="https://discord.com/invite/impactcity", style=discord.ButtonStyle.link))

@bot.tree.command(name="help", description="Send a custom help message to the admin team")
@app_commands.describe(message="Aapka message jo admin ko bhejna hai")
async def help_command(interaction: discord.Interaction, message: str):
    HELP_CHANNEL_ID = 1362413073436250354  # Yaha apna Custom Channel ID dalein
    channel = bot.get_channel(HELP_CHANNEL_ID)
    
    embed = discord.Embed(title="New Help Request", description=message, color=discord.Color.blue())
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url)
    
    await channel.send(embed=embed, view=HelpContactView())
    await interaction.response.send_message("Aapka message bhej diya gaya hai!", ephemeral=True)

# --- 2. /clear Command (Admin Only) ---
@bot.tree.command(name="clear", description="Delete messages from the channel")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"Done! {len(deleted)} messages deleted.", ephemeral=True)

# --- 3. Custom Messenger (Modal & Dashboard System) ---

class ChannelModal(discord.ui.Modal, title='Manual Channel ID Entry'):
    channel_id_input = discord.ui.TextInput(
        label='Enter Channel ID',
        placeholder='Paste the ID here...',
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            ch_id = int(self.channel_id_input.value.strip())
            ch = bot.get_channel(ch_id)
            if not ch:
                return await interaction.followup.send("❌ Channel nahi mila!", ephemeral=True)
            await interaction.followup.send(f"✅ Target set to: <#{ch.id}>", ephemeral=True)
        except:
            await interaction.followup.send("❌ Invalid ID!", ephemeral=True)

class PriorityChannelSelect(discord.ui.Select):
    def __init__(self):
        # Aapki screenshot wali list
        priority_names = ["staff-talk", "general-chat-💬", "announcements", "polls", "store"]
        options = [discord.SelectOption(label=f"#{name}", value=name) for name in priority_names]
        super().__init__(placeholder='Select a priority channel...', options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"✅ Selected: {self.values[0]}", ephemeral=True)

class DashboardView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(PriorityChannelSelect())

    @discord.ui.button(label="Manual ID", style=discord.ButtonStyle.primary)
    async def manual_id(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ChannelModal())

# --- 4. /userinfo Command ---
@bot.tree.command(name="userinfo", description="Get detailed info about a user")
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    roles = [role.mention for role in member.roles[1:]] # @everyone ko hata kar
    
    embed = discord.Embed(title=f"User Info - {member.name}", color=member.color)
    embed.set_thumbnail(url=member.avatar.url)
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%d-%m-%Y"))
    embed.add_field(name="Account Created", value=member.created_at.strftime("%d-%m-%Y"))
    embed.add_field(name="Roles", value=" ".join(roles) if roles else "No roles", inline=False)
    
    await interaction.response.send_message(embed=embed)

# --- 5. Punishment System (/list_punishment) ---
punishments = {} # Temporal storage (Iske liye Database use karna best hai)

@bot.tree.command(name="punish", description="Punish a user")
async def punish(interaction: discord.Interaction, member: discord.Member):
    view = View()
    select = Select(placeholder="Choose Punishment Type", options=[
        discord.SelectOption(label="Warn", value="Warn"),
        discord.SelectOption(label="Mute", value="Mute"),
        discord.SelectOption(label="Kick", value="Kick")
    ])
    
    async def select_callback(inter: discord.Interaction):
        punishments[member.id] = select.values[0]
        await inter.response.send_message(f"{member.mention} ko {select.values[0]} diya gaya.", ephemeral=True)
    
    select.callback = select_callback
    view.add_item(select)
    await interaction.response.send_message("Select punishment type:", view=view, ephemeral=True)

@bot.tree.command(name="list_punishment", description="See all punishments")
async def list_punishment(interaction: discord.Interaction):
    if not punishments:
        return await interaction.response.send_message("Koi punishments nahi hain.")
    
    msg = "\n".join([f"<@{uid}>: {action}" for uid, action in punishments.items()])
    await interaction.response.send_message(f"**Punishment List:**\n{msg}")

@bot.tree.command(name="dashboard", description="NEXUS Priority Dashboard")
async def dashboard(interaction: discord.Interaction):
    await interaction.response.send_message("⚙️ **NEXUS Dashboard**", view=DashboardView(), ephemeral=True)
    
bot.run(os.getenv('TOKEN'))
  
