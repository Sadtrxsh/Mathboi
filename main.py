import logging
import sys
from bot import TheBot
from bot_beg import BegBot
from bot_search import SearchBot
from bot_meme import MemeBot
from bot_fish import FishBot
from bot_hunt import HuntBot
from bot_event import EventBot
from bot_gamble import GambleBot
from bot_blackjack import BlackjackBot
from bot_autodep import AutoDepBot
from bot_invfetch import InvFetchBot
from bot_transfer import TransferBot
from bot_give import GiveBot

if len(sys.argv) != 2:
    print("main.py <config path>")
    exit(1)

exec(open(sys.argv[1]).read())

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(name)s %(message)s', stream=sys.stdout)
logging.getLogger("bot").setLevel(logging.DEBUG)

bot = TheBot(config)
bot.add_bot(BegBot(bot))
bot.add_bot(SearchBot(bot))
bot.add_bot(MemeBot(bot))
bot.add_bot(FishBot(bot))
bot.add_bot(HuntBot(bot))
bot.add_bot(EventBot(bot))
bot.add_bot(GambleBot(bot))
bot.add_bot(BlackjackBot(bot))
bot.add_bot(AutoDepBot(bot))
bot.add_bot(InvFetchBot(bot))
bot.add_bot(TransferBot(bot))
bot.add_bot(GiveBot(bot))
bot.run(config["token"])
bot.stop()