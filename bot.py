import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='.', intents=intents)


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'audioquality': '0', 
    'cookiefile': 'cookies.txt'
}

ffmpeg_path = "/ffmpeg/ffmpeg.exe"

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -ar 48000 -ac 2 -b:a 320k',
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class MusicQueue:
    def __init__(self):
        self.songs = asyncio.Queue()

    async def put(self, item):
        await self.songs.put(item)

    async def get(self):
        return await self.songs.get()

    def is_empty(self):
        return self.songs.empty()

    def clear(self):
        self.songs = asyncio.Queue()

queue = MusicQueue()

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')

@bot.command(name='join', help='Joins the voice channel')
async def join(ctx):
    if not ctx.author.voice:
        await ctx.send(f"Por favor, entre em um canal de voz primeiro!")
        return
    channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await channel.connect()
        await ctx.send(f"Entrei no canal de voz {channel}!")
    else:
        await ctx.voice_client.move_to(channel)
        await ctx.send(f"Fui movido para o canal de voz {channel}!")

@bot.command(name='play', help='Plays a song')
async def play(ctx, url):
    if ctx.voice_client is None:
        await ctx.send(f"Não estou em um canal de voz. Use o comando .join primeiro.")
        return

    async with ctx.typing():
        try:
            player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
            await queue.put(player)
            if not ctx.voice_client.is_playing():
                await play_next(ctx)
            await ctx.send(f"{player.title} foi adicionado à fila!")
        except Exception as e:
            await ctx.send(f"Erro: {str(e)}")

async def play_next(ctx):
    if not queue.is_empty():
        player = await queue.get()
        ctx.voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
        await ctx.send(f"Tocando: {player.title}")
    else:
        await ctx.send("A fila está vazia!")

@bot.command(name='skip', help='Skips the currently playing song')
async def skip(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Música pulada!")
    else:
        await ctx.send("Nenhuma música está tocando para pular.")

@bot.command(name='leave', help='Leaves the voice channel')
async def leave(ctx):
    if ctx.voice_client is not None:
        await ctx.voice_client.disconnect()
        queue.clear()
        await ctx.send(f"Saí do canal de voz e limpei a fila!")
    else:
        await ctx.send(f"Não estou em um canal de voz.")

@bot.command(name='pause', help='Pauses the song')
async def pause(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("Música pausada!")
    else:
        await ctx.send("Nenhuma música está tocando para pausar.")

@bot.command(name='resume', help='Resumes the song')
async def resume(ctx):
    if ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("Música retomada!")
    else:
        await ctx.send("Nenhuma música está pausada para retomar.")

@bot.command(name='stop', help='Stops the song')
async def stop(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Música parada!")
    else:
        await ctx.send("Nenhuma música está tocando para parar.")
bot.run('#')
