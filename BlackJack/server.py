import socket
import threading
import time
import random
import protocol

class BlackjackServer:
    def __init__(self, tcp_port=8888):  
        self.tcp_port = tcp_port
        self.running = True
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Keep the reuse address fix we added earlier
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        self.tcp_socket.bind(("", self.tcp_port))
        self.tcp_socket.listen()
        
        # Determine local IP for printing
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            self.local_ip = s.getsockname()[0]
            s.close()
        except:
            self.local_ip = "127.0.0.1"

        print(f"Server started, listening on IP address {self.local_ip}")

    def broadcast_offers(self):
        """UDP Broadcast loop"""
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        packet = protocol.pack_offer(self.tcp_port, "MysticDealer")
        
        while self.running:
            try:
                udp_sock.sendto(packet, ('<broadcast>', protocol.UDP_PORT))
                time.sleep(1) # Broadcast every 1 second [cite: 70]
            except Exception as e:
                print(f"UDP Broadcast Error: {e}")

    def handle_client(self, conn, addr):
        print(f"New connection from {addr}")
        try:
            # 1. Receive Request
            data = conn.recv(1024)
            req = protocol.unpack_request(data)
            if not req:
                print("Invalid request packet")
                return
            
            num_rounds, team_name = req
            print(f"Team {team_name} wants to play {num_rounds} rounds.")

            wins = 0
            
            # 2. Game Loop
            for i in range(num_rounds):
                print(f"Starting round {i+1} for {team_name}")
                deck = self.create_deck()
                
                # --- Initial Deal ---
                # Dealer gets 2 cards, Client gets 2 cards.
                # However, protocol sends cards one by one as they are revealed/dealt.
                
                player_cards = [deck.pop(), deck.pop()]
                dealer_cards = [deck.pop(), deck.pop()] 
                
                # Send player their two cards
                self.send_card(conn, protocol.RESULT_ACTIVE, player_cards[0])
                self.send_card(conn, protocol.RESULT_ACTIVE, player_cards[1])
                
                # Player Turn
                player_value = self.calculate_hand(player_cards)
                player_busted = False
                
                while player_value < 21:
                    # Wait for player decision
                    # NOTE: We need to handle the specific packet size for payload (10 bytes)
                    p_data = conn.recv(10) 
                    decision = protocol.unpack_payload_client(p_data)
                    
                    if decision == "Hittt":
                        new_card = deck.pop()
                        player_cards.append(new_card)
                        player_value = self.calculate_hand(player_cards)
                        
                        # Send the new card
                        self.send_card(conn, protocol.RESULT_ACTIVE, new_card)
                        
                    elif decision == "Stand":
                        break
                    else:
                        print(f"Invalid decision from client: {decision}")
                        break
                
                if player_value > 21:
                    player_busted = True
                
                # Dealer Turn
                dealer_value = self.calculate_hand(dealer_cards)
                
                # If player didn't bust, dealer plays
                if not player_busted:
                    while dealer_value < 17: # Dealer hits on < 17 [cite: 54]
                        new_card = deck.pop()
                        dealer_cards.append(new_card)
                        dealer_value = self.calculate_hand(dealer_cards)
                        # Note: We don't send dealer cards to client in real-time based on protocol specs?
                        # Re-reading source [102]: "The card the client/server pulled from the deck".
                        # It implies we send updates. But usually dealer reveals at end.
                        # For simplicity/protocol limits, we only send the RESULT payload at the end 
                        # or if we want to animate dealer we'd send active payloads.
                        # Let's just calculate winner.

                # Determine Winner
                if player_busted:
                    result = protocol.RESULT_LOSS
                elif dealer_value > 21:
                    result = protocol.RESULT_WIN
                elif player_value > dealer_value:
                    result = protocol.RESULT_WIN
                elif dealer_value > player_value:
                    result = protocol.RESULT_LOSS
                else:
                    result = protocol.RESULT_TIE
                
                if result == protocol.RESULT_WIN:
                    wins += 1
                
                # Send End of Round Result (with a dummy card 0,0 just to fill packet)
                # Source [101] says Server sends result.
                protocol.pack_payload_server(result, 0, 0)
                conn.sendall(protocol.pack_payload_server(result, 0, 0))
                
                print(f"Round {i+1} result for {team_name}: {result} (Player: {player_value}, Dealer: {dealer_value})")

            print(f"Finished playing with {team_name}. Wins: {wins}")
            
        except Exception as e:
            print(f"Client Error: {e}")
        finally:
            conn.close()

    def send_card(self, conn, status, card):
        """Helper to pack and send a card."""
        # card is (rank, suit)
        # ranks 11,12,13 are J,Q,K. 1 is Ace.
        packet = protocol.pack_payload_server(status, card[0], card[1])
        conn.sendall(packet)

    def create_deck(self):
        """Creates a shuffled 52-card deck (Rank 1-13, Suit 0-3)."""
        deck = [(rank, suit) for suit in range(4) for rank in range(1, 14)]
        random.shuffle(deck)
        return deck

    def calculate_hand(self, cards):
        """Calculates blackjack value."""
        total = 0
        aces = 0
        for rank, suit in cards:
            if rank == 1: # Ace
                aces += 1
                total += 11
            elif rank >= 10: # Face cards + 10
                total += 10
            else:
                total += rank
        
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        return total

    def start(self):
        # Start UDP Broadcaster
        t = threading.Thread(target=self.broadcast_offers, daemon=True)
        t.start()
        
        while self.running:
            try:
                conn, addr = self.tcp_socket.accept()
                t_client = threading.Thread(target=self.handle_client, args=(conn, addr))
                t_client.start()
            except KeyboardInterrupt:
                self.running = False

if __name__ == "__main__":
    srv = BlackjackServer()
    srv.start()