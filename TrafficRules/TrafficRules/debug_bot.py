"""
Diagnostic helper for @ca_driver_bot — inspect what the bot actually sends.

Run:
    python debug_bot.py
"""

import asyncio

from telethon import TelegramClient

from ca_driver_bot_collector import API_ID, API_HASH, BOT_USERNAME, DELAY


async def debug():
    if API_ID == 0 or API_HASH == "":
        print("ERROR: fill in API_ID / API_HASH in credentials.py")
        return

    print("Connecting...")
    async with TelegramClient("ca_driver_session", API_ID, API_HASH) as client:
        bot = await client.get_entity(BOT_USERNAME)
        print(f"Bot: {BOT_USERNAME}\n")

        await client.send_message(bot, "/start")
        await asyncio.sleep(DELAY)
        await client.send_message(bot, "/test")
        await asyncio.sleep(DELAY * 2)

        print("=" * 60)
        print("LATEST MESSAGES FROM THE BOT:")
        print("=" * 60)
        async for msg in client.iter_messages(bot, limit=5):
            print(f"\n--- msg.id={msg.id} ---")
            print(f"  text/message : {repr(msg.text)}")
            print(f"  media        : {type(msg.media).__name__ if msg.media else None}")
            if msg.buttons:
                print(f"  buttons      :")
                for row in msg.buttons:
                    for btn in row:
                        print(f"    [{btn.text}]  data={getattr(btn, 'data', None)}")
            else:
                print(f"  buttons      : none")

        print("\n" + "=" * 60)
        print("Trying to click the first button of the latest message with buttons:")
        async for msg in client.iter_messages(bot, limit=5):
            if msg.buttons:
                print(f"  Clicking the first button: [{msg.buttons[0][0].text}]")
                await msg.buttons[0][0].click()
                await asyncio.sleep(DELAY * 2)
                async for new_msg in client.iter_messages(bot, limit=2):
                    print(f"\n--- REPLY msg.id={new_msg.id} ---")
                    print(f"  text  : {repr(new_msg.text)}")
                    print(f"  media : {type(new_msg.media).__name__ if new_msg.media else None}")
                    if new_msg.buttons:
                        for row in new_msg.buttons:
                            for btn in row:
                                print(f"  btn: [{btn.text}]")
                break
        else:
            print("  No messages with buttons were found.")


asyncio.run(debug())
