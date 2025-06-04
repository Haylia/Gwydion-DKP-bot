import discord
import random
import os
import gspread
from datetime import datetime as dt
import time
import ast
import pytesseract
from PIL import Image
import requests
from io import BytesIO
import re
import cv2
import numpy as np
import asyncio
import traceback
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
from discord.ext import commands, tasks
from discord import guild, embeds, Embed, InteractionResponse
from discord.utils import get
intents = discord.Intents.all()
client = commands.Bot(command_prefix = '$', intents = intents, case_insensitive = True)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# google account 1: general kp use (lia-paranoid)
googleacc1 = gspread.service_account(filename = "paranoid-kp-bot-43a1e7152411.json") # replace with the service account for the bot in googles apis (https://docs.gspread.org/en/latest/oauth2.html)
bot1sheet = googleacc1.open_by_url("https://docs.google.com/spreadsheets/d/1Izu2wSmi0aEQCWTvfLAXX0ucXR2223ILzFxTiQXcl80/edit#gid=0")
bot1ws1 = bot1sheet.get_worksheet(0)
bot1ws2 = bot1sheet.get_worksheet(1) 
bot1ws3 = bot1sheet.get_worksheet(2) 
bot1ws4 = bot1sheet.get_worksheet(3) 
bot1ws5 = bot1sheet.get_worksheet(4) 
bot1ws6 = bot1sheet.get_worksheet(5)
bot1ws7 = bot1sheet.get_worksheet(6)
bot1ws8 = bot1sheet.get_worksheet(7)
bot1ws9 = bot1sheet.get_worksheet(8)
bot1ws10 = bot1sheet.get_worksheet(9)
bot1ws11 = bot1sheet.get_worksheet(10)
print("accessing the spreadsheet for account 1")

# google account 2: rbpp (lia-bkp-bot)
googleacc2 = gspread.service_account(filename = "paranoid-kp-bot-513a901effbc.json") # replace with the service account for the bot in googles apis (https://docs.gspread.org/en/latest/oauth2.html)
bot2sheet = googleacc2.open_by_url("https://docs.google.com/spreadsheets/d/1Izu2wSmi0aEQCWTvfLAXX0ucXR2223ILzFxTiQXcl80/edit#gid=0")
bot2ws1 = bot2sheet.get_worksheet(0) 
bot2ws2 = bot2sheet.get_worksheet(1) 
bot2ws3 = bot2sheet.get_worksheet(2) 
bot2ws4 = bot2sheet.get_worksheet(3)
bot2ws5 = bot2sheet.get_worksheet(4)
bot2ws6 = bot2sheet.get_worksheet(5)
bot2ws7 = bot2sheet.get_worksheet(6)
bot2ws8 = bot2sheet.get_worksheet(7)
bot2ws9 = bot2sheet.get_worksheet(8)
bot2ws10 = bot2sheet.get_worksheet(9)
bot2ws11 = bot2sheet.get_worksheet(10)
print("accessing the spreadsheet for account 2")

# google account 3: loot and logging (lia-dkp-bot)
googleacc3 = gspread.service_account(filename = "paranoid-kp-bot-29090cc5a87a.json") # replace with the service account for the bot in googles apis (https://docs.gspread.org/en/latest/oauth2.html)
bot3sheet = googleacc3.open_by_url("https://docs.google.com/spreadsheets/d/1Izu2wSmi0aEQCWTvfLAXX0ucXR2223ILzFxTiQXcl80/edit#gid=0")
bot3ws1 = bot3sheet.get_worksheet(0) 
bot3ws2 = bot3sheet.get_worksheet(1)  
bot3ws3 = bot3sheet.get_worksheet(2) 
bot3ws4 = bot3sheet.get_worksheet(3)
bot3ws5 = bot3sheet.get_worksheet(4)
bot3ws6 = bot3sheet.get_worksheet(5)
bot3ws7 = bot3sheet.get_worksheet(6)
bot3ws8 = bot3sheet.get_worksheet(7)
bot3ws9 = bot3sheet.get_worksheet(8)
bot3ws10 = bot3sheet.get_worksheet(9)
bot3ws11 = bot3sheet.get_worksheet(10)
bot3sheet2 = googleacc3.open_by_url("https://docs.google.com/spreadsheets/d/1GFWWkCs5jJNbgt8b_rizyOv8qIGdKh4550B5EaDtM_k/edit#gid=0")
bot3ws12 = bot3sheet2.get_worksheet(0) # bid tracking
bot3ws13 = bot3sheet2.get_worksheet(1) # player tracking
print("accessing the spreadsheet for account 3")

# google account 4: clan member reads (lia-leaderboard-bot)
googleacc4 = gspread.service_account(filename = "paranoid-kp-bot-b724a91cd608.json") # replace with the service account for the bot in googles apis (https://docs.gspread.org/en/latest/oauth2.html)
bot4sheet = googleacc4.open_by_url("https://docs.google.com/spreadsheets/d/1Izu2wSmi0aEQCWTvfLAXX0ucXR2223ILzFxTiQXcl80/edit#gid=0")
bot4ws1 = bot4sheet.get_worksheet(0) 
bot4ws2 = bot4sheet.get_worksheet(1) 
bot4ws3 = bot4sheet.get_worksheet(2) 
bot4ws4 = bot4sheet.get_worksheet(3) 
bot4ws5 = bot4sheet.get_worksheet(4) 
bot4ws6 = bot4sheet.get_worksheet(5) 
bot4ws7 = bot4sheet.get_worksheet(6) 
bot4ws8 = bot4sheet.get_worksheet(7) 
bot4ws9 = bot4sheet.get_worksheet(8) 
bot4ws10 = bot4sheet.get_worksheet(9) 
bot4ws11 = bot4sheet.get_worksheet(10) 
print("accessing the spreadsheet for account 4")

# google account 5: admin use (lia-reaping-bot)
googleacc5 = gspread.service_account(filename = "paranoid-kp-bot-410d8c0e26d1.json") # replace with the service account for the bot in googles apis (https://docs.gspread.org/en/latest/oauth2.html)
bot5sheet = googleacc5.open_by_url("https://docs.google.com/spreadsheets/d/1Izu2wSmi0aEQCWTvfLAXX0ucXR2223ILzFxTiQXcl80/edit#gid=0")
bot5ws1 = bot5sheet.get_worksheet(0) 
bot5ws2 = bot5sheet.get_worksheet(1) 
bot5ws3 = bot5sheet.get_worksheet(2) 
bot5ws4 = bot5sheet.get_worksheet(3) 
bot5ws5 = bot5sheet.get_worksheet(4)
bot5ws6 = bot5sheet.get_worksheet(5)
bot5ws7 = bot5sheet.get_worksheet(6)
bot5ws8 = bot5sheet.get_worksheet(7)
bot5ws9 = bot5sheet.get_worksheet(8)
bot5ws10 = bot5sheet.get_worksheet(9)
bot5ws11 = bot5sheet.get_worksheet(10)
bot5ws12 = bot5sheet.get_worksheet(11) 
bot5ws13 = bot5sheet.get_worksheet(12)
print("accessing the spreadsheet for account 5")

vkp_bosses = {"Crom": 125}
gkp_bosses = {"Reaver":5, "Lich":5, "Bt":50}
pkp_bosses = {"Bane": 10}
akp_bosses = {"Gele":50, "Base":10, "Prime":20}
rbppunox_bosses = {"Unox5":1, "Unox6": 1}
dpkp_bosses = {"Dino":75, "Dinofast":100}
rbpp_bosses = {"Unox5":1, "Rev6":1, "Kroth6":1, "Gron6":1, "Unox6": 1, "Hrung":1, "Mord":1, "Necro":1, "Dino":1, "Dinofast":1, "Bane": 1, "Bt":1, "Base":1, "Prime":1, "Gele":1, "Crom":1}


bidslastupdate = time.time()

guilds=[814048353603813376,1116453904922726544,1215443011400376391,920411637297598484]

print("setup done")

def toBool(string):
    string = string.capitalize()
    if string == "True":
        return True
    else:
        return False
    
def find_name(name, list):
    # name might be misspelled, so we will check for partial matches and return the closest one
    ogname = name
    # print("looking for " + name + " in " + str(list))
    name = name.lower()
    for i in range(len(list)):
        if name == list[i].lower():
            #print("found " + list[i] + " in " + str(list) + " for " + ogname)
            return list[i], True, False
    name = name.replace(" ","")
    for i in range(len(list)):
        if name == list[i].lower().replace(" ",""):
            #print("found " + list[i] + " in " + str(list) + " for " + ogname)
            return list[i], True, True
    #print("could not find " + name + " in " + str(list) + " for " + ogname)
    return None, False, False
            
    
