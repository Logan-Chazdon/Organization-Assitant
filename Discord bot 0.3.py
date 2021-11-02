#Logan Chazdon
#Lchazdon@cnm.edu


import discord
from dotenv import load_dotenv
import os
import pymongo
import datetime
import re


load_dotenv()

#discord
token = os.getenv('') #Token removed for security. 
global client
client = discord.Client()

#database
myclient = pymongo.MongoClient("mongodb://localhost:27017/")

mydb = myclient["mydatabase"]


#=========Functions===========#
def AddRow(assignment, guild, owner): 
    assignment = assignment.split(",")
    if len(assignment[2].split("/")) != 3:
        raise "date in unsupported format"
    if len(assignment) == 4: #this line can cause bugs if we want more than 4 items in the insert
        row = { "class": assignment[0].strip(), "name": assignment[1].strip(),
                "due date": assignment[2].strip(), "reminders" : assignment[3].strip(), "lastReminded" : '0',
                "guild":guild, "owner": owner}
    else:
        row = { "class": assignment[0].strip(), "name": assignment[1].strip(),
                "due date": assignment[2].strip(), "reminders" : "1", "lastReminded" : '0',
                "guild":guild, "owner": owner}
    assignmentsTable.insert_one(row)

def RemoveCommandWord(message):
    'Returns the input but without the first word.'
    message = message.split()
    message.pop(0)
    strMessage = ''
    i = 0
    while i < len(message):
        strMessage += message[i] + " "
        i += 1
    return strMessage

def QueryTable(search, guild):
    table = []
    if search == 'everything':
        mydoc = assignmentsTable.find({"guild": guild})
    else:
        myquery = { "class": search.strip(), "guild": guild }

        mydoc = assignmentsTable.find(myquery)
    for x in mydoc:
        try:
            row = x["class"].strip() + ', ' + x["name"].strip() + ', ' + x["due date"].strip() + ', ' + x["reminders"].strip()
            table.append(row)
        except:
            print("Error found in table : querytable")
    print(table)    
    return table

def DelName(name, guild):
    x = assignmentsTable.delete_many({'name' : name, "guild": guild})
    x = x.deleted_count
    print("Deleted " + str(x) + " rows.")
    return x

def ConvertDate(date):
    '''Converts a date from discord entry format(mm/dd/yy) into
    something the bot can use'''
    date = date.split("/")
    if len(date[2]) == 2: #lets us use yy instead of yyyy
        #print("short form dating being updated") #turned off due to spamm
        date[2] = int('20' + date[2])
    date = datetime.datetime(int(date[2]), int(date[0]), int(date[1]))
    return date

def RemoveOutDated(guild):
    table = QueryTable('everything', guild) #getting data
    i = 0
    print('Table len = ' + str(len(table)))
    while i < len(table):
        print('processing row: ' + table[i])
        dueDate = ConvertDate(table[i].split(',')[2].replace(',', '')) #casting due date
        date =  datetime.datetime.now() #current date
        currentDate = datetime.datetime.now()
        print("Is it outdated")
        print("due",dueDate)
        print("current",currentDate)
        if dueDate.strftime("%j") < currentDate.strftime("%j"): #is it outdated??
            DelName(table[i].split(',')[1].strip(), guild)
            print("yes")
        i += 1

def Feedback(feedback, name):
    feedbackTable.insert_one({"name" : str(name), "feedback" : feedback})
#========Tables========#
assignmentsTable = mydb["tasks"]
config = mydb["config"]
feedbackTable = mydb["feedback"]

#========Main========#

helpMessage = """
Format: !command (variable1), (variable2)

Commands:
!list all - shows you all assignments
!list (class) - shows all assingments with the class specified
!add (class), (name), (due date mm/dd/yy or mm/dd/yyyy), (reminders 1 or 0, optional) - adds a task to the table
!delete (name) - removes a task from the table
!my config - shows you your user settings
!update_config (name), (new value) - changes a setting
!feedback (message) - send me feedback
"""
mydoc = assignmentsTable.find()

print("Assignments")
print("class, name, due date, reminders, lastReminded, guild, owner")
for x in mydoc:
    print(x["class"] + ", " + x["name"] + ", " + x["due date"] + ", " + x["reminders"] + ", " + x["lastReminded"] + ", " + str(x["guild"]) + ", " + str(x["owner"]))


configdoc = config.find()

print("Configs")
for x in configdoc:
    print(x)

feedbackdoc = feedbackTable.find()

print("Feedback")
for x in feedbackdoc:
    print(x['name'] + " says: " + x["feedback"])

@client.event
async def on_guild_join(guild):
    print('We have logged in as {0.user}'.format(client))



