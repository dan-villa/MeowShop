import asyncio
import os
import uuid
import discord
from discord.ext import commands
from pymongo import MongoClient
from forex_python.converter import CurrencyCodes
from datetime import datetime

c = CurrencyCodes()
cluster = MongoClient(os.environ['TOKEN'])

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix='$', intents=intents)
bot.remove_command('help')


def listToString(s):
    str1 = ""

    for element in s:
        str1 += (element + " ")

        # return string
    return str1


@bot.event
async def on_ready():
    print("bot ready")


@bot.event
async def on_reaction_add(self, payload):
    pass


@bot.command()
@commands.is_owner()
async def setup(ctx, currCode: str, shippingCost: int):
    embedVar = discord.Embed(title="Setup", description="Shop setup", color=0xffcccc)
    db = cluster["MeowShop"]
    serv = db["Server"]
    item = serv.find_one({"_id": ctx.guild.id})
    currency = c.get_symbol(currCode)
    manager = [ctx.guild.owner]
    if item is None:
        if currency is not None:
            searchCode = uuid.uuid4().hex[:8]
            newSet = {"_id": ctx.guild.id, "currency": currCode, "shippingCost": shippingCost, "searchCode": searchCode
                , "payments": dict(), "manager": manager}
            serv.insert_one(newSet)
            embedVar.add_field(name="Updated Shop",
                               value="Currency: " + currCode + "\nShipping Cost: " + str(shippingCost)
                                     + "\nSearch Code: " + searchCode,
                               inline=False)
        elif currency is None:
            embedVar.add_field(name="Invalid Currency", value="Enter a currency found in ISO 4217.", inline=True)
    else:
        updatedServ = serv.find_one_and_update({"_id": ctx.guild.id}, {
            "$set": {"_id": ctx.guild.id, "currency": currCode, "shippingCost": shippingCost}})
        embedVar.add_field(name="Updated Shop", value="Currency: " + currCode + "\nShipping Cost: " + str(shippingCost)
                                                      + "\nSearch Code: " + item["searchCode"],
                           inline=False)
    await ctx.send(embed=embedVar)


# currently unusable
@bot.command()
@commands.is_owner()
async def addmgr(ctx, role):
    db = cluster["MeowShop"]
    serv = db["Server"]
    servInf = serv.find_one({"_id": ctx.guild.id})
    embedVar = discord.Embed(title="Add manager", description="Add shop manager", color=0xffcccc)
    guildData = bot.get_guild(servInf["_id"])

    if servInf is None:
        embedVar.add_field(name="Shop not setup",
                           value="Setup server shop using `$setup`", inline=False)
    else:
        if isinstance(role, int):
            checkRole = guildData.get_role(role.id)
            if checkRole is None:
                embedVar.add_field(name="Role not found",
                                   value="Role dies not exist in the server.", inline=False)
            else:
                managers = servInf["manager"]
                managers.append(role)
                embedVar.add_field(name="Added Manager",
                                   value="Added Role: `" + role + "` to the Manager List", inline=False)
        elif isinstance(role, discord.Role):

            checkRole = guildData.get_role(role.id)
            if checkRole is None:
                embedVar.add_field(name="Role not found",
                                   value="Role dies not exist in the server.", inline=False)
            else:
                managers = servInf["manager"]
                managers.append(role.id)
                embedVar.add_field(name="Added Manager",
                                   value="Added Role: `" + role + "` to the Manager List", inline=False)