@tasks.loop(seconds=60)
async def bidloop():
    global bidslastupdate
    bidslastupdate = time.time()
    twelvehoursinseconds = 43200
    resultschannel = 1232811852811993169
    try:
        bidopentimes = bot3ws12.col_values(1)
        itemids = bot3ws12.col_values(2)
        itemnames = bot3ws12.col_values(3)
        itemkp = bot3ws12.col_values(4)
        bidstatus = bot3ws12.col_values(5)
        combilist = list(zip(bidopentimes, itemids, bidstatus, itemnames, itemkp))
        useritemids = bot3ws13.col_values(3)
        useritemstatus = bot3ws13.col_values(7)
        combiuserlist = list(zip(useritemids,useritemstatus))
        for i in range(1, len(combilist)):
            if combilist[i][2] == "Open" and float(time.time()) > float(combilist[i][0]) + twelvehoursinseconds:
                bot3ws12.update_cell(int(combilist[i][1]) + 1, 5, "Closed")
                for j in range(1, len(combiuserlist)):
                    if combiuserlist[j][1] == "Open" and combiuserlist[j][0] == combilist[i][1]:
                        bot3ws13.update_cell(j + 1, 7, "Closed")
                cell = bot3ws12.find(combilist[i][1])
                row_num = cell.row
                print(row_num)
                bidrow = bot3ws12.row_values(row_num)
                #cut off everything but the player name and the bids
                print(bidrow)
                bidrow = bidrow[5:]
                print(bidrow)
                # split the rest alternating between the player and their bid
                length = len(bidrow)
                results = []
                for k in range(length//2):
                    player = bidrow.pop(0)
                    bid = bidrow.pop(0)
                    results.append([player, bid])
                    print(player, bid)
                results.sort(key = lambda x: x[1], reverse = True)
                msgtosend = "The bid for " + combilist[i][3] + " has been closed. The highest bidder was " + results[0][0] + " with a bid of " + str(results[0][1]) + " " + combilist[i][4]
                print(msgtosend)
                for k in range(1, len(results)):
                    msgtosend += "\n" + results[k][0] + " bid " + str(results[k][1]) + " " + combilist[i][4]
                print(msgtosend)
                await client.get_channel(resultschannel).send(msgtosend)
                
    except Exception as e:
        print(e, e.__traceback__.tb_lineno)



@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    bidloop.start()

    
@client.event
async def on_message(msg):
    if msg.author == client.user:
        return
    checkformemes = msg.content.lower()
    if checkformemes.startswith("$"):
        print("command used: " + str(msg.content) + " by " + str(msg.author))
    # format here
    # message starts with command
    # any image just google images right click copy image address
    if checkformemes == "chico":
        await msg.channel.send("is a 69 year old vegan teacher")
        await msg.channel.send("https://imgur.com/blrOjjE")
    if checkformemes == "thank you winston":
        await msg.channel.send("https://tenor.com/view/oh-yeah-winston-dance-overwatch-gorrila-gif-22531380")
    if checkformemes == "Axy":
        await msg.channel.send("STOP SPENDING MONEY")
    if checkformemes == "deez":
        await msg.channel.send("NUTS (gottem)")
    if checkformemes == "luv":
        await msg.channel.send("ily2 <3")
    if checkformemes == "jax":
        await msg.channel.send("is one sexy mofo")
    if checkformemes == "fax":
        await msg.channel.send("no printer")
    if checkformemes == "cap":
        await msg.channel.send("no cap 🧢")
    if checkformemes == "behave":
        await msg.channel.send("no promises 👀")
    if checkformemes == "m0ney":
        await msg.channel.send("go to sleep")
    if checkformemes == "sleep":
        await msg.channel.send("is for the weak")
    if checkformemes == "nobu":
        await msg.channel.send("got no bitches")
    if checkformemes == "exemp":
        await msg.channel.send("I would just like to say on behalf of Exemp that we do not condone our members causing issues with other clans and that anything said does not reflect our clan as a whole. I am in the process of talking to the parties involved to sort things out as I believe the vast majority of us want to see a fun and non-toxic environment for everyone. \n That being said, I believe this should have been brought to Exemp leaders directly and would appreciate the opportunity to resolve situations before thy are allowed to escalate in the future. \n If anyone has any concerns regarding Exemp or our members please reach out to me directly and I will do my best to mediate the situation. \n Thank you.")
    if checkformemes == "dark":
        await msg.channel.send("likes jalapeño")
    if checkformemes == "jalapeño":
        await msg.channel.send("DEEZ NUTZ JALAPEÑO MOUTH")
    if checkformemes == "mz":
        await msg.channel.send("is in the chats")
    if checkformemes == "trimmings":
        await msg.channel.send("guys. the debuff uptime in relentless is abyssmal. we need people with grims to time them and the phoenix to always be up! how is this a hard concept to grasp")
    if checkformemes == "magi jr":
        await msg.channel.send("is outdated")
    if checkformemes == "renz":
        await msg.channel.send("is the best pvp rogue on server 🤩🤩🤩🤩")
    if checkformemes == "t1ny":
        await msg.channel.send("dick")
    if checkformemes == "bad chain":
        await msg.channel.send("chain sux")
    if checkformemes == "festo":
        await msg.channel.send("are you tired of bidding? Not being able to sell items? Join me in this clan! All drops are rolled to class! No rules! no recruiting period! No more bidding! We are here for personal gain!")
    if checkformemes == "tinyarrow":
        await msg.channel.send("Hello guys, I'm quitting CH. The rewards this game offers just aren't worth the effort and time we all put in, and a busy real life schedule demands my full attention at this point. It was great to meet you all and raid for the past year.  Stay relentless!")
    if checkformemes == "surya":
        await msg.channel.send("meow yusss")
        await msg.channel.send("https://imgur.com/dgVjK3T")
    if checkformemes == "zeroroot":
        await msg.channel.send("hello every one I am sorry to inform you with sad news but I am quitting the game I have no more time to play this game as I am busy with work and irl things I will be leaving clan and all chats and will be selling all my things please pm if you would like to buy any of my stuff take care every one and have a good rest of your day")
    if checkformemes == "radi":
        await msg.channel.send("Hi all. I'm selling out, with a heavy heart. I love yall. I'll sell to rele first. Goodluck in life ❤️")
    if checkformemes == "slap":
        await msg.channel.send("https://imgur.com/BZLb5g9")
    if checkformemes == "swag":
        await msg.channel.send("sux")
    if checkformemes.startswith("who is"):
        person = checkformemes.split(" ")[2]
        if person == "keni":
            await msg.channel.send("Keni is Laur, Laur is Keni")
        elif person == "m0ney" or person == "money":
            await msg.channel.send("For the blind, He is vision. For the hungry, He is the chef. For the thirsty, He is water. If " + person + " thinks, I agree. If " + person + " speaks, I’m listening. If " + person + " has one fan, it is me. If "+ person + " has no fans, I do not exist.")
        else:
            pass
    if checkformemes == "reda sucks at programming":
        await msg.channel.send("water is wet")
    if checkformemes == "reda":
        await msg.channel.send("sucks at programming")
    if checkformemes == "deca":
        await msg.channel.send("https://media.discordapp.net/attachments/1119563151600529468/1166217517862228010/image.png?ex=6629ceb3&is=66287d33&hm=8b2e694af7728d701520eb4fc84c9ce8102814b4fe740d619f8f70f54c837961&=&format=webp&quality=lossless&width=507&height=514")
    if checkformemes == "cheating":
        await msg.channel.send("https://media.discordapp.net/attachments/1119563151600529468/1155310050643021926/IMG_1836.png?ex=6629ad54&is=66285bd4&hm=96b663e76bd9b31ca1aa154c44d4786845febee91e4e514b95bcc1f2425b947a&=&format=webp&quality=lossless&width=365&height=481")
    if checkformemes == "siuuu":
        await msg.channel.send("shud give magi white oni")
    if checkformemes == "siuu":
        await msg.channel.send("sux")
    if checkformemes == "boo":
        await msg.channel.send("BEEZ")
    if checkformemes == "lizzo":
        await msg.channel.send("""NNN
When the nut was plentiful,
When the nut was tender

Because I was fasting from the nut,
I go outside to clear my mind 

But I see a NUT TREE,
I see nuts of every kind.

And so I begin to wonder,
If fasting from the nut was a blunder

Should I just go crazy?
Or should I release the thunder?

But oh no, I made a bet that could resist in that,
And I’m not about to pay that 5 dollars.

A week left in my journey,
For the nut I am yearney
                               
The nut will not bug me,
I’m not a roller polley.

I am a man,
The nut will not control me.


So December comes blooming 
Bloomy like a daisy,
Best believe now that it’s December,
Your boy going crazy""")
    if checkformemes == "mean":
        await msg.channel.send("listen here u lil shit")
    if checkformemes == "lit":
        await msg.channel.send("stfu reda")
    await client.process_commands(msg)

@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send("you made an error in the command arguments")
        print(error)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("there is a required section missing in this command")
        print(error)
    elif isinstance(error, commands.CommandInvokeError):
        await ctx.send("Winston is crying himself to sleep (google sheets may have been rate limited, there was an error, or reda sucks at programming)")
        # test all the service accounts to see if they are rate limited
        # print out the error
        print(error)
        try:
            bot1ws1.get_all_records()
        except Exception as e:
            print("bot1 is rate limited")
        try:
            bot2ws1.get_all_records()
        except Exception as e:
            print("bot2 is rate limited")
        try:
            bot3ws1.get_all_records()
        except Exception as e:
            print("bot3 is rate limited")
        try:
            bot4ws1.get_all_records()
        except Exception as e:
            print("bot4 is rate limited")
        try:
            bot5ws1.get_all_records()
        except Exception as e:
            print("bot5 is rate limited")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("command doesn't exist. yet? try $information for text based help or $help for a full list of commands. If what you want isn't there, DM reda to get it added!")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("This command can't be used in DMs")
    else:
        await ctx.send("Winston got confused")
        raise error



@client.command(guild_ids = guilds)
async def startbid(ctx, item, startprice, kp, startbidder):
    """Starts a bid for a new item"""
    kp = kp.upper()
    if kp not in ["VKP", "GKP", "PKP", "AKP", "RBPPUNOX", "DPKP"]:
        await ctx.send("Invalid kp type! Please use VKP, GKP, PKP, AKP, RBPPUNOX, DPKP")
        return
    #get the bottom row for the id
    id = len(bot3ws12.col_values(1))
    startprice = int(startprice)
    bidrow = [time.time(), id, item, kp, "Open", startbidder, startprice]
    bot3ws12.append_row(bidrow)
    userrow = [time.time(), str(ctx.author.id), id, item, startprice, kp, "Open", startbidder]
    bot3ws13.append_row(userrow)
    await ctx.send("Bid for " + item + " has started at " + str(startprice) + " " + kp + " by " + startbidder)
    await ctx.send("The ID for this bid is " + str(id) + ". Please use this to bid on the item!")

@client.command(guild_ids = guilds)
async def getitemname(ctx):
    """gets the item name from an image"""
    image = ctx.message.attachments[0]
    response = requests.get(image.url)
    img = Image.open(BytesIO(response.content))
    processed = preprocessforgreen(img)
    text = pytesseract.image_to_string(processed)
    item_regex = r'(\b[A-Z][a-z]{1,}(?:\s+(?:of\s+the|of|the|and))?\s+[A-Z][a-z]{1,}((\s+(?:of\s+the|of|the|and))?\s+[A-Z][a-z]{1,})*)'
    extracted_items = re.findall(item_regex, text, re.DOTALL)
    if not extracted_items:
        await ctx.send("No items were found in the image.")
        return
    item_name = ' '.join(extracted_items[0][0].split())
    await ctx.send(item_name)


def preprocessforgreen(img):
    img_cv = np.array(img)
    img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
    lower_green = np.array([40, 40, 40])
    upper_green = np.array([70, 255, 255])
    mask = cv2.inRange(hsv, lower_green, upper_green)
    green_text = cv2.bitwise_and(img_cv, img_cv, mask=mask)
    gray = cv2.cvtColor(green_text, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    final_img = Image.fromarray(binary)
    return final_img


@client.command(guild_ids = guilds)
async def sendbid(ctx, id, price, bidder):
    """command for sending a bid to the bid sheet"""
    id = int(id)
    price = int(price)
    bidrow = bot3ws12.find(str(id))
    bidrownum = bidrow.row
    bidrow = bot3ws12.row_values(bidrownum)
    if bidrow[4] == "Open":
        bidrow.append(bidder)
        bidrow.append(price)
        bot3ws12.update([bidrow], "A" + str(bidrownum), value_input_option='USER_ENTERED')
        userrow = [time.time(), str(ctx.author.id), id, bidrow[2], price, bidrow[3], "Open", bidder]
        bot3ws13.append_row(userrow, value_input_option="raw")
        await ctx.send("Bid for " + bidrow[2] + " has been placed at " + str(price) + " " + bidrow[3] + " by " + bidder)
    else:
        await ctx.send("This bid is closed!")

@client.command(guild_ids = guilds)
async def cancelbid(ctx, id, price, bidder):
    """command for cancelling a bid"""
    # check on the user bids sheet if the bid exists
    userids = bot3ws13.col_values(2)
    itemids = bot3ws13.col_values(3)
    itemprices = bot3ws13.col_values(5)
    toonnames = bot3ws13.col_values(8)
    combili = list(zip(userids, itemids, itemprices, toonnames))
    bidfound = False
    for i in range(1, len(combili)):
        if combili[i][0] == str(ctx.author.id) and combili[i][1] == id and combili[i][2] == price and combili[i][3] == bidder:
            rownum = i + 1
            bot3ws13.delete_rows(rownum)
            bidfound = True
    if bidfound:
        #get the row for the item from the main sheet
        bidrow = bot3ws12.find(str(id))
        bidrownum = bidrow.row
        bidrow = bot3ws12.row_values(bidrownum)
        #remove the bidder price from the bid row
        #check that the bidder and price are sequential on the row
        print(bidder, price)
        for i in range(5, len(bidrow)):
            print(bidrow[i],bidrow[i+1])
            if bidrow[i] == bidder and bidrow[i + 1] == price:
                bidrow.pop(i)
                bidrow.pop(i)
                break
        if(len(bidrow) <= 6):
            bot3ws12.update_cell(bidrownum, 5, "Closed")
            await ctx.send("The bid for " + bidrow[2] + " has been closed. " + bidder + " has cancelled their bid")
        else:
        #update the bid row
            bidrow.append("")
            bidrow.append("")
            bot3ws12.update([bidrow], "A" + str(bidrownum), value_input_option='USER_ENTERED')
        await ctx.send("Bid for " + id + " with bid " + price + " has been cancelled")
    


@client.command(guild_ids = guilds)
async def bidtimeinfo(ctx):
    global bidslastupdate
    currenttime = time.time()
    timepassed = currenttime - bidslastupdate
    await ctx.send("The last bid update was " + str(round(timepassed, 2)) + " seconds ago")

@client.command(guild_ids = guilds)
async def mybids(ctx):
    """Shows the bids you have placed"""
    user = ctx.author.id
    userids = bot3ws13.col_values(2)
    userbids = []
    for i in range(len(userids)):
        if userids[i] == str(user):
            userbids.append(bot3ws13.row_values(i + 1))
    if not userbids:
        await ctx.send("You have no bids placed")
    else:
        for i in range(len(userbids)):
            await ctx.send("You have bid " + str(userbids[i][4]) + " " + userbids[i][5] + " on " + userbids[i][3] + ", Auction ID: " + str(userbids[i][2]) + ", Bidder: " + userbids[i][7] + ", Status: " + userbids[i][6])


@client.command(guild_ids = guilds)
async def bidinfo(ctx, id):
    """Shows the info for a bid"""
    try:
        id = int(id)
        # bidrow = bot3ws12.find(str(id))
        # search column 2 for the id
        bidrow = bot3ws12.find(str(id), in_column=2)
        if bidrow:
            bidrownum = bidrow.row
            bidrow = bot3ws12.row_values(bidrownum)
            timeleft = float(bidrow[0]) + 43200 - time.time()
            hoursleft = timeleft // 3600
            minutesleft = (timeleft % 3600) // 60
            timeleft = str(int(hoursleft)) + " hours and " + str(int(minutesleft)) + " minutes"
            await ctx.send("Bid ID " + str(bidrow[1]) + " for " + bidrow[2] + " is currently " + bidrow[4] + " with a starting bid of " + str(bidrow[6]) + " " + bidrow[3])
            if timeleft.startswith("-"):
                timeleft = timeleft[1:]
                await ctx.send("This bid for " + bidrow[2] + " ended " + timeleft + " ago")
            else:
                await ctx.send("This bid was opened at " + bidrow[0] + " and has " + timeleft + " left")
        else:
            await ctx.send("No bid with that ID exists")
    except Exception as e:
        print(e)
        await ctx.send(e)


@client.command(guild_ids = guilds)
@commands.has_any_role("General", "REDALiCE")
async def addpoints(ctx, playername, pointtype, earned, spent, adjusted):
    """setup command for initializing points on the sheet. only to be used in setup"""
    pointtype = pointtype.upper()
    if pointtype not in ["VKP", "GKP", "PKP", "AKP", "RBPPUNOX", "DPKP", "RBPP"]:
        await ctx.send("Invalid point type! Please use VKP, GKP, PKP, AKP, RBPPUNOX, DPKP, or RBPP")
        return
    earned = float(earned)
    spent = float(spent)
    adjusted = float(adjusted)
    findnames, caps, spaces = find_name(playername, bot5ws1.col_values(1))
    if not findnames:
        await ctx.send("Player not found")
    else:
        playername = findnames
    if pointtype == "VKP":
        # using the playername, find the row number
        playerrow = bot5ws2.find(playername)
        rownum = playerrow.row
        # earned spent and adjusted are in cols d e f
        bot5ws2.update_cell(rownum, 4, earned)
        bot5ws2.update_cell(rownum, 5, spent)
        bot5ws2.update_cell(rownum, 6, adjusted)
        await ctx.send("VKP for " + playername + " has been updated")
    elif pointtype == "GKP":
        playerrow = bot5ws3.find(playername)
        rownum = playerrow.row
        bot5ws3.update_cell(rownum, 4, earned)
        bot5ws3.update_cell(rownum, 5, spent)
        bot5ws3.update_cell(rownum, 6, adjusted)
        await ctx.send("GKP for " + playername + " has been updated")
    elif pointtype == "PKP":
        playerrow = bot5ws4.find(playername)
        rownum = playerrow.row
        bot5ws4.update_cell(rownum, 4, earned)
        bot5ws4.update_cell(rownum, 5, spent)
        bot5ws4.update_cell(rownum, 6, adjusted)
        await ctx.send("PKP for " + playername + " has been updated")
    elif pointtype == "AKP":
        playerrow = bot5ws5.find(playername)
        rownum = playerrow.row
        bot5ws5.update_cell(rownum, 4, earned)
        bot5ws5.update_cell(rownum, 5, spent)
        bot5ws5.update_cell(rownum, 6, adjusted)
        await ctx.send("AKP for " + playername + " has been updated")
    elif pointtype == "RBPPUNOX":
        playerrow = bot5ws6.find(playername)
        rownum = playerrow.row
        bot5ws6.update_cell(rownum, 4, earned)
        bot5ws6.update_cell(rownum, 5, spent)
        bot5ws6.update_cell(rownum, 6, adjusted)
        await ctx.send("RBPPUNOX for " + playername + " has been updated")
    elif pointtype == "DPKP":
        playerrow = bot5ws7.find(playername)
        rownum = playerrow.row
        bot5ws7.update_cell(rownum, 4, earned)
        bot5ws7.update_cell(rownum, 5, spent)
        bot5ws7.update_cell(rownum, 6, adjusted)
        await ctx.send("DPKP for " + playername + " has been updated")
    elif pointtype == "RBPP":
        playerrow = bot5ws8.find(playername)
        rownum = playerrow.row
        bot5ws8.update_cell(rownum, 4, earned)
        bot5ws8.update_cell(rownum, 5, spent)
        bot5ws8.update_cell(rownum, 6, adjusted)
        await ctx.send("RBPP for " + playername + " has been updated")

@client.command(guild_ids = guilds)
@commands.has_any_role("General", "REDALiCE")
async def addallearned(ctx, playername, VKP, GKP, PKP, AKP, RBPPUNOX, DPKP, RBPP):
    """Adds all the points earned to the player in the order VKP, GKP, PKP, AKP, RBPPUNOX, DPKP, RBPP"""
    playerrow = bot5ws2.find(playername)
    rownum = playerrow.row
    bot5ws2.update_cell(rownum, 4, float(VKP))
    playerrow = bot5ws3.find(playername)
    rownum = playerrow.row
    bot5ws3.update_cell(rownum, 4, float(GKP))
    playerrow = bot5ws4.find(playername)
    rownum = playerrow.row
    bot5ws4.update_cell(rownum, 4, float(PKP))
    playerrow = bot5ws5.find(playername)
    rownum = playerrow.row
    bot5ws5.update_cell(rownum, 4, float(AKP))
    playerrow = bot5ws6.find(playername)
    rownum = playerrow.row
    bot5ws6.update_cell(rownum, 4, float(RBPPUNOX))
    playerrow = bot5ws7.find(playername)
    rownum = playerrow.row
    bot5ws7.update_cell(rownum, 4, float(DPKP))
    playerrow = bot5ws8.find(playername)
    rownum = playerrow.row
    bot5ws8.update_cell(rownum, 4, float(RBPP))
    await ctx.send("All points for " + playername + " have been updated")


@client.command(guild_ids = guilds)
async def inputterinfo(ctx):
     """Displays the help for point inputters"""
     embed = discord.Embed(title = "Info Dump", colour=discord.Color.orange())
     embed.add_field(name = "Bosses", value = "Mono, Osan, Rev6, Kroth6, Gron6, Unox5, Unox6, Hrung, Mord, Necro, Bane, Base, Prime, Gele, Reaver, Lich, Bt, Dino, Dinofast", inline = False)
     embed.add_field(name = "Command usage for adding points", value = "$boss <bossname> <list of characters> \n remember to put the list of characters in quotes", inline=False)
     embed.add_field(name = "Command usage for adding half points", value = "$bosshalf <bossname> <list of characters> \n remember to put the list of characters in quotes", inline=False)
     await ctx.send(embed=embed)

@client.command(guild_ids = guilds)
@commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
async def addmem(ctx, name, rank, main, level, cclass):
    """Adds a member to the Roster, KP Lists and loot list"""
    cclass = cclass.capitalize()
    rank = rank.capitalize()
    main = toBool(main)
    level = int(level)
    user_list = bot5ws1.col_values(1)
    if cclass not in ["Warrior", "Rogue", "Mage", "Druid", "Ranger"]:
        await ctx.send("Invalid class! Please use Warrior, Rogue, Mage, Druid, or Ranger")
        return
    if rank not in ["General", "Guardian", "Clansman", "Recruit", "Chieftain"]:
        await ctx.send("Invalid rank! Please use General, Guardian, Clansman, Recruit, or Chieftain")
        return
    realname, caps, spaces = find_name(name, user_list)
    if realname == None:
        body =[name,rank,main,level,cclass,"","","",False,False,False,False,False,False,False]
        bot5ws1.append_row(body)
        rownum = len(bot5ws2.col_values(1)) + 1
        rownum = str(rownum)
        currformula = '=Sum(D' + rownum + '+F'+rownum+'-E'+rownum+')'
        attendformula1 = "=(COUNTIFS('Bosses last 45'!C2:C, \"*VKP*\", 'Bosses last 45'!D2:D, \"*" + name + "*\"))/COUNTIFS('Bosses last 45'!B2:B, \"<>*HALF*\", 'Bosses last 45'!B2:B, \"<>\", 'Bosses last 45'!C2:C, \"*VKP*\")"
        kpbody1 = [name,0,attendformula1,0,0,0,currformula]
        attendformula2 = "=(COUNTIFS('Bosses last 45'!C2:C, \"*GKP*\", 'Bosses last 45'!D2:D, \"*" + name + "*\"))/COUNTIFS('Bosses last 45'!B2:B, \"<>*HALF*\", 'Bosses last 45'!B2:B, \"<>\", 'Bosses last 45'!C2:C, \"*GKP*\")"
        kpbody2 = [name,0,attendformula2,0,0,0,currformula]
        attendformula3 = "=(COUNTIFS('Bosses last 45'!C2:C, \"*PKP*\", 'Bosses last 45'!D2:D, \"*" + name + "*\"))/COUNTIFS('Bosses last 45'!B2:B, \"<>*HALF*\", 'Bosses last 45'!B2:B, \"<>\", 'Bosses last 45'!C2:C, \"*PKP*\")"
        kpbody3 = [name,0,attendformula3,0,0,0,currformula]
        attendformula4 = "=(COUNTIFS('Bosses last 45'!C2:C, \"*AKP*\", 'Bosses last 45'!D2:D, \"*" + name + "*\"))/COUNTIFS('Bosses last 45'!B2:B, \"<>*HALF*\", 'Bosses last 45'!B2:B, \"<>\", 'Bosses last 45'!C2:C, \"*AKP*\")"
        kpbody4 = [name,0,attendformula4,0,0,0,currformula]
        attendformula5 = "=(COUNTIFS('Bosses last 45'!C2:C, \"*RBPPUNOX*\", 'Bosses last 45'!D2:D, \"*" + name + "*\"))/COUNTIFS('Bosses last 45'!B2:B, \"<>*HALF*\", 'Bosses last 45'!B2:B, \"<>\", 'Bosses last 45'!C2:C, \"*RBPPUNOX*\")"
        kpbody5 = [name,0,attendformula5,0,0,0,currformula]
        attendformula6 = "=(COUNTIFS('Bosses last 45'!C2:C, \"*DPKP*\", 'Bosses last 45'!D2:D, \"*" + name + "*\"))/COUNTIFS('Bosses last 45'!B2:B, \"<>*HALF*\", 'Bosses last 45'!B2:B, \"<>\", 'Bosses last 45'!C2:C, \"*DPKP*\")"
        kpbody6 = [name,0,attendformula6,0,0,0,currformula]
        attendformula7 = "=(COUNTIFS('Bosses last 45'!C2:C, \"*RBPP*\", 'Bosses last 45'!D2:D, \"*" + name + "*\"))/COUNTIFS('Bosses last 45'!B2:B, \"<>*HALF*\", 'Bosses last 45'!B2:B, \"<>\", 'Bosses last 45'!C2:C, \"*RBPP*\")"
        kpbody7 = [name,0,attendformula7,0,0,0,currformula]
        bot5ws2.append_row(kpbody1, value_input_option='USER_ENTERED')
        bot5ws3.append_row(kpbody2, value_input_option='USER_ENTERED')
        bot5ws4.append_row(kpbody3, value_input_option='USER_ENTERED')
        bot5ws5.append_row(kpbody4, value_input_option='USER_ENTERED')
        bot5ws6.append_row(kpbody5, value_input_option='USER_ENTERED')
        bot5ws7.append_row(kpbody6, value_input_option='USER_ENTERED')
        bot5ws8.append_row(kpbody7, value_input_option='USER_ENTERED')
        lootbody = [name]
        lootbody2 = ["Costs"]
        bot5ws9.append_row(lootbody)
        bot5ws9.append_row(lootbody2)
        if main:
            maintext = "Main"
        else:
            maintext = "Alt"
        await ctx.send(name + " (" + str(level) + " " + cclass + ", " + maintext + ", " + rank + ") was added to the list")
        logbody = ["addmem", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([name, rank, main, level, cclass])]
        bot3ws11.append_row(logbody)
    else:
        await ctx.send(name + " is already in the list!")

@client.command(guild_ids = guilds)
@commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
async def rosteradmin(ctx, subcommand, name, params):
    """roster management for admins
    subcommands: rank, main"""
    user_list = bot5ws1.col_values(1)
    realname, caps, spaces = find_name(name, user_list)
    if realname != None:
        cell = bot5ws1.find(realname)
        row_num = cell.row
        subcommand = subcommand.lower()
        if subcommand == "rank":
            params = params.capitalize()
            bot5ws1.update_cell(row_num, 2, params)
            await ctx.send(realname + "'s rank has been updated to " + str(params))
            # find all their alts and update those too
            alts = bot5ws1.col_values(7)
            for i in range(1, len(alts)):
                if alts[i] == realname:
                    bot5ws1.update_cell(i + 1, 2, params)
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            bot3ws11.append_row(logbody)
        elif subcommand == "main":
            params = toBool(params)
            bot5ws1.update_cell(row_num, 3, params)
            await ctx.send(realname + "'s main status has been updated to " + str(params))
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            bot3ws11.append_row(logbody)
        else:
            await ctx.send("invalid subcommand")

@client.command(guild_ids = guilds)
async def roster(ctx, subcommand, name, params):
    """Roster Management Command
    subcommands: dg, subclass, cgoffhand, dl, dlmain, dloffhand, edl, edlmain, edloffhand, setall, level, setmain, bulksetmain"""
    user_list = bot5ws1.col_values(1)
    realname, caps, spaces = find_name(name, user_list)
    if realname != None:
        cell = bot5ws1.find(realname)
        row_num = cell.row
        subcommand = subcommand.lower()
        if subcommand == "dg":
            bot5ws1.update_cell(row_num, 6, params)
            await ctx.send(realname + "'s DG has been updated to " + str(params))
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            bot3ws11.append_row(logbody)
        elif subcommand == "removealt":
            if realname != None:
                bot5ws1.update_cell(row_num, 7, "")
                await ctx.send(realname + "'s Main character has been removed")
                logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
                bot3ws11.append_row(logbody)
            else:
                await ctx.send(params + " not in list!")
        elif subcommand == "setmain":
            names_list = params.split(",")
            # set the realname main to itself as well
            bot5ws1.update_cell(row_num, 7, realname)
            await ctx.send(realname + "'s Main character has been updated to " + str(realname))
            if realname != None:
                for names in names_list:
                    findnames, caps, spaces = find_name(names, user_list)
                    if findnames != None:
                        cell = bot5ws1.find(findnames)
                        row_num = cell.row
                        bot5ws1.update_cell(row_num, 7, realname)
                        await ctx.send(findnames + "'s Main character has been updated to " + realname)
                        logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([findnames, subcommand, realname])]
                        bot3ws11.append_row(logbody)
                    else:
                        await ctx.send(names + " not in list!")
        elif subcommand == "bulksetmain":
            names_list = params.split(",")
            # set the realname main to itself as well
            bot5ws1.update_cell(row_num, 7, realname)
            await ctx.send(realname + "'s Main character has been updated to " + str(realname))
            if realname != None:
                for names in names_list:
                    findnames, caps, spaces = find_name(names, user_list)
                    if findnames != None:
                        cell = bot5ws1.find(findnames)
                        row_num = cell.row
                        bot5ws1.update_cell(row_num, 7, realname)
                        await ctx.send(findnames + "'s Main character has been updated to " + realname)
                        logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([findnames, subcommand, realname])]
                        bot3ws11.append_row(logbody)
                    else:
                        await ctx.send(names + " not in list!")
        elif subcommand == "level":
            bot5ws1.update_cell(row_num, 4, params)
            await ctx.send(realname + "'s level has been updated to " + str(params))
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            bot3ws11.append_row(logbody)
        elif subcommand == "class":
            params = params.capitalize()
            if params not in ["Warrior", "Rogue", "Mage", "Druid", "Ranger"]:
                await ctx.send("Invalid class! Please use Warrior, Rogue, Mage, Druid, or Ranger")
                return
            bot5ws1.update_cell(row_num, 5, params)
            await ctx.send(realname + "'s class has been updated to " + str(params))
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            bot3ws11.append_row(logbody)
        elif subcommand == "subclass":
            bot5ws1.update_cell(row_num, 8, params)
            await ctx.send(realname + "'s Subclass has been updated to " + str(params))
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            bot3ws11.append_row(logbody)
        elif subcommand == "cgoffhand":
            bot5ws1.update_cell(row_num, 9, params)
            await ctx.send(realname + "'s CG Offhand has been updated to " + str(params))
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            bot3ws11.append_row(logbody)
        elif subcommand == "dl":
            params = toBool(params)
            bot5ws1.update_cell(row_num, 10, params)
            await ctx.send(realname + "'s DL has been updated to " + str(params))
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            bot3ws11.append_row(logbody)
        elif subcommand == "dlmain":
            params = toBool(params)
            bot5ws1.update_cell(row_num, 11, params)
            await ctx.send(realname + "'s DL Main has been updated to " + str(params))
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            bot3ws11.append_row(logbody)
        elif subcommand == "dloffhand":
            params = toBool(params)
            bot5ws1.update_cell(row_num, 12, params)
            await ctx.send(realname + "'s DL Offhand has been updated to " + str(params))
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            bot3ws11.append_row(logbody)
        elif subcommand == "edl":
            params = toBool(params)
            bot5ws1.update_cell(row_num, 13, params)
            await ctx.send(realname + "'s EDL has been updated to " + str(params))
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            bot3ws11.append_row(logbody)
        elif subcommand == "edlmain":
            params = toBool(params)
            bot5ws1.update_cell(row_num, 14, params)
            await ctx.send(realname + "'s EDL Main has been updated to " + str(params))
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            bot3ws11.append_row(logbody)
        elif subcommand == "edloffhand":
            params = toBool(params)
            bot5ws1.update_cell(row_num, 15, params)
            await ctx.send(realname + "'s EDL Offhand has been updated to " + str(params))
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            bot3ws11.append_row(logbody)
        elif subcommand == "setall":
            params = toBool(params)
            bot5ws1.update_cell(row_num, 9, params)
            bot5ws1.update_cell(row_num, 10, params)
            bot5ws1.update_cell(row_num, 11, params)
            bot5ws1.update_cell(row_num, 12, params)
            bot5ws1.update_cell(row_num, 13, params)
            bot5ws1.update_cell(row_num, 14, params)
            bot5ws1.update_cell(row_num, 15, params)
            await ctx.send(realname + "'s gear has all been updated to " + str(params))
        else:
            await ctx.send("invalid subcommand")
    else:
        await ctx.send(name + " not in list!")

