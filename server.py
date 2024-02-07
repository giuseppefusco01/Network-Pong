import socket
import threading
from queue import Queue

server_IP = "127.0.0.1"
server_port = 5005

socket_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
socket_server.bind((server_IP, server_port))

# Dizionario per mantenere traccia degli IP degli utenti
players = {}

# Coda per memorizzare le posizioni delle racchette dagli utenti con l'IP del giocatore che riceverà la posizione
positions_queue = Queue()


# Coda per memorizzare la posizione della pallina con l'IP del giocatore che riceverà la posizione
ball_queue = Queue()


# Funzione per la ricezione dei dati dagli utenti
def handle_client():
    while True:
        try:
            data, client_address = socket_server.recvfrom(1024)
            position = data.decode()        # Position è il contenuto del messaggio inviato dal client,
                                            # può essere un messaggio di reset (segnalare all'avversario un punto segnato), passo (segnalare all'avversario il suo turno di controllo della pallina), la posizione della pallina (il messagio inizia con "ball") o la posizione della racchetta

            # Se l'IP del mittente non è nel dizionario, lo aggiunge
            if client_address not in players:
                players[client_address] = position
                print(f"Nuovo client connesso {client_address}")

            # Se il messaggio inviato dal client inizia con la parola "reset" il server invia il segnale di reset al client avversario (il giocatore che ha inviato il comando di reset ha segnato un punto)
            if position.startswith("reset"):
                opponents = [ip for ip in players.keys() if ip != client_address]       # Recupero l'IP dell'avversario
                reset_players(opponents[0])         # Invio il comando di reset all'avversario attraverso la funzione reset_players


            # Se il messaggio inviato dal client inizia con la parola "passo" il server invia il segnale di passo al client avversario (il giocatore che ha inviato il comando comunica all'avversario di prendere il controllo della pallina)
            elif position.startswith("passo"):
                opponents = [ip for ip in players.keys() if ip != client_address]       # Recupero l'IP dell'avversario
                next_players(opponents[0])         # Invio il comando di passo all'avversario attraverso la funzione next_players

            else:       # Il messaggio ricevuto dal client contiene la posizione della racchetta o della pallina

                # Se il messaggio inizia con "ball" contiene le componenti X ed Y della posizione della pallina
                if position.startswith("ball"):
                    # Divisione sulla base dello spazio per ottenere ["ball", "x", "y"]
                    ball_data = position.split(" ")
                    ball_x = int(ball_data[1])      # Componente X della pallina
                    ball_y = int(ball_data[2])      # Componente Y della pallina

                    opponents = [ip for ip in players.keys() if ip != client_address]       # Recupero l'IP dell'avversario
                    if opponents:           # Se è presente l'avversario
                        opponent_address = opponents[0]
                        ball_queue.put(((ball_x, ball_y), opponent_address))    # Inserisco nella coda della pallina la posizione della pallina con l'IP del giocatore avversario (non ha il controllo della pallina, riceve la posizione della pallina dall'avversario)

                else:       # Il messaggio contiene la posizione della racchetta
                    player_position = float(position)   # Posizione della racchetta
                    opponents = [ip for ip in players.keys() if ip != client_address]       # Recupero l'IP dell'avversario
                    if opponents:           # Se è presente l'avversario
                        opponent_address = opponents[0]

                        # Aggiungi la posizione alla coda delle racchette
                        positions_queue.put((player_position, opponent_address))    # Inserisco nella coda delle posizioni la posizione della racchetta con l'IP del giocatore avversario
                    else:
                        print("Non ci sono avversari collegati")

        except (socket.error, ValueError) as e:
            print(f"Errore nella gestione del client {client_address}: {e}, ultimo pacchetto ricevuto: {position}")
            break  # Il client si è disconnesso, interrompi il loop

    # Giocatore disconnesso
    print(f"Client {client_address} disconnesso.")
    del players[client_address]


# Funzione per inviare le posizioni ai giocatori
def send_positions():
    while True:
        # Invia la posizione delle racchette
        if not positions_queue.empty():     # Se la coda delle posizioni delle racchette non è vuota
            position, target_address = positions_queue.get()    # Recupera la posizione
            positions_queue.task_done()
            # Invia la posizione all'IP del giocatore opposto
            try:
                socket_server.sendto(str(position).encode(), target_address)     # Invia la posizione all'avversario
            except socket.error as e:
                print(f"Errore nell'invio al giocatore avversario: {e}")

        # Invia la posizione della pallina
        if not ball_queue.empty():     # Se la coda della posizione della pallina non è vuota
            ball_position, ball_target_address = ball_queue.get()
            ball_queue.task_done()
            try:
                socket_server.sendto(str(ball_position).encode(), ball_target_address)     # Invia la posizione all'avversario
            except socket.error as e:
                print(f"Errore nell'invio della posizione della pallina a {ball_target_address}: {e}")


# Funzione per inviare il comando di reset al giocatore avversario (il giocatore che ha subito un punto)
def reset_players(ip_to_reset):     # ip_to_reset è l'ip del giocatore che deve ricevere il comando di reset
    socket_server.sendto(str("reset").encode(), ip_to_reset)     #se il giocatore riceve questo l'avversario ha segnato e il giocatore cede il controllo (se per sbaglio lo ha preso)
    ball_queue.queue.clear()    # Svuoto la coda della pallina


def next_players(next_ip):     # next_ip è l'ip del giocatore che deve ricevere il comando di passo
    socket_server.sendto(str("passo").encode(), next_ip)     #se il giocatore riceve questo prende il controllo della pallina
    ball_queue.queue.clear()    # Svuoto la coda della pallina


# Thread per la gestione dei client
client_thread = threading.Thread(target=handle_client, daemon=True)
client_thread.start()


# Thread per l'invio delle posizioni
send_thread = threading.Thread(target=send_positions, daemon=True)
send_thread.start()


while True:
    pass  # Loop principale del server