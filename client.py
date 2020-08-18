import continuousEngine
import pygame
import threading
import socket
import json
import chess
import sys
import traceback
class NetworkGame:
    """
    represents the client side of a game connected to a server.
    This is a wrapper for a continuousEngine.Game object
    the continuousEngine.Game object must defined attempt_move, load_state
    The client can be in two states: live or offline.
    In offline mode, the game works exactly as if you were not connected
    In live mode, loading state is disabled, and the game tracks the server's state. 
    Attempting to make a move results in it being sent to the server; no change is made to your local gamestate.
    
    """
    def __init__(self,game):
        self.game = game
        self.server=None
        self.live_mode = 0
        self.server_state = {}
        self.lock = threading.RLock()
        self.game.keyPress[pygame.K_n] = lambda e:(setattr(self,"live_mode",1-self.live_mode), self.update_to_server_state() if self.live_mode else 0) if self.server!=None else 0
        self.game.handle = self.handle
        self.f = self.game.attemptMove
        self.game.attemptMove = self.attemptMove

    def join(self,server,i,team,user):
        """
        server is a tcp socket that you've already connected to that is a continuous games server.
        """
        d = {
            "action":"join",
            "user":user,
            "id":i,
            "team":team
            }
        self.live_mode = 1
        self.server=server
        send(server,d)
        print("joined game {} as user {} on team {}".format(i, user, team))
        threading.Thread(target=self.server_listener, daemon=True).start()
        #threading.Thread(target=(lambda :print("hi",flush=True))).start()
        print("started server listening thread",flush=True)

    def handle(self, event):
        if event.type in self.game.handlers:
            with self.lock:
                self.game.handlers[event.type](event)

    def update_to_server_state(self):
        with self.lock:
            self.game.load_state(self.server_state)
        self.game.render()
            
    def server_listener(self):
        while True:
            try:
                print("listening for gamestate",flush=True)
                s = recieve(self.server)
                if not s or s["action"]!="move":
                    print(str(s),flush = True)
                else:
                    print("recieved gamestate",flush=True)
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
            print("move sent",flush=True)
        else:
            self.f(m)

def send(socket, m):
    #socket.sendall((json.dumps(m)+"\n").encode())
    socket.makefile(mode="w").write((json.dumps(m)+"\n"))
def recieve(socket):
    return json.loads(socket.makefile(mode="r").readline().strip())
ip = "localhost"
port = 9999
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((ip,port))
print("connected to {}".format(ip))
#s.rfile = s.makefile(mode="r")
#s.wfile = s.makefile(mode="w")
joined=False
while not joined:
    send(s,{"action":"list"})
    games = recieve(s)
    print("listing games")
    print(games,flush=True)
    for i in games:
        available_colors = [x for x in ["white","black"] if x not in [p["team"] for p in games[i]["players"]]]
        if available_colors:
            g = chess.Chess()
            NetworkGame(g.game).join(s,i,available_colors[0],"brunnerj")
            #threading.Thread(target = g.game.run).start()
            g.game.run()
            joined=True
    if not joined:
        d = {
            "action":"create",
            "name":"chess"
        }
        send(s,d)

        