@client.command(guild_ids = guilds)
async def player(ctx, name):
    """Displays a player's information"""
    user_list = bot4ws1.col_values(1)
    realname, caps, spaces = find_name(name, user_list)
    if realname != None:
        cell = bot4ws1.find(realname)
        row_num = cell.row
        embedvals = bot4ws1.row_values(row_num, value_render_option='UNFORMATTED_VALUE')
        embed = discord.Embed(title = realname, colour=discord.Color.orange())
        embed.add_field(name = "Rank", value = embedvals[1], inline = True)
        embed.add_field(name = "Main", value = embedvals[2], inline = True)
        embed.add_field(name = "Level", value = embedvals[3], inline = True)
        embed.add_field(name = "Class", value = embedvals[4], inline = True)
        # embed.add_field(name = "DG", value = embedvals[5], inline = True)
        embed.add_field(name = "Main Character", value = embedvals[6], inline = True)
        # embed.add_field(name = "Subclass", value = embedvals[7], inline = True)
        # embed.add_field(name = "CG Offhand", value = embedvals[8], inline = True)
        # embed.add_field(name = "DL", value = embedvals[9], inline = True)
        # embed.add_field(name = "DL Main", value = embedvals[10], inline = True)
        # embed.add_field(name = "DL Offhand", value = embedvals[11], inline = True)
        # embed.add_field(name = "EDL", value = embedvals[12], inline = True)
        # embed.add_field(name = "EDL Main", value = embedvals[13], inline = True)
        # embed.add_field(name = "EDL Offhand", value = embedvals[14], inline = True)
        cell2 = bot4ws2.find(realname)
        row_num2 = cell2.row
        dkprowvals = bot4ws2.row_values(row_num2, value_render_option='UNFORMATTED_VALUE')
        embed.add_field(name = "VKP", value = "Earned: " + str(dkprowvals[3]) + ", Current: " + str(dkprowvals[6]), inline = False)
        cell3 = bot4ws3.find(realname)
        row_num3 = cell3.row
        dkprowvals2 = bot4ws3.row_values(row_num3, value_render_option='UNFORMATTED_VALUE')
        embed.add_field(name = "GKP", value = "Earned: " + str(dkprowvals2[3]) + ", Current: " + str(dkprowvals2[6]), inline = False)
        cell4 = bot4ws4.find(realname)
        row_num4 = cell4.row
        dkprowvals3 = bot4ws4.row_values(row_num4, value_render_option='UNFORMATTED_VALUE')
        embed.add_field(name = "PKP", value = "Earned: " + str(dkprowvals3[3]) + ", Current: " + str(dkprowvals3[6]), inline = False)
        cell5 = bot4ws5.find(realname)
        row_num5 = cell5.row
        dkprowvals4 = bot4ws5.row_values(row_num5, value_render_option='UNFORMATTED_VALUE')
        embed.add_field(name = "AKP", value = "Earned: " + str(dkprowvals4[3]) + ", Current: " + str(dkprowvals4[6]), inline = False)
        cell6 = bot4ws6.find(realname)
        row_num6 = cell6.row
        dkprowvals5 = bot4ws6.row_values(row_num6, value_render_option='UNFORMATTED_VALUE')
        embed.add_field(name = "RBPPUNOX", value = "Earned: " + str(dkprowvals5[3]) + ", Current: " + str(dkprowvals5[6]), inline = False)
        cell7 = bot4ws7.find(realname)
        row_num7 = cell7.row
        dkprowvals6 = bot4ws7.row_values(row_num7, value_render_option='UNFORMATTED_VALUE')
        embed.add_field(name = "DPKP", value = "Earned: " + str(dkprowvals6[3]) + ", Current: " + str(dkprowvals6[6]), inline = False)
        cell8 = bot4ws8.find(realname)
        row_num8 = cell8.row
        dkprowvals7 = bot4ws8.row_values(row_num8, value_render_option='UNFORMATTED_VALUE')
        embed.add_field(name = "RBPP", value = "Earned: " + str(dkprowvals7[3]) + ", Current: " + str(dkprowvals7[6]), inline = False)
        await ctx.send(embed=embed)
    else:
        await ctx.send(name + " not in list!")

@client.command(guild_ids = guilds)
async def playerfull(ctx, name):
    """Displays a player's information"""
    user_list = bot4ws1.col_values(1)
    realname, caps, spaces = find_name(name, user_list)
    if realname != None:
        cell = bot4ws1.find(realname)
        row_num = cell.row
        embedvals = bot4ws1.row_values(row_num, value_render_option='UNFORMATTED_VALUE')
        embed = discord.Embed(title = realname, colour=discord.Color.orange())
        embed.add_field(name = "Rank", value = embedvals[1], inline = True)
        embed.add_field(name = "Main", value = embedvals[2], inline = True)
        embed.add_field(name = "Level", value = embedvals[3], inline = True)
        embed.add_field(name = "Class", value = embedvals[4], inline = True)
        embed.add_field(name = "DG", value = embedvals[5], inline = True)
        embed.add_field(name = "Main Character", value = embedvals[6], inline = True)
        embed.add_field(name = "Subclass", value = embedvals[7], inline = True)
        embed.add_field(name = "CG Offhand", value = embedvals[8], inline = True)
        embed.add_field(name = "DL", value = embedvals[9], inline = True)
        embed.add_field(name = "DL Main", value = embedvals[10], inline = True)
        embed.add_field(name = "DL Offhand", value = embedvals[11], inline = True)
        embed.add_field(name = "EDL", value = embedvals[12], inline = True)
        embed.add_field(name = "EDL Main", value = embedvals[13], inline = True)
        embed.add_field(name = "EDL Offhand", value = embedvals[14], inline = True)
        cell2 = bot4ws2.find(realname)
        row_num2 = cell2.row
        dkprowvals = bot4ws2.row_values(row_num2, value_render_option='UNFORMATTED_VALUE')
        embed.add_field(name = "VKP", value = "Earned: " + str(dkprowvals[3]) + ", Current: " + str(dkprowvals[6]), inline = False)
        cell3 = bot4ws3.find(realname)
        row_num3 = cell3.row
        dkprowvals2 = bot4ws3.row_values(row_num3, value_render_option='UNFORMATTED_VALUE')
        embed.add_field(name = "GKP", value = "Earned: " + str(dkprowvals2[3]) + ", Current: " + str(dkprowvals2[6]), inline = False)
        cell4 = bot4ws4.find(realname)
        row_num4 = cell4.row
        dkprowvals3 = bot4ws4.row_values(row_num4, value_render_option='UNFORMATTED_VALUE')
        embed.add_field(name = "PKP", value = "Earned: " + str(dkprowvals3[3]) + ", Current: " + str(dkprowvals3[6]), inline = False)
        cell5 = bot4ws5.find(realname)
        row_num5 = cell5.row
        dkprowvals4 = bot4ws5.row_values(row_num5, value_render_option='UNFORMATTED_VALUE')
        embed.add_field(name = "AKP", value = "Earned: " + str(dkprowvals4[3]) + ", Current: " + str(dkprowvals4[6]), inline = False)
        cell6 = bot4ws6.find(realname)
        row_num6 = cell6.row
        dkprowvals5 = bot4ws6.row_values(row_num6, value_render_option='UNFORMATTED_VALUE')
        embed.add_field(name = "RBPPUNOX", value = "Earned: " + str(dkprowvals5[3]) + ", Current: " + str(dkprowvals5[6]), inline = False)
        cell7 = bot4ws7.find(realname)
        row_num7 = cell7.row
        dkprowvals6 = bot4ws7.row_values(row_num7, value_render_option='UNFORMATTED_VALUE')
        embed.add_field(name = "DPKP", value = "Earned: " + str(dkprowvals6[3]) + ", Current: " + str(dkprowvals6[6]), inline = False)
        cell8 = bot4ws8.find(realname)
        row_num8 = cell8.row
        dkprowvals7 = bot4ws8.row_values(row_num8, value_render_option='UNFORMATTED_VALUE')
        embed.add_field(name = "RBPP", value = "Earned: " + str(dkprowvals7[3]) + ", Current: " + str(dkprowvals7[6]), inline = False)
        await ctx.send(embed=embed)
    else:
        await ctx.send(name + " not in list!")

@client.command(guild_ids = guilds)
async def playerkp(ctx, name):
    """Displays a player's KP information"""
    user_list = bot4ws1.col_values(1)
    realname, caps, spaces = find_name(name, user_list)
    if realname != None:
        cell = bot4ws2.find(realname)
        row_num = cell.row
        embedvals = bot4ws2.row_values(row_num)
        embed = discord.Embed(title = realname + "'s KP", colour=discord.Color.orange())
        embed.add_field(name = "VKP", value = "Last Raid: " + embedvals[1] + ", Att %: " + embedvals[2] + ", Earned: " + embedvals[3] + ", Spent: " + embedvals[4] + ", Adjusted: " + embedvals[5] + ", Current: " + str(embedvals[6]), inline = False)
        cell2 = bot4ws3.find(realname)
        row_num2 = cell2.row
        embedvals2 = bot4ws3.row_values(row_num2)
        embed.add_field(name = "GKP", value = "Last Raid: " + embedvals2[1] + ", Att %: " + embedvals2[2] + ", Earned: " + embedvals2[3] + ", Spent: " + embedvals2[4] + ", Adjusted: " + embedvals2[5] + ", Current: " + str(embedvals2[6]), inline = False)
        cell3 = bot4ws4.find(realname)
        row_num3 = cell3.row
        embedvals3 = bot4ws4.row_values(row_num3)
        embed.add_field(name = "PKP", value = "Last Raid: " + embedvals3[1] + ", Att %: " + embedvals3[2] + ", Earned: " + embedvals3[3] + ", Spent: " + embedvals3[4] + ", Adjusted: " + embedvals3[5] + ", Current: " + str(embedvals3[6]), inline = False)
        cell4 = bot4ws5.find(realname)
        row_num4 = cell4.row
        embedvals4 = bot4ws5.row_values(row_num4)
        embed.add_field(name = "AKP", value = "Last Raid: " + embedvals4[1] + ", Att %: " + embedvals4[2] + ", Earned: " + embedvals4[3] + ", Spent: " + embedvals4[4] + ", Adjusted: " + embedvals4[5] + ", Current: " + str(embedvals4[6]), inline = False)
        cell5 = bot4ws6.find(realname)
        row_num5 = cell5.row
        embedvals5 = bot4ws6.row_values(row_num5)
        embed.add_field(name = "RBPPUNOX", value = "Last Raid: " + embedvals5[1] + ", Att %: " + embedvals5[2] + ", Earned: " + embedvals5[3] + ", Spent: " + embedvals5[4] + ", Adjusted: " + embedvals5[5] + ", Current: " + str(embedvals5[6]), inline = False)
        cell6 = bot4ws7.find(realname)
        row_num6 = cell6.row
        embedvals6 = bot4ws7.row_values(row_num6)
        embed.add_field(name = "DPKP", value = "Last Raid: " + embedvals6[1] + ", Att %: " + embedvals6[2] + ", Earned: " + embedvals6[3] + ", Spent: " + embedvals6[4] + ", Adjusted: " + embedvals6[5] + ", Current: " + str(embedvals6[6]), inline = False)
        cell7 = bot4ws8.find(realname)
        row_num7 = cell7.row
        embedvals7 = bot4ws8.row_values(row_num7)
        embed.add_field(name = "RBPP", value = "Last Raid: " + embedvals7[1] + ", Att %: " + embedvals7[2] + ", Earned: " + embedvals7[3] + ", Spent: " + embedvals7[4] + ", Adjusted: " + embedvals7[5] + ", Current: " + str(embedvals7[6]), inline = False)
        await ctx.send(embed=embed)
    else:
        await ctx.send(name + " not in list!")

@client.command(guild_ids = guilds)
async def characters(ctx, name):
    """shows all characters a player has"""
    mains_list = bot4ws1.col_values(7)
    characters_list = bot4ws1.col_values(1)
    levels_list = bot4ws1.col_values(4)
    cclass_list = bot4ws1.col_values(5)
    mains_to_chars = zip(mains_list, characters_list, levels_list, cclass_list)
    realname, caps, spaces = find_name(name, mains_list)
    if realname != None:
        embed = discord.Embed(title = realname + "'s Characters", colour=discord.Color.orange())
        #find all instances of main name in the character list, add to the embed and return
        for main, character, level, cclass in mains_to_chars:
            if main == realname:
                embed.add_field(name = character, value = "Level " + str(level) + " " + cclass, inline = False)
        await ctx.send(embed=embed)
        return
    altrealname, caps, spaces = find_name(name, characters_list)
    if altrealname != None:
        #pull the main first, then find all instances of the main in the character list, add to the embed and return
        cell = bot4ws1.find(altrealname)
        row_num = cell.row
        main_name = bot4ws1.cell(row_num, 7).value
        embed = discord.Embed(title = main_name + "'s Characters", colour=discord.Color.orange())
        for main, character, level, cclass in mains_to_chars:
            if main == main_name:
                embed.add_field(name = character, value = "Level " + str(level) + " " + cclass, inline = False)
        
        await ctx.send(embed=embed)
    else:
        await ctx.send(name + " not in list!")
        

@client.command(guild_ids = guilds)
@commands.has_any_role("General", "REDALiCE")
async def fullpointwipe(ctx, name, verification):
    """fully wipes someones points, including earned points"""
    if verification == "releleaderfullwipe":
        user_list = bot5ws1.col_values(1)
        realname, caps, spaces = find_name(name, user_list)
        if realname != None:
            cell1 = bot5ws2.find(realname)
            row_num1 = cell1.row
            currformula1 = '=Sum(D' + str(row_num1) + '+F'+str(row_num1)+'-E'+str(row_num1)+')'
            attendformula1 = "=(COUNTIFS('Bosses last 45'!C2:C, \"*VKP*\", 'Bosses last 45'!D2:D, \"*" + realname + "*\"))/COUNTIFS('Bosses last 45'!B2:B, \"<>*HALF*\", 'Bosses last 45'!B2:B, \"<>\", 'Bosses last 45'!C2:C, \"*VKP*\")"
            wipedrow1 = [realname,0,attendformula1,0,0,0,currformula1]
            bot5ws2.update([wipedrow1], "A" + str(row_num1), value_input_option='USER_ENTERED')
            cell2 = bot5ws3.find(realname)
            row_num2 = cell2.row
            currformula2 = '=Sum(D' + str(row_num2) + '+F'+str(row_num2)+'-E'+str(row_num2)+')'
            attendformula2 = "=(COUNTIFS('Bosses last 45'!C2:C, \"*GKP*\", 'Bosses last 45'!D2:D, \"*" + realname + "*\"))/COUNTIFS('Bosses last 45'!B2:B, \"<>*HALF*\", 'Bosses last 45'!B2:B, \"<>\", 'Bosses last 45'!C2:C, \"*GKP*\")"
            wipedrow2 = [realname,0,attendformula2,0,0,0,currformula2]
            bot5ws3.update([wipedrow2], "A" + str(row_num2), value_input_option='USER_ENTERED')
            cell3 = bot5ws4.find(realname)
            row_num3 = cell3.row
            currformula3 = '=Sum(D' + str(row_num3) + '+F'+str(row_num3)+'-E'+str(row_num3)+')'
            attendformula3 = "=(COUNTIFS('Bosses last 45'!C2:C, \"*PKP*\", 'Bosses last 45'!D2:D, \"*" + realname + "*\"))/COUNTIFS('Bosses last 45'!B2:B, \"<>*HALF*\", 'Bosses last 45'!B2:B, \"<>\", 'Bosses last 45'!C2:C, \"*PKP*\")"
            wipedrow3 = [realname,0,attendformula3,0,0,0,currformula3]
            bot5ws4.update([wipedrow3], "A" + str(row_num3), value_input_option='USER_ENTERED')
            cell4 = bot5ws5.find(realname)
            row_num4 = cell4.row
            currformula4 = '=Sum(D' + str(row_num4) + '+F'+str(row_num4)+'-E'+str(row_num4)+')'
            attendformula4 = "=(COUNTIFS('Bosses last 45'!C2:C, \"*AKP*\", 'Bosses last 45'!D2:D, \"*" + realname + "*\"))/COUNTIFS('Bosses last 45'!B2:B, \"<>*HALF*\", 'Bosses last 45'!B2:B, \"<>\", 'Bosses last 45'!C2:C, \"*AKP*\")"
            wipedrow4 = [realname,0,attendformula4,0,0,0,currformula4]
            bot5ws5.update([wipedrow4], "A" + str(row_num4), value_input_option='USER_ENTERED')
            cell5 = bot5ws6.find(realname)
            row_num5 = cell5.row
            currformula5 = '=Sum(D' + str(row_num5) + '+F'+str(row_num5)+'-E'+str(row_num5)+')'
            attendformula5 = "=(COUNTIFS('Bosses last 45'!C2:C, \"*RBPPUNOX*\", 'Bosses last 45'!D2:D, \"*" + realname + "*\"))/COUNTIFS('Bosses last 45'!B2:B, \"<>*HALF*\", 'Bosses last 45'!B2:B, \"<>\", 'Bosses last 45'!C2:C, \"*RBPPUNOX*\")"
            wipedrow5 = [realname,0,attendformula5,0,0,0,currformula5]
            bot5ws6.update([wipedrow5], "A" + str(row_num5), value_input_option='USER_ENTERED')
            cell6 = bot5ws7.find(realname)
            row_num6 = cell6.row
            currformula6 = '=Sum(D' + str(row_num6) + '+F'+str(row_num6)+'-E'+str(row_num6)+')'
            attendformula6 = "=(COUNTIFS('Bosses last 45'!C2:C, \"*DPKP*\", 'Bosses last 45'!D2:D, \"*" + realname + "*\"))/COUNTIFS('Bosses last 45'!B2:B, \"<>*HALF*\", 'Bosses last 45'!B2:B, \"<>\", 'Bosses last 45'!C2:C, \"*DPKP*\")"
            wipedrow6 = [realname,0,attendformula6,0,0,0,currformula6]
            bot5ws7.update([wipedrow6], "A" + str(row_num6), value_input_option='USER_ENTERED')
            cell7 = bot5ws8.find(realname)
            row_num7 = cell7.row
            currformula7 = '=Sum(D' + str(row_num7) + '+F'+str(row_num7)+'-E'+str(row_num7)+')'
            attendformula7 = "=(COUNTIFS('Bosses last 45'!C2:C, \"*RBPP*\", 'Bosses last 45'!D2:D, \"*" + realname + "*\"))/COUNTIFS('Bosses last 45'!B2:B, \"<>*HALF*\", 'Bosses last 45'!B2:B, \"<>\", 'Bosses last 45'!C2:C, \"*RBPP*\")"
            wipedrow7 = [realname,0,attendformula7,0,0,0,currformula7]
            bot5ws8.update([wipedrow7], "A" + str(row_num7), value_input_option='USER_ENTERED')
            await ctx.send(realname + "'s points have been fully wiped")
            logbody = ["wipe", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname])]
            bot3ws11.append_row(logbody)
        else:
            await ctx.send(name + " not in list!")

        



