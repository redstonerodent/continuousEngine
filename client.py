# usage (see initial_script):
# python client.py game [game_id [team [username [ip]]]]

import continuousEngine
import pygame
import threading
import socket
import json
import chess, reversi, go, jrap
import sys
import traceback
import asyncio

games = {
    'chess'     : chess.Chess,
    'reversi'   : reversi.Reversi,
    'go'        : go.Go,
    'jrap'      : jrap.Jrap,
    }

port = 9974

class NetworkGame:
    """
    represents the client side of a game connected to a server.
    This is a wrapper for a continuousEngine.Game object
    the continuousEngine.Game object must define attempt_move, load_state
    The client can be in two states: live or offline.
    In offline mode, the game works exactly as if you were not connected
    In live mode, loading state is disabled, and the game tracks the server's state. 
    Attempting to make a move results in it being sent to the server; no change is made to your local gamestate.
    
    """
    def __init__(self,game):
        self.game = game
        self.server = None
        self.live_mode = False
        self.server_state = {}
        self.server_history = []
        self.game.handlers[pygame.USEREVENT] = lambda e: (
            self.game.load_state(e.state),
            self.server_history.append(e.state),
            setattr(self.game, 'history', self.server_history[:-1]),
            setattr(self.game, 'future', []),
            )
        self.game.keyPress[pygame.K_n] = lambda e:(setattr(self,"live_mode", not self.live_mode), self.update_to_server_state() if self.live_mode else None) if self.server!=None else None
        
        if game.allow_skip:
            pass
        else:
            # exit live mode when skipping
            self.game.keyPress[self.game.keys.skipTurn] = (lambda f: lambda e: (f(e), setattr(self, 'live_mode', False)))(self.game.keyPress[self.game.keys.skipTurn])

        # viewing history exits live mode
        self.game.keyPress[self.game.keys.undo] = (lambda f: lambda e: (f(e), setattr(self, 'live_mode', False)))(self.game.keyPress[self.game.keys.undo])
        self.game.keyPress[self.game.keys.redo] = (lambda f: lambda e: (f(e), setattr(self, 'live_mode', False)))(self.game.keyPress[self.game.keys.redo])
        self.game.keyPress[self.game.keys.resetGame] = (lambda f: lambda e: (f(e), setattr(self, 'live_mode', False)))(self.game.keyPress[self.game.keys.resetGame])


        self.f = self.game.attemptMove
        self.game.attemptMove = self.attemptMove

        continuousEngine.ScreenBorder(game, 10**10, (100,100,100), 7).GETvisible = lambda _: not self.live_mode

    async def join(self,server,i,team,user):
        """
        server is a tcp socket that you've already connected to that is a continuous games server.
        server is actually a tuple (reader, writer) returned from asyncio.open_connection
        """
        d = {
            "action":"join",
            "user":user,
            "id":i,
            "team":team
            }
        self.live_mode = True
        self.server=server
        send(server,d)
        print("joined game {} as user {} on team {}".format(i, user, team))
        print("started server listening thread",flush=True)
        a = asyncio.get_running_loop().run_in_executor(None, self.game.run)
        await asyncio.gather(self.server_listener(), a)
        #threading.Thread(target=(lambda :print("hi",flush=True))).start()
#    def handle(self, event):
#        if event.type in self.game.handlers:
#            with self.lock:
#                self.game.handlers[event.type](event)

    def update_to_server_state(self):
        if not self.server_state:
            return
        #with self.lock:
            #self.game.load_state(self.server_state)
        pygame.event.post(pygame.event.Event(pygame.USEREVENT, state=self.server_state))
            
    async def server_listener(self):
        while True:
            try:
                print("listening for gamestate",flush=True)
                s = await receive(self.server)
                if not s or s["action"]!="move":
                    print(str(s),flush = True)
                else:
                    print("received gamestate",flush=True)
                    self.server_state = s["state"]
                    if self.live_mode:
                        self.update_to_server_state()
            except Exception as e:
                print(traceback.format_exc(),flush=True)
                sys.exit()
                


    def attemptMove(self, m):
        """
        in offline mode, simply calls attempt_move
        if connected to a game, it sends the move to the server.
        """
        d = {"action":"move", "move":m}
        if self.live_mode:
            print("sending move to server")
            print(d,flush=True)
            try:
                send(self.server,d)
            except:
                print(traceback.format_exc(),flush=True)
        else:
            self.f(m)

def send(server, m):
    #server.sendall((json.dumps(m)+"\n").encode())
    #server.makefile(mode="w").write((json.dumps(m)+"\n"))
    server[1].write((json.dumps(m)+"\n").encode())
    #asyncio.get_event_loop().create_task(server[1].drain())
    #asyncio.create_task(server[1].drain())
    #await server[1].drain()

async def receive(server):
    return json.loads((await server[0].readline()).strip())
    #return json.loads(server.makefile(mode="r").readline().strip())

async def initial_script(_, game, ip='localhost', game_id=None, team=None, username='anonymous'):
    # ip = "localhost" if len(sys.argv)==1 else sys.argv[1]
    #s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #s.connect((ip,port))
    s = await asyncio.open_connection(host=ip, port=port)

    print("connected to {}".format(ip))

    send(s, {"action":"list"})
    ids = await receive(s)
    print("listing games")
    print(ids,flush=True)

    async def attempt_joining(id):
        if team != None:
            if team not in ids[id]["open teams"]:
                print("team {} doesn't exist".format(team), flush=True)
                sys.exit()

            if team not in [x["team"] for x in ids[id]["players"]]:
                await NetworkGame(await asyncio.get_running_loop().run_in_executor(None, games[game])).join(s, id, team, username)
            else:
                print('{} is already taken in game {}'.format(team, id), flush=True)
        else:
            available_colors = [x for x in ids[id]["open teams"] if x not in [p["team"] for p in ids[id]["players"]]]

            if available_colors:
                await NetworkGame(await asyncio.get_running_loop().run_in_executor(None, games[game])).join(s,id,available_colors[0], username)
            else:
                print('{} is full'.format(id), flush=True)

    if game_id == None:
        for i in ids:
            if ids[i]["type"]==game:
                await attempt_joining(i)
        print('no available game found. make a new one by specifying an id.', flush=True)
        sys.exit()


    if game_id not in ids:
        send(s, {"action":"create", "name":game, "id":game_id})
        send(s, {"action":"list"})
        ids = await receive(s)

    if ids[game_id]["type"] != game:
        print('{} is a game of {}, not {}'.format(game_id, ids[game_id]["type"], game), flush=True)
        sys.exit()

    await attempt_joining(game_id)


asyncio.run(initial_script(*sys.argv))

            
        


