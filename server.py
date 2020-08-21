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
    attempt_move
    get_state
"""
   

import socketserver
import threading
import chess
import json
import traceback
import sys
class NetworkGameServer:
    def create_game(self, name):
        with self.server_lock:
            new_id = min(range(10000),key=(lambda i:i not in self.games))
            game = chess.Chess(headless=True).game 
            self.games[new_id] = {
                "type":name,
                "players":[],
                "lock":threading.RLock(),
                "game":game
            }
        return new_id
    def join_game(self, i,team, user, client):
        if i not in self.games:
            raise Exception("game id doesn't exist")
        with self.games[i]["lock"]:
            player = {"user":user, "team":team, "client":client}
            self.games[i]["players"].append(player)
            self.send_gamestate(i, player)
        return player
    def broadcast_move(self, game_id):
        with self.games[game_id]["lock"]:
            l = self.games[game_id]["players"].copy()
            for player in l:
                self.send_gamestate(game_id,  player)
    def send_gamestate(self, game_id, player):
        try:
            player["client"].wfile.write((json.dumps({"action":"move","state":self.games[game_id]["game"].get_state(player["team"])})+"\n").encode())
        except:
            print(traceback.format_exc(),flush=True)
            self.games[game_id]["players"].remove(player)
    def list_games(self):
        result = {}
        for i in self.games:
            result[i] = self.games[i].copy()
            pl = [p.copy() for p in self.games[i]["players"]]
            result[i]["players"] = pl
            for p in pl:
                del p["client"]
            del result[i]["lock"]
            del result[i]["game"]
        print(result,flush=True)
        return result
        
    def __init__(self,ip="localhost"):
        self.games = {}
        self.server_lock = threading.RLock()
        with ThreadedTCPServer((ip,9999), self.makeHandler()) as server:
            print("server listening",flush=True)
            server.serve_forever()

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

    def a(self,client):
        print("connected",flush=True)
        game_id = -1
        player = None
        server = self
        while True:
            try:
                r = json.loads(client.rfile.readline().strip())
            except:
                if game_id != -1:
                    with server.games[game_id]["lock"]:
                        server.games[game_id]["players"].remove(player)
                return
            if r["action"] == "create":
                server.create_game(r["name"])
            elif r["action"] == "join":
                if game_id != -1:
                    with server.games[game_id]["lock"]:
                        server.games[game_id]["players"].remove(player)
                i = int(r["id"])
                player = server.join_game(i,r["team"],r["user"],client)
                game_id = i
            elif r["action"] == "move":
                if r["move"]["player"] != player["team"]:
                    print("trying to move for the wrong team",flush=True)
                    continue
                if server.games[game_id]["game"].attemptMove(r["move"]):
                    print("successfully applied move to gamestate",flush=True)
                    server.broadcast_move(game_id)
                else:
                    print("move was illegal",flush=True)
            elif r["action"] == "list":
                client.wfile.write((json.dumps(server.list_games())+"\n").encode())

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

        
if __name__ == "__main__":
    server = NetworkGameServer(ip="localhost" if len(sys.argv)==1 else sys.argv[1])
