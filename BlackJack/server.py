import socket
import threading
import time
import random
import protocol


class BlackjackServer:
    """Simple Blackjack server handling UDP offers and TCP game sessions.

    This server broadcasts offers over UDP and accepts TCP connections
    from clients that wish to play a number of blackjack rounds.
    """

    def __init__(self, tcp_port=8888):
        self.tcp_port = tcp_port
        self.running = True

        # TCP socket for game connections
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.bind(("", self.tcp_port))
        self.tcp_socket.listen()

        # Determine a broadcast address to advertise the server on the local network.
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            self.local_ip = s.getsockname()[0]
            sepreated = self.local_ip.split('.')
            sepreated[-1] = '255'
            self.broadcast_ip = '.'.join(sepreated)
            s.close()
        except Exception:
            # Fallback to loopback when network detection fails
            self.local_ip = "127.0.0.1"

        print(f"Server started, listening on IP address {self.local_ip}")

    def broadcast_offers(self):
        """Broadcast UDP offer packets periodically.

        Uses `protocol.pack_offer` to create the packet and sends it once
        per second to the local broadcast address on the configured UDP port.
        """
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        packet = protocol.pack_offer(self.tcp_port, "MysticDealer")

        while self.running:
            try:
                udp_sock.sendto(packet, (self.broadcast_ip, protocol.UDP_PORT))
                time.sleep(1)  # broadcast interval
            except Exception as e:
                print(f"UDP Broadcast Error: {e}")

    def handle_client(self, conn, addr):
        """Handle a single TCP client session.

        This method receives the client's request (number of rounds, team name),
        then runs the specified number of blackjack rounds sending card payloads
        back to the client using the binary `protocol` helpers.
        """
        print(f"New connection from {addr}")
        try:
            data = conn.recv(1024)
            req = protocol.unpack_request(data)
            if not req:
                print("Invalid request packet")
                return

            num_rounds, team_name = req
            print(f"Team {team_name} wants to play {num_rounds} rounds.")

            wins = 0

            for i in range(num_rounds):
                print(f"Starting round {i+1} for {team_name}")
                deck = self.create_deck()

                # Initial deal: two cards each (server follows protocol ordering)
                player_cards = [deck.pop(), deck.pop()]
                dealer_cards = [deck.pop(), deck.pop()]

                # Send initial cards (protocol defines payload structure)
                self.send_card(
                    conn,
                    protocol.RESULT_CLIENT_WIN
                    if protocol.calculate_hand(player_cards) > 21
                    else protocol.RESULT_ACTIVE,
                    player_cards[0],
                )
                self.send_card(
                    conn,
                    protocol.RESULT_DEALER_WIN
                    if protocol.calculate_hand(player_cards) > 21
                    else protocol.RESULT_ACTIVE,
                    player_cards[1],
                )
                # Show one dealer card to the player
                self.send_card(
                    conn,
                    protocol.RESULT_DEALER_WIN
                    if protocol.calculate_hand(player_cards) > 21
                    else protocol.RESULT_ACTIVE,
                    dealer_cards[0],
                )

                # Player turn
                player_value = protocol.calculate_hand(player_cards)
                player_busted = False

                while player_value < 21:
                    # Payload from client has fixed size (10 bytes)
                    p_data = conn.recv(10)
                    decision = protocol.unpack_payload_client(p_data)

                    if decision == "Hittt":
                        new_card = deck.pop()
                        player_cards.append(new_card)
                        player_value = protocol.calculate_hand(player_cards)
                        if player_value > 21:
                            player_busted = True
                        # Inform client about the new card
                        self.send_card(
                            conn,
                            protocol.RESULT_ACTIVE if not player_busted else protocol.RESULT_DEALER_WIN,
                            new_card,
                        )
                    elif decision == "Stand":
                        break
                    else:
                        print(f"Invalid decision from client: {decision}")
                        break

                if player_value > 21:
                    player_busted = True
                    result = protocol.RESULT_DEALER_WIN

                # Dealer turn: follow standard dealer rules (hit < 17)
                dealer_value = protocol.calculate_hand(dealer_cards)

                if not player_busted:
                    if dealer_value > 21:
                        result = protocol.RESULT_CLIENT_WIN
                    elif dealer_value >= 17:
                        if player_value > dealer_value:
                            result = protocol.RESULT_CLIENT_WIN
                        elif dealer_value > player_value:
                            result = protocol.RESULT_DEALER_WIN
                        else:
                            result = protocol.RESULT_TIE
                    else:
                        result = protocol.RESULT_ACTIVE

                    # Reveal dealer's second card
                    self.send_card(conn, result, dealer_cards[1])

                    while dealer_value < 17:
                        new_card = deck.pop()
                        dealer_cards.append(new_card)
                        dealer_value = protocol.calculate_hand(dealer_cards)

                        if player_busted or dealer_value > 21:
                            result = protocol.RESULT_CLIENT_WIN
                        elif player_value > dealer_value:
                            result = protocol.RESULT_CLIENT_WIN
                        elif dealer_value > player_value:
                            result = protocol.RESULT_DEALER_WIN
                        else:
                            result = protocol.RESULT_TIE

                        if result == protocol.RESULT_CLIENT_WIN:
                            wins += 1
                        self.send_card(conn, result, new_card)

                print(
                    f"Round {i+1} result for {team_name}: {result} (Player: {player_value}, Dealer: {dealer_value})"
                )

            print(f"Finished playing with {team_name}. Wins: {wins}")

        except Exception as e:
            print(f"Client Error: {e}")
        finally:
            conn.close()

    def send_card(self, conn, status, card):
        """Pack and send a single card payload to the client.

        `card` is a tuple of (rank, suit). Uses `protocol.pack_payload_server`.
        """
        packet = protocol.pack_payload_server(status, card[0], card[1])
        conn.sendall(packet)

    def create_deck(self):
        """Return a shuffled 52-card deck as (rank, suit) tuples."""
        deck = [(rank, suit) for suit in range(4) for rank in range(1, 14)]
        random.shuffle(deck)
        return deck

    def start(self):
        """Start broadcasting offers and accept incoming TCP clients."""
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