@bot.command()
@commands.is_owner()
async def confirm(ctx, orderCode: str):
    db = cluster["MeowShop"]
    serv = db["Server"]
    orders = db["Orders"]
    products = db["Products"]
    order = orders.find_one({"_id": orderCode})

    embedVar = discord.Embed(title="Order confirmation", description="Order Code: " + orderCode, color=0xffcccc)
    if order is None:
        embedVar.add_field(name="Order Code not found.", value="The order for the given order code does not exist",
                           inline=False)
    else:
        items = order["items"]
        embedVar.add_field(name="Order Date and Time", value=str(order["orderDate"]),
                           inline=False)
        servInf = serv.find_one({"searchCode": order["searchCode"]})
        for key in items:
            prod = products.find_one({"_id": items[key][3]})
            value = "Price: `" + servInf["currency"] + " " + str(items[key][0]) + "` Quantity: `" \
                    + str(items[key][1]) + "` Code: `" + items[key][3] + "`\nDescription:\n" + prod["desc"]
            embedVar.add_field(name=key, value=value, inline=False)
        embedVar.add_field(name="Sub-Total", value="`" + servInf["currency"] + " " + str(order["subtotal"]) + "`",
                           inline=False)
        embedVar.add_field(name="Shipping",
                           value="`" + servInf["currency"] + " " + str(order["shipping"]) + "`",
                           inline=False)

        embedVar.add_field(name="Total", value="`" + servInf["currency"] + " " + str(order["total"]) + "`",
                           inline=False)
        embedVar.set_footer(text="React to process order")
        message = await ctx.send(embed=embedVar)
        await message.add_reaction('✅')

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == '✅'

        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await ctx.author.send("Checkout timed out")
        else:
            embedVar1 = discord.Embed(title="Order Confirmed",
                                      description="The order `" + orderCode + "` has been confirmed. Payment Received.",
                                      color=0xffcccc)
            embedVar1.set_footer(text="Time Processed: " + str(datetime.utcnow()))
            await ctx.send(embed=embedVar1)

            embedVar2 = discord.Embed(title="Order Confirmed",
                                      description="The order `" + orderCode + "` has been confirmed. Payment Received.",
                                      color=0xffcccc)
            for key in items:
                prod = products.find_one({"_id": items[key][3]})
                value = "Price: `" + servInf["currency"] + " " + str(items[key][0]) + "` Quantity: `" \
                        + str(items[key][1]) + "` Item ID: `" + items[key][2] + "`\nDescription:\n" + items[key][3]
                embedVar.add_field(name=key, value=value, inline=False)
            embedVar2.add_field(name="Sub-Total", value="`" + servInf["currency"] + " " + str(order["subtotal"]) + "`",
                                inline=False)
            embedVar2.add_field(name="Shipping",
                                value="`" + servInf["currency"] + " " + str(order["shipping"]) + "`",
                                inline=False)

            embedVar2.add_field(name="Total", value="`" + servInf["currency"] + " " + str(order["total"]) + "`",
                                inline=False)
            buyer = bot.get_user(order["userID"])
            await buyer.send(embed=embedVar2)
            orders.find_one_and_update({"_id": orderCode}, {"$set": {"processed": True}})


@bot.command()
@commands.is_owner()
async def addp(ctx, name: str, price: float, count: int, *desc):
    db = cluster["MeowShop"]
    prods = db["Products"]
    serv = db["Server"]
    servInf = serv.find_one({"_id": ctx.guild.id})
    code = uuid.uuid4().hex[:8]
    desc = listToString(desc)
    newProd = {"_id": code,
               "name": name,
               "price": price,
               "count": count,
               "desc": desc,
               "serverID": ctx.guild.id}
    prods.insert_one(newProd)
    result = prods.find_one({"_id": code})
    description = "Succesfully added: `" + result["name"] + "`"
    value = "Price: `" + servInf["currency"] + " " + str(result["price"]) + "` Count: `" + str(
        result["count"]) + "` Code: `" + result["_id"] + "`\n\n Description: \n" + result["desc"]
    embedVar = discord.Embed(title="Product Added", description=description, color=0xffcccc)
    embedVar.add_field(name="Details", value=value, inline=True)
    await ctx.send(embed=embedVar)


@bot.command()
@commands.is_owner()
async def delp(ctx, code: str):
    db = cluster["MeowShop"]
    prods = db["Products"]
    serv = db["Server"]
    servInf = serv.find_one({"_id": ctx.guild.id})
    deleted = prods.find_one_and_delete({"_id": code, "serverID": ctx.guild.id})
    name = "Successfully deleted: `" + deleted["name"] + "`"
    value = "Price: `" + servInf["currency"] + " " + str(deleted["price"]) + "` Count: `" + str(
        deleted["count"]) + "` Code: `" + deleted[
                "_id"] + "`\n Description: \n" + deleted["desc"]
    embedVar = discord.Embed(title="Delete Status", description="", color=0xffcccc)
    embedVar.add_field(name=name, value=value, inline=True)
    await ctx.send(embed=embedVar)


