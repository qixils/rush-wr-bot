import discord
import asyncio
import requests
import time
import json

def httpget(url):
    status_code = 0
    while status_code != 200:
        r=requests.get(url, headers={"User-Agent":"rush-wr-bot/3.0"})
        status_code = r.status_code
    return r

def jsonget(rawjson): return json.loads(rawjson.content)

def comma(items): # https://stackoverflow.com/a/38982008
    start, last = items[:-1], items[-1]
    if start:
        return "{}, and {}".format(", ".join(start), last)
    else:
        return last

def sec2time(sec, n_msec=3): # https://stackoverflow.com/a/33504562
    ''' Convert seconds to 'D days, HH:MM:SS.FFF' '''
    if hasattr(sec,'__len__'):
        return [sec2time(s) for s in sec]
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    if n_msec > 0:
        pattern = '%%02d:%%02d:%%0%d.%df' % (n_msec+3, n_msec)
    else:
        pattern = r'%02d:%02d:%02d'
    if d == 0:
        return pattern % (h, m, s)
    return ('%d days, ' + pattern) % (d, h, m, s)



class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create the background task and run it in the background
        self.bg_task = self.loop.create_task(self.my_background_task())

    async def on_ready(self):
        print('Logged in as {self.user.name} ({self.user.id})\n------')

    async def my_background_task(self):
        await self.wait_until_ready()
        channel = self.get_channel(545063651808247833)
        checked_ids = []
        startup = True
        while not self.is_closed():
            try:
                r=httpget("https://www.speedrun.com/api/v1/runs?status=verified&orderby=verify-date&direction=desc")
                recent_runs=jsonget(r) # turn that json into fun python things

                if startup: # initial startup code
                    checked_ids.append(recent_runs["data"][0]["id"])
                    startup = False
                else: # not initial startup code
                    finished = False
                    next_check = 0

                    while not finished: # cycles through all runs until an already processed run is reached
                        run = recent_runs["data"][next_check]

                        if run["id"] in checked_ids:
                            finished = True
                        elif run["level"] is None:
                            # current run is new, grabbing WR run to check if this is WR
                            toprun=httpget("https://www.speedrun.com/api/v1/leaderboards/"+run["game"]+"/category/"+run["category"]+"?top=1")
                            if jsonget(toprun)["data"]["runs"][0]["run"]["id"] == run["id"]:
                                # this run is WR, time to grab run information
                                game_get=httpget("https://www.speedrun.com/api/v1/games/"+run["game"])
                                category_get=httpget("https://www.speedrun.com/api/v1/categories/"+run["category"])
                                game=jsonget(game_get)["data"]["names"]["international"]
                                category=jsonget(category_get)["data"]["name"]
                                players = []
                                for player in run["players"]:
                                    if player["rel"] == "user":
                                        # usernames aren't provided so we need to grab them manually
                                        playerpage=httpget(player["uri"])
                                        players.append(jsonget(playerpage)["data"]["names"]["international"])
                                    else:
                                        # but guests do have names
                                        players.append(player["name"])
                                # turning raw seconds into processed time
                                microsec = 3 if not float(run["times"]["primary_t"]).is_integer() else 0
                                runtime = sec2time(run["times"]["primary_t"], microsec)
                                # finally pipe the run information into file output
                                wr = f"{game}\n{category}\n{runtime}\n{comma(players)}\n<:PogChamp:455481013242691616>"
                                await channel.send(wr)
                                checked_ids.append(run["id"]) # add run to processed runs
                        else:
                            # run was an Individual Level run, processing but not checking for WR
                            checked_ids.append(run["id"])
                        next_check += 1 # increase run id to check next

            except Exception as e:
                print(e)
            await asyncio.sleep(60)


client = MyClient()
client.run(open("token.txt").read().split("\n")[0])
