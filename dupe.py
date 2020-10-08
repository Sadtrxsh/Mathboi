# the dupe bot needs a lot of special logic so it can't really use the same code as the other bots sadly
import discord
import logging
import time
import asyncio
from enum import Enum
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from asyncio import Lock, Event, Queue
from cmd_util import *
from cooldown import CooldownHelper


class TheTyper:
    def __init__(self, profile_id, url):
        self.profile_id = profile_id
        self.url = url
        self.current_msg = None
        self.event = Event()
        self.lock = Lock()

        options = webdriver.ChromeOptions()
        options.add_argument("user-data-dir=profiles/" + self.profile_id)
        self.driver = webdriver.Chrome(options=options)
        self.driver.get(self.url)

    async def send_message(self, msg):
        async with self.lock:
            self.event.clear()
            self.current_msg = msg
            elem = TheTyper.get_input_box(self.driver)
            TheTyper.type_message(elem, msg)
            TheTyper.do_send_message(elem)
            await self.event.wait()

    def on_message(self, msg):
        if msg.content == self.current_msg:
            self.current_msg = None
            self.event.set()

    @staticmethod
    def get_input_box(driver):
        while True:
            try:
                return driver.find_element_by_xpath("//div[contains(@class, 'slateTextArea')]")
            except NoSuchElementException:
                time.sleep(1)

    @staticmethod
    def type_message(elem, txt):
        elem.click()
        elem.send_keys(Keys.CONTROL, 'a')
        elem.send_keys(txt)

    @staticmethod
    def do_send_message(elem):
        elem.send_keys(Keys.RETURN)


class StealResult(Enum):
    TIMEOUT = 0
    NOT_ENOUGH_COINS = 1
    CAUGHT = 2
    TWO_MIN = 3
    SMALL_AMOUNT = 4
    LARGE_AMOUNT = 5
    FULL_AMOUNT = 6


