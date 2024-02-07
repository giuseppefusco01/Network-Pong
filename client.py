import turtle       # Libreria grafica
import socket
import time
import threading
from queue import Queue
import sys          # Importa il modulo sys per accedere agli argomenti della riga di comando


server_IP = "127.0.0.1"
server_port = 5005
socket_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP


player = 0      # Valore 0 io gioco a sinistra, valore 1 io gioco a destra
ball_control = True  # Variabile per il controllo della pallina, se True la pallina la controllo io, se False la controlla l'avversario


if len(sys.argv) > 1:
    valore = int(sys.argv[1])
    if valore == 0:
        player = 0
        ball_control = True  # Variabile per il controllo della pallina, se True la pallina la controllo io, se False la controlla l'avversario
    else:
        player = 1
        ball_control = False  # Variabile per il controllo della pallina, se True la pallina la controllo io, se False la controlla l'avversario


score_player0 = 0       # Punteggio del giocatore sx
score_player1 = 0       # Punteggio del giocatore dx

avv_pad_queue = Queue()     # Coda della posizione della racchetta avversaria

ball_queue = Queue()        # Coda della posizione della pallina


last_received_position = None  # Variabile con l ultima posizione ricevuta dalla racchetta avversaria

# Finestra di gioco
sc = turtle.Screen()
sc.title("Pong")
sc.bgcolor("black")
sc.setup(width=1000, height=600)

# Linea tratteggiata di metà campo
line_turtle = turtle.Turtle()
line_turtle.speed(0)
line_turtle.color("white")
line_turtle.penup()
line_turtle.hideturtle()
line_turtle.goto(0, -300)
line_turtle.setheading(90)
for _ in range(30):
    line_turtle.pendown()
    line_turtle.forward(20)  # Lunghezza del tratteggio
    line_turtle.penup()
    line_turtle.forward(10)  # Spazio tra i tratteggi

# Racchetta sinistra
left_pad = turtle.Turtle()
left_pad.speed(0)
left_pad.shape("square")
left_pad.color("white")
left_pad.shapesize(stretch_wid=6, stretch_len=2)
left_pad.penup()
left_pad.goto(-400, 0)

# Racchetta destra
right_pad = turtle.Turtle()
right_pad.speed(0)
right_pad.shape("square")
right_pad.color("white")
right_pad.shapesize(stretch_wid=6, stretch_len=2)
right_pad.penup()
right_pad.goto(400, 0)

# Pallina
ball = turtle.Turtle()
ball.speed(2)
ball.shape("circle")
ball.color("white")
ball.penup()
ball.goto(0, 0)
ball.dx = 3 if player == 0 else -3  # Initial ball movement direction
ball.dy = 3

# Punteggi giocatori
score_display = turtle.Turtle()
score_display.speed(0)
score_display.color("white")
score_display.penup()
score_display.hideturtle()
score_display.goto(0, 260)
score_display.write("Giocatore 1: 0   Giocatore 2: 0", align="center", font=("Courier", 24, "normal"))

score_display.write(f"Giocatore 1: {score_player0}   Giocatore 2: {score_player1}", align="center", font=("Courier", 24, "normal"))     # Scrivo il punteggio appena avvio la partita

# Seleziona il giocatore dalla linea di comando
if (player == 0):
    mypad = left_pad
    avv_pad = right_pad
else:
    mypad = right_pad
    avv_pad = left_pad


# Funzioni per muovere la racchetta
def paddle_up():
    y = mypad.ycor()
    y += 20
    mypad.sety(y)


def paddle_down():
    y = mypad.ycor()
    y -= 20
    mypad.sety(y)


# Mappatura delle frecce della tastiera per muovere la racchetta
sc.listen()
sc.onkeypress(paddle_up, "Up")
sc.onkeypress(paddle_down, "Down")


# Funzione per inviare la posizione della racchetta e della pallina (se ho io il controllo della pallina)
def send_position():
    global ball_control
    while True:
        position = mypad.ycor()
        position_bytes = str(position).encode()

        try:
            socket_client.sendto(position_bytes, (server_IP, server_port))      # Invio la posizione codificata al server
        except socket.error as e:
            print(f"Errore nell'invio: {e}")

        if(ball_control == True):       # Se ho il controllo della pallina invio la posizione all'avversario
            ball_position_str = f"ball {int(ball.xcor())} {int(ball.ycor())}"
            socket_client.sendto(ball_position_str.encode(), (server_IP, server_port))

        time.sleep(0.15)        # Aggiungi una piccola pausa prima di inviare di nuovo