@client.event
async def on_message(message):
    #getting data for reminders
    mydoc = assignmentsTable.find()

 
    response = ""
    if message.author.bot:
        pass 
    else:
        #sending reminders
        for x in mydoc:
            due = ConvertDate(x['due date'])
            
            if datetime.datetime.now().strftime("%j") == due.strftime("%j") and x['reminders'] == '1' and x["guild"] == message.guild.id:
                
                configdoc = config.find()
                for j in configdoc:
                    
                    if j['reminders'] == 'on' and x['lastReminded'] !=  datetime.datetime.now().strftime("%j") and j["guild"] == message.guild.id:
                        print("sending reminders for " + x['name'])
                        try:
                            
                            inclass = 0
                            classes = j['classes'].split(",")
                            for i in classes:
                                if i.strip() == x["class"]:
                                    inclass = 1
                                    
                            if j['classes'] == "all" or inclass == 1:
                                try:
                                    query = {'name' : x['name']}
                                    
                                    update = {'lastReminded' : datetime.datetime.now().strftime("%j") }
                                    
                                    assignmentsTable.update_many(query, {"$set" : update} )
                                    
                                    print("last reminded set to " + datetime.datetime.now().strftime("%j"))
                                    response += message.guild.get_member(j['id']).mention  + x['name'] + ', is due on ' + x['due date'] + "\n"
                                except:
                                    print("error. probably someone leaving the guild.")
                        except error as e:
                            print("Erorr in database: found in reminders loop")
                            print(e)
        if len(response) != 0:
            await message.channel.send(response)
                        
    #making new configs
    if message.author.bot:
        pass
    else:
        #checking for the users config
        author = str(message.author)
        configdoc = config.find()
        exists = 0
        otherGuild = 0
        for x in configdoc:
            if x['name'] == author and x["guild"] == message.guild.id:
                exists = 1
            if str(x['guild']) == str(message.guild.id) and  x['name'] == author:
                otherGuild = 1
                clone = x["reminders"] #this needs to be updates everytime we add a new config option
                clone1 = x["classes"]

            

        if otherGuild == 0 and exists == 0:
            print("Generating new config for", author)
            config.insert_one({"name" : author, "id" : message.author.id , "reminders" : "on", "classes" : "all", "guild" : message.guild.id})

            
        if otherGuild == 1 and exists == 0:
            #This needs to be updated with every new config
            #This clones configs
            #So users dont have to create them over and over
            print("Copying config for", author)
            config.insert_one({"name" : author, "id" : message.author.id , "reminders" : clone, "classes": clone1 , "guild" : message.guild.id})

        

    
    #searching for what command the user wants to execute
    if message.content.lower() == "!help":
        await message.channel.send(helpMessage)


        
    elif message.content.split()[0].lower() == "!add":
        assignment = RemoveCommandWord(message.content)
        try:
            AddRow(assignment, message.guild.id, message.author.id)
        except:
            await message.channel.send("""Assignment not added due to format. Use !help if confused.
Example !add class, name, 1/1/30, 1""")
        else:
            await message.channel.send("Assignment: " + assignment + " added.")



            
    elif message.content.lower() == "!list all":
        RemoveOutDated(message.guild.id)
        table = QueryTable('everything', message.guild.id)
        i = 0
        response = """Class, Name, Due date, reminders
---------------------------------------------
"""
        while i < len(table):
            response += table[i] + "\n"
            i += 1
        await message.channel.send(response)
        
    elif message.content.split()[0] == "!list":
        search = RemoveCommandWord(message.content)
        RemoveOutDated(message.guild.id)
        table = QueryTable(search, message.guild.id)
        i = 0
        response = """Class, Name, Due date, Reminders
---------------------------------------------
"""
        while i < len(table):
            response += table[i] + "\n"
            i += 1
        await message.channel.send(response)



        
    elif message.content.split()[0].lower() =="!delete":
        name = RemoveCommandWord(message.content).strip()
        print(name)
        x = DelName(name, message.guild.id)
        if x == 1:
            await message.channel.send(str(x) + " assignment named " + name +  " deleted.")
        else:
            await message.channel.send(str(x) + " assignments named " + name +  " deleted.")


        
    elif message.content.lower() == "!my config":
        response = '''Config
----------
'''
        configdoc = config.find({'name' : str(message.author), 'guild' : message.guild.id})
        for x in configdoc:
            response += 'reminders' + " = "  + str(x['reminders']) + " - on or off should I send reminders" + '\n'
            response += 'classes' + " = " + str(x["classes"]) + " -comma delimited list of classes or all" + "\n"
            break
        response += """----------
To change a config enter: !update_config (name), (new value)
EX: !update_config reminders off
EX: !update_config classes class, class1, class2
"""
        await message.channel.send(response)




        
    elif message.content.split()[0] == "!update_config":
        update = RemoveCommandWord(message.content)
        new = RemoveCommandWord(update)
        update = update.split()

        #formating the users input
        #checking for mistakes
        if update[1].lower == "false" or update[1].lower == "disabled" or update[1] == "0":
            update[1] = "off"
        elif update[1].lower == "true" or update[1].lower == "enabled" or update[1] == "1":
            update[1] == "on"

        #updating config
        
        setting = {"$set" : {update[0].strip(): new.lower().strip()}}
        print(update)
        config.update_one({'name' : str(message.author).split()[0], 'guild' : message.guild.id}, setting)
        await message.channel.send(str("Setting " + str(update[0]) +  " updated to " + new))

        
    elif message.content.split()[0] == "!feedback":
        feedback = RemoveCommandWord(message.content)
        Feedback(feedback, message.author)
        await message.channel.send("Thank you for your feedback.")

                                 
client.run('') #Token removed for security. 