class TheBot(discord.Client):
    T_STEAL_COOLDOWN = "Woahhh there, you need some time to plan your next hit. Wait "
    T_STEAL_NOT_ENOUGH_COINS = "You need at least 250 coins to try and rob someone."
    T_STEAL_CAUGHT = "You were caught **HAHAHA**\nYou paid the person you stole from **250** coins."
    T_STEAL_2_MIN = "This user has already been stolen from within the last 2 minutes, give it a rest"
    P_STEAL_SMALL_AMOUNT = re.compile("^You stole a small portion! 💸\nYour payout was \\*\\*([0-9,]+)\\*\\* coins.$")
    P_STEAL_LARGE_AMOUNT = re.compile("^You stole a good chunk! 💰\nYour payout was \\*\\*([0-9,]+)\\*\\* coins.$")
    P_STEAL_FULL_AMOUNT = re.compile("^You stole A SHIT TON! 🤑\nYour payout was \\*\\*([0-9,]+)\\*\\* coins.$")

    P_GIVE_RESULT = re.compile(f"^You gave .+ \*\*[0-9,]+\*\* coins after a [0-9,]+% tax rate, now you have (-?[0-9,]+) and they've got [0-9,]+" + P_EOL)
    P_GIVE_ERROR = re.compile("^You only have ([0-9,]+) coins, you can't share that many$");

    T_SEARCH_OPTIONS = "Where do you want to search? Pick from the list below and type it in chat.\n"
    T_SEARCH_COOLDOWN = "You've already scouted the area for coins, try again in "

    def __init__(self, config_loser, config_winner):
        super().__init__()
        self.log = logging.getLogger("bot")
        self.bot_id = config_winner["bot_id"]
        self.bot_prefix = config_winner["bot_prefix"]
        self.config_loser = config_loser
        self.config_winner = config_winner
        self.loser_id = config_loser["user_id"]
        self.winner_id = config_winner["user_id"]
        self.owner_id = config_winner["owner_id"]
        self.typer_loser = TheTyper(config_loser["profile_id"], config_loser["type_url"])
        self.typer_winner = TheTyper(config_winner["profile_id"], config_winner["type_url"])
        self.typer_loser_q = Queue()
        self.typer_winner_txt = Queue()
        self.doing_it = False
        self.steal_result = None
        self.stolen_amount = 0
        self.loser_balance = 0
        self.cooldown_time = 0
        self.search_ok = False
        self.search_entered_location = False
        self.current_event = Event()
        self.current_handler = None
        self.extended_timeout = 0

    def get_prefixed_cmd(self, cmd):
        return self.bot_prefix + " " + cmd

    async def on_ready(self):
        self.log.info(f"Logged on as {self.user}")

    async def wait_for_handler(self, handler):
        self.extended_timeout = 0
        self.current_event.clear()
        self.current_handler = handler
        try:
            await asyncio.wait_for(self.current_event.wait(), 20)  # wait up to 20s
            self.current_handler = None
        except asyncio.exceptions.TimeoutError:
            while True:
                rem = self.extended_timeout - time.time()
                if rem <= 0:
                    break
                self.log.info(f"Waiting with extended timeout: {rem}s")
                try:
                    await asyncio.wait_for(self.current_event.wait(), rem)
                    self.current_handler = None
                    return
                except asyncio.exceptions.TimeoutError:
                    pass

    async def synctest(self):
        await self.typer_winner.lock.acquire()
        await self.typer_loser.lock.acquire()

        box_winner = TheTyper.get_input_box(self.typer_winner.driver)
        box_loser = TheTyper.get_input_box(self.typer_loser.driver)
        TheTyper.type_message(box_winner, "account 1")
        TheTyper.type_message(box_loser, "account 2")

        self.log.info(f"Pressing enter")
        TheTyper.do_send_message(box_winner)
        TheTyper.do_send_message(box_loser)

        self.typer_winner.lock.release()
        self.typer_loser.lock.release()

    async def do_it(self, channel):
        if self.doing_it:
            await channel.send("you are dumb, the process is already in progress")
            return
        self.doing_it = True
        await channel.send("gotcha, good luck")

        self.log.info("1. STEAL")
        while True:
            result, amount = await self.steal(self.winner_id)
            # result, amount = StealResult.FULL_AMOUNT, 1353345
            self.log.info(f"Steal completed: result={result} amount={amount}")
            if result == StealResult.NOT_ENOUGH_COINS:
                self.log.info(f"Giving ourself money from winner")
                await self.typer_winner.send_message(f"pls give <@!{self.loser_id}> 250")
                await asyncio.sleep(1)
                continue
            if result == StealResult.TIMEOUT:
                await asyncio.sleep(self.cooldown_time + 0.5)
                continue
            if result == StealResult.CAUGHT:
                await asyncio.sleep(self.config_loser["cooldown"]["steal"] + 0.5)
                continue
            if result == StealResult.TWO_MIN:
                self.log.info(f"Steal failed")
                await channel.send(f"<@!{self.owner_id}> steal failed :/")
                self.doing_it = False
                return
            if result == StealResult.SMALL_AMOUNT or result == StealResult.LARGE_AMOUNT or result == StealResult.FULL_AMOUNT:
                break

        self.log.info("2. THE RACE")
        self.log.info(f"Stolen {amount}")

        await self.typer_winner.lock.acquire()
        await self.typer_loser.lock.acquire()

        box_winner = TheTyper.get_input_box(self.typer_winner.driver)
        box_loser = TheTyper.get_input_box(self.typer_loser.driver)
        TheTyper.type_message(box_winner, "pls use reversal")
        TheTyper.type_message(box_loser, f"pls give <@!{self.winner_id}> {amount+250}")

        self.log.info(f"Pressing enter")
        TheTyper.do_send_message(box_winner)
        TheTyper.do_send_message(box_loser)

        self.typer_winner.lock.release()
        self.typer_loser.lock.release()

        self.loser_balance = 0
        await self.wait_for_handler(self.handle_race)

        self.log.info("3. DEATH")
        if self.loser_balance < 0:
            await self.suicide()

        self.log.info("DONE")
        await channel.send("we completed this process i guess?")
        self.doing_it = False

    async def suicide(self):
        first_attempt = True
        self.search_ok = False
        while not self.search_ok:
            if not first_attempt:
                await asyncio.sleep(self.config_loser["cooldown"]["search"])
            first_attempt = False
            self.search_entered_location = False
            await self.typer_loser.send_message("pls search")
            await self.wait_for_handler(self.handle_search)
            self.log.info(f"A search has completed: ok={self.search_ok}")

    async def steal(self, from_who):
        self.steal_result = None
        self.current_event.clear()
        await self.typer_loser.send_message(self.get_prefixed_cmd(f"steal <@!{from_who}>"))
        await self.wait_for_handler(self.handle_steal)
        return self.steal_result, self.stolen_amount

    async def handle_steal(self, message):
        if message.channel.id != self.config_loser["type_channel_id"]:
            return
        c = CooldownHelper.extract_cooldown(message, TheBot.T_STEAL_COOLDOWN)
        if c is not None:
            self.steal_result = StealResult.TIMEOUT
            self.cooldown_time = c
            return True
        if message.content == TheBot.T_STEAL_NOT_ENOUGH_COINS:
            self.steal_result = StealResult.NOT_ENOUGH_COINS
            return True
        if message.content == TheBot.T_STEAL_CAUGHT:
            self.steal_result = StealResult.CAUGHT
            return True
        if message.content == TheBot.T_STEAL_2_MIN:
            self.steal_result = StealResult.TWO_MIN
            return True
        for s, ss in [(TheBot.P_STEAL_SMALL_AMOUNT, StealResult.SMALL_AMOUNT), (TheBot.P_STEAL_LARGE_AMOUNT, StealResult.LARGE_AMOUNT), (TheBot.P_STEAL_FULL_AMOUNT, StealResult.FULL_AMOUNT)]:
            t = s.match(message.content)
            if t:
                self.steal_result = ss
                self.stolen_amount = parse_bot_int(t.group(1))
                return True
        return False

    async def handle_race(self, message):
        if message.channel.id != self.config_loser["type_channel_id"]:
            return
        t = TheBot.P_GIVE_RESULT.match(message.content)
        if t:
            self.loser_balance = parse_bot_int(t.group(1))
            return True
        t = TheBot.P_GIVE_ERROR.match(message.content)
        if t:
            self.loser_balance = parse_bot_int(t.group(1))
            return True
        return False

    async def handle_search(self, message):
        if message.channel.id != self.config_loser["type_channel_id"]:
            return
        if self.search_entered_location:
            self.log.info("Search msg: " + message.content)
            if "what are you THINKING man that's not a valid option from the list??" in message.content:
                return True
            if "You got off scot-free this time, but you better pay your fine next time or else the police might getcha" in message.content:
                return True
            if "The police are on your ass and they're coming for you " in message.content:
                self.log.info("Extended timeout for police")
                self.extended_timeout = time.time() + 60
                return False
            if "Area searched" in message.content and ("You drowned in a river of shit, how fun!" in message.content or "You contracted dog ass disease from touching dog shit. You died." in message.content or "You got hit by a car LOL." in message.content): # You contracted dog ass disease from touching dog shit. You died.
                self.search_ok = True
                return True
            if "Area searched" in message.content:
                return True
            if "The police are here, and they're after you!" in message.content:
                await self.typer_loser.send_message("0gleeb57ne")
                self.search_ok = True
                return True

            return False
        c = CooldownHelper.extract_cooldown(message, TheBot.T_SEARCH_COOLDOWN)
        if c is not None:
            return True
        preferences = ["street", "car", "dog", "purse", "pocket", "sewer", "dumpster", "coat", "attic"]
        if message.content.startswith(TheBot.T_SEARCH_OPTIONS):
            options, _, _ = message.content[len(TheBot.T_SEARCH_OPTIONS):].partition("\n")
            options = options.split(", ")
            options = [o[1:-1] for o in options if len(o) > 0 and o[0] == '`' and o[-1] == '`']
            for s in preferences:
                if s in options:
                    await self.typer_loser.send_message(s)
                    self.search_entered_location = True
                    return False
            await self.typer_loser.send_message("neither")
            self.search_entered_location = True
            return False
        return False

    async def on_message(self, message):
        if message.author.id == self.winner_id:
            self.typer_winner.on_message(message)
        if message.author.id == self.loser_id:
            self.typer_loser.on_message(message)
        if message.author.id == self.bot_id:
            message.content = filter_out_hint(message.content)
            if self.current_handler is not None:
                if await self.current_handler(message):
                    self.current_handler = None
                    self.current_event.set()

        if message.content.startswith("plz ") and (message.author.id == self.owner_id):
            args = message.content[4:].split(" ")
            if args[0] == "doit":
                await self.do_it(message.channel)
            if args[0] == "synctest":
                await self.synctest()
            if args[0] == "suicide":
                await self.suicide()


import sys

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(name)s %(message)s', stream=sys.stdout)
logging.getLogger("bot").setLevel(logging.DEBUG)

from config_alt1 import config
config_winner = dict(config)
from config_alt2 import config
config_loser = dict(config)

bot = TheBot(config_loser, config_winner)
bot.run(config_winner["token"])