@client.command(guild_ids = guilds)
@commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
async def deduct(ctx, name, item, number, kp):
    """Deducts points from a player and adds the item to their loot list"""
    kp = kp.upper()
    number = float(number)

    if kp == "VKP":
        user_list = bot3ws2.col_values(1)
        realname, caps, spaces = find_name(name, user_list)
        if realname != None:
            cell = bot3ws2.find(realname)
            row_num = cell.row
            current = float(bot3ws2.cell(row_num, 7).value)
            new = current - number
            newspent = float(bot3ws2.cell(row_num, 5).value) + number
            if new < 0:
                await ctx.send("Cannot deduct more points than the player has")
            else:
                bot3ws2.update_cell(row_num, 5, newspent)
                lootcell = bot3ws9.find(realname)
                lootrow = lootcell.row
                costrow = lootcell.row + 1
                lootlist = bot3ws9.row_values(lootrow)
                costlist = bot3ws9.row_values(costrow)
                lootlist.append(item)
                costlist.append(str(number) + " VKP")
                bot3ws9.update([lootlist], "A" + str(lootrow))
                bot3ws9.update([costlist], "A" + str(costrow))
                await ctx.send(realname + " has been deducted " + str(number) + " VKP for " + item)
                logbody = ["deduct", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, item, number, kp])]
                bot3ws11.append_row(logbody)
        else:
            await ctx.send(name + " not in list!")
    if kp == "GKP":
        user_list = bot3ws3.col_values(1)
        realname, caps, spaces = find_name(name, user_list)
        if realname != None:
            cell = bot3ws3.find(realname)
            row_num = cell.row
            current = float(bot3ws3.cell(row_num, 7).value)
            new = current - number
            newspent = float(bot3ws3.cell(row_num, 5).value) + number
            if new < 0:
                await ctx.send("Cannot deduct more points than the player has")
            else:
                bot3ws3.update_cell(row_num, 5, newspent)
                lootcell = bot3ws9.find(realname)
                lootrow = lootcell.row
                costrow = lootcell.row + 1
                lootlist = bot3ws9.row_values(lootrow)
                costlist = bot3ws9.row_values(costrow)
                lootlist.append(item)
                costlist.append(str(number) + " GKP")
                bot3ws9.update([lootlist], "A" + str(lootrow))
                bot3ws9.update([costlist], "A" + str(costrow))
                await ctx.send(realname + " has been deducted " + str(number) + " GKP for " + item)
                logbody = ["deduct", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, item, number, kp])]
                bot3ws11.append_row(logbody)
        else:
            await ctx.send(name + " not in list!")
    if kp == "PKP":
        user_list = bot3ws4.col_values(1)
        realname, caps, spaces = find_name(name, user_list)
        if realname != None:
            cell = bot3ws4.find(realname)
            row_num = cell.row
            current = float(bot3ws4.cell(row_num, 7).value)
            new = current - number
            newspent = float(bot3ws4.cell(row_num, 5).value) + number
            if new < 0:
                await ctx.send("Cannot deduct more points than the player has")
            else:
                bot3ws4.update_cell(row_num, 5, newspent)
                lootcell = bot3ws9.find(realname)
                lootrow = lootcell.row
                costrow = lootcell.row + 1
                lootlist = bot3ws9.row_values(lootrow)
                costlist = bot3ws9.row_values(costrow)
                lootlist.append(item)
                costlist.append(str(number) + " PKP")
                bot3ws9.update([lootlist], "A" + str(lootrow))
                bot3ws9.update([costlist], "A" + str(costrow))
                await ctx.send(realname + " has been deducted " + str(number) + " PKP for " + item)
                logbody = ["deduct", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, item, number, kp])]
                bot3ws11.append_row(logbody)
        else:
            await ctx.send(name + " not in list!")
    if kp == "AKP":
        user_list = bot3ws5.col_values(1)
        realname, caps, spaces = find_name(name, user_list)
        if realname != None:
            cell = bot3ws5.find(realname)
            row_num = cell.row
            current = float(bot3ws5.cell(row_num, 7).value)
            new = current - number
            newspent = float(bot3ws5.cell(row_num, 5).value) + number
            if new < 0:
                await ctx.send("Cannot deduct more points than the player has")
            else:
                bot3ws5.update_cell(row_num, 5, newspent)
                lootcell = bot3ws9.find(realname)
                lootrow = lootcell.row
                costrow = lootcell.row + 1
                lootlist = bot3ws9.row_values(lootrow)
                costlist = bot3ws9.row_values(costrow)
                lootlist.append(item)
                costlist.append(str(number) + " AKP")
                bot3ws9.update([lootlist], "A" + str(lootrow))
                bot3ws9.update([costlist], "A" + str(costrow))
                await ctx.send(realname + " has been deducted " + str(number) + " AKP for " + item)
                logbody = ["deduct", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, item, number, kp])]
                bot3ws11.append_row(logbody)
        else:
            await ctx.send(name + " not in list!")
    if kp == "RBPPUNOX":
        user_list = bot3ws6.col_values(1)
        realname, caps, spaces = find_name(name, user_list)
        if realname != None:
            cell = bot3ws6.find(realname)
            row_num = cell.row
            current = float(bot3ws6.cell(row_num, 7).value)
            new = current - number
            newspent = float(bot3ws6.cell(row_num, 5).value) + number
            if new < 0:
                await ctx.send("Cannot deduct more points than the player has")
            else:
                bot3ws6.update_cell(row_num, 5, newspent)
                lootcell = bot3ws9.find(realname)
                lootrow = lootcell.row
                costrow = lootcell.row + 1
                lootlist = bot3ws9.row_values(lootrow)
                costlist = bot3ws9.row_values(costrow)
                lootlist.append(item)
                costlist.append(str(number) + " RBPPUNOX")
                bot3ws9.update([lootlist], "A" + str(lootrow))
                bot3ws9.update([costlist], "A" + str(costrow))
                await ctx.send(realname + " has been deducted " + str(number) + " RBPPUNOX for " + item)
                logbody = ["deduct", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, item, number, kp])]
                bot3ws11.append_row(logbody)
        else:
            await ctx.send(name + " not in list!")
    if kp == "DPKP":
        user_list = bot3ws7.col_values(1)
        realname, caps, spaces = find_name(name, user_list)
        if realname != None:
            cell = bot3ws7.find(realname)
            row_num = cell.row
            current = float(bot3ws7.cell(row_num, 7).value)
            new = current - number
            newspent = float(bot3ws7.cell(row_num, 5).value) + number
            if new < 0:
                await ctx.send("Cannot deduct more points than the player has")
            else:
                bot3ws7.update_cell(row_num, 5, newspent)
                lootcell = bot3ws9.find(realname)
                lootrow = lootcell.row
                costrow = lootcell.row + 1
                lootlist = bot3ws9.row_values(lootrow)
                costlist = bot3ws9.row_values(costrow)
                lootlist.append(item)
                costlist.append(str(number) + " DPKP")
                bot3ws9.update([lootlist], "A" + str(lootrow))
                bot3ws9.update([costlist], "A" + str(costrow))
                await ctx.send(realname + " has been deducted " + str(number) + " DPKP for " + item)
                logbody = ["deduct", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, item, number, kp])]
                bot3ws11.append_row(logbody)
        else:
            await ctx.send(name + " not in list!")
        

@client.command(guild_ids = guilds)
async def winnings(ctx, name, kp = "ALL"):
    """Displays a player's loot winnings"""
    kp = kp.upper()
    if kp == "ALL":
        user_list = bot4ws9.col_values(1)
        realname, caps, spaces = find_name(name, user_list)
        if realname != None:
            cell = bot4ws9.find(realname)
            row_num = cell.row
            lootlist = bot4ws9.row_values(row_num)
            costlist = bot4ws9.row_values(row_num + 1)
            lootlist.pop(0)
            costlist.pop(0)
            pagecounter = 0
            if len(lootlist) == 0:
                await ctx.send(realname + " has no loot winnings")
            else:
                for i in range(len(lootlist)):
                    if i % 20 == 0:
                        if i != 0:
                            await ctx.send(embed=embed)
                        pagecounter += 1
                        embed = discord.Embed(title = realname + "'s Winnings Page " + str(pagecounter), colour=discord.Color.orange())
                    embed.add_field(name = str(i + 1) + ". " + lootlist[i], value = costlist[i], inline = False)
                await ctx.send(embed=embed)
        else:
            await ctx.send(name + " not in list!")
    else:
        user_list = bot4ws9.col_values(1)
        realname, caps, spaces = find_name(name, user_list)
        if realname != None:
            cell = bot4ws9.find(realname)
            row_num = cell.row
            lootlist = bot4ws9.row_values(row_num)
            costlist = bot4ws9.row_values(row_num + 1)
            lootlist.pop(0)
            costlist.pop(0)
            pagecounter = 0
            itemsadded = 0
            for i in range(len(lootlist)):
                if kp in costlist[i]:
                    if itemsadded % 20 == 0:
                        if itemsadded != 0:
                            await ctx.send(embed=embed)
                        pagecounter += 1
                        embed = discord.Embed(title = realname + "'s " + kp + " Winnings Page " + str(pagecounter), colour=discord.Color.orange())
                    embed.add_field(name = str(i + 1) + ". " + lootlist[i], value = costlist[i], inline = False)
                    itemsadded += 1
            if itemsadded == 0:
                await ctx.send(realname + " has no loot winnings for " + kp)
            else:
                await ctx.send(embed=embed)
        else:
            await ctx.send(name + " not in list!")

@client.command(guild_ids = guilds)
@commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
async def refunditem(ctx, name, itemnum):
    """Refunds an item and returns the points to the player"""
    itemnum = int(itemnum)
    user_list = bot3ws9.col_values(1)
    realname, caps, spaces = find_name(name, user_list)
    if realname != None:
        cell = bot3ws9.find(realname)
        row_num = cell.row
        lootlist = bot3ws9.row_values(row_num)
        costlist = bot3ws9.row_values(row_num + 1)
        if itemnum < len(lootlist):
            itemname = lootlist[itemnum]
            cost = costlist[itemnum]
            cost = cost.split(" ")
            itemprice = float(cost[0])
            itemkp = cost[1]
            newitemname = "[REFUNDED] " + itemname
            lootlist[itemnum] = newitemname
            bot3ws9.update([lootlist], "A" + str(row_num))
            if itemkp == "VKP":
                kpcell = bot3ws2.find(realname)
                kprow = kpcell.row
                spent = float(bot3ws2.cell(kprow, 5).value)
                newspent = spent - itemprice
                bot3ws2.update_cell(kprow, 5, newspent)
                await ctx.send(realname + " has been refunded " + str(itemprice) + " VKP for " + itemname)
                logbody = ["refund", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, itemname, itemprice, itemkp])]
                bot3ws11.append_row(logbody)
            elif itemkp == "GKP":
                kpcell = bot3ws3.find(realname)
                kprow = kpcell.row
                spent = float(bot3ws3.cell(kprow, 5).value)
                newspent = spent - itemprice
                bot3ws3.update_cell(kprow, 5, newspent)
                await ctx.send(realname + " has been refunded " + str(itemprice) + " GKP for " + itemname)
                logbody = ["refund", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, itemname, itemprice, itemkp])]
                bot3ws11.append_row(logbody)
            elif itemkp == "PKP":
                kpcell = bot3ws4.find(realname)
                kprow = kpcell.row
                spent = float(bot3ws4.cell(kprow, 5).value)
                newspent = spent - itemprice
                bot3ws4.update_cell(kprow, 5, newspent)
                await ctx.send(realname + " has been refunded " + str(itemprice) + " PKP for " + itemname)
                logbody = ["refund", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, itemname, itemprice, itemkp])]
                bot3ws11.append_row(logbody)
            elif itemkp == "AKP":
                kpcell = bot3ws5.find(realname)
                kprow = kpcell.row
                spent = float(bot3ws5.cell(kprow, 5).value)
                newspent = spent - itemprice
                bot3ws5.update_cell(kprow, 5, newspent)
                await ctx.send(realname + " has been refunded " + str(itemprice) + " AKP for " + itemname)
                logbody = ["refund", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, itemname, itemprice, itemkp])]
                bot3ws11.append_row(logbody)
            elif itemkp == "RBPPUNOX":
                kpcell = bot3ws6.find(realname)
                kprow = kpcell.row
                spent = float(bot3ws6.cell(kprow, 5).value)
                newspent = spent - itemprice
                bot3ws6.update_cell(kprow, 5, newspent)
                await ctx.send(realname + " has been refunded " + str(itemprice) + " RBPPUNOX for " + itemname)
                logbody = ["refund", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, itemname, itemprice, itemkp])]
                bot3ws11.append_row(logbody)
            elif itemkp == "DPKP":
                kpcell = bot3ws7.find(realname)
                kprow = kpcell.row
                spent = float(bot3ws7.cell(kprow, 5).value)
                newspent = spent - itemprice
                bot3ws7.update_cell(kprow, 5, newspent)
                await ctx.send(realname + " has been refunded " + str(itemprice) + " DPKP for " + itemname)
                logbody = ["refund", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, itemname, itemprice, itemkp])]
                bot3ws11.append_row(logbody)
            else:
                await ctx.send("Invalid KP type. somehow?")


@client.command(guild_ids = guilds)
@commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
async def refundolditem(ctx, name, amount, kp):
    """Processes a refund for an item that was not added to the loot list"""
    amount = float(amount)
    kp = kp.upper()
    if kp == "VKP":
        user_list = bot3ws2.col_values(1)
        realname, caps, spaces = find_name(name, user_list)
        if realname != None:
            cell = bot3ws2.find(realname)
            row_num = cell.row
            currentspent = float(bot3ws2.cell(row_num, 5).value)
            new = currentspent - amount
            bot3ws2.update_cell(row_num, 5, new)
            await ctx.send(realname + " has been refunded " + str(amount) + " VKP")
            logbody = ["refund", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, amount, kp])]
            bot3ws11.append_row(logbody)
        else:
            await ctx.send(name + " not in list!")
    if kp == "GKP":
        user_list = bot3ws3.col_values(1)
        realname, caps, spaces = find_name(name, user_list)
        if realname != None:
            cell = bot3ws3.find(realname)
            row_num = cell.row
            currentspent = float(bot3ws3.cell(row_num, 5).value)
            new = currentspent - amount
            bot3ws3.update_cell(row_num, 5, new)
            await ctx.send(realname + " has been refunded " + str(amount) + " GKP")
            logbody = ["refund", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, amount, kp])]
            bot3ws11.append_row(logbody)
        else:
            await ctx.send(name + " not in list!")
    if kp == "PKP":
        user_list = bot3ws4.col_values(1)
        realname, caps, spaces = find_name(name, user_list)
        if realname != None:
            cell = bot3ws4.find(realname)
            row_num = cell.row
            currentspent = float(bot3ws4.cell(row_num, 5).value)
            new = currentspent - amount
            bot3ws4.update_cell(row_num, 5, new)
            await ctx.send(realname + " has been refunded " + str(amount) + " PKP")
            logbody = ["refund", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, amount, kp])]
            bot3ws11.append_row(logbody)
        else:
            await ctx.send(name + " not in list!")
    if kp == "AKP":
        user_list = bot3ws5.col_values(1)
        realname, caps, spaces = find_name(name, user_list)
        if realname != None:
            cell = bot3ws5.find(realname)
            row_num = cell.row
            currentspent = float(bot3ws5.cell(row_num, 5).value)
            new = currentspent - amount
            bot3ws5.update_cell(row_num, 5, new)
            await ctx.send(realname + " has been refunded " + str(amount) + " AKP")
            logbody = ["refund", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, amount, kp])]
            bot3ws11.append_row(logbody)
        else:
            await ctx.send(name + " not in list!")
    if kp == "RBPPUNOX":
        user_list = bot3ws6.col_values(1)
        realname, caps, spaces = find_name(name, user_list)
        if realname != None:
            cell = bot3ws6.find(realname)
            row_num = cell.row
            currentspent = float(bot3ws6.cell(row_num, 5).value)
            new = currentspent - amount
            bot3ws6.update_cell(row_num, 5, new)
            await ctx.send(realname + " has been refunded " + str(amount) + " RBPPUNOX")
            logbody = ["refund", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, amount, kp])]
            bot3ws11.append_row(logbody)
        else:
            await ctx.send(name + " not in list!")
    if kp == "DPKP":
        user_list = bot3ws7.col_values(1)
        realname, caps, spaces = find_name(name, user_list)
        if realname != None:
            cell = bot3ws7.find(realname)
            row_num = cell.row
            currentspent = float(bot3ws7.cell(row_num, 5).value)
            new = currentspent - amount
            bot3ws7.update_cell(row_num, 5, new)
            await ctx.send(realname + " has been refunded " + str(amount) + " DPKP")
            logbody = ["refund", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, amount, kp])]
            bot3ws11.append_row(logbody)
        else:
            await ctx.send(name + " not in list!")
    if kp == "RBPP":
        user_list = bot5ws8.col_values(1)
        realname, caps, spaces = find_name(name, user_list)
        if realname != None:
            cell = bot5ws8.find(realname)
            row_num = cell.row
            currentspent = float(bot5ws8.cell(row_num, 5).value)
            new = currentspent - amount
            bot5ws8.update_cell(row_num, 5, new)
            await ctx.send(realname + " has been refunded " + str(amount) + " RBPP")
            logbody = ["refund", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, amount, kp])]
            bot3ws11.append_row(logbody)
        else:
            await ctx.send(name + " not in list!")
    


    

@client.command(guild_ids = guilds)
@commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
async def adjust(ctx, name, number, kp):
    """adjusts a players kp by a certain amount"""
    kp = kp.upper()
    number = float(number)
    if kp == "VKP":
        user_list = bot5ws2.col_values(1)
        realname, caps, spaces = find_name(name, user_list)
        if realname != None:
            cell = bot5ws2.find(realname)
            row_num = cell.row
            adjusted = float(bot5ws2.cell(row_num, 6).value) + number
            bot5ws2.update_cell(row_num, 6, adjusted)
            await ctx.send(realname + "'s VKP has been adjusted by " + str(number))
            logbody = ["adjust", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, number, kp])]
            bot3ws11.append_row(logbody)
        else:
            await ctx.send(name + " not in list!")
    if kp == "GKP":
        user_list = bot5ws3.col_values(1)
        realname, caps, spaces = find_name(name, user_list)
        if realname != None:
            cell = bot5ws3.find(realname)
            row_num = cell.row
            adjusted = float(bot5ws3.cell(row_num, 6).value) + number
            bot5ws3.update_cell(row_num, 6, adjusted)
            await ctx.send(realname + "'s GKP has been adjusted by " + str(number))
            logbody = ["adjust", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, number, kp])]
            bot3ws11.append_row(logbody)
        else:
            await ctx.send(name + " not in list!")
    if kp == "PKP":
        user_list = bot5ws4.col_values(1)
        realname, caps, spaces = find_name(name, user_list)
        if realname != None:
            cell = bot5ws4.find(realname)
            row_num = cell.row
            adjusted = float(bot5ws4.cell(row_num, 6).value) + number
            bot5ws4.update_cell(row_num, 6, adjusted)
            await ctx.send(realname + "'s PKP has been adjusted by " + str(number))
            logbody = ["adjust", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, number, kp])]
            bot3ws11.append_row(logbody)
        else:
            await ctx.send(name + " not in list!")
    if kp == "AKP":
        user_list = bot5ws5.col_values(1)
        realname, caps, spaces = find_name(name, user_list)
        if realname != None:
            cell = bot5ws5.find(realname)
            row_num = cell.row
            adjusted = float(bot5ws5.cell(row_num, 6).value) + number
            bot5ws5.update_cell(row_num, 6, adjusted)
            await ctx.send(realname + "'s AKP has been adjusted by " + str(number))
            logbody = ["adjust", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, number, kp])]
            bot3ws11.append_row(logbody)
        else:
            await ctx.send(name + " not in list!")
    if kp == "RBPPUNOX":
        user_list = bot5ws6.col_values(1)
        realname, caps, spaces = find_name(name, user_list)
        if realname != None:
            cell = bot5ws6.find(realname)
            row_num = cell.row
            adjusted = float(bot5ws6.cell(row_num, 6).value) + number
            bot5ws6.update_cell(row_num, 6, adjusted)
            await ctx.send(realname + "'s RBPPUNOX has been adjusted by " + str(number))
            logbody = ["adjust", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, number, kp])]
            bot3ws11.append_row(logbody)
        else:
            await ctx.send(name + " not in list!")
    if kp == "DPKP":
        user_list = bot5ws7.col_values(1)
        realname, caps, spaces = find_name(name, user_list)
        if realname != None:
            cell = bot5ws7.find(realname)
            row_num = cell.row
            adjusted = float(bot5ws7.cell(row_num, 6).value) + number
            bot5ws7.update_cell(row_num, 6, adjusted)
            await ctx.send(realname + "'s DPKP has been adjusted by " + str(number))
            logbody = ["adjust", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, number, kp])]
            bot3ws11.append_row(logbody)
        else:
            await ctx.send(name + " not in list!")
    if kp == "RBPP":
        user_list = bot5ws8.col_values(1)
        realname, caps, spaces = find_name(name, user_list)
        if realname != None:
            cell = bot5ws8.find(realname)
            row_num = cell.row
            adjusted = float(bot5ws8.cell(row_num, 6).value) + number
            bot5ws8.update_cell(row_num, 6, adjusted)
            await ctx.send(realname + "'s RBPP has been adjusted by " + str(number))
            logbody = ["adjust", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, number, kp])]
            bot3ws11.append_row(logbody)
        else:
            await ctx.send(name + " not in list!")

