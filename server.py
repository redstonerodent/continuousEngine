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
import chess, reversi, go, jrap
import json
import traceback
import sys
import asyncio

games = {
    'chess'     : chess.Chess,
    'reversi'   : reversi.Reversi,
    'go'        : go.Go,
    'jrap'      : jrap.Jrap,
    }

port = 9974

class NetworkGameServer:
    def create_game(self, name, id, args):
        if id in self.list_games():
            print('game {} already exists'.format(id), flush=True)
            return
        game = games[name](*args, headless=True)
        self.games[id] = {
            "type":name,
            "players":[],
            "game":game
        }
        return id
    async def join_game(self, i,team, user, client):
        if i not in self.games:
            raise Exception("game id doesn't exist")
        player = {"user":user, "team":team, "client":client}
        self.games[i]["players"].append(player)
        await self.send_gamestate(i, player)
        await self.broadcast_game_info(i)
        return player
    async def broadcast_move(self, game_id):
        l = self.games[game_id]["players"].copy()
        for player in l:
            await self.send_gamestate(game_id, player)
    async def broadcast_game_info(self, game_id):
        l = self.games[game_id]["players"].copy()
        for player in l:
            await send(player["client"],{"action":"game_info", **self.get_game_info(game_id)})
    async def send_gamestate(self, game_id, player):
        try:
            await send(player["client"],{"action":"move","state":self.games[game_id]["game"].get_state(player["team"])})
        except:
            print(traceback.format_exc(),flush=True)
            self.games[game_id]["players"].remove(player)
            server.broadcast_game_info(game_id)
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
        
    def __init__(self):
        self.games = {}

    async def serve(self, ip="localhost"):
        server = await asyncio.start_server(self.a, host=ip, port=9974)
        self.next_game_id = 0
        print("server listening",flush=True)
        try:
            async with server:
                await server.serve_forever()
        finally:
            with open("continuous_games.txt") as f:
                f.write(json.dumps(self.games, lambda o: o.get_state()))

    def makeHandler(self):
        s = self
        class MoveHandler(socketserver.StreamRequestHandler):
            def handle(self):
                try:
                    s.a(self)
                except Exception as e:
                    print(traceback.format_exc())
                    print(e,flush=True)
        return MoveHandler

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
                    server.broadcast_game_info(game_id)
                return
            if r["action"] == "create":
                server.create_game(r["name"], r["id"], r["args"])
            elif r["action"] == "join":
                if game_id != None:
                    server.games[game_id]["players"].remove(player)
                game_id = r["id"]
                player = await server.join_game(game_id,r["team"],r["user"],client)
            elif r["action"] == "move":
                if r["move"]["player"] != player["team"]:
                    print("trying to move for the wrong team",flush=True)
                    continue
                if server.games[game_id]["game"].attemptMove(r["move"]):
                    print("successfully applied move to gamestate",flush=True)
                    await server.broadcast_move(game_id)
                else:
                    print("move was illegal",flush=True)
            elif r["action"] == "list":
                await send(client, server.list_games())


async def send(client, message):
    client[1].write((json.dumps(message)+"\n").encode())
    await client[1].drain()
async def recieve(client):
    return json.loads((await client[0].readline()).strip())
        
if __name__ == "__main__":
    asyncio.run(NetworkGameServer().serve(ip="localhost" if len(sys.argv)==1 else sys.argv[1]))