# Funzione per la ricezione della posizione della racchetta avversaria e della pallina
def receive_position():
    global ball_control
    global score_player0, score_player1
    while True:
        data, addr = socket_client.recvfrom(1024)        # Ricevo il pacchetto dal server
        position = data.decode()

        # Rimuovo parentesi dalla stringa
        position = position.strip('()')

        # Split sulla base della virgola per ottenere ["x", "y"]
        position_data = position.split(", ")

        # Se la stringa ricevuta dal server ha solo una componente diversa dal testo "reset" o "passo" il dato ricevuto è il valore float corrispondente alla posizione della racchetta avversaria
        if len(position_data) == 1 and not position_data[0]==("reset") and not position_data[0]==("passo") :
            avv_pad_queue.put(float(position))     # Inserisco la posizione della racchetta avversaria nella coda delle posizioni della racchetta avversaria

        # Se la stringa ricevuta dal server ha due componenti e non contiene testo il dato ricevuto sono le coordinate X ed Y della pallina
        elif len(position_data) == 2 and not position_data[0]==("reset") and not position_data[0]==("passo") :
            ball_x = int(position_data[0])      # Coordinata X della pallina
            ball_y = int(position_data[1])      # Coordinata Y della pallina
            ball_queue.put((ball_x, ball_y))      # Inserisco la posizione della pallina nella coda delle posizioni della pallina

        # La stringa ricevuta dal server ha il testo "reset": l'avversario ha segnato un punto ed io cedo il controllo della pallina (se l'ho preso per errore)
        elif position_data[0] == ("reset"):
            ball_control = False
            ball.goto(0, 0)

            if player == 0:       # Incremento il punteggio del giocatore che ha segnato
                score_player1 += 1
            else:
                score_player0 += 1
            score_display.clear()       # Pulisco il punteggio precedentemente scritto
            score_display.write(f"Giocatore 1: {score_player0}   Giocatore 2: {score_player1}", align="center", font=("Courier", 24, "normal"))     # Scrivo il punteggio aggiornato
            check_win()     # Controlla se un giocatore è arrivato a 10 punti

        # La stringa ricevuta dal server contiene la parola "passo", la pallina è stata toccata correttamente da me e l'avversario mi cede il controllo
        elif position_data[0] == ("passo"):
            ball_control = True         # Assumo il controllo della pallina
            ball_queue.queue.clear()    # Svuoto la coda della pallina (ora ho il controllo della pallina, elimino eventuali posizioni rimaste)


# Funzione per aggiornare la posizione della racchetta avversaria
def update_opponent_paddle():
    global last_received_position

    if not avv_pad_queue.empty():
        avv_pad_position = avv_pad_queue.get()         # Prelevo dalla coda la posizione della racchetta avversaria
        avv_pad.sety(avv_pad_position)              # Imposto la posizione della racchetta avversaria con sety


