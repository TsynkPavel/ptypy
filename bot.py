import os
import argparse

import asyncio
import telegram

TOKEN = '7627721826:AAHrzkzWrGAlgw36fTE10GflGI2fcyGqeGo'
RECIPIENT_ID = '403248839'

async def send(chat, args):
    message = ""
    for param in args.folder.split("/"):
        if "_" in param:
            message += param.replace("_", " ")
            message += "\n"
    
    await telegram.Bot(TOKEN).send_message(chat_id=chat, disable_notification=False, text=message)
    
    # for filename in sorted(os.listdir(subfolder)):
    #     photo_path = os.path.join(subfolder, filename)

    for item in os.listdir(args.folder):
        if os.path.isfile(os.path.join(args.folder, item)):
            with open(os.path.join(args.folder, item), 'rb') as f:
                await telegram.Bot(TOKEN).send_document(chat_id=chat, document=f, disable_notification=True)

    # for item in args.files:
    #     if os.path.isfile(item):
    #         with open(item, 'rb') as f:
    #             await telegram.Bot(TOKEN).send_document(chat_id=chat, document=f, disable_notification=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", dest="folder", type=str)
    parser.add_argument("--file", dest="files", type=str, action="append")
    # parser.add_argument("--subfolder", dest="subfolder", type=str)
    args = parser.parse_args()
    
    asyncio.run(send(RECIPIENT_ID, args))