@client.command(guild_ids = guilds)
@commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
async def boss(ctx, bossname, toonlist):
    """attendance command"""
    # check the bossname against the lists
    # some bosses have level requirements to check also, so need to pull the row from the roster
    user_list = bot4ws1.col_values(1)
    bossname = bossname.capitalize()
    await ctx.send("processing attendance for " + bossname)
    toonlist = toonlist.split(",")
    # remove leading and trailing spaces from the toon list
    toonlist = [x.strip() for x in toonlist]
    rbpp_list = []
    dpkp_list = []
    akp_list = []
    akp_low_list = []
    pkp_list = []
    pkp_low_list = []  
    gkp_list = []
    vkp_list = []
    rbppunox_list = []
    kppool = []
    toonlist = list(set(toonlist))
    currenttime =  dt.now().strftime("%d/%m/%Y %H:%M:%S")
    for t in toonlist:
        findt, caps, spaces = find_name(t, user_list)
        print("doing attendance for " + findt)
        if findt != None:
            cell = bot4ws1.find(findt, in_column=1)
            row_num = cell.row
            #get the whole row
            row = bot3ws1.row_values(row_num)
            level = int(row[3])
            maintoon = row[2]
            maintoon = toBool(maintoon)
            mainchar = row[6]
            #insert level checking here if its needed

            if maintoon and findt not in rbpp_list:
            # rbpp and dino and crom
                if bossname in rbpp_bosses:
                    cell2 = bot2ws8.find(findt, in_column=1)
                    row_num2 = cell2.row
                    earned = float(bot2ws8.cell(row_num2, 4).value)
                    new = earned + 1
                    bot2ws8.update_cell(row_num2, 4, new)
                    bot5ws8.update_cell(row_num2, 2, currenttime)
                    rbpp_list.append(findt)
                    if "RBPP" not in kppool:
                        kppool.append("RBPP")
                if bossname in dpkp_bosses:
                    cell3 = bot1ws7.find(findt, in_column=1)
                    row_num3 = cell3.row
                    earned = float(bot1ws7.cell(row_num3, 4).value)
                    new = earned + dpkp_bosses[bossname]
                    bot1ws7.update_cell(row_num3, 4, new)
                    bot5ws7.update_cell(row_num3, 2, currenttime)
                    dpkp_list.append(findt)
                    if "DPKP" not in kppool:
                        kppool.append("DPKP")
                if bossname in rbppunox_bosses:
                    cell8 = bot2ws6.find(findt, in_column=1)
                    row_num8 = cell8.row
                    earned = float(bot2ws6.cell(row_num8, 4).value)
                    new = earned + rbppunox_bosses[bossname]
                    bot2ws6.update_cell(row_num8, 4, new)
                    bot5ws6.update_cell(row_num8, 2, currenttime)
                    rbppunox_list.append(findt)
                    if "RBPPUNOX" not in kppool:
                        kppool.append("RBPPUNOX")
                if bossname in vkp_bosses:
                    cell7 = bot1ws2.find(findt, in_column=1)
                    row_num7 = cell7.row
                    earned = float(bot1ws2.cell(row_num7, 4).value)
                    new = earned + vkp_bosses[bossname]
                    bot1ws2.update_cell(row_num7, 4, new)
                    bot5ws2.update_cell(row_num7, 2, currenttime)
                    vkp_list.append(findt)
                    if "VKP" not in kppool:
                        kppool.append("VKP")
            elif mainchar not in rbpp_list:
                if bossname in rbpp_bosses:
                    cell2 = bot2ws8.find(mainchar, in_column=1)
                    row_num2 = cell2.row
                    earned = float(bot2ws8.cell(row_num2, 4).value)
                    new = earned + 1
                    bot2ws8.update_cell(row_num2, 4, new)
                    bot5ws8.update_cell(row_num2, 2, currenttime)
                    rbpp_list.append(mainchar)
                    if "RBPP" not in kppool:
                        kppool.append("RBPP")
                if bossname in dpkp_bosses:
                    cell3 = bot1ws7.find(mainchar, in_column=1)
                    row_num3 = cell3.row
                    earned = float(bot1ws7.cell(row_num3, 4).value)
                    new = earned + dpkp_bosses[bossname]
                    bot1ws7.update_cell(row_num3, 4, new)
                    bot5ws7.update_cell(row_num3, 2, currenttime)
                    dpkp_list.append(mainchar)
                    if "DPKP" not in kppool:
                        kppool.append("DPKP")
                if bossname in rbppunox_bosses:
                    cell8 = bot2ws6.find(mainchar, in_column=1)
                    row_num8 = cell8.row
                    earned = float(bot2ws6.cell(row_num8, 4).value)
                    new = earned + rbppunox_bosses[bossname]
                    bot2ws6.update_cell(row_num8, 4, new)
                    bot5ws6.update_cell(row_num8, 2, currenttime)
                    rbppunox_list.append(mainchar)
                    if "RBPPUNOX" not in kppool:
                        kppool.append("RBPPUNOX")
                if bossname in vkp_bosses:
                    cell7 = bot1ws2.find(mainchar, in_column=1)
                    row_num7 = cell7.row
                    earned = float(bot1ws2.cell(row_num7, 4).value)
                    new = earned + vkp_bosses[bossname]
                    bot1ws2.update_cell(row_num7, 4, new)
                    bot5ws2.update_cell(row_num7, 2, currenttime)
                    vkp_list.append(mainchar)
                    if "VKP" not in kppool:
                        kppool.append("VKP")
            if bossname in akp_bosses:
                if level >= 220:
                    cell4 = bot1ws5.find(findt, in_column=1)
                    row_num4 = cell4.row
                    earned = float(bot1ws5.cell(row_num4, 4).value)
                    new = earned + akp_bosses[bossname]
                    bot1ws5.update_cell(row_num4, 4, new)
                    bot5ws5.update_cell(row_num4, 2, currenttime)
                    akp_list.append(findt)
                    if "AKP" not in kppool:
                        kppool.append("AKP")
                else:
                    cell4 = bot1ws5.find(findt, in_column=1)
                    row_num4 = cell4.row
                    earned = float(bot1ws5.cell(row_num4, 4).value)
                    new = earned + akp_bosses[bossname] - 5
                    bot1ws5.update_cell(row_num4, 4, new)
                    bot5ws5.update_cell(row_num4, 2, currenttime)
                    akp_low_list.append(findt)
                    if "AKP" not in kppool:
                        kppool.append("AKP")
            if bossname in pkp_bosses:
                if level >= 220 or bossname == "Bane":
                    cell5 = bot1ws4.find(findt, in_column=1)
                    row_num5 = cell5.row
                    earned = float(bot1ws4.cell(row_num5, 4).value)
                    new = earned + pkp_bosses[bossname]
                    bot1ws4.update_cell(row_num5, 4, new)
                    bot5ws4.update_cell(row_num5, 2, currenttime)
                    pkp_list.append(findt)
                    if "PKP" not in kppool:
                        kppool.append("PKP")
                else:
                    cell5 = bot1ws4.find(findt, in_column=1)
                    row_num5 = cell5.row
                    earned = float(bot1ws4.cell(row_num5, 4).value)
                    new = earned + pkp_bosses[bossname] - 5
                    bot1ws4.update_cell(row_num5, 4, new)
                    bot5ws4.update_cell(row_num5, 2, currenttime)
                    pkp_low_list.append(findt)
                    if "PKP" not in kppool:
                        kppool.append("PKP")
            if bossname in gkp_bosses:
                cell6 = bot1ws3.find(findt, in_column=1)
                row_num6 = cell6.row
                earned = float(bot1ws3.cell(row_num6, 4).value)
                new = earned + gkp_bosses[bossname]
                bot1ws3.update_cell(row_num6, 4, new)
                bot5ws3.update_cell(row_num6, 2, currenttime)
                gkp_list.append(findt)
                if "GKP" not in kppool:
                    kppool.append("GKP")
        else:
            await ctx.send(t + " not in list!")
            toonlist.pop(toonlist.index(t))
    print("creating embed")
    embed = discord.Embed(title = bossname + " Attendance", colour=discord.Color.orange())
    #emptyattend = False
    if len(toonlist) == 0:
        embed.add_field(name = "No toons attended", value = "No KP awarded", inline = False)
        #emptyattend = True
    if rbpp_list != []:
        rbpp_to_send = ', '.join(map(str, rbpp_list))
        embed.add_field(name = "1 RBPP", value = rbpp_to_send, inline = False)
        bosslog = [dt.now().strftime("%d/%m/%Y %H:%M:%S"), str(bossname), "RBPP", str(rbpp_list)]
        bot3ws10.append_row(bosslog, value_input_option='USER_ENTERED')
    if dpkp_list != []:
        dpkp_to_send = ', '.join(map(str, dpkp_list))
        embed.add_field(name = str(dpkp_bosses[bossname])+ " DPKP", value = dpkp_to_send, inline = False)
        bosslog = [dt.now().strftime("%d/%m/%Y %H:%M:%S"), str(bossname), "DPKP", str(dpkp_list)]
        bot3ws10.append_row(bosslog, value_input_option='USER_ENTERED')
    if akp_list != []:
        akp_to_send = ', '.join(map(str, akp_list))
        embed.add_field(name = str(akp_bosses[bossname])+ " AKP", value = akp_to_send, inline = False)
        bosslog = [dt.now().strftime("%d/%m/%Y %H:%M:%S"), str(bossname), "AKP", str(akp_list)]
        bot3ws10.append_row(bosslog, value_input_option='USER_ENTERED')
    if akp_low_list != []:
        akp_low_to_send = ', '.join(map(str, akp_low_list))
        embed.add_field(name = str((akp_bosses[bossname]-5)) + " AKP", value = akp_low_to_send, inline = False)
        bosslog = [dt.now().strftime("%d/%m/%Y %H:%M:%S"), str(bossname), "AKP", str(akp_list)]
        bot3ws10.append_row(bosslog, value_input_option='USER_ENTERED')
    if pkp_list != []:
        pkp_to_send = ', '.join(map(str, pkp_list))
        embed.add_field(name = str(pkp_bosses[bossname])+ " PKP", value = pkp_to_send, inline = False)
        bosslog = [dt.now().strftime("%d/%m/%Y %H:%M:%S"), str(bossname), "PKP", str(pkp_list)]
        bot3ws10.append_row(bosslog, value_input_option='USER_ENTERED')
    if pkp_low_list != []:
        pkp_low_to_send = ', '.join(map(str, pkp_low_list))
        embed.add_field(name = str((pkp_bosses[bossname]-5)) + " PKP", value = pkp_low_to_send, inline = False)
        bosslog = [dt.now().strftime("%d/%m/%Y %H:%M:%S"), str(bossname), "PKP", str(pkp_list)]
        bot3ws10.append_row(bosslog, value_input_option='USER_ENTERED')
    if gkp_list != []:
        gkp_to_send = ', '.join(map(str, gkp_list))
        embed.add_field(name = str(gkp_bosses[bossname])+ " GKP", value = gkp_to_send, inline = False)
        bosslog = [dt.now().strftime("%d/%m/%Y %H:%M:%S"), str(bossname), "GKP", str(gkp_list)]
        bot3ws10.append_row(bosslog, value_input_option='USER_ENTERED')
    if vkp_list != []:
        vkp_to_send = ', '.join(map(str, vkp_list))
        embed.add_field(name = str(vkp_bosses[bossname])+ " VKP", value = vkp_to_send, inline = False)
        bosslog = [dt.now().strftime("%d/%m/%Y %H:%M:%S"), str(bossname), "VKP", str(vkp_list)]
        bot3ws10.append_row(bosslog, value_input_option='USER_ENTERED')
    if rbppunox_list != []:
        rbppunox_to_send = ', '.join(map(str, rbppunox_list))
        embed.add_field(name = str(rbppunox_bosses[bossname])+ " RBPPUNOX", value = rbppunox_to_send, inline = False)
        bosslog = [dt.now().strftime("%d/%m/%Y %H:%M:%S"), str(bossname), "RBPPUNOX", str(rbppunox_list)]
        bot3ws10.append_row(bosslog, value_input_option='USER_ENTERED')
    
    print("sending embed")

    # if not emptyattend:
    #     bosslog = [dt.now().strftime("%d/%m/%Y %H:%M:%S"), str(bossname), str(kppool), str(toonlist)]
    #     bot3ws10.append_row(bosslog, value_input_option='USER_ENTERED')

    await ctx.send(embed=embed)
    logbody = ["boss", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([bossname, toonlist])]
    bot3ws11.append_row(logbody)
    
@client.command(guild_ids = guilds)
@commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
async def bosshalf(ctx, bossname, toonlist):
    """attendance command that grants half points for the boss"""
    await ctx.send("processing a half point attendance for " + bossname)
    # check the bossname against the lists
    # some bosses have level requirements to check also, so need to pull the row from the roster
    user_list = bot3ws1.col_values(1)
    bossname = bossname.capitalize()
    toonlist = toonlist.split(",")
    toonlist = [x.strip() for x in toonlist]
    rbpp_list = []
    dpkp_list = []
    akp_list = []
    akp_low_list = []
    pkp_list = []
    pkp_low_list = []  
    gkp_list = []
    vkp_list = []
    rbppunox_list = []
    kppool = []
    toonlist = list(set(toonlist))
    currenttime =  dt.now().strftime("%d/%m/%Y %H:%M:%S")
    for t in toonlist:
        findt, caps, spaces = find_name(t, user_list)
        if findt != None:
            cell = bot3ws1.find(findt)
            row_num = cell.row
            level = int(bot3ws1.cell(row_num, 4).value)
            maintoon = bot3ws1.cell(row_num, 3).value
            maintoon = toBool(maintoon)
            # fun times: no dpkp and rbpp from bosshalf
            # if maintoon:
            # # rbpp and dino
            #     if bossname in rbpp_bosses:
            #         cell2 = bot2ws8.find(findt)
            #         row_num2 = cell2.row
            #         earned = float(bot2ws8.cell(row_num2, 4).value)
            #         new = earned + 1
            #         bot2ws8.update_cell(row_num2, 4, new)
            #         bot5ws8.update_cell(row_num2, 2, currenttime)
            #         rbpp_list.append(findt)
            #         if "RBPP" not in kppool:
            #             kppool.append("RBPP")
            #     if bossname in dpkp_bosses:
            #         cell3 = bot1ws7.find(findt)
            #         row_num3 = cell3.row
            #         earned = float(bot1ws7.cell(row_num3, 4).value)
            #         new = earned + (dpkp_bosses[bossname])/2
            #         bot1ws7.update_cell(row_num3, 4, new)
            #         bot5ws7.update_cell(row_num3, 2, currenttime)
            #         dpkp_list.append(findt)
            #         if "DPKP" not in kppool:
            #             kppool.append("DPKP")
            #     if bossname in rbppunox_bosses:
            #         cell8 = bot2ws6.find(findt)
            #         row_num8 = cell8.row
            #         earned = float(bot2ws6.cell(row_num8, 4).value)
            #         new = earned + (rbppunox_bosses[bossname])/2
            #         bot2ws6.update_cell(row_num8, 4, new)
            #         bot5ws6.update_cell(row_num8, 2, currenttime)
            #         rbppunox_list.append(findt)
            #         if "RBPPUNOX" not in kppool:
            #             kppool.append("RBPPUNOX")
            if bossname in akp_bosses:
                if level >= 220:
                    cell4 = bot1ws5.find(findt)
                    row_num4 = cell4.row
                    earned = float(bot1ws5.cell(row_num4, 4).value)
                    new = earned + (akp_bosses[bossname])/2
                    bot1ws5.update_cell(row_num4, 4, new)
                    bot5ws5.update_cell(row_num4, 2, currenttime)
                    akp_list.append(findt)
                    if "AKP" not in kppool:
                        kppool.append("AKP")
                else:
                    cell4 = bot1ws5.find(findt)
                    row_num4 = cell4.row
                    earned = float(bot1ws5.cell(row_num4, 4).value)
                    new = earned + (akp_bosses[bossname] - 5)/2
                    bot1ws5.update_cell(row_num4, 4, new)
                    bot5ws5.update_cell(row_num4, 2, currenttime)
                    akp_low_list.append(findt)
                    if "AKP" not in kppool:
                        kppool.append("AKP")
            if bossname in pkp_bosses:
                if level >= 220 or bossname == "Bane":
                    cell5 = bot1ws4.find(findt)
                    row_num5 = cell5.row
                    earned = float(bot1ws4.cell(row_num5, 4).value)
                    new = earned + (pkp_bosses[bossname])/2
                    bot1ws4.update_cell(row_num5, 4, new)
                    bot5ws4.update_cell(row_num5, 2, currenttime)
                    pkp_list.append(findt)
                    if "PKP" not in kppool:
                        kppool.append("PKP")
                else:
                    cell5 = bot1ws4.find(findt)
                    row_num5 = cell5.row
                    earned = float(bot1ws4.cell(row_num5, 4).value)
                    new = earned + (pkp_bosses[bossname] - 5)/2
                    bot1ws4.update_cell(row_num5, 4, new)
                    bot5ws4.update_cell(row_num5, 2, currenttime)
                    pkp_low_list.append(findt)
                    if "PKP" not in kppool:
                        kppool.append("PKP")
            if bossname in gkp_bosses:
                cell6 = bot1ws3.find(findt)
                row_num6 = cell6.row
                earned = float(bot1ws3.cell(row_num6, 4).value)
                new = earned + (gkp_bosses[bossname])/2
                bot1ws3.update_cell(row_num6, 4, new)
                bot5ws3.update_cell(row_num6, 2, currenttime)
                gkp_list.append(findt)
                if "GKP" not in kppool:
                    kppool.append("GKP")
        else:
            await ctx.send(t + " not in list!")
            toonlist.pop(toonlist.index(t))
    embed = discord.Embed(title = bossname + " Attendance", colour=discord.Color.orange())
    emptyattend = False
    if len(toonlist) == 0:
        embed.add_field(name = "No toons attended", value = "No KP awarded", inline = False)
        emptyattend = True
    if rbpp_list != []:
        rbpp_to_send = ', '.join(map(str, rbpp_list))
        embed.add_field(name = "1 RBPP", value = rbpp_to_send, inline = False)
    if dpkp_list != []:
        dpkp_to_send = ', '.join(map(str, dpkp_list))
        embed.add_field(name = str(dpkp_bosses[bossname]/2)+ " DPKP", value = dpkp_to_send, inline = False)
    if akp_list != []:
        akp_to_send = ', '.join(map(str, akp_list))
        embed.add_field(name = str(akp_bosses[bossname]/2)+ " AKP", value = akp_to_send, inline = False)
    if akp_low_list != []:
        akp_low_to_send = ', '.join(map(str, akp_low_list))
        embed.add_field(name = str((akp_bosses[bossname]-5)/2) + " AKP", value = akp_low_to_send, inline = False)
    if pkp_list != []:
        pkp_to_send = ', '.join(map(str, pkp_list))
        embed.add_field(name = str(pkp_bosses[bossname]/2)+ " PKP", value = pkp_to_send, inline = False)
    if pkp_low_list != []:
        pkp_low_to_send = ', '.join(map(str, pkp_low_list))
        embed.add_field(name = str((pkp_bosses[bossname]-5)/2) + " PKP", value = pkp_low_to_send, inline = False)
    if gkp_list != []:
        gkp_to_send = ', '.join(map(str, gkp_list))
        embed.add_field(name = str(gkp_bosses[bossname]/2)+ " GKP", value = gkp_to_send, inline = False)
    if vkp_list != []:
        vkp_to_send = ', '.join(map(str, vkp_list))
        embed.add_field(name = str(vkp_bosses[bossname]/2)+ " VKP", value = vkp_to_send, inline = False)

    if not emptyattend:
        bosslog = [dt.now().strftime("%d/%m/%Y %H:%M:%S"), str(bossname + " HALF"), str(kppool), str(toonlist)]
        bot3ws10.append_row(bosslog, value_input_option='USER_ENTERED')

    await ctx.send(embed=embed)
    
    logbody = ["bosshalf", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([bossname, toonlist])]
    bot3ws11.append_row(logbody)



