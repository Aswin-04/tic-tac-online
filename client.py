import socket
import pickle 

HEADER_SIZE = 10

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

def get_choice(client_sock: socket.socket, data: dict):
      choice = int(input(data["prompt"]))
      print()
      choice_obj = pickle.dumps({"choice": choice})
      choice_obj = get_bytes(choice_obj)
      client_sock.sendall(choice_obj)

def main(): 
  
  client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  client_sock.connect(("localhost", 5000))


  while True:

    buff_len = recvall(client_sock, HEADER_SIZE)
    data = recvall(client_sock, int(buff_len))
    data = pickle.loads(data)

    if data["type"] == "name":
      name = input(data["prompt"])
      name_obj = pickle.dumps({"name": name})
      name_obj = get_bytes(name_obj)
      client_sock.sendall(name_obj)
      print()

    if data["type"] == "board":
      size = data["size"]
      print("="*(size*5) + data["board"] + "="*(size*5) + "\n")

    if data["type"] == "result":
      print(data["message"])
      break

    if data["type"] == "choice":
      get_choice(client_sock, data)

    if data["type"] == "info":
      print(data["prompt"])
      print()

    if data["type"] == "error":
      print(data["message"])
      get_choice(client_sock, data)

    if data["type"] == "player":
      print(data["player"])

if __name__ == "__main__":
  main()
