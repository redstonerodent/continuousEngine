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
import argparse
import random, string

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
        self.players = {t:[] for t in game.teams+['spectator']}
        self.id = ''
        self.user = ''
        self.game.handlers[pygame.USEREVENT] = lambda e: (
            self.game.load_state(e.state),
            setattr(self.game, 'history', self.server_history[:-1]),
            setattr(self.game, 'future', []),
            ) if e.action=='state' else None
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

        font = pygame.font.Font(pygame.font.match_font('ubuntu-mono'),24)
        class GameInfo(continuousEngine.Renderable):
            def render(_):
                vals = {'id':self.id, 'turn':self.game.turn, 'you':self.user, 'live':self.live_mode}
                for i,k in enumerate(vals):
                    continuousEngine.write(game.screen, font, '{}: {}'.format(k, vals[k]), 24, 24*(i+1), (0,0,0), halign='l', valign='t')

                d = len(vals)+2
                for i,t in enumerate(game.teams+['spectator']):
                    continuousEngine.write(game.screen, font, '{}: {}'.format(t, ', '.join(self.players[t])), 24, 24*(i+d), (0,0,0), halign='l', valign='t')
        GameInfo(game, 10**10)

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
        self.id = i
        self.user = user
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
        pygame.event.post(pygame.event.Event(pygame.USEREVENT, action='state', state=self.server_state))
            
    async def server_listener(self):
        while True:
            try:
                print("listening for gamestate",flush=True)
                s = await receive(self.server)
                if not s:
                    continue
                elif s["action"]=="move":
                    print("received gamestate",flush=True)
                    self.server_state = s["state"]
                    if self.live_mode:
                        self.server_history.append(self.server_state)
                        self.update_to_server_state()
                elif s["action"]=="game_info":
                    print("received game info",flush=True)
                    self.players = {t:[] for t in self.game.teams+['spectator']}
                    for pl in s["players"]:
                        self.players[pl["team"]].append(pl["user"])
                    pygame.event.post(pygame.event.Event(pygame.USEREVENT, action='info'))
                elif s["action"]=="history":
                    print("received history")
                    self.server_history = s["history"]
                else:
                    print(str(s),flush = True)
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

async def initial_script(ip, game, game_id, team, username, new, args):

    s = await asyncio.open_connection(host=ip, port=port)

    print("connected to {}".format(ip))

    send(s, {"action":"list"})
    ids = await receive(s)
    print("listing ids")
    print(ids,flush=True)

    async def attempt_joining(id, t):
        await NetworkGame(await asyncio.get_running_loop().run_in_executor(None, games[game], *args)).join(s, id, t, username)


    if game_id:
        if new and game_id in ids:
            print('{} already exists'.format(game_id), flush=True)
            sys.exit()

        while game_id not in ids:
            send(s, {"action":"create", "name":game, "id":game_id, "args":args})
            send(s, {"action":"list"})
            ids = await receive(s)

        if ids[game_id]["type"] != game:
            print('{} is a game of {}, not {}'.format(game_id, ids[game_id]["type"], game), flush=True)
            sys.exit()

        if team:
            if team not in ids[game_id]["open teams"]+["spectator"]:
                print("team {} doesn't exist or is already taken in {}".format(team, game_id), flush=True)
                sys.exit()
            await attempt_joining(game_id, team)

        else:
            await attempt_joining(game_id, (ids[game_id]["open teams"]+["spectator"])[0])

    else:
        joined = False
        if not new:
            if team:
                for i in ids:
                    if ids[i]["type"] == game and team in ids[i]["open teams"]+["spectator"]:
                        await attempt_joining(i, team)
                        joined = True
            else:
                for i in ids:
                    if ids[i]["type"] == game and ids[i]["open teams"]:
                        await attempt_joining(i, ids[i]["open teams"][0])
                        joined = True
        if not joined:
            id = None
            while id==None or id in ids:
                id = ''.join(random.choice(string.ascii_lowercase) for _ in range(5))
            send(s, {"action":"create", "name":game, "id":id, "args":args})
            send(s, {"action":"list"})
            ids = await receive(s)
            if team:
                if team not in ids[id]["open teams"]+["spectator"]:
                    print("team {} doesn't exist or is already taken in {}".format(team, id), flush=True)
                    sys.exit()
                await attempt_joining(id, team)
            else:
                await attempt_joining(id, (ids[id]["open teams"])[0])



parser = argparse.ArgumentParser(prog='python client.py')
parser.add_argument('-g','--game', required=True, choices=list(games))
parser.add_argument('-ip', default='localhost')
parser.add_argument('-id', '--game_id')
parser.add_argument('-t', '--team')
parser.add_argument('-u', '--username', default='anonymous')
parser.add_argument('-n', '--new', action='store_true', default=False)
parser.add_argument('args', nargs=argparse.REMAINDER, help=argparse.SUPPRESS)


asyncio.run(initial_script(**vars(parser.parse_args())))