@client.command(guild_ids = guilds)
async def pointleaderboard(ctx, kp, maxkp = 99999, number = 10):
    """displays the leaderboard for current points in a certain KP pool"""
    kp = kp.upper()
    maxkp = float(maxkp)
    number = int(number)
    if kp == "VKP":
        namelist = bot4ws2.col_values(1)
        pointlist = bot4ws2.col_values(7)
    elif kp == "GKP":
        namelist = bot4ws3.col_values(1)
        pointlist = bot4ws3.col_values(7)
    elif kp == "PKP":
        namelist = bot4ws4.col_values(1)
        pointlist = bot4ws4.col_values(7)
    elif kp == "AKP":
        namelist = bot4ws5.col_values(1)
        pointlist = bot4ws5.col_values(7)
    elif kp == "RBPPUNOX":
        namelist = bot4ws6.col_values(1)
        pointlist = bot4ws6.col_values(7)
    elif kp == "DPKP":
        namelist = bot4ws7.col_values(1)
        pointlist = bot4ws7.col_values(7)
    elif kp == "RBPP":
        namelist = bot4ws8.col_values(1)
        pointlist = bot4ws8.col_values(7)
    else:
        await ctx.send("Invalid KP pool")
    del namelist[0]
    del pointlist[0]
    floatpointlist = list(map(float, pointlist))
    combined = list(zip(namelist, floatpointlist))
    sortedcombined = sorted(combined, key=lambda x: x[1], reverse=True)
    # remove the people who have more than maxkp
    sortedcombined = [x for x in sortedcombined if x[1] <= maxkp]
    embed = discord.Embed(title = kp + " Leaderboard", colour=discord.Color.orange())
    if number < len(sortedcombined):
        for i in range(number):
            embed.add_field(name = str(i + 1) + ". " + sortedcombined[i][0], value = sortedcombined[i][1], inline = False)
    else:
        for i in range(len(sortedcombined)):
            embed.add_field(name = str(i + 1) + ". " + sortedcombined[i][0], value = sortedcombined[i][1], inline = False)
    await ctx.send(embed=embed)
    

@client.command(guild_ids = guilds)
async def pointleaderboardlast30(ctx, kp, maxatt = 100, number = 10):
    """darkhealz last 30 command"""
    kp = kp.upper()
    maxatt = int(maxatt)
    number = int(number)
    if kp == "VKP":
       namelist = bot4ws2.col_values(1)
       pointlist = bot4ws2.col_values(7)
       attlist = bot4ws2.col_values(3)
    elif kp == "GKP":
        namelist = bot4ws3.col_values(1)
        pointlist = bot4ws3.col_values(7)
        attlist = bot4ws3.col_values(3)
    elif kp == "PKP":
        namelist = bot4ws4.col_values(1)
        pointlist = bot4ws4.col_values(7)
        attlist = bot4ws4.col_values(3)
    elif kp == "AKP":
        namelist = bot4ws5.col_values(1)
        pointlist = bot4ws5.col_values(7)
        attlist = bot4ws5.col_values(3)
    elif kp == "RBPPUNOX":
        namelist = bot4ws6.col_values(1)
        pointlist = bot4ws6.col_values(7)
        attlist = bot4ws6.col_values(3)
    elif kp == "DPKP":
        namelist = bot4ws7.col_values(1)
        pointlist = bot4ws7.col_values(7)
        attlist = bot4ws7.col_values(3)
    elif kp == "RBPP":
        namelist = bot4ws8.col_values(1)
        pointlist = bot4ws8.col_values(7)
        attlist = bot4ws8.col_values(3)
    else:
        await ctx.send("Invalid KP pool")

    del namelist[0]
    del pointlist[0]
    del attlist[0]
    floatpointlist = list(map(float, pointlist))
    # attlist is in the format "7.49%", so we need to convert it to a float and remove the percentage sign
    floatattlist = [float(x.strip('%')) for x in attlist]
    combined = list(zip(namelist, floatpointlist, floatattlist))
    # sort by attlist
    sortedcombined = sorted(combined, key=lambda x: x[2], reverse=True)
    # remove the people who have more than maxatt
    sortedcombined = [x for x in sortedcombined if x[2] <= maxatt]
    embed = discord.Embed(title = kp + " Leaderboard", colour=discord.Color.orange())
    if number < len(sortedcombined):
        for i in range(number):
            embed.add_field(name = str(i + 1) + ". " + sortedcombined[i][0], value = f"{sortedcombined[i][1]} ({sortedcombined[i][2]}%)", inline = False)
    else:
        for i in range(len(sortedcombined)):
            embed.add_field(name = str(i + 1) + ". " + sortedcombined[i][0], value = f"{sortedcombined[i][1]} ({sortedcombined[i][2]}%)", inline = False)
    await ctx.send(embed=embed)




# @client.command(guild_ids = guilds)
# async def classpointleaderboard(ctx, kp, classname, maxkp = 99999, number = 10):
#     """displays the leaderboard for current points in a certain KP pool"""
#     kp = kp.upper()
#     classname = classname.capitalize()
#     maxkp = float(maxkp)
#     if kp == "VKP":
#         namelist = bot4ws2.col_values(1)
#         pointlist = bot4ws2.col_values(7)
#     elif kp == "GKP":
#         namelist = bot4ws3.col_values(1)
#         pointlist = bot4ws3.col_values(7)
#     elif kp == "PKP":
#         namelist = bot4ws4.col_values(1)
#         pointlist = bot4ws4.col_values(7)
#     elif kp == "AKP":
#         namelist = bot4ws5.col_values(1)
#         pointlist = bot4ws5.col_values(7)
#     elif kp == "RBPPUNOX":
#         namelist = bot4ws6.col_values(1)
#         pointlist = bot4ws6.col_values(7)
#     elif kp == "DPKP":
#         namelist = bot4ws7.col_values(1)
#         pointlist = bot4ws7.col_values(7)
#     elif kp == "RBPP":
#         namelist = bot4ws8.col_values(1)
#         pointlist = bot4ws8.col_values(7)
#     else:
#         await ctx.send("Invalid KP pool")
#     del namelist[0]
#     del pointlist[0]
#     floatpointlist = list(map(float, pointlist))
#     combined = list(zip(namelist, floatpointlist))
#     sortedcombined = sorted(combined, key=lambda x: x[1], reverse=True)
#     # remove the people who have more than maxkp
#     sortedcombined = [x for x in sortedcombined if x[1] <= maxkp]
#     embed = discord.Embed(title = kp + " Leaderboard", colour=discord.Color.orange())
#     if number < len(sortedcombined):
#         for i in range(number):
#             embed.add_field(name = str(i + 1) + ". " + sortedcombined[i][0], value = sortedcombined[i][1], inline = False)
#     else:
#         for i in range(len(sortedcombined)):
#             embed.add_field(name = str(i + 1) + ". " + sortedcombined[i][0], value = sortedcombined[i][1], inline = False)
#     await ctx.send(embed=embed)
    

@client.command(guild_ids = guilds)
async def earnedleaderboard(ctx, kp, number = 10):
    """displays the leaderboard for total points earned in a certain KP pool"""
    kp = kp.upper()
    if kp == "VKP":
        namelist = bot4ws2.col_values(1)
        pointlist = bot4ws2.col_values(4)
    elif kp == "GKP":
        namelist = bot4ws3.col_values(1)
        pointlist = bot4ws3.col_values(4)
    elif kp == "PKP":
        namelist = bot4ws4.col_values(1)
        pointlist = bot4ws4.col_values(4)
    elif kp == "AKP":
        namelist = bot4ws5.col_values(1)
        pointlist = bot4ws5.col_values(4)
    elif kp == "RBPPUNOX":
        namelist = bot4ws6.col_values(1)
        pointlist = bot4ws6.col_values(4)
    elif kp == "DPKP":
        namelist = bot4ws7.col_values(1)
        pointlist = bot4ws7.col_values(4)
    elif kp == "RBPP":
        namelist = bot4ws8.col_values(1)
        pointlist = bot4ws8.col_values(4)
    else:
        await ctx.send("Invalid KP pool")
    del namelist[0]
    del pointlist[0]
    floatpointlist = list(map(float, pointlist))
    combined = list(zip(namelist, floatpointlist))
    sortedcombined = sorted(combined, key=lambda x: x[1], reverse=True)
    embed = discord.Embed(title = kp + " Leaderboard", colour=discord.Color.orange())
    if number < len(sortedcombined):
        for i in range(number):
            embed.add_field(name = str(i + 1) + ". " + sortedcombined[i][0], value = sortedcombined[i][1], inline = False)
    else:
        for i in range(len(sortedcombined)):
            embed.add_field(name = str(i + 1) + ". " + sortedcombined[i][0], value = sortedcombined[i][1], inline = False)
    await ctx.send(embed=embed)


@client.command(guild_ids = guilds)
async def apply(ctx):
    """allows new members to apply for the clan"""
    await ctx.send("Please fill out the application form here: https://forms.gle/zDD3mr56xELXUG4n6")
    leaderchannelid = 1180242808070742117
    leaderchannel = client.get_channel(leaderchannelid)
    await leaderchannel.send("New application started by " + str(ctx.author.name))


@client.command(guild_ids = guilds)
async def new(ctx):
    """Displays the help for new players"""
    await ctx.send("""Welcome to Relentless! Please start by sending your toon names and levels to the character-declaration channel, along with which is your main.
For Example:
Main: REDALiCE, 220 DPS Druid
Alts: LiLALiCE, 180 Fire Mage
BiGALiCE, 178 Sword Warrior               

as this discord bot is a work in progress, please also set up an account on our website. This is found at http://www.relentless.dkpsystem.com

A leader will approve all this shortly so you can start earning KP (Kill points)
                   
All the point acronyms may be confusing at first, but here is the break down:
                   
VKP - Dragon Kill Points (earned for killing Crom)
PKP - Proteus Kill Points (earned for killing Proteus and Bane Legits)
AKP - Arcane Kill Points (earned for killing Gelebron and Proteus)
GKP - Gardens Kill Points (earned for killing Bloodthorn and Factions)
DPKP - Dino Kill Points (earned for killing Dino)
RBPP - Relentless Boss Participation Points (earned for attending raids that give KP, not legacies)
                   
send \"$new2\" for the next steps!""")
    
@client.command(guild_ids = guilds)
async def new2(ctx):
    """displays the second set of help for new players"""
    await ctx.send("""You are setup and ready to start earning some points! Your Recruitment period will be 1 month, and you are required to get 50 RBPP (attendance points) through this period to be promoted. 

Please take some time to get familiar with the Relentless Rules document, here you can find all the rules each player in Relentless must abide by. You can find the rules doc here. https://docs.google.com/document/d/1WT0nh2NzUh2XQpnODY3zPMe_35KwQImsznA7dXqGxds/mobilebasic
                   
Once you read this, you may have some questions! Feel free to ask for clarification in the #question-faq channel.
                   
As this is a lot of information to take in, please allow yourself to review this content over the course of a few days. And of course if you have any further questions please reach out to a fellow clannie or a leader. The Winston bot is also a valuable resource created by REDALiCE (and largely plagiarised from Magister22's bot Magi Jr), you can type “$information” and get a wide assortment of answers. Once you finish and fully understand the rules, please type $new3.""")
    
@client.command(guild_ids = guilds)
async def new3(ctx):
    """displays the third set of help for new players"""
    await ctx.send("""So you are now setup to earn points and know the rules. You are ready to start grinding points. It is important to note, each toon is considered its separate toon. It earns its own points, and spends its own points. You are allowed to transfer points from one toon to another only up to 4 hours after the attend has been posted in KP chat. After that you can no longer transfer those points.
                   
CAMPING! Camping is the easiest way to earn points! If you are camping a raid while it is open (Mord Necro Hrung Gele BT) and another raid spawns while you are/have been camping it, you will receive FULL POINTS to the toon camping that is unable to attend the raid due to camping. Please note you can only collect points for a single toon for camping each spawning raid.
                   
(You can not log when a raid spawns and run to camp something, you must have been camping before/during when the raid spawns). Be sure to say in KP chat after the raid attend is posted “(Toon you wish to receive points on) was camping (raid camping)” to get points. You do not need to camp with the toon you want points on, any toon you camp with will suffice.

Congratulations you have completed the Relentless Orientation. Again, if you have any questions at all please reach out to a fellow clannie or leader and we will be happy to help you out. You can type “$leadership” for a list of the current leaders. We strive to see everyone succeed and thrive here in Relentless, Have Fun!""")
    

@client.command(guild_ids = guilds)
async def clanrules(ctx):
    """Displays the clan rules"""
    await ctx.send("""Here is the link to the Relentless Clan rules:
https://docs.google.com/document/d/1WT0nh2NzUh2XQpnODY3zPMe_35KwQImsznA7dXqGxds/mobilebasic""")


@client.command(guild_ids = guilds)
async def kpinfo(ctx):
    """Displays the KP information"""
    await ctx.send("""Here is the breakdown of the KP pools:
                   
VKP (Valley kill points); earned from Crom (maybe future Valley content)
Used to bid on Crom Gear
GKP (Garden kill points); earned from Bloodthorn and Weekly bosses
Used to bid on Bloodthorn items
AKP (Arcane kill points); earned from Gelebron and Proteus
Used to bid on Gelebron items
PKP (Proteus kill points); earned from Proteus and Bane Legit
Used to bid on Proteus items                  
LEP (Legacy kill points); Old legacy point pool. unused, repurposed for RBPPUNOX
DPKP (Dhiothu kill points); earned from Dhiothu
Used to bid on Dhiothu items
RBPP (attendance points); earned from all bosses listed above except Weekly bosses and Legacy bosses
RBPP only used to keep track of attendance and activity, not used to bid on items""")
    

@client.command(guild_ids = guilds)
async def dinoreq(ctx):
    """Displays the Dino requirements"""
    await ctx.send("""Dino Requirements:
                   
To start Dino will require every class to have Dino Ready gear + Skills to participate for points. Dino Requirement: MUST BE LEVEL 220 FOR ANY POINTS.
Dino Requirement Update:

All Dino’s starting from December 22nd 2021 will now require every class to have Dino Ready gear + Skills to participate for points and raid. You will also be required to know Dino mechanics. IF you have no idea what this boss does but reach all requirements you will still not be eligible for points.""")
    
@client.command(guild_ids = guilds)
async def dinoclassreq(ctx, cclass):
    """Displays the Dino class requirements"""
    cclass = cclass.lower()
    if cclass == "warrior":
        await ctx.send("""Warrior Requirements:
Warriors:
        - Tanks: - Ability to time Dino Heal - 42 Skill Points in bash.
              -MT STATS - MINIMUM OF 28k HP and 13k DEFENSE with SOME DIRECT TAUNT GEAR (more is always better)
                (This can be a Mord/Dino Taunt brace, Taunting bloom ring or BT bands)
              -Add tanks stats - MINIMUN OF 17K HP and 7k defense. 
        - DPS Warriors - Gelebron Axe (or Dino wep) - Hexforged Axe of Might (400 DAMAGE OFFHAND) - 42 Skill points in Bash - Ability to time Dino Heal
*Changes* Last Requirement made it so DPS warriors needed to have full dg but they are now able to participate in raids. DPS Warriors will now have to have 42 points in bash and bash dino. 
**IN THE EVENT THAT WE ARE MISSING PLAYERS AND NEED A PLAYER TO FULLFILL THE ROLES BUT THEY DON” T REACH REQUIREMENTS, LEADERS MAY DEEM IT APPROPIATE FOR THEM TO JOIN DINO AND THEY WILL BE ABLE TO EARN POINTS DURNG THAT SPECIFIC DINO**""")
    if cclass == "ranger":
        await ctx.send("""Ranger Requirements:
Rangers: Magic Quiver - Gelebron Bow (Or Dino) - Entangle at 42 Skill Points 
*Changes* Last Requirement made it so Rangers needed DG gloves, this will not be needed but Rangers will always be the first one to ask to leave the raid if People are starting to get teleported unless a DPS rogue is in raid.""")
    if cclass == "rogue":
        await ctx.send("""Rogue Requirements:
Rogues: 
      - Support Rogue: 50 Points in Expose Weakness and Smokebomb. 
      -DPS Rogue: - Gelebron Dagger (or Dino) - Hexforged Axe of Might (400 MAGIC DAMAGE OFFHAND)
*Changes* Last Requirement made it so rogues needed to have full DG to participate, but now they’re able to participate as long as they meet requirements. DPS rogues will be the first to leave the raid if players are being teleported.""")
    if cclass == "druid":
        await ctx.send("""Druid Requirements:
Druids: 
        - DPS DRUIDS: 30+ Points in magic Ward - BT or Dino Amulet - BT DPS Charm. NOT REQUIRED BUT SUGGESTED: Spring of Life 
        - Support Druid: Minimun of 5.5k heal - Howling winds - Magic Ward - 25% Natures touch recast 
        *Changes* Last Requirement made it so DPS druids needed 50 magic ward which has been changed to a minimum of 30 points. Rooting druids Removed. Also Support druids will now be required to have a 5.5k heal and Natures touch recast.""")
    if cclass == "mage":
        await ctx.send("""Mage Requirements:
Mages: Bloodthorn or Dino Amulet - Bloodthorn Charm - 42 Points in freeze - Ability to time bash
       - Freezers for Troll: 42 points in freeze with a recast freeze skull. 
*Mages will now be required to Time dino heal, and added a sub category for troll freezing where they are required to have a freeze skull to freeze.""")
    

@client.command(guild_ids = guilds)
async def dinoweps(ctx):
    await ctx.send("""Dino Weapons:
*Dino Weapon Rule Change Rev. 3.0*
 
⭐️ -You may own a total of two (2) Dino weapons across ALL toons. The second weapon must be won for base DPKP price. If you had already won a Dino weapon for above base, and are interested in a new weapon, you must state you will be refunding your current weapon if won on the bidding note, and are allowed to bid above base. If you had won, you must refund your current weapon to receive your new one.
⭐️-  The weapons must be for different toons of different class, you are not able to win 2 weapons for the same toon.
⭐️ -The following bidding restrictions still apply to bid on any tier Dino weapons:
  ~15% RBPP in the past 30 days
  ~3 Dino, 2 Prot, 2 Bloodthorn, 2 Gele attends in the past 30 days.
⭐️- You must own a T10 CG on the toon that will be winning the Dino weapon.

🗡Daggers:
- if you win a Dino dagger, you must refund your Gele dagger(s) and can’t win future Gele dags""")
    
@client.command(guild_ids = guilds)
async def leadership(ctx):
    """Displays the current leadership"""
    await ctx.send("""07/05/2024 - Leadership

Generals:
Ambie/Sylv (Keni):
Discord ID: @keniwin
Darkhealz:
Discord ID: @darkhealz.
Ayhano (Shicu): 
Discord ID: @shicu_
Unreal:
Discord ID: @unrealmatty 

Guardians:

hubott:
Discord ID: @hubott
Abomination:
Discord ID: @valhallaxx
Aspire:
Discord ID: steller._.
M0neyBank
Discord ID: @moneydeez1
Bones:
Discord ID: @zealous_otter_24291
Swag:
Discord ID: @elijah040404
REDALiCE:
Discord ID: @yukarip3
                   
Bot Creator and Admin:
REDALiCE:
Discord ID: @yukarip3""")
                   

@client.command(guild_ids = guilds)
async def itemlimit(ctx):
    """Displays the current item limits"""
    await ctx.send("""Item Limitations:
Bloodthorn Helmet- A person can only have one Bloodthorn helmet per person amongst all of their accounts obtained from clan bank or outside clan.
Bloodthorn Recast Rings. Only one recast ring of each skill per character.
Bloodthorn Charms and Necklaces. Only one charm or necklace of each type per character. (Each class has two different types of necks and charms, each character may have both types.)
Bloodthorn Bands:It’s now Alt toons of a different class are allowed 3 bloodleaf bands (Royal/Imperial) Imperial BT bands have main priority if bid on above 2500 GKP. If a Main does not bid above 2500 GKP, an alt may bid and win for above 2500 GKP.
You are only able to earn bands on 3 toons. With main toons able to win up to 4 bands and alts toons winning a maximum of 3 bands. 
Main change: if your main currently has 4 bands and you change your main to another account one band is required to be refunded""")

@client.command(guild_ids = guilds)
async def multibidding(ctx):
    """Displays the rules for bidding on multiple items"""
    await ctx.send("""When bidding on items where there are multiple of the specific item available a note will be created and bidding will occurs for these items though a single note.This applies for AKP/PKP/GKP/DPKP  (Closed) Bidding. In the comments of the note state how many of the item you are interested in then send your bids ingame to "mcbidders" stating Bid #1 and Bid#2 on the same mail with the subject as the item name (since you are not able to win more than 2 items per KP above base per week).
common misconceptions are that you are able to select and bid on Item #1, Item #2, Item #3, etc… which is incorrect, you are placing one or two separate bids against all items available, the top X (amount of items available) bids win the items.""")
    