@bot.command()
@commands.is_owner()
async def setcurrency(ctx, currcode: str):
    db = cluster["MeowShop"]
    serv = db["Server"]
    item = serv.find_one({"_id": ctx.guild.id})
    currency = c.get_symbol(currcode)
    embedVar = discord.Embed(title="Set Currency", description="", color=0xffcccc)

    if currency is None:
        embedVar.add_field(name="Invalid Currency", value="Enter a currency found in ISO 4217.", inline=True)
    if currency is not None and item is None:
        embedVar.add_field(name="Shop not setup", value="Setup Shop using $setup", inline=True)
    elif currency is not None and item is not None:
        updatedCurr = serv.find_one_and_update({"_id:": ctx.guild.id}, {"$set": {"currency": currcode}})
        embedVar.add_field(name="Updated Currency",
                           value="Updated store currency to " + currcode + " (" + currency + ")", inline=True)
    await ctx.send(embed=embedVar)


@bot.command()
@commands.is_owner()
async def setshipping(ctx, cost: float):
    db = cluster["MeowShop"]
    serv = db["Server"]
    item = serv.find_one({"_id": ctx.guild.id})
    embedVar = discord.Embed(title="Set Shipping Cost", description="", color=0xffcccc)
    if item is None:
        embedVar.add_field(name="Shop not setup", value="Setup Shop using $setup", inline=True)
    else:
        updatedCurr = serv.find_one_and_update({"_id:": ctx.guild.id}, {"$set": {"shippingCost": cost}})
        embedVar.add_field(name="Updated Shipping", value="Shipping Price: `" + item["currency"] + " " + str(cost),
                           inline=True)
    await ctx.send(embed=embedVar)


@bot.command()
@commands.is_owner()
async def addpayment(ctx, paymentType: str, *instruction):
    db = cluster["MeowShop"]
    serv = db["Server"]
    item = serv.find_one({"_id": ctx.guild.id})
    instruction = listToString(instruction)
    embedVar = discord.Embed(title="Add Payment", description="Add a payment option.", color=0xffcccc)
    if item is None:
        embedVar.add_field(name="Shop not setup.", value="Setup shop using `$setup`",
                           inline=True)
    else:
        item["payments"][paymentType] = instruction
        options = item["payments"]
        newSet = {"payments": options}
        serv.find_one_and_update({"_id": ctx.guild.id}, {"$set": newSet})
        embedVar.add_field(name=paymentType, value="Option Instruction:\n" + instruction, inline=True)

    await ctx.send(embed=embedVar)


@bot.command()
@commands.is_owner()
async def delpayment(ctx, type: str):
    db = cluster["MeowShop"]
    serv = db["Server"]
    item = serv.find_one({"_id": ctx.guild.id})
    embedVar = discord.Embed(title="Set Payment", description="Add a payment option.", color=0xffcccc)
    if item is None:
        embedVar.add_field(name="Shop not setup.", value="Setup shop using `$setup`",
                           inline=True)
    else:
        options = item["payments"]
        if type in options:
            options.pop(type)
            newSet = {"payments": options}
            serv.find_one_and_update({"_id": ctx.guild.id}, {"$set": newSet})
            embedVar.add_field(name="Pay option removed", value="Removed **" + type + "** as a payment option.",
                               inline=False)
        else:
            embedVar.add_field(name="Pay option not found",
                               value="Possible typo or the payment option was never added.",
                               inline=False)

    await ctx.send(embed=embedVar)


#need to update this command
@bot.command()
async def help(ctx):
    embedVar = discord.Embed(title="Help", description="Command List. Prefix: `$`", color=0xffcccc)
    embedVar.add_field(name="`$products`", value="Show product list.", inline=True)
    embedVar.add_field(name="`$addp`", value="Add product to the list.", inline=True)
    embedVar.add_field(name="`$delp`", value="delete product from the list.", inline=True)
    embedVar.add_field(name="`$resource`", value="Show resource list.", inline=True)
    embedVar.add_field(name="`$addr`", value="Add resource to the list.", inline=True)
    embedVar.add_field(name="`$delr`", value="delete resource from the list.", inline=True)
    embedVar.add_field(name="`$add`", value="Add an item to your cart.", inline=True)
    embedVar.add_field(name="`$remove`", value="Delete an item from your cart.", inline=True)
    embedVar.add_field(name="`$cart`", value="Show cart.", inline=True)
    embedVar.add_field(name="`$checkout`", value="Checkout cart.", inline=True)

    await ctx.send(embed=embedVar)


