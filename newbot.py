import os
from typing import Dict, Optional, Tuple

import discord
from discord import app_commands
from discord.ext import commands
import json
from pathlib import Path

# Basic config
DEFAULT_COLOR = discord.Color.blurple()
DEFAULT_CONFIG_FILE = os.getenv("EMBED_CONFIG_FILE", "embed_config.json")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)  # Prefix unused; slash commands only.


class EmbedSession:
    """Keeps an in-progress embed per user."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.embed = discord.Embed(color=DEFAULT_COLOR)
        self.extra_embeds: list[discord.Embed] = []
        self.content: str = ""

    def set_color(self, raw: str) -> Tuple[bool, str]:
        try:
            self.embed.color = discord.Color.from_str(raw)
            return True, f"Set color to `{raw}`."
        except (ValueError, TypeError):
            pass

        raw_clean = raw.replace("#", "").strip()
        try:
            value = int(raw_clean, 16)
        except ValueError:
            return False, "Color must be a hex value (e.g. #5865F2) or a Discord-named color."

        if not 0 <= value <= 0xFFFFFF:
            return False, "Color must be a 24-bit hex value."

        self.embed.color = discord.Color(value)
        return True, f"Set color to `#{raw_clean}`."


sessions: Dict[int, EmbedSession] = {}


def get_session(user_id: int) -> EmbedSession:
    session = sessions.get(user_id)
    if not session:
        session = EmbedSession()
        sessions[user_id] = session
    return session


def embed_is_empty(embed: discord.Embed) -> bool:
    return not any([embed.title, embed.description, embed.fields, embed.image, embed.thumbnail, embed.author])


def copy_with_timestamp(embed: discord.Embed) -> discord.Embed:
    clone = embed.copy()
    return clone


def safe_json_path(name: str) -> Path:
    base = Path(name).name or DEFAULT_CONFIG_FILE
    if not base.lower().endswith(".json"):
        base = f"{base}.json"
    return Path(base)


def parse_color(raw: str) -> Tuple[bool, Optional[discord.Color] | str]:
    try:
        return True, discord.Color.from_str(raw)
    except (ValueError, TypeError):
        pass

    raw_clean = raw.replace("#", "").strip()
    try:
        value = int(raw_clean, 16)
    except ValueError:
        return False, "Color must be a hex value (e.g. #5865F2) or a Discord-named color."

    if not 0 <= value <= 0xFFFFFF:
        return False, "Color must be a 24-bit hex value."

    return True, discord.Color(value)


def apply_embed_data(session: EmbedSession, data: dict) -> Tuple[bool, str]:
    """Populate a session from a dict that may contain content and multiple embeds."""
    def build_embed(obj: dict) -> Tuple[bool, Optional[discord.Embed] | str]:
        embed = discord.Embed(color=DEFAULT_COLOR)
        embed.title = obj.get("title") if obj.get("title") is not None else None
        embed.description = obj.get("description") if obj.get("description") is not None else None

        color_raw = obj.get("color")
        if color_raw:
            ok, color_val = parse_color(str(color_raw))
            if not ok:
                return False, color_val  # type: ignore
            embed.color = color_val  # type: ignore

        thumb = obj.get("thumbnail")
        if thumb:
            embed.set_thumbnail(url=thumb)

        image = obj.get("image")
        if image:
            embed.set_image(url=image)

        footer = obj.get("footer")
        if footer:
            embed.set_footer(text=footer)

        author = obj.get("author") or {}
        author_name = author.get("name")
        author_icon = author.get("icon_url") or None
        if author_name:
            embed.set_author(name=author_name, icon_url=author_icon)

        fields = obj.get("fields") or []
        for field in fields:
            name = field.get("name")
            value = field.get("value")
            if not name or not value:
                continue
            inline = bool(field.get("inline", False))
            embed.add_field(name=name, value=value, inline=inline)
        return True, embed

    session.reset()
    session.content = data.get("content") or ""

    embeds_data = data.get("embeds")
    embeds_to_apply = []

    if isinstance(embeds_data, list) and embeds_data:
        for obj in embeds_data[:10]:  # Discord allows up to 10 embeds per message
            ok, emb_or_msg = build_embed(obj)
            if not ok:
                return False, f"Color invalid: {emb_or_msg}"
            embeds_to_apply.append(emb_or_msg)  # type: ignore
    else:
        ok, emb_or_msg = build_embed(data)
        if not ok:
            return False, f"Color invalid: {emb_or_msg}"
        embeds_to_apply.append(emb_or_msg)  # type: ignore

    # Apply to session
    session.embed = embeds_to_apply[0]
    session.extra_embeds = embeds_to_apply[1:]

    return True, "Embed loaded from import data."


class EmbedForm(discord.ui.Modal, title="Embed configurator"):
    def __init__(self, session: EmbedSession):
        super().__init__(timeout=300)
        self.session = session

        self.title_input = discord.ui.TextInput(label="Title", style=discord.TextStyle.short, required=False)
        self.description_input = discord.ui.TextInput(
            label="Description", style=discord.TextStyle.paragraph, required=False
        )
        self.color_input = discord.ui.TextInput(
            label="Color (hex or name)", placeholder="#5865F2 or blurple", required=False
        )
        self.thumbnail_input = discord.ui.TextInput(
            label="Thumbnail URL", placeholder="https://example.com/thumb.png", required=False
        )
        self.image_input = discord.ui.TextInput(
            label="Image URL", placeholder="https://example.com/image.png", required=False
        )

        for item in (
            self.title_input,
            self.description_input,
            self.color_input,
            self.thumbnail_input,
            self.image_input,
        ):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        embed = self.session.embed
        embed.title = self.title_input.value if self.title_input.value is not None else None
        embed.description = self.description_input.value if self.description_input.value is not None else None

        if self.color_input.value:
            ok, msg = self.session.set_color(self.color_input.value)
            if not ok:
                await interaction.response.send_message(f"Color not set: {msg}", ephemeral=True)
                return

        if self.thumbnail_input.value:
            embed.set_thumbnail(url=self.thumbnail_input.value)
        if self.image_input.value:
            embed.set_image(url=self.image_input.value)

        preview = copy_with_timestamp(embed)
        await interaction.response.send_message("Embed updated from form.", embed=preview, ephemeral=True)


class EmbedCommands(app_commands.Group):
    def __init__(self) -> None:
        super().__init__(name="embed", description="Build and send embeds")

    @app_commands.command(name="form", description="Open a form to set title/description/colors/images")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def form(self, interaction: discord.Interaction) -> None:
        session = get_session(interaction.user.id)
        await interaction.response.send_modal(EmbedForm(session))

    @app_commands.command(name="add_field", description="Add a field to your embed")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def add_field(self, interaction: discord.Interaction, name: str, value: str, inline: bool = False) -> None:
        session = get_session(interaction.user.id)
        session.embed.add_field(name=name, value=value, inline=inline)
        await interaction.response.send_message(f"Added field `{name}`.", ephemeral=True)

    @app_commands.command(name="clear_fields", description="Remove all fields")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def clear_fields(self, interaction: discord.Interaction) -> None:
        session = get_session(interaction.user.id)
        session.embed.clear_fields()
        await interaction.response.send_message("Cleared all fields.", ephemeral=True)

    @app_commands.command(name="preview", description="Preview your current embed")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def preview(self, interaction: discord.Interaction) -> None:
        session = get_session(interaction.user.id)
        embeds = [copy_with_timestamp(session.embed)] + [copy_with_timestamp(e) for e in session.extra_embeds]
        usable_embeds = [e for e in embeds if not embed_is_empty(e)]

        if not usable_embeds and not session.content.strip():
            await interaction.response.send_message("Nothing to preview yet. Add content or an embed first.", ephemeral=True)
            return

        content_text = session.content or "Preview (no message content set)"
        await interaction.response.send_message(content_text, embeds=usable_embeds[:10], ephemeral=True)

    @app_commands.command(name="send", description="Send your embed to a channel (or here)")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def send(
        self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None
    ) -> None:
        session = get_session(interaction.user.id)
        embeds = [copy_with_timestamp(session.embed)] + [copy_with_timestamp(e) for e in session.extra_embeds]
        usable_embeds = [e for e in embeds if not embed_is_empty(e)]

        if not usable_embeds and not session.content.strip():
            await interaction.response.send_message("Cannot send an empty message. Add content or an embed first.", ephemeral=True)
            return

        target = channel or interaction.channel
        if not hasattr(target, "send"):
            await interaction.response.send_message("Cannot send to that target.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await target.send(content=session.content or None, embeds=usable_embeds[:10])
        except discord.Forbidden:
            await interaction.followup.send(
                "I don't have permission to send messages or embeds in that channel.", ephemeral=True
            )
            return
        except discord.HTTPException as exc:
            await interaction.followup.send(f"Failed to send embed: {exc}", ephemeral=True)
            return

        target_label = getattr(target, "mention", "DM")
        await interaction.followup.send(f"Message sent to {target_label}", ephemeral=True)

    @app_commands.command(name="reset", description="Start a fresh embed")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def reset(self, interaction: discord.Interaction) -> None:
        session = get_session(interaction.user.id)
        session.reset()
        await interaction.response.send_message("Started a new blank embed.", ephemeral=True)

    @app_commands.command(name="import", description="Load embed config from a local JSON file")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def import_(self, interaction: discord.Interaction, file_name: Optional[str] = None) -> None:
        session = get_session(interaction.user.id)
        path = safe_json_path(file_name or DEFAULT_CONFIG_FILE)
        if not path.exists():
            await interaction.response.send_message(f"No import file found at {path.resolve()}", ephemeral=True)
            return

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            await interaction.response.send_message(f"Import file is not valid JSON: {exc}", ephemeral=True)
            return

        ok, msg = apply_embed_data(session, data)
        if not ok:
            await interaction.response.send_message(f"Import failed: {msg}", ephemeral=True)
            return

        embeds = [copy_with_timestamp(session.embed)] + [copy_with_timestamp(e) for e in session.extra_embeds]
        usable_embeds = [e for e in embeds if not embed_is_empty(e)]
        preview_text = msg if not session.content else f"{msg}\n\n{session.content}"
        await interaction.response.send_message(preview_text, embeds=usable_embeds[:10], ephemeral=True)

    @app_commands.command(name="import_file", description="Upload a JSON embed config to load")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def import_file(self, interaction: discord.Interaction, file: discord.Attachment) -> None:
        session = get_session(interaction.user.id)

        if file.size > 256 * 1024:
            await interaction.response.send_message("File too large. Max 256KB.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            content = await file.read()
            data = json.loads(content.decode("utf-8"))
        except UnicodeDecodeError:
            await interaction.followup.send("File must be UTF-8 text/JSON.", ephemeral=True)
            return
        except json.JSONDecodeError as exc:
            await interaction.followup.send(f"Invalid JSON: {exc}", ephemeral=True)
            return

        ok, msg = apply_embed_data(session, data)
        if not ok:
            await interaction.followup.send(f"Import failed: {msg}", ephemeral=True)
            return

        embeds = [copy_with_timestamp(session.embed)] + [copy_with_timestamp(e) for e in session.extra_embeds]
        usable_embeds = [e for e in embeds if not embed_is_empty(e)]
        preview_text = f"{msg} (from upload)"
        if session.content:
            preview_text = f"{preview_text}\n\n{session.content}"
        await interaction.followup.send(preview_text, embeds=usable_embeds[:10], ephemeral=True)

    @app_commands.command(name="summary", description="Show a quick summary of your embed")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def summary(self, interaction: discord.Interaction) -> None:
        session = get_session(interaction.user.id)
        embed = session.embed
        lines = [
            f"Content length: {len(session.content)}",
            f"Embed count: {1 + len(session.extra_embeds)}",
            f"Title (first): {embed.title or '-'}",
            f"Description (first): {bool(embed.description)}",
            f"Fields (first): {len(embed.fields)}",
            f"Color (first): {embed.color.value:06X}",
        ]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="footer", description="Set footer text")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def footer(self, interaction: discord.Interaction, text: str) -> None:
        session = get_session(interaction.user.id)
        footer_icon = session.embed.footer.icon_url or None
        session.embed.set_footer(text=text, icon_url=footer_icon)
        await interaction.response.send_message("Footer set.", ephemeral=True)

    @app_commands.command(name="author", description="Set author name and optional icon URL")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def author(
        self, interaction: discord.Interaction, name: str, icon_url: Optional[str] = None
    ) -> None:
        session = get_session(interaction.user.id)
        session.embed.set_author(name=name, icon_url=icon_url or None)
        await interaction.response.send_message("Author set.", ephemeral=True)

    @app_commands.command(name="content", description="Set message text to send with embeds")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def content(self, interaction: discord.Interaction, text: str) -> None:
        session = get_session(interaction.user.id)
        session.content = text
        await interaction.response.send_message("Content set.", ephemeral=True)


@bot.event
async def on_ready() -> None:
    print(f"Logged in as {bot.user} (id={bot.user.id})")
    await bot.tree.sync()
    print("Slash commands synced. Use /embed form to configure.")


def main() -> None:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("Set the DISCORD_TOKEN environment variable with your bot token.")
    bot.tree.add_command(EmbedCommands())
    bot.run(token)


if __name__ == "__main__":
    main()