@client.command(guild_ids = guilds)
async def altbidding(ctx):
    """Displays the rules for bidding on items for alts"""
    await ctx.send("""Alt Bidding:
The term “Alt Bidding” means using points from your main toon to bid for gear for one of your Alternate toons. This may ONLY be done for OPEN BIDDING items (DKP)
Any bidding that is made using a toons OWN earned points (Alt or Main) takes priority over “Alt bidding”
-For example, anyone may create a note for a DKP item, the bottom would read, Bidder: (main toon) Alt bidding for (alt toon). If won points would be deducted from the main toon, and item would be won by the alt toon.
What if someone else is interested in the same item that I had bid on using “alt bid”? if the other person interested had done an “Alt Bid” you may continue to “Alt bid” back and forth until the bidding is over.
If the other person interested places a bid using a toons OWN points (alt or main) this will cancel ALL previously made “Alt bids” made from all who had bid using this method.""")

@client.command(guild_ids = guilds)
async def minimumbids(ctx):
    """Displays the minimum bids for each item type"""
    await ctx.send("""Minimum Bids:""")
    await ctx.send("https://imgur.com/WDQUBaW")

@client.command(guild_ids = guilds)
async def bidtemplate(ctx):
    """Displays the bidding template"""
    await ctx.send("""Bidding Template:
Copy and paste the correct template for the item you are bidding on. Replace text in (brackets).""")
    await ctx.send("""⭐️ DKP bidding ⭐️: (Mordris, Necro, Hrung, Crowns, Legacy)
This item is being purchased for (insert cost of item) (insert KP type) minimum bid. If interested please comment below with your bid amount and name of toon whose points are being bid with in the next 12 hours. Each bid you place must include the name of the toon whose points are being used, and @tag every other player who bidded above to be valid. Bidding will take place over the next 13 hours.Only your last bid submission within the 13 hours will be used.Bidder: (insert your character's name)""")
    await ctx.send("""⭐️ AKP, GKP, PKP, DPKP ⭐️:
(Gelebron, Bloodthorn, Proteus, Dhiothu)

This item is being purchased for (insert cost of item) (insert KP type) minimum bid. If you are also interested in this item, post interested below using the character name that will be bidding.  
Mail in your bid to McBidders with your name and the name of the item you are bidding on within the next 13 hours.  
Bidder: (insert your character name)""")

@client.command(guild_ids = guilds)
async def refundsinfo(ctx):
    """Displays the refund policy"""
    await ctx.send("""*rule clarification*

Current refund rule states:
*   Refunding: Raid drops that you have received from the clan may be refunded for 100% of the cost you paid. You may only refund an item after having it for more than 2 weeks.
*   DKP items will be capped at 15,000 points when you refund them.
*   You may only refund 4 items per category every 30 days. DKP items are excluded from this limit.
*   You may not bid on the same item you have refunded in the past 2 weeks.

Instead changing the refunding rule, we want to provide some new clarity in the way that we process refunds.
In the past, as some leaders refunded items based on the smallest KP, other leaders had been refunding chronologically. Refunding based on KP amount has worked well in avoiding loopholes, but we also feel that it isn’t fair as players continue to lose KP. Because we, as leaders, have been unknowingly refunding items in different ways, we have taken the last couple of months to look at how to better clarify the refunding process.
It has been agreed upon that in the future, all refunds will be processed chronologically. This means that whatever item you won first, that KP will be returned to you. But won’t this result in another loophole? No; since we can compare items received to item adjustments, we are able to assure that no one is able to duplicate points.
Because Dino refunds are the hardest to track, we will refund the chronological sum that was spent, unless you won that specific tier through bidding. 
Example: If you built your own imperial brace, but also won an imperial brace, we will refund the points spent on the one that you did not build.""")
    

@client.command(guild_ids = guilds)
async def halfpoints(ctx):
    """Displays the half points policy"""
    await ctx.send("""Are you multi-loging at raids? If you log two accounts for raids you will be able to receive full points for both accounts! If you are capable and decide to log a 3rd account one if those accounts will get half points and the other two will get full points!
Bonus: on resets you can get half points for a 4th account!""")
    
@client.command(guild_ids = guilds)
async def mainprio(ctx):
    """Displays the main priority information"""
    await ctx.send("""Main Priority gives those with a main toon of the desired drop to have priority over inactive/alternate toons.
Items that have Main Priority are as follows:
   - Godly Gelebron Jewelry
   - Void Gelebron Weapons
   - Godly Bloodthorn Jewely
   - Imperial/Godly Dino Jewelry
   - All Dino Weapons
   - Godly Dex/Vit Prot Braces
Main priority will now be split into two sections. End game and Mid Game. 
End Game Priority Raids: This category now includes PROT, GELE, BT, and DINO. To achieve main priority for these bosses, you must participate in at least 4 of each raid within the last 45 days.
Mid Game Priority Raids: This encompasses UNOX, HRUNG, MORD, and NECRO. This means that Toons who participate in 4 Mord, 4 Hrung, and 4 Necro raids within the last 45 days will receive priority on certain items over those who do not attend these raids
Specific Requirements for BT Helms and Dino Weapons:
The requirements for BT Helms and Dino Weapons have been adjusted to align with the End Game Priority Raids. Additionally, a minimum RBPP of 250 is now necessary to bid on these items.""")

@client.command(guild_ids = guilds)
async def questupgrades(ctx):
    """Displays the quest upgrade information"""
    await ctx.send("""Warden, Meteoric, Frozen, DL armor are available upon request. Weapons for Warden, Meteoric, and Frozen are also provided, these are available to Recruits upon request from clan Guardians.
DL weapons (crowns) need to be obtained by calling and rolling at snorri, or purchased from bank for 50 DKP each. Snorri is typically announced in Green 🟢 chat. Keep track of this timer in boss dead chat. All crowns are banked except if called for at Snorri. You must have an eligible toon of the class you call to be awarded the crown(s)
EDL Armor is available to Clansman upon reaching 205, request this with a clan General.
Due to the changes in main priority raids and the introduction of mid-game priority raids, the requirement for EDL Offhand has been modified. To qualify, you must now have attended Unox raids with a minimum RBPP of 15%, along with participation in 4 Hrung, 4 Mord, and 4 Necro within the past 45 days.
Doch upgrades, when the clan acquires 15 pures in bank, a poll will be created in the “Doch Voters” chat. This chat consists of all leaders, and all clannies who have full doch sets. It is the persons preference who they vote for while following the limited number of pures we have available, although most base their votes off attends (RBPP and AKP/PKP)
once awarded a piece there is a 2 poll waiting period before your next upgrade eligibility. You must be in the clan for 90 days and have 25%+ RBPP in the past 90 days to be eligible to be placed on the Doch poll.
You must meet the following RBPP milestones for your next upgrade piece to be eligible:
Gloves ——-> 200 TOTAL RBPP
Top————>400 TOTAL RBPP
Boots———> 550 TOTAL RBPP
Legs———-> 700 TOTAL RBPP
Hat————>850 TOTAL RBPP                                     
Exception to Doch voting, when leaders seem fit and all leaders agree, there is a possibility of a expedited use of pures to upgrade a certain toon(s) or to complete a set. Although this is rare, leaders may do this at a desperate time to benefit the clan. This action will count as a poll during a previously awarded persons 2 poll waiting period.
Echos and Seeds, weeklies are scheduled by leaders at a clannies request, reach out to any guardian to schedule a weekly to get 7 echos to upgrade your EDL OH to T8, reminder weeklies award GKP so help out your fellow clannies. Once you reach a T8 OH reach out to a General to receive 2 Bloodthorn seeds, to upgrade your offhand to T10.""")


@client.command(guild_ids = guilds)
async def esttime(ctx):
    """Displays the EST time"""
    await ctx.send("""Curious on the current EST time? Click this link to find out : https://time.is/ET/
A lot of the clan is US based and EST is the most common timezone used to time raids and events.
If you are using the discord timer bot, the time is automatically converted to your local timezone""")

@client.command(guild_ids = guilds)
async def spawntimes(ctx):
    """Displays the spawn times for various bosses"""
    await ctx.send("type \"refresh\" in #dead-timers to get the latest spawn times")

@client.command(guild_ids = guilds)
async def spreadsheet(ctx):
    """Links Winston's master point spreadsheet"""
    await ctx.send("https://docs.google.com/spreadsheets/d/1Izu2wSmi0aEQCWTvfLAXX0ucXR2223ILzFxTiQXcl80/edit#gid=393681553")

@client.command(guild_ids=guilds)
async def oldwins(ctx):
    """Links Alice's old wins spreadsheet"""
    await ctx.send("https://docs.google.com/spreadsheets/d/1FbfNkF9SkD0A8a61ChoKvcG88yC2vpaHL8ffm37TSb8/edit?gid=1217357805#gid=1217357805")

@client.command(guild_ids = guilds)
async def kpsite(ctx):
    """Links the KP site"""
    await ctx.send("http://www.relentless.dkpsystem.com/news.php")


@client.command(guild_ids = guilds)
async def information(ctx):
    """Displays the information dump commands"""
    await ctx.send("""to get started, type one of these commands:
                   
$information - displays this message
$new - new player induction messages
$clanrules - links the clan rules
$spreadsheet - links Winston's master point spreadsheet
$kpinfo - displays information about the various KP pools
$dinoreq - displays the requirements for Dino
$dinoclassreq - displays the requirements for Dino by class. make sure to add the class after the command
$dinoweps - displays the requirements to get weapons from Dino
$leadership - displays the current leadership
$itemlimit - displays current limitations on items
$multibidding - displays the rules for bidding on multiple items
$altbidding - displays the rules for bidding on items for alts
$minimumbids - displays the minimum bids for each item type
$bidtemplate - displays the bidding template
$refundsinfo - displays the refund policy
$halfpoints - displays the half points policy
$mainprio - displays information about main priority
$questupgrades - displays information about acquiring various quest items
$esttime - displays info about EST time
$spawntimes - tells you where to find the spawn times
$kpsite - links the KP site""")
    
@client.command(guild_ids = guilds)
async def ban(ctx, name):
    """Bans a player"""
    await ctx.send(name + " has been banned")

@client.command(guild_ids = guilds)
async def kick(ctx, name):
    """Kicks a player"""
    await ctx.send(name + " has been kicked")

@client.command(guild_ids = guilds)
async def demote(ctx, name):
    """Demotes a player"""
    await ctx.send(name + " has been demoted")

@client.command(guild_ids = guilds)
async def promote(ctx, name):
    """Promotes a player"""
    await ctx.send(name + " has been promoted")

@client.command(guild_ids = guilds)
async def sudo(ctx):
    """pretends to break"""
    await ctx.send("Logging in as Super Admin")
    await ctx.send("Executing...")
    # wait a second
    async with ctx.typing():
        await asyncio.sleep(5)
        await ctx.send("Error: you're a silly goose")

@client.command(guild_ids = guilds)
async def unban(ctx, name):
    """Unbans a player"""
    await ctx.send(name + " has been unbanned")

@client.command(guild_ids = guilds)
async def delete(ctx, *args):
    """Deletes something"""
    await ctx.send("Deleting " + " ".join(args))

@client.command(guild_ids = guilds)
async def source(ctx):
    """posts the link for the source code"""
    await ctx.send("https://github.com/Haylia/Gwydion-DKP-bot")

@client.command(guild_ids = guilds)
async def donate(ctx):
    """posts the link for donations"""
    await ctx.send("https://www.paypal.me/liastarrrr")

#@client.command(guild_ids = guilds)
#async def leaderboard(ctx, kp, number):
#    """Displays the current point leaderboard"""
#    if int(number) > 25:
#        await ctx.send("bot is configured for 25 players max")
#    else:
#        kp = kp.upper()
#        embed = discord.Embed(title = kp + " Leaderboard top " + str(number), colour=discord.Color.orange())
#        if kp == "AKP":
#            kplist = bot4ws1.col_values(2)
#            namelist = bot4ws1.col_values(1)
#            del kplist[0]
#            del namelist[0]
#            floatkplist = list(map(float, kplist))
#            comblist = list(zip(namelist,floatkplist))
#            sortedkplist = sorted(comblist,reverse=True,key=lambda xkp: xkp[1])
#            for i in range(int(number)):
#                embed.add_field(name =  sortedkplist[i][0], value = sortedkplist[i][1], inline = False)
#        if kp == "BKP":
#            kplist = bot4ws1.col_values(3)
#            namelist = bot4ws1.col_values(1)
#            del kplist[0]
#            del namelist[0]
#            floatkplist = list(map(float, kplist))
#            comblist = list(zip(namelist,floatkplist))
#            sortedkplist = sorted(comblist,reverse=True,key=lambda xkp: xkp[1])
#            for i in range(int(number)):
#                embed.add_field(name =  sortedkplist[i][0], value = sortedkplist[i][1], inline = False)
#        if kp == "DKP":
#            kplist = bot4ws1.col_values(4)
#            namelist = bot4ws1.col_values(1)
#            del kplist[0]
#            del namelist[0]
#            floatkplist = list(map(float, kplist))
#            comblist = list(zip(namelist,floatkplist))
#            sortedkplist = sorted(comblist,reverse=True,key=lambda xkp: xkp[1])
#            for i in range(int(number)):
#                embed.add_field(name =  sortedkplist[i][0], value = sortedkplist[i][1], inline = False)
#        await ctx.send(embed=embed)
#
# @client.command(guild_ids = guilds)
# async def classleaderboard(ctx, kp, number, cclass):
#     """Current point leaderboard for a class"""
#     if int(number) > 25:
#         await ctx.send("bot is configured for 25 players max")
#     else:
#         kp = kp.upper()
#         cclass = cclass.lower()
#         embed = discord.Embed(title = kp + " Leaderboard top " + str(number) + " for " + cclass, colour=discord.Color.orange())
#         if kp == "AKP":
#             kplist = bot4ws1.col_values(2)
#         elif kp == "BKP":
#             kplist = bot4ws1.col_values(3)
#         elif kp == "DKP":
#             kplist = bot4ws1.col_values(4)
#         namelist = bot4ws1.col_values(1)
#         classlist = bot4ws1.col_values(11)
#         del kplist[0]
#         del namelist[0]
#         del classlist[0]
#         floatkplist = list(map(float, kplist))
#         comblist = list(zip(namelist,floatkplist,classlist))
#         sortedkplist = sorted(comblist,reverse=True,key=lambda xkp: xkp[1])
#         full = False
#         counter = 0
#         loopcounter = 0
#         while not full:
#             if str(sortedkplist[loopcounter][2]) == cclass:
#                 embed.add_field(name =  sortedkplist[loopcounter][0], value = sortedkplist[loopcounter][1], inline = False)
#                 counter += 1
#                 if counter >= int(number):
#                     full = True
#             loopcounter += 1
#             if loopcounter >= len(sortedkplist):
#                 break
#         await ctx.send(embed=embed)
# 
# @client.command(guild_ids = guilds)
# async def classlifeleaderboard(ctx, kp, number, cclass):
#     """Lifetime point leaderboard for a class"""
#     if int(number) > 25:
#         await ctx.send("bot is configured for 25 players max")
#     else:
#         kp = kp.upper()
#         cclass = cclass.lower()
#         embed = discord.Embed(title = kp + " Lifetime top " + str(number) + " for " + cclass, colour=discord.Color.orange())
#         if kp == "AKP":
#             kplist = bot4ws1.col_values(8)
#         elif kp == "BKP":
#             kplist = bot4ws1.col_values(9)
#         elif kp == "DKP":
#             kplist = bot4ws1.col_values(10)
#         namelist = bot4ws1.col_values(1)
#         classlist = bot4ws1.col_values(11)
#         del kplist[0]
#         del namelist[0]
#         del classlist[0]
#         floatkplist = list(map(float, kplist))
#         comblist = list(zip(namelist,floatkplist,classlist))
#         sortedkplist = sorted(comblist,reverse=True,key=lambda xkp: xkp[1])
#         full = False
#         counter = 0
#         loopcounter = 0
#         while not full:
#             if str(sortedkplist[loopcounter][2]) == cclass:
#                 embed.add_field(name =  sortedkplist[loopcounter][0], value = sortedkplist[loopcounter][1], inline = False)
#                 counter += 1
#                 if counter >= int(number):
#                     full = True
#             loopcounter += 1
#             if loopcounter >= len(sortedkplist):
#                 break
#         await ctx.send(embed=embed)



@client.command(guild_ids = guilds)
async def winston(ctx):
    """winston"""
    quotes = ("Excuse me for dropping in.","The best defense is a good barrier.","You're safe with me.","Science means going where outcomes are uncertain. But I AM certain that we're going to have a great time.","I'm over the moon!","I call that gorilla warfare.","Greetings!")
    await ctx.send(quotes[random.randint(0,len(quotes))])

#@client.command(guild_ids = guilds)
#async def lifeleaderboard(ctx, kp, number):
#    """Displays the lifetime point leaderboard"""
#    if int(number) > 25:
#        await ctx.send("bot is configured for 25 players max")
#    else:
#        kp = kp.upper()
#        embed = discord.Embed(title = "lifetime " + kp + " Leaderboard top " + str(number), colour=discord.Color.orange())
#        if kp == "AKP":
#            kplist = bot4ws1.col_values(8)
#            namelist = bot4ws1.col_values(1)
#            del kplist[0]
#            del namelist[0]
#            floatkplist = list(map(float, kplist))
#            comblist = list(zip(namelist,floatkplist))
#            sortedkplist = sorted(comblist,reverse=True,key=lambda xkp: xkp[1])
#            for i in range(int(number)):
#                embed.add_field(name =  sortedkplist[i][0], value = sortedkplist[i][1], inline = False)
#        if kp == "BKP":
#            kplist = bot4ws1.col_values(9)
#            namelist = bot4ws1.col_values(1)
#            del kplist[0]
#            del namelist[0]
#            floatkplist = list(map(float, kplist))
#            comblist = list(zip(namelist,floatkplist))
#            sortedkplist = sorted(comblist,reverse=True,key=lambda xkp: xkp[1])
#            for i in range(int(number)):
#                embed.add_field(name =  sortedkplist[i][0], value = sortedkplist[i][1], inline = False)
#        if kp == "DKP":
#            kplist = bot4ws1.col_values(10)
#            namelist = bot4ws1.col_values(1)
#            del kplist[0]
#            del namelist[0]
#            floatkplist = list(map(float, kplist))
#            comblist = list(zip(namelist,floatkplist))
#            sortedkplist = sorted(comblist,reverse=True,key=lambda xkp: xkp[1])
#            for i in range(int(number)):
#                embed.add_field(name =  sortedkplist[i][0], value = sortedkplist[i][1], inline = False)
#        await ctx.send(embed=embed)
# 
# @client.command(guild_ids = guilds)
# async def win(ctx, kp, members):
#     """Decides the winner of a drop"""
#     kp = kp.lower()
#     user_list = bot5ws1.col_values(1)
#     memlist = members.split(",")
#     winnerlist = []
#     for mem in memlist:
#         if mem in user_list:
#             cell = bot5ws1.find(mem.lower())
#             row_num = cell.row
#             if kp == "akp":
#                 winnerlist.append((mem,float(bot5ws1.cell(row_num, 2).value)))
#             if kp == "bkp":
#                 winnerlist.append((mem,float(bot5ws1.cell(row_num, 3).value)))
#             if kp == "dkp":
#                 winnerlist.append((mem,float(bot5ws1.cell(row_num, 4).value)))
#     sortedkplist = sorted(winnerlist,reverse=True,key=lambda xkp: xkp[1])
#     await ctx.send("Winner: " + sortedkplist[0][0])
# 
#
#@client.command(guild_ids = guilds)
#@commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
#async def reap(ctx, playername, kp, perc, itemname):
#    "reaps a player for a set value of their points"
#    user_list = bot5ws1.col_values(1)
#    playername = playername.lower()
#    kp = kp.upper()
#    if playername in user_list:
#        cell = bot5ws1.find(playername)
#        row_num = cell.row
#        if kp == "AKP":
#            akp = bot5ws1.cell(row_num, 2).value
#            nkp = float(akp) * (100 - float(perc)) / 100
#            bot5ws1.update_cell(row_num, 2, nkp)
#            newreaped = float(bot5ws1.cell(row_num, 5).value) + round(float(akp) - float(nkp), 2)
#            bot5ws1.update_cell(row_num, 5, newreaped)
#        if kp == "BKP":
#            akp = bot5ws1.cell(row_num, 3).value
#            nkp = float(akp) * (100 - float(perc)) / 100
#            bot5ws1.update_cell(row_num, 3, nkp)
#            newreaped = float(bot5ws1.cell(row_num, 6).value) + round(float(akp) - float(nkp), 2)
#            bot5ws1.update_cell(row_num, 6, newreaped)
#        if kp == "DKP":
#            akp = bot5ws1.cell(row_num, 4).value
#            nkp = float(akp) * (100 - float(perc)) / 100
#            bot5ws1.update_cell(row_num, 4, nkp)
#            newreaped = float(bot5ws1.cell(row_num, 7).value) + round(float(akp) - float(nkp), 2)
#            bot5ws1.update_cell(row_num, 7, newreaped)
#        msg = f"{playername} has been reaped for {round(float(akp) - float(nkp), 2)}, {perc}% of their {kp} for {itemname}. Old {kp}: {akp}. New {kp}: {nkp}"
#        bot5ws3.append_row([f"commanduser: {ctx.message.author} at {datetime.datetime.now().strftime('%a %d %b %Y, %I:%M%p')} " + msg])
#        await ctx.send(msg)
#    else:
#        await ctx.send(f"{playername} not in list! No Points reaped")
#
#
# @client.command(guild_ids = guilds)
# @commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
# async def refund(ctx, playername, kp, points):
#     "refunds a player an exact value of points"
#     points = float(points)
#     user_list = bot5ws1.col_values(1)
#     playername = playername.lower()
#     kp = kp.upper()
#     if playername in user_list:
#         cell = bot5ws1.find(playername)
#         row_num = cell.row
#         if kp == "AKP":
#             akp = float(bot5ws1.cell(row_num, 2).value)
#             nkp = akp + points
#             bot5ws1.update_cell(row_num, 2, nkp)
#             newreaped = float(bot5ws1.cell(row_num, 5).value) - points
#             bot5ws1.update_cell(row_num, 5, newreaped)
#         if kp == "BKP":
#             akp = float(bot5ws1.cell(row_num, 3).value)
#             nkp = akp + points
#             bot5ws1.update_cell(row_num, 3, nkp)
#             newreaped = float(bot5ws1.cell(row_num, 6).value) - points
#             bot5ws1.update_cell(row_num, 6, newreaped)
#         if kp == "DKP":
#             akp = float(bot5ws1.cell(row_num, 4).value)
#             nkp = akp + points
#             bot5ws1.update_cell(row_num, 4, nkp)
#             newreaped = float(bot5ws1.cell(row_num, 7).value) - points
#             bot5ws1.update_cell(row_num, 7, newreaped)
#         msg = f"{playername} has been refunded for {points} {kp}. Old {kp}: {akp}. New {kp}: {nkp}"
#         bot5ws3.append_row([f"commanduser: {ctx.message.author} at {datetime.datetime.now().strftime('%a %d %b %Y, %I:%M%p')} " + msg])
#         await ctx.send(msg)
#     else:
#         await ctx.send(f"{playername} not in list! No Points refunded")

