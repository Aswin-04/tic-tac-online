import socket
import pickle

HEADER_SIZE = 10

class Player:
  def __init__(self, id: int, name: str, sign: str, socket: socket.socket, addr: str):
    self.id = id
    self.name = name
    self.sign = sign 
    self.sock = socket
    self.addr = addr

  def get_id(self): return self.id
  def get_name(self): return self.name
  def get_sign(self): return self.sign 
  def get_sock(self): return self.sock
  def get_addr(self): return self.addr
  def to_obj(self):
    return {
      "id": self.id,
      "name": self.name,
      "sign": self.sign
    }

class Game: 
  def __init__(self, player1: Player, player2: Player, size: int):
    self.player1 = player1
    self.player2 = player2 
    self.current_player = player1
    self.size = size 
    self.moves_made = 0
    self.board = [["-" for _ in range(size)] for _ in range(size)]
  
  def check_for_win(self):
    sign = self.current_player.sign

    for i in range(self.size):
      if all(self.board[i][j] == sign for j in range(self.size)): return True # row check
      if all(self.board[j][i] == sign for j in range(self.size)): return True # col check

    # diagonal check
    if all(self.board[i][i] == sign for i in range(self.size)): return True 
    if all(self.board[i][self.size-i-1] == sign for i in range(self.size)): return True 

    return False
  
  def check_for_tie(self):
    return self.moves_made >= self.size*self.size
  
  def switch_player_turn(self):
    if self.current_player == self.player1:
      self.current_player = self.player2 
    else: 
      self.current_player = self.player1

  def get_cur_player(self): return self.current_player

  def get_board_str(self):
    board_str = "\n"
    for row in range(self.size):
      for col in range(self.size):
        board_str+=f" {self.board[row][col]} "
        if col != self.size-1:
          board_str+="|"
      board_str+="\n"
      if row != self.size-1:
        board_str+=f"{'-'*self.size*4}"
      board_str+="\n"

    return board_str[:-1]
  
  def update_cell(self, choice):
    idx = choice-1
    row, col = divmod(idx, self.size)
    self.board[row][col] = self.current_player.get_sign()
    self.moves_made+=1

  def is_valid(self, choice: int):
    if choice < 1 or choice > self.size*self.size:
      return False

    row, col = divmod(choice-1, self.size)
    return self.board[row][col] == "-"


def recvall(sock: socket.socket, buff_len: int):

  buff = b""

  while len(buff) < buff_len:
    chunk = sock.recv(buff_len-len(buff))
    if not chunk:
      raise ConnectionError("Socket closed")
    buff+=chunk 

  return buff

def get_bytes(obj: bytes):
  return bytes(f"{len(obj):<{HEADER_SIZE}}", "utf-8") + obj

def main():
  PORT = 5000
  server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  server_sock.bind(("0.0.0.0", PORT))
  server_sock.listen(1)

  print(f'server is ready... running on addr: {server_sock.getsockname()[0]} port: {PORT}.\n')

  game_players: list[Player] = []
  while len(game_players) < 2:
    client_sock, addr = server_sock.accept()
    id = len(game_players)+1
    sign = "X" if id&1 else "O"

    name_obj = pickle.dumps({
      "type": "name",
      "prompt": f"Enter player {id} name: "
    })
    name_obj = get_bytes(name_obj)
    client_sock.sendall(name_obj)

    name_len = int(recvall(client_sock, HEADER_SIZE))
    name = pickle.loads(recvall(client_sock, name_len))["name"]

    player = Player(id, name, sign, client_sock, addr)
    game_players.append(player)
    print(f"{player.get_name()} connected with addr {player.get_addr()}")

    player_obj = pickle.dumps({
      "type": "player",
      "player": player.to_obj()
    })
    player_obj = get_bytes(player_obj)
    client_sock.sendall(player_obj)


  size = int(input("Enter the board size: "))
  
  player1, player2 = game_players
  game_controller = Game(player1, player2, size)

  board_obj = pickle.dumps({
    "type": "board",
    "board": game_controller.get_board_str(),
    "size": game_controller.size
  })
  for player in game_players:
    player.get_sock().sendall(get_bytes(board_obj))

  while True:
    cur_player: Player = game_controller.get_cur_player()
    idle_player: Player = [player for player in game_players if player != cur_player][0]

    cur_player_sock = cur_player.get_sock()
    idle_player_sock = idle_player.get_sock()

    cur_player_prompt_obj = pickle.dumps({
      "type": "choice",
      "prompt": f"{cur_player.get_name()}'s turn\nChoose (1-{size*size}): ",
    })

    idle_player_prompt_obj = pickle.dumps({
      "type": "info",
      "prompt": f"waiting for {cur_player.get_name()}'s move..",
    })

    cur_player_prompt_obj = get_bytes(cur_player_prompt_obj)
    idle_player_prompt_obj = get_bytes(idle_player_prompt_obj)

    cur_player_sock.sendall(cur_player_prompt_obj)
    idle_player_sock.sendall(idle_player_prompt_obj)
    

    while True:
      choice_len = int(recvall(cur_player_sock, HEADER_SIZE))
      choice = pickle.loads(recvall(cur_player_sock, choice_len))["choice"]
      
      if game_controller.is_valid(choice):
        game_controller.update_cell(choice)
        break 

      else:
        err_obj = pickle.dumps({
          "type": "error",
          "prompt": f"{cur_player.get_name()}'s turn\nChoose (1-{size*size}): ",
          "message": "invalid choice, please enter a valid choice\n"
        })
        cur_player_sock.sendall(get_bytes(err_obj))
        continue 
        
    board_obj = pickle.dumps({
      "type": "board",
      "board": game_controller.get_board_str(),
      "size": game_controller.size 
    })
    for player in game_players:
      player.get_sock().sendall(get_bytes(board_obj))

    has_won = game_controller.check_for_win()
    is_tie = game_controller.check_for_tie()
    result_obj = {"type": "result"}

    if has_won:
      result_obj["message"] = f"{cur_player.get_name()} won the game!!"
    
    if is_tie:
      result_obj["message"] = f"damn, it's a tie.."

    result_obj = pickle.dumps(result_obj)
    if has_won or is_tie:
      for player in game_players:
        player.get_sock().sendall(get_bytes(result_obj))

      server_sock.close()
      print("Game over\n")
      return 

    game_controller.switch_player_turn()
    
if __name__ == "__main__":
  main()

