"""
clients when connected are in the lobby state

in this state, they can send one of these:

create game
makes a new game of game
e.g. create chess

join user id side
join the game with id id as user user on side side
e.g. join brunnerj 6 white

list
returns a list of game ids and who is in them

create or join put the client in the 'in game' state
In this state, the server will send the client the gamestate when they join and when any player makes a move
here, they can send
move m
make move m in the current game

leave
returns to lobby state


The server needs an abstract  version of the game. This must implement the following:
    __init__ to create a new game
    attemptMove
    get_state
    teams
"""
   

import socketserver
import threading
import json
import traceback
import sys
import asyncio
import os
import continuousEngine

port = 9974
SERVER_STATE_FILENAME = "serverstate"

class NetworkGameServer:
    def create_game(self, name, id, args):
        if id in self.list_games():
            print('game {} already exists'.format(id), flush=True)
            return
        game = continuousEngine.game_class(name)(*args, headless=True)
        self.games[id] = {
            "game_type":name,
            "players":[],
            "game":game
        }
        return id
    async def join_game(self, i,team, user, client):
        if i not in self.games:
            raise Exception("game id doesn't exist")
        player = {"user":user, "team":team, "client":client}
        self.games[i]["players"].append(player)
        await self.broadcast_game_info(i)
        await self.send_gamestate(i, player, None)
        await send(client, {"action":"history", "history":self.games[i]["game"].history})
        return player
    async def broadcast_move(self, game_id, move):
        l = self.games[game_id]["players"].copy()
        for player in l:
            await self.send_gamestate(game_id, player, move)
    async def broadcast_game_info(self, game_id):
        l = self.games[game_id]["players"].copy()
        for player in l:
            await send(player["client"],{"action":"game_info", **self.get_game_info(game_id)})
    async def send_gamestate(self, game_id, player, move):
        try:
            await send(player["client"],{"action":"move","state":self.games[game_id]["game"].get_state(player["team"]), "move":move})
        except:
            #print(traceback.format_exc(),flush=True)
            self.games[game_id]["players"].remove(player)
            print("Player removed during send_gamestate",flush=True)
            await self.broadcast_game_info(game_id)
    def get_game_info(self, i):
        result = self.games[i].copy()
        pl = [p.copy() for p in self.games[i]["players"]]
        result["players"] = pl
        result["open teams"] = [t for t in result["game"].teams if t not in {p["team"] for p in pl}]
        for p in pl:
            del p["client"]
        del result["game"]
        return result
    def list_games(self):
        result = {}
        for i in self.games:
            result[i] = self.get_game_info(i)
        print(result,flush=True)
        return result
        
    def __init__(self, clean=False, unsafe=False):
        # clean: if True, don't save state
        # unsafe: if True, don't enforce players only making moves for their own team
        self.games = {}
        self.clean, self.unsafe = clean, unsafe

    async def serve(self, ip="localhost"):
        if self.clean:
            self.games = {}
        else:
            try:
                self.load_server_state(SERVER_STATE_FILENAME)
            except:
                self.games = {}
        server = await asyncio.start_server(self.a, host=ip, port=9974)
        print("server listening",flush=True)
        try:
            async with server:
                await asyncio.gather(server.serve_forever(),self.server_console(), *([] if self.clean else [self.server_save_loop()]))
        finally:
            #doesn't run if you keyboard interrupt
            print("awoenoasioshvoihoianef",flush=True)
    def load_server_state(self, filename):
        with open(filename) as f:
            self.games = json.loads(f.read())
            for i in self.games:
                g = games[self.games[i]["game_type"]](headless=True)
                g.load_state(self.games[i]["game"]["state"])
                g.history = self.games[i]["game"]["history"]
                self.games[i]["game"] = g                             
    def save_server_state(self):
        g = self.games.copy()
        for i in g:
            g[i] = g[i].copy()
            g[i]["players"]=[]
        with open(SERVER_STATE_FILENAME,'w') as f:
            f.write(json.dumps(g, default=lambda o: {"state": o.save_state(), "history": o.history}))
    async def server_save_loop(self):
        while True:
            await asyncio.sleep(120)
            self.save_server_state()
    async def server_console(self):
        while 1:
            s = await asyncio.get_running_loop().run_in_executor(None, input)
            if s=="q":
                self.save_server_state()
                sys.exit()
            elif s=="l":
                self.load_server_state("a.txt")

    async def a(self,reader, writer):
        print("connected",flush=True)
        game_id = None
        player = None
        server = self
        client = (reader, writer)
        while True:
            try:
                r = await recieve(client)
                print("recieved {}".format(r),flush=True)
            except:
                #print(traceback.format_exc(),flush=True)
                if game_id != None:
                    server.games[game_id]["players"].remove(player)
                    await server.broadcast_game_info(game_id)
                return
            if r["action"] == "create":
                server.create_game(r["name"], r["id"], r["args"])
            elif r["action"] == "join":
                if game_id != None:
                    server.games[game_id]["players"].remove(player)
                game_id = r["id"]
                player = await server.join_game(game_id,r["team"],r["user"],client)
            elif r["action"] == "move":
                if not ((self.unsafe and player["team"] == "spectator") or r["move"]["player"] == player["team"]):
                    print("trying to move for the wrong team",flush=True)
                    continue
                if server.games[game_id]["game"].attemptMove(r["move"]):
                    print("successfully applied move to gamestate",flush=True)
                    await server.broadcast_move(game_id, r["move"])
                else:
                    print("move was illegal",flush=True)
            elif r["action"] == "list":
                await send(client, server.list_games())
            elif r["action"] == "override_state":
                if not self.unsafe:
                    print("trying to override state")
                    continue
                server.games[game_id]["game"].load_state(r["state"])
                server.games[game_id]["game"].history = []
                server.games[game_id]["game"].future = []

async def send(client, message):
    client[1].write((json.dumps(message)+"\n").encode())
    await client[1].drain()
async def recieve(client):
    return json.loads((await client[0].readline()).strip())
