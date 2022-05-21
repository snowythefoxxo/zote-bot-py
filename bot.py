import discord
import logging
import os

from discord.ext import commands
from utils import aloc, DBConnection, PermissionDenied, access_level_check, AccessLevel

# Constants

BOT_DESCRIPTION = '''
bot.
'''
BOT_VERSION = '0.2.0'
DEFAULT_PREFIX = '>'


class BasicCog(commands.Cog):
    async def cog_check(self, ctx):
        return await access_level_check(ctx, AccessLevel.USER)


async def get_prefix(_bot, message):
    if not message.guild:  # if the message is a DM
        return DEFAULT_PREFIX

    guild = await _bot.db.get_guild(message.guild.id)

    if not guild:  # no guild data
        return DEFAULT_PREFIX

    return guild.get('prefix', DEFAULT_PREFIX)  # return the guild prefix or default


class ZoteBot(commands.AutoShardedBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = DBConnection()
        self._watcher_mode = os.environ.get('WATCHER_MODE', '0') == '1'

    async def close(self):
        if self.db.is_connected:
            await self.db.close()

        await super().close()

    async def on_message(self, message):
        if not self._watcher_mode:  # Normal bot functionality
            if message.author.bot:
                return

            prefix = await get_prefix(self, message)
            if self.user.mention in message.content \
                    and not message.content.startswith(prefix):  # any ping, except when a command is used
                # build bot info embed
                emb = discord.Embed(title='Zote', description=BOT_DESCRIPTION, color=message.guild.me.color)
                emb.set_thumbnail(url=self.user.avatar_url)
                emb.set_footer(text=f'{self.user.name}#{self.user.discriminator} (v{BOT_VERSION})',
                               icon_url=self.user.avatar_url)
                emb.add_field(name='Prefix', value=prefix)
                await message.channel.send(embed=emb)
                return

            await self.process_commands(message)

    async def on_ready(self):
        await self.db.connect()
        logger.debug(f'Logged in as {bot.user} ({bot.user.id})')
        logger.debug(f'All lines of code: {aloc()}')

    async def on_command_error(self, context, exception):
        if isinstance(exception, PermissionDenied):
            await context.send(exception)
            return

        if isinstance(exception, commands.MissingPermissions):
            await context.send(f'You don\'t have the required permissions to use this command.')
            return

        if isinstance(exception, commands.CommandNotFound):
            return

        logger.exception(f'Exception in command {context.command.qualified_name}:', exc_info=exception)


if __name__ == '__main__':
    logger = logging.getLogger(  # create logger
        'zote' if os.environ.get('DEBUG', "0") == "0"
        else 'purple'
    )
    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    bot = ZoteBot(command_prefix=get_prefix, intents=discord.Intents.all())

    for filename in os.listdir('cogs'):
        if filename.endswith('.py'):
            try:
                bot.load_extension(f'cogs.{filename[:-3]}')  # load all cogs
            except commands.ExtensionError as e:
                logger.error(e)

    bot.run(
        # get token from environment, run purple if debug mode is enabled
        os.environ.get('ZOTE_DISCORD_TOKEN', 'abcdefg1234567') if os.environ.get('DEBUG', '0') == '0'
        else os.environ.get('PURPLE_DISCORD_TOKEN', 'abcdefg1234567'),
    )