@bot.command()
async def info(ctx, searchCode: str = None):
    embedVar = discord.Embed(title="Shop Info", description=" ", color=0xffcccc)
    db = cluster["MeowShop"]
    serv = db["Server"]
    if searchCode is None:
        item = serv.find_one({"_id": ctx.guild.id})
        embedVar.add_field(name="Currency", value="`" + item["currency"] + "`",
                           inline=False)
        embedVar.add_field(name="Shipping Cost", value="`" + str(item["shippingCost"]) + "`",
                           inline=False)
        embedVar.add_field(name="Search Code", value="`" + item["searchCode"] + "`",
                           inline=False)
        options = "💳: "
        for key in item["payments"]:
            options += (key + ",")
        options = options[:-1]
        print(options)
        embedVar.add_field(name="Payment Options", value=options, inline=False)
    else:
        item = serv.find_one({"searchCode": searchCode})
        embedVar.add_field(name="Currency", value="`" + item["currency"] + "`",
                           inline=False)
        embedVar.add_field(name="Shipping Cost", value="`" + str(item["shippingCost"]) + "`",
                           inline=False)
        embedVar.add_field(name="Search Code", value="`" + item["searchCode"] + "`",
                           inline=False)
        options = " "
        for key in item["payments"]:
            options += (item["payments"][key] + ",")
        options = options[:-1]
        print(options)
        embedVar.add_field(name="Payment Options", value=options, inline=False)
    await ctx.send(embed=embedVar)


@bot.command()
async def products(ctx, searchCode: str = None):
    db = cluster["MeowShop"]
    prods = db["Products"]
    serv = db["Server"]
    embedVar = discord.Embed(title="Products", description="Product List.", color=0xffcccc)
    if searchCode is None:
        servInf = serv.find_one({"_id": ctx.guild.id})
        results = prods.find({"serverID": ctx.guild.id})
        for product in results:
            name = product["name"]
            value = "Price: `" + servInf["currency"] + " " + str(product["price"]) + "` Count: `" + str(
                product["count"]) + "` Item ID: `" + product[
                        "_id"] + "`\n" + product["desc"]
            embedVar.add_field(name=name, value=value, inline=False)
    else:
        servInf = serv.find_one({"searchCode": searchCode})
        results = prods.find({"serverID": servInf["_id"]})
        for product in results:
            name = product["name"]
            value = "Price: `" + servInf["currency"] + " " + str(product["price"]) + "` Count: `" + str(
                product["count"]) + "` Item ID: `" + product[
                        "_id"] + "`\n" + product["desc"]
            embedVar.add_field(name=name, value=value, inline=False)

    await ctx.send(embed=embedVar)


@bot.command()
async def payments(ctx, searchCode: str = None):
    db = cluster["MeowShop"]
    serv = db["Server"]
    embedVar = discord.Embed(title="Payment Options", description="List of available payment options.", color=0xffcccc)
    if searchCode is None:
        servInf = serv.find_one({"_id": ctx.guild.id})
        for key in servInf["payments"]:
            embedVar.add_field(name=key, value=servInf["payments"][key], inline=False)
    else:
        servInf = serv.find_one({"searchCode": searchCode})
        for key in servInf["payments"]:
            embedVar.add_field(name=key, value=servInf["payments"][key], inline=False)
    await ctx.send(embed=embedVar)


@bot.command()
@commands.dm_only()
async def add(ctx, serverCode: str, code: str, quant: int):
    db = cluster["MeowShop"]
    prods = db["Products"]
    carts = db["Carts"]
    serv = db["Server"]
    servInf = serv.find_one({"searchCode": serverCode})
    item = prods.find_one({"_id": code, "serverID": servInf["_id"]})
    value = "Price: `" + servInf["currency"] + " " + str(item["price"]) + "` Quantity: in cart`" + str(
        quant) + "` Item ID: `" + item["_id"] + "`\n Description: \n" + item["desc"]
    embedVar = discord.Embed(title="Add to Cart", description="", color=0xffcccc)
    if quant <= 0:
        embedVar.add_field(name="Invalid Quantity", value="You must order at least 1 item.", inline=True)
    elif item is None:
        embedVar.add_field(name="Item code does not exist", value="No items correspond with the code given.",
                           inline=True)
    elif item is not None and item["count"] < quant:
        embedVar.add_field(name="Invalid Quantity", value="Order count beyond what is in-stock", inline=True)
    elif item is not None and item["count"] >= quant:
        existCart = carts.find_one({"userID": ctx.author.id, "serverID": servInf["_id"], "itemCode": item["_id"]})
        if existCart is not None and item["count"] < (quant + existCart["quantity"]):
            embedVar.add_field(name="Invalid Quantity",
                               value="Order count beyond what is in-stock.Your cart contains this item.", inline=True)
        elif existCart is not None and item["count"] >= (quant + existCart["quantity"]):
            myquery = {"userID": ctx.author.id, "serverID": servInf["_id"], "itemCode": item["_id"]}
            newquantity = {"quantity": quant + existCart["quantity"]}
            carts.update_one(myquery, {"$set": newquantity})
            name = "Updated Quantity of item `" + item["name"] + "`"
            embedVar.add_field(name=name, value="Order count beyond what is in-stock.Your cart contains this item.",
                               inline=True)
        elif existCart is None:
            cartID = uuid.uuid4().hex[:8]
            addToCart = {"_id": cartID,
                         "userID": ctx.author.id,
                         "serverID": servInf["_id"],
                         "itemCode": item["_id"],
                         "quantity": quant}
            carts.insert_one(addToCart)
            name = "Successfully added: `" + item["name"] + "` to cart."
            embedVar.add_field(name=name, value=value, inline=True)
    await ctx.send(embed=embedVar)