# @client.command(guild_ids = guilds)
# @commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
# async def boss(ctx, name, members):
#     """Gives a list of players a set of points for a boss"""
#     await ctx.send("running command boss " + name)
#     memlist = list(members.split(","))
#     emb_msg = ''
#     user_list = bot5ws1.col_values(1)
#     name = name.lower()
#     ratelimit = False
#     #await ctx.defer()
#     for mem in memlist:
#             mem = mem.lower()
#             if mem in user_list:
#                 try:
#                     if mem not in emb_msg:
#                         cell = bot5ws1.find(mem.lower())
#                         row_num = cell.row
#                         akp = bot1ws1.cell(row_num, 2).value
#                         bkp = bot2ws1.cell(row_num, 3).value
#                         dkp = bot3ws1.cell(row_num, 4).value
#                         nakp = float(akp) + akp_bosses[name]
#                         nbkp = float(bkp) + bkp_bosses[name]
#                         ndkp = float(dkp) + dkp_bosses[name]
#                         bot1ws1.update_cell(row_num, 2, nakp)
#                         bot2ws1.update_cell(row_num, 3, nbkp)
#                         bot3ws1.update_cell(row_num, 4, ndkp)
#                         emb_msg += mem + ' '
#                     else:
#                         await ctx.send(mem + " added multiple times on this attendance, credited once")
#                 except:
#                     ratelimit = True
#             else:
#                 await ctx.send(f"{mem} not in list!")
#     if ratelimit:
#         await ctx.send("An error occurred, likely rate limit hit. Please wait a minute and add the rest of the players on this attendance then")
#     if emb_msg != '':
#         embed = discord.Embed(title = f" {name} point update", description = f"{emb_msg} gained {akp_bosses[name]} AKP, {bkp_bosses[name]} BKP, {dkp_bosses[name]} DKP", colour= 0x3498db)
#         bot5ws2.append_row([f"commanduser: {ctx.message.author} at {datetime.datetime.now().strftime('%a %d %b %Y, %I:%M%p')} {name}. {emb_msg} have gained {akp_bosses[name]} AKP, {bkp_bosses[name]} BKP, {dkp_bosses[name]} DKP"])
#     elif emb_msg == '':
#         embed = discord.Embed(title = "No valid users found!")
#     await ctx.send(embed=embed)
# 
# 
# @client.command(guild_ids = guilds)
# @commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
# async def bossalt(ctx, name, members):
#     """Boss command for alts"""
#     await ctx.send("running command bossalt " + name)
#     memlist = list(members.split(","))
#     emb_msg = ''
#     user_list = bot5ws1.col_values(1)
#     name = name.lower()
#     ratelimit = False
#     #await ctx.defer()
#     for mem in memlist:
#             mem = mem.lower()
#             if mem in user_list:
#                 try:
#                     if mem not in emb_msg:
#                         cell = bot5ws1.find(mem.lower())
#                         row_num = cell.row
#                         akp = bot1ws1.cell(row_num, 2).value
#                         bkp = bot2ws1.cell(row_num, 3).value
#                         dkp = bot3ws1.cell(row_num, 4).value
#                         nakp = float(akp) + (akp_bosses[name]/2)
#                         nbkp = float(bkp) + (bkp_bosses[name]/2)
#                         ndkp = float(dkp) + (dkp_bosses[name]/2)
#                         bot1ws1.update_cell(row_num, 2, nakp)
#                         bot2ws1.update_cell(row_num, 3, nbkp)
#                         bot3ws1.update_cell(row_num, 4, ndkp)
#                         emb_msg += mem + ' '
#                     else:
#                         await ctx.send(mem + " added multiple times on this attendance, credited once")
#                 except:
#                     ratelimit = True
#             else:
#                 await ctx.send(f"{mem} not in list!")
#     if ratelimit:
#         await ctx.send("An error occurred, likely rate limit hit. Please wait a minute and add the rest of the players on this attendance then")
#     if emb_msg != '':
#         embed = discord.Embed(title = f" {name} alt point update", description = f"{emb_msg} gained {akp_bosses[name]/2} AKP, {bkp_bosses[name]/2} BKP, {dkp_bosses[name]/2} DKP", colour= 0x3498db)
#         bot5ws2.append_row([f"commanduser: {ctx.message.author} at {datetime.datetime.now().strftime('%a %d %b %Y, %I:%M%p')} {name}. {emb_msg} have gained {akp_bosses[name]/2} AKP, {bkp_bosses[name]/2} BKP, {dkp_bosses[name]/2} DKP"])
#     elif emb_msg == '':
#         embed = discord.Embed(title = "No valid users found!")
#     await ctx.send(embed=embed)
# 
# @client.command(guild_ids = guilds)
# @commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
# async def bossminus(ctx, name, members):
#     """When ur idiot and put the wrong people or boss"""
#     await ctx.send("running command bossminus " + name)
#     memlist = list(members.split(","))
#     emb_msg = ''
#     user_list = bot5ws1.col_values(1)
# 
#     #await ctx.defer()
#     for mem in memlist:
#             mem = mem.lower()
#             if mem in user_list:
#                 cell = bot5ws1.find(mem)
#                 row_num = cell.row
#                 akp = bot1ws1.cell(row_num, 2).value
#                 bkp = bot2ws1.cell(row_num, 3).value
#                 dkp = bot3ws1.cell(row_num, 4).value
#                 nakp = float(akp) - akp_bosses[name]
#                 nbkp = float(bkp) - bkp_bosses[name]
#                 ndkp = float(dkp) - dkp_bosses[name]
#                 bot1ws1.update_cell(row_num, 2, nakp)
#                 bot2ws1.update_cell(row_num, 3, nbkp)
#                 bot3ws1.update_cell(row_num, 4, ndkp) 
#                 emb_msg += mem + ' '
# 
#             else:
#                 await ctx.send(f"{mem} not in list!")
#     if emb_msg != '':
#         embed = discord.Embed(title = f"{name} point update", description = f"{emb_msg} lost {akp_bosses[name]} AKP, {bkp_bosses[name]} BKP, {dkp_bosses[name]} DKP", colour= 0x3498db)
#         bot5ws2.append_row([f"commanduser: {ctx.message.author} at {datetime.datetime.now().strftime('%a %d %b %Y, %I:%M%p')}{emb_msg} have lost {akp_bosses[name]} AKP, {bkp_bosses[name]} BKP, {dkp_bosses[name]} DKP"])
#     elif emb_msg == '':
#         embed = discord.Embed(title = "No valid users found!")
#     await ctx.send(embed=embed)

# @client.command()
# async def points(ctx, clanmem):
#     """See how many points you have"""
#     user = str(clanmem).lower()
#     user_list = bot4ws1.col_values(1)
#     if user in user_list:
#         
#         ind = user_list.index(user) +1
#         user_points = bot4ws1.row_values(ind)
#         embed = discord.Embed(title = f"{user}'s points", colour=discord.Color.orange())
#         embed.add_field(name = "AKP", value = user_points[1], inline = True)
#         embed.add_field(name = "BKP", value = user_points[2], inline = False)
#         embed.add_field(name = "DKP", value = user_points[3], inline = False)
#         await ctx.send(embed=embed)
#     else:
#         await ctx.send("User not found!")


            


# @client.command()
# async def lifetime(ctx, clanmem):
#     """See how much lifetime you have"""
#     user = str(clanmem).lower()
#     user_list = bot4ws1.col_values(1)
#     if user in user_list:
#         
#         ind = user_list.index(user) +1
#         user_points = bot4ws1.row_values(ind)
#         embed = discord.Embed(title = f"{user}'s lifetime points", colour=discord.Color.orange())
#         embed.add_field(name = "AKP", value = user_points[7], inline = True)
#         embed.add_field(name = "BKP", value = user_points[8], inline = False)
#         embed.add_field(name = "DKP", value = user_points[9], inline = False)
#         await ctx.send(embed=embed)
#     else:
#         await ctx.send("User not found!")

# @client.command()
# async def dg(ctx, clanmem, camp, conflux, necessity, cooldown):
#     """DG eligibility calculation"""
#     user = str(clanmem).lower()
#     user_list = bot5ws1.col_values(1)
#     if user in user_list:
#         
#         ind = user_list.index(user) +1
#         user_points = bot5ws1.row_values(ind)
#         embed = discord.Embed(title = f"{user}'s DG points", colour=discord.Color.orange())
#         embed.add_field(name = "Lifetime AKP", value = user_points[7], inline = True)
#         embed.add_field(name = "Lifetime BKP", value = user_points[8], inline = False)
#         embed.add_field(name = "Lifetime DKP", value = user_points[9], inline = False)
#         embed.add_field(name = "", value = "", inline = False)
#         embed.add_field(name = "Current DG Calculation", value = "(Lifetime AKP + Lifetime BKP/2 + Lifetime DKP/2) * Camping * Conflux Availability * Necessity * Cooldown", inline = False)
#         embed.add_field(name = user + "'s DG calculation", value = f"({user_points[7]} + {float(user_points[8])/2} + {float(user_points[9])/2}) * {camp} * {conflux} * {necessity} * {cooldown}", inline = False)
#         embed.add_field(name = user + " DG Points", value=(float(user_points[7])+ float(user_points[8]) / 2 + float(user_points[9]) / 2) * float(camp) * float(conflux) * float(necessity) * float(cooldown))
#         await ctx.send(embed=embed)
#     else:
#         await ctx.send("User not found!")

#@client.command()
#async def dgcompare(ctx, clanmems):
#    """DG comparison command"""
#    memlist = list(clanmems.split(","))
#    user_list = bot5ws1.col_values(1)
#    embed = discord.Embed(title = "DG Point Comparison", colour=discord.Color.orange())
#
#    for mem in memlist:
#        mem = mem.lower()
#        if mem in user_list:
#            cell = bot5ws1.find(mem)
#            row_num = cell.row
#            akp = bot1ws1.cell(row_num, 8).value
#            bkp = bot2ws1.cell(row_num, 9).value
#            dkp = bot3ws1.cell(row_num, 10).value
#            dgpoints = float(akp) + float(bkp/2) + float(dkp)/2
#            embed.add_field(name = mem, value = str(dgpoints), inline = False)
#
#    await ctx.send(embed=embed)



# @client.command(guild_ids = guilds)
# async def dgleaderboard(ctx, number):
#     """Displays the dg point leaderboard with no multipliers"""
#     if int(number) > 25:
#         await ctx.send("bot is configured for 25 players max")
#     else:
#         akplist = bot5ws1.col_values(8)
#         bkplist = bot5ws1.col_values(9)
#         dkplist = bot5ws1.col_values(10)
#         namelist = bot5ws1.col_values(1)
#         del akplist[0]
#         del bkplist[0]
#         del dkplist[0]
#         del namelist[0]
#         floatakplist = list(map(float, akplist))
#         floatbkplist = list(map(float, bkplist))
#         floatdkplist = list(map(float, dkplist))
#         comblist = list(zip(namelist,floatakplist,floatbkplist,floatdkplist,[0] * len(namelist)))
#         for i in range(len(comblist)):
#             comblist[i] = list(comblist[i])
#             comblist[i][4] = comblist[i][1] + (comblist[i][2] / 2) + (comblist[i][3] / 2)
#         sortedkplist = sorted(comblist,reverse=True,key=lambda xkp: xkp[4])
#         embed = discord.Embed(title = "DG Leaderboard top " + str(number), colour=discord.Color.orange())
#         for i in range(int(number)):
#             embed.add_field(name =  sortedkplist[i][0], value = sortedkplist[i][4], inline = False)
#         await ctx.send(embed=embed)

# @client.command(guild_ids = guilds)
# async def dgleaderboardnocap(ctx, number):
#     """Displays the dg point leaderboard with no multipliers"""
#     akplist = bot5ws1.col_values(8)
#     bkplist = bot5ws1.col_values(9)
#     dkplist = bot5ws1.col_values(10)
#     namelist = bot5ws1.col_values(1)
#     del akplist[0]
#     del bkplist[0]
#     del dkplist[0]
#     del namelist[0]
#     floatakplist = list(map(float, akplist))
#     floatbkplist = list(map(float, bkplist))
#     floatdkplist = list(map(float, dkplist))
#     comblist = list(zip(namelist,floatakplist,floatbkplist,floatdkplist,[0] * len(namelist)))
#     for i in range(len(comblist)):
#         comblist[i] = list(comblist[i])
#         comblist[i][4] = comblist[i][1] + (comblist[i][2] / 2) + (comblist[i][3] / 2)
#     sortedkplist = sorted(comblist,reverse=True,key=lambda xkp: xkp[4])
#     msg = "```DG leaderboard top " + str(number) + "```\n"
#     for i in range(int(number)):
#         msg = msg + str(sortedkplist[i][0]) + " : " + str(sortedkplist[i][4]) + "\n"
#     await ctx.send(msg)



#@client.command(guild_ids = guilds)
#async def dgclassleaderboard(ctx, number, cclass):
#    """Displays the dg point leaderboard with no multipliers"""
#    if int(number) > 25:
#        await ctx.send("bot is configured for 25 players max")
#    else:
#        akplist = bot5ws1.col_values(8)
#        bkplist = bot5ws1.col_values(9)
#        dkplist = bot5ws1.col_values(10)
#        namelist = bot5ws1.col_values(1)
#        classlist = bot5ws1.col_values(11)
#        del akplist[0]
#        del bkplist[0]
#        del dkplist[0]
#        del namelist[0]
#        del classlist[0]
#        floatakplist = list(map(float, akplist))
#        floatbkplist = list(map(float, bkplist))
#        floatdkplist = list(map(float, dkplist))
#        comblist = list(zip(namelist,floatakplist,floatbkplist,floatdkplist,[0] * len(namelist),classlist))
#        for i in range(len(comblist)):
#            comblist[i] = list(comblist[i])
#            comblist[i][4] = comblist[i][1] + (comblist[i][2] / 2) + (comblist[i][3] / 2)
#        sortedkplist = sorted(comblist,reverse=True,key=lambda xkp: xkp[4])
#        embed = discord.Embed(title = "DG " + cclass + " Leaderboard top " + str(number), colour=discord.Color.orange())
#        listfull = False
#        counter = 0
#        listsize = 0
#        while not listfull:
#            if cclass == sortedkplist[counter][5]:
#                embed.add_field(name =  sortedkplist[counter][0], value = sortedkplist[counter][4], inline = False)
#                listsize += 1
#            if listsize == number:
#                listfull = True
#            if counter == len(sortedkplist):
#                listfull = True
#            counter += 1
#        await ctx.send(embed=embed)

## $gear dg player piece
#@client.command(guild_ids = guilds)
#@commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
#async def gear(ctx, member, piece):
#    member = str(member).lower()

# $additem toonname itemname
#@client.command(guild_ids = guilds)
#@commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
#async def gear(ctx, toon, itename):
#    member = str(member).lower()

#
# $request itemname playername toonname itemreturn
#@client.command(guild_ids = guilds)
#async def request(ctx, itemname, playername, toonname, itemreturn):
#    playername = str(playername).lower()
#    toonname = str (toonname).lower()
#    daterequested = datetime.datetime.now().strftime('%a %d %b %Y, %I:%M%p')
#    previd = bot5ws5.col_values(7)[-1]
#    id = int(previd) + 1
#    body = [itemname,playername,toonname,daterequested,itemreturn,"pending",id,""]
#    bot3ws5.append_row(body)
#    await ctx.send("New Request ID " + id + "Created for " + playername + " (" + toonname + ") for " + itemname)


## $return itemname toonname
#@client.command(guild_ids = guilds)
#@commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
#async def returnitem(ctx, itemname, toonname):
#    toonname = str(toonname).lower()
#
#
## $viewopenrequests
#@client.command(guild_ids = guilds)
#async def viewopenrequests(ctx):
#
#
# $viewallrequests
#@client.command(guild_ids = guilds)
#async def viewallrequests(ctx):
#    await ctx.send("https://docs.google.com/spreadsheets/d/1JwbiWu68ZE0gCfDUTqsTAs3l2QwfhPDX2d95ZrLAxFw/edit#gid=289715180")

## $viewitemrequests itemname
#@client.command(guild_ids = guilds)
#async def viewitemrequests(ctx, itemname):
#
#
## $viewplayerrequests playername
# make an embed with every open request someone has made on their toon
#@client.command(guild_ids = guilds)
#async def viewplayerrequests(ctx, playername):
#    playername = str(playername).lower()
#
#
# $approverequest idnum
#@client.command(guild_ids = guilds)
#@commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
#async def approverequest(ctx, idnum):
#    #idnum = int(idnum)
#    idlist = bot5ws5.col_values(7)
#    if idnum in idlist:
#        cell = bot5ws5.find(idnum)
#        row_num = cell.row
#        bot5ws5.update_cell(row_num, 6, "approved")
#        await ctx.send("request ID " + idnum + " approved")
#        #add the approved request to sheet 6
#        #add the item to the toon on sheet 4
#    else:
#        await ctx.send(f"{idnum} not in list!")
#
## $rejectrequest idnum
#@client.command(guild_ids = guilds)
#@commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
#async def rejectrequest(ctx, idnum):
#    #idnum = int(idnum)
#    idlist = bot5ws5.col_values(7)
#    if idnum in idlist:
#        cell = bot5ws5.find(idnum)
#        row_num = cell.row
#        bot5ws5.update_cell(row_num, 6, "rejected")
#        await ctx.send("request ID " + idnum + " rejected")
#    else:
#        await ctx.send(f"{idnum} not in list!")
#
## $addnote idnum contents
#@client.command(guild_ids = guilds)
#async def addnote(ctx, idnum, note):
#    # idnum = int(idnum)
#    idlist = bot5ws5.col_values(7)
#    if idnum in idlist:
#        cell = bot5ws5.find(idnum)
#        row_num = cell.row
#        bot5ws5.update_cell(row_num, 8, note)
#        await ctx.send(note + " added to request ID " + idnum)
#    else:
#        await ctx.send(f"{idnum} not in list!")



client.run(TOKEN)