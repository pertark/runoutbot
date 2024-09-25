import discord
from discord.ext import commands
import dotenv
import os
import asyncio
import poker

dotenv.load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = discord.ext.commands.Bot(command_prefix="$", intents=intents)

runouts = {}
post_runouts = {}

# thanks https://gist.github.com/lykn/bac99b06d45ff8eed34c2220d86b6bf4
# (interaction and button are actually swapped)
class RunoutButton(discord.ui.View):
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)
    @discord.ui.button(label="Join runout",style=discord.ButtonStyle.gray)
    async def gray_button(self,interaction,button):
        await interaction.response.send_message(content=f"You've joined the runout! Wait for cards to be dealt...", ephemeral=True)
        user = interaction.user
        runouts[interaction.message.id]['users'].append(user)
        runouts[interaction.message.id]['interaction_handles'][user.id] = interaction

class PostRunoutModal(discord.ui.View):
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)
    
    @discord.ui.button(label="Fold",style=discord.ButtonStyle.red)
    async def red_button(self,interaction,button):
        user = interaction.user
        runout = runouts[post_runouts[interaction.message.id]['runout_id']]
        if user not in runout['users']:
            await interaction.response.send_message(content=f"You are not in the hand!", ephemeral=True)
            return
        if post_runouts[interaction.message.id]['acted'][user.id]:
            await interaction.response.send_message(content=f"You already showed your hand!", ephemeral=True)
            return
        post_runouts[interaction.message.id]['acted'][user.id] = True
        post_runouts[interaction.message.id]['folded'][user.id] = True
        await interaction.response.send_message(content=f"{user.mention} folded!")
        await finish_runout(interaction)

    @discord.ui.button(label="Show Cards",style=discord.ButtonStyle.green)
    async def green_button(self,interaction,button):
        user = interaction.user
        runout = runouts[post_runouts[interaction.message.id]['runout_id']]
        if user not in runout['users']:
            await interaction.response.send_message(content=f"You are not in the hand!", ephemeral=True)
            return
        if post_runouts[interaction.message.id]['acted'][user.id]:
            await interaction.response.send_message(content=f"You already showed your hand!", ephemeral=True)
            return
        post_runouts[interaction.message.id]['acted'][user.id] = True

        hand = runout['hands'][user]
        await interaction.response.send_message(content=f"{user.mention} has {poker.card_to_str(hand[0])} {poker.card_to_str(hand[1])}!")
        await finish_runout(interaction)

async def finish_runout(interaction):
    if all(post_runouts[interaction.message.id]['acted'].values()):
        runout = runouts[post_runouts[interaction.message.id]['runout_id']]
        community_cards = runout['community_cards']

        scores = {}
        for user in runout['users']:
            if not post_runouts[interaction.message.id]['folded'][user.id]:
                hand = runout['hands'][user]
                score = poker.evaluate_hand(community_cards, hand)
                scores[user] = score
        
        if len(scores) == 0:
            await interaction.message.channel.send(content="Everyone folded!")
            del runouts[post_runouts[interaction.message.id]['runout_id']]
            del post_runouts[interaction.message.id]
            return

        winners = []
        max_score = max(scores.values())
        for user, score in scores.items():
            if score == max_score:
                winners.append(user)

        if len(winners) == 1:
            await interaction.message.channel.send(content=f"{winners[0].mention} wins!")
        else:
            await interaction.message.channel.send(content=f"It's a tie between {', '.join([winner.mention for winner in winners])}!")

        # remove buttons
        await interaction.message.edit(embed=post_runouts[interaction.message.id]['embed'], view=None)
    
        # cleanup
        del runouts[post_runouts[interaction.message.id]['runout_id']]
        del post_runouts[interaction.message.id]


@bot.tree.command(name='runout', description='Start a runout')
async def start_runout(ctx: discord.Interaction, countdown: int = 10):
    await ctx.response.send_message(f'Starting a runout in {countdown} seconds; 0 players joined', view=RunoutButton())
    msg = await ctx.original_response()
    m = await msg.fetch()
    runouts[m.id] = {'users': [], 'interaction_handles': {}, 'hands': {}, 'community_cards': []}

    for i in range(countdown - 1, 0, -1):
        await asyncio.sleep(1)
        await ctx.edit_original_response(content=f'Starting a runout in {i} seconds; {len(runouts[m.id]["users"])} players joined')

    runout = runouts[m.id]
    if len(runout['users']) < 1:
        await ctx.edit_original_response(content='Not enough players. Runout aborted.')
        del runouts[m.id]
        return
    
    await ctx.edit_original_response(content=f'Starting runout between {", ".join(user.mention for user in runout["users"])}', view=None)

    deck = poker.Deck()
    for user in runout['users']:
        itn = runout['interaction_handles'][user.id]
        hand = [deck.deal(), deck.deal()]
        runout['hands'][user] = hand
        await itn.edit_original_response(content=f'{user.mention} has been dealt {poker.card_to_str(hand[0])} and {poker.card_to_str(hand[1])}')

    community_cards = [deck.deal(), deck.deal(), deck.deal(), deck.deal(), deck.deal()]
    runouts[m.id]['community_cards'] = community_cards

    embed = discord.Embed(title='Community cards', colour=0xFFFFFF, description=f'{poker.card_to_str(community_cards[0])} {poker.card_to_str(community_cards[1])} {poker.card_to_str(community_cards[2])}')
    community_msg = await m.channel.send(embed=embed)
    post_runouts[community_msg.id] = {
        'runout_id': m.id, 
        'acted': {user.id: False for user in runout['users']}, 
        'folded': {user.id: False for user in runout['users']},
        'embed': None,
        }
    await asyncio.sleep(2)
    embed = discord.Embed(title='Community cards', colour=0xFFFFFF, description=f'{poker.card_to_str(community_cards[0])} {poker.card_to_str(community_cards[1])} {poker.card_to_str(community_cards[2])} {poker.card_to_str(community_cards[3])}')
    await community_msg.edit(embed=embed)
    await asyncio.sleep(2)
    embed = discord.Embed(title='Community cards', colour=0xFFFFFF, description=f'{poker.card_to_str(community_cards[0])} {poker.card_to_str(community_cards[1])} {poker.card_to_str(community_cards[2])} {poker.card_to_str(community_cards[3])} {poker.card_to_str(community_cards[4])}')
    await community_msg.edit(embed=embed)
    await asyncio.sleep(1)
    post_runouts[community_msg.id]['embed'] = embed
    await community_msg.edit(embed=embed, view=PostRunoutModal())
    
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    await bot.tree.sync()
    print("Synced slash commands")

bot.run(os.getenv('DISCORD_TOKEN'))