# Funzione per gestire il movimento della pallina
def update_ball():
    global ball_control         # Variabile per sapere se ho il controllo della pallina
    global player               # Variabile per sapere in che la to del campo sto giocando (0 controllo la racchetta sinistra, 1 controllo la racchetta destra)
    global score_player0, score_player1     # Punteggi dei giocatori

    if ball_control == False:       # La pallina è controllata dall'avversario, io ricevo la posizione e aggiorno la posizione dalla pallina
        if not ball_queue.empty():
            ball_position = ball_queue.get()         # Prelevo dalla coda la posizione della pallina

            ball.goto(ball_position[0], ball_position[1])       # Imposto la posizione della pallina attraverso goto

    else:       # ball_control == True, ho io il controllo della pallina, calcolo la posizione e le collisioni con i bordi e le racchette

        ball.goto(ball.xcor() + ball.dx, ball.ycor() + ball.dy)     # Aggiorno la posizione della pallina aggiungendo lo spostamento lungo gli assi x e y (dx e dy) alla posizione attuale (ball.xcor() e ball.ycor())

        # Logica di collisione con il bordo superiore
        if ball.ycor() > 290 or ball.ycor() < -290:
            ball.dy *= -1

        # Logica di collisione con la racchetta avversaria, dopo la collisione imposto il controllo della pallina a falso e mando il testo "passo" per segnalare all'avversario che cedo il controllo della pallina
        if (ball.xcor() > 385 and ball.xcor() < 410) and (ball.ycor() < right_pad.ycor() + 50 and ball.ycor() > right_pad.ycor() - 50) and player == 0:      # Se sono il giocatore di sx ed la pallina viene toccata dal giocatore di dx perdo il controllo
            ball_control = False
            passo_msg = str(f"passo").encode()
            socket_client.sendto(passo_msg, (server_IP, server_port))
            ball_queue.queue.clear()    # Svuoto la coda della pallina

        # Logica di collisione con la racchetta avversaria, dopo la collisione imposto il controllo della pallina a falso e mando il testo "passo" per segnalare all'avversario che cedo il controllo della pallina
        if (ball.xcor() < -385 and ball.xcor() > -410) and (ball.ycor() < left_pad.ycor() + 50 and ball.ycor() > left_pad.ycor() - 50) and player == 1:      # Se sono il giocatore di dx ed la pallina viene toccata dal giocatore di sx perdo il controllo
            ball_control = False
            passo_msg = str(f"passo").encode()
            socket_client.sendto(passo_msg, (server_IP, server_port))
            ball_queue.queue.clear()    # Svuoto la coda della pallina

        # Se la pallina supera la racchetta avversaria senza essere stata toccata segno un punto
        if ball.xcor() < -420 and player == 1:
            score_player1 += 1
            ball.goto(0, 0)

            score_display.clear()       # Pulisco il punteggio precedentemente scritto
            score_display.write(f"Giocatore 1: {score_player0}   Giocatore 2: {score_player1}", align="center", font=("Courier", 24, "normal"))     # Scrivo il punteggio aggiornato
            ball.clear()

            reset_msg = str(f"reset").encode()      # Mando il messaggio "reset" all'avversario per segnalare il punto segnato
            socket_client.sendto(reset_msg, (server_IP, server_port))
            time.sleep(3)               # Tempo per far tornare la pallina al centro dopo un punto segnato

        # Se la pallina supera la racchetta avversaria senza essere stata toccata segno un punto
        if ball.xcor() > 420 and player == 0:
            score_player0 += 1
            ball.goto(0, 0)

            score_display.clear()       # Pulisco il punteggio precedentemente scritto
            score_display.write(f"Giocatore 1: {score_player0}   Giocatore 2: {score_player1}", align="center", font=("Courier", 24, "normal"))     # Scrivo il punteggio aggiornato
            ball.clear()

            reset_msg = str(f"reset").encode()      # Mando il messaggio "reset" all'avversario per segnalare il punto segnato
            socket_client.sendto(reset_msg, (server_IP, server_port))
            time.sleep(3)               # Tempo per far tornare la pallina al centro dopo un punto segnato
        check_win()     # Controlla se un giocatore è arrivato a 10 punti


# Funzione per controllare se un giocatore ha vinto e interrompere la partita
def check_win():
    global score_player0, score_player1
    if score_player0 >= 10:
        win_display = turtle.Turtle()
        win_display.speed(0)
        win_display.color("red")
        win_display.penup()
        win_display.hideturtle()
        win_display.goto(0, 0)
        win_display.write(f" Il Giocatore 1 ha vinto", align="center", font=("Courier", 24, "normal"))

        send_thread.join()         # Termina il thread per l'invio delle posizioni
        receive_thread.join()      # Termina il thread per la ricezione delle posizioni
        turtle.done()              # Termina il ciclo di Turtle

    if score_player1 >= 10:
        win_display = turtle.Turtle()
        win_display.speed(0)
        win_display.color("red")
        win_display.penup()
        win_display.hideturtle()
        win_display.goto(0, 0)
        win_display.write(f" Il Giocatore 2 ha vinto", align="center", font=("Courier", 24, "normal"))

        send_thread.join()         # Termina il thread per l'invio delle posizioni
        receive_thread.join()      # Termina il thread per la ricezione delle posizioni
        turtle.done()              # Termina il ciclo di Turtle


# Avvia il thread per l'invio dei dati
send_thread = threading.Thread(target=send_position)
send_thread.start()

# Avvia il thread per la ricezione dei dati
receive_thread = threading.Thread(target=receive_position)
receive_thread.start()


def main_loop():

    update_ball()                # Aggiorna la posizione della pallina
    update_opponent_paddle()     # Aggiorna la posizione della racchetta avversaria

    turtle.ontimer(main_loop, 5)  # Tempo per il richiamo del main_loop


# Avvia il ciclo principale di Turtle
turtle.ontimer(main_loop, 0)
turtle.mainloop()