@bot.command()
@commands.dm_only()
async def remove(ctx, serverCode: str, code: str, quant: int):
    embedVar = discord.Embed(title="Removed from cart", description="", color=0xffcccc)
    db = cluster["MeowShop"]
    prods = db["Products"]
    carts = db["Carts"]
    serv = db["Server"]
    servInf = serv.find_one({"searchCode": serverCode})
    item = carts.find_one({"itemCode": code, "userID": ctx.author.id, "serverID": servInf["_id"]})
    if item is None:
        embedVar.add_field(name="Item not found in your cart.",
                           value="The item you are looking for is not in your cart. Check your cart using: `$cart servercode`",
                           inline=True)
    elif item is not None:
        details = prods.find_one({"_id": code, "serverID": servInf["_id"]})
        if quant >= item["quantity"]:
            deleted = carts.find_one_and_delete({"itemCode": code, "userID": ctx.author.id, "serverID": servInf["_id"]})
            embedVar.add_field(name="Deleted Items: `" + details["name"] + "`",
                               value="Removed the item from your cart. Check your cart using: `$cart`\n" +
                                     "`" + details["name"] + "`\n Quantity removed: `" + str(quant) + "` Price: `"
                                     + details["price"] + "` Item ID: `" + code + "`\n\nDescription: \n" + details[
                                         "desc"],
                               inline=True)
        elif quant < item["quantity"]:
            carts.update_one({"itemCode": code, "userID": ctx.author.id, "serverID": servInf["_id"]},
                             {"$set": {"quantity": item["quantity"] - quant}})
            embedVar.add_field(name="Deleted `" + str(quant) + " " + details["name"] + "` from your cart.",
                               value="Removed the item(s) from your cart. Check your cart using: `$cart`\n\n" +
                                     "`" + details["name"] + "`\n Quantity in your cart: `" + str(
                                   item["quantity"] - quant) + "` Price: `" + servInf["currency"] + " " + str(
                                   details["price"]) + "` Item ID: `" + code + "`\n\nDescription: \n" + details["desc"],
                               inline=True)
    await ctx.send(embed=embedVar)


@bot.command()
@commands.dm_only()
async def cart(ctx, serverCode: str):
    db = cluster["MeowShop"]
    carts = db["Carts"]
    prods = db["Products"]
    serv = db["Server"]
    servInf = serv.find_one({"searchCode": serverCode})
    embedVar = discord.Embed(title="Your Cart", description="", color=0xffcccc)
    results = carts.find({"userID": ctx.author.id, "serverID": servInf["_id"]})
    for item in results:
        product = prods.find_one({"_id": item["itemCode"], "serverID": servInf["_id"]})
        name = product["name"]
        if product["count"] >= item["quantity"]:
            value = "Price: `" + servInf["currency"] + " " + str(product["price"]) + "` Quantity: `" + str(
                item["quantity"]) + "` Item ID: `" + product[
                        "_id"] + "`\n\nDescription:\n" + product["desc"]
            embedVar.add_field(name=name, value=value, inline=False)
        else:
            value = "Out of stock or ordering too many.\n Available Items: `" + str(item["quantity"]) \
                    + "` Order quantity: `" + str(product["count"])
            embedVar.add_field(name=name, value=value, inline=False)

    await ctx.send(embed=embedVar)


@bot.command()
@commands.dm_only()
async def checkout(ctx, serverCode: str):
    embedVar = discord.Embed(title="Checkout", description="", color=0xffcccc)
    db = cluster["MeowShop"]
    carts = db["Carts"]
    prods = db["Products"]
    serv = db["Server"]
    servInf = serv.find_one({"searchCode": serverCode})
    results = carts.find({"userID": ctx.author.id, "serverID": servInf["_id"]})
    items = {}
    subtotal = 0
    total = 0
    shipping = 0
    for item in results:
        product = prods.find_one({"_id": item["itemCode"], "serverID": servInf["_id"]})
        name = product["name"]
        if product["count"] >= item["quantity"]:
            value = "Price: `" + servInf["currency"] + " " + str(product["price"]) + "` Quantity: `" + str(
                item["quantity"]) + "` Item ID: `" + product[
                        "_id"] + "`\nDescription:\n" + product["desc"]
            subtotal = subtotal + product["price"] * item["quantity"]
            items[name] = (product["price"], item["quantity"], product["_id"], product["desc"])
            embedVar.add_field(name=name, value=value, inline=False)
        else:
            value = "Order cancelled. Out of stock or ordering too many.\n Available Items: `" \
                    + str(product["count"]) + "` Order quantity: `" + str(item["quantity"])
            embedVar.add_field(name=name, value=value, inline=False)
    embedVar.add_field(name="Sub-Total", value="`" + servInf["currency"] + " " + str(subtotal) + "`", inline=False)
    if subtotal != 0:
        embedVar.add_field(name="Shipping", value="`" + servInf["currency"] + " " + str(servInf["shippingCost"]) + "`",
                           inline=False)
        shipping = servInf["shippingCost"]
        total = total + subtotal + shipping
    else:
        total = subtotal
    embedVar.add_field(name="Total", value="`" + servInf["currency"] + " " + str(total) + "`", inline=False)
    embedVar.set_footer(text="React to confirm order")
    message = await ctx.send(embed=embedVar)
    await message.add_reaction('✅')

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) == '✅'

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await ctx.author.send("Checkout timed out")
    else:
        orders = db["Orders"]
        orderID = uuid.uuid4().hex[:8]
        dt = datetime.utcnow()
        newOrder = {"_id": orderID, "userID": ctx.author.id, "searchCode": servInf["searchCode"], "items": items,
                    "subtotal": subtotal, "shipping": shipping, "total": total, "orderDate": dt,
                    "messageID": message.id, "processed": False}
        orders.insert_one(newOrder)

        embedVar1 = discord.Embed(title="Order Code: " + newOrder["_id"], description="Order Date: " + str(dt),
                                  color=0xffcccc)
        for key in items:
            value = "Price: `" + servInf["currency"] + " " + str(items[key][0]) + "` Quantity: `" \
                    + str(items[key][1]) + "` Item ID: `" + items[key][2] + "`\nDescription:\n" + items[key][3]
            embedVar1.add_field(name=key, value=value, inline=False)
        embedVar1.add_field(name="Sub-Total",
                            value="`" + servInf["currency"] + " " + str(newOrder["subtotal"]) + "`",
                            inline=False)
        embedVar1.add_field(name="Shipping",
                            value="`" + servInf["currency"] + " " + str(newOrder["shipping"]) + "`",
                            inline=False)
        embedVar1.add_field(name="Total", value="`" + servInf["currency"] + " " + str(newOrder["total"]) + "`",
                            inline=False)
        await ctx.send(embed=embedVar1)

        embedVar2 = discord.Embed(title="Payment Options", description="List of available payment options.",
                                  color=0xffcccc)
        for key in servInf["payments"]:
            embedVar2.add_field(name=key, value=servInf["payments"][key], inline=False)

        for item in items:
            prods.find_one_and_update({"_id": items[item][2], "serverID": servInf["_id"]},
                                      {"$inc": {"count": -items[item][1]}})
            carts.find_one_and_delete({"userID": ctx.author.id, "serverID": servInf["_id"], "itemCode": items[item][2]})

        await ctx.send(embed=embedVar2)

        owner = bot.get_user(bot.get_guild(servInf["_id"]).owner_id)
        await owner.send(embed=embedVar1)


bot.run(os.environ['TOKEN'])
