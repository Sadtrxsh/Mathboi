cooldown_normal = {
    "beg": 40,
    "search": 30,
    "fish": 45,
    "hunt": 60,
    "meme": 60,
    "gamble": 10,
    "blackjack": 10,
    "dep": 10,
    "gift": 20,
    "give": 20,
    "steal": 30
}
cooldown_donator = {
    "beg": 25,
    "search": 20,
    "fish": 30,
    "hunt": 40,
    "meme": 45,
    "gamble": 5,
    "blackjack": 5,
    "dep": 0.5,
    "gift": 10,
    "give": 10,
    "steal": 10
}

config = {
    # system
    "token": "BOT_TOKEN",
    "blahjack_exe": "blahjack",

    # bot
    "max_reply_s": 10,
    "retry_on_timeout_s": 10,
    "search_preference": ["tree", "couch", "mailbox", "dresser", "discord", "bed", "attic", "laundromat", "grass", "shoe"],
    "autodep_threshold": [4000, 8000],
    "autodep_result": [1000, 3500],
    # "autodep_threshold": [400, 800],
    # "autodep_result": [100, 350],

    # memer
    "bot_id": 270904126974590976,
    "bot_prefix": "pls",

    # owner
    "owner_id": YOUR_DISCORD_ACCOUNT_ID_FOR_IMPORTANT_NOTIFICATIONS_FROM_THE_BOT_THAT_PING_YOU,
    "notify_channel_id": CHANNEL_ID_WHERE_NOTIFICATIONS_ARE_POSTED,
}

config.update({
    "profile_id": "theBot",
    "user_id": BOT_ACCOUNT_USER_ID,
    "type_channel_id": CHANNEL_ID_WHERE_THE_BOT_TYPES,
    "type_url": "https://discord.com/channels/SERVER/CHANNEL_ID_WHERE_THE_BOT_TYPES",
    "cooldown": cooldown_donator, # or cooldown_normal
    "event_notify": True # will send event notifications to notify channel
})
