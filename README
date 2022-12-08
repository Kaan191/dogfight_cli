# About

`dogfight-cli` is a cross-platform terminal-based Python game using the `curses` library. The game hopes to recreate the joy I experienced playing Super Dogfight on the Commodore64.

Two (for now) player-controlled planes battle it out in an infinite box-arena firing and dodging cannon rounds.

The game uses the `socket` library to allow for multiplayer games over a network.

No extra dependencies are required. The game has been tested on `python 3.8`.

# Installation

Clone the git repository.

Navigate into the directory and run:
```
python3 dogfight-cli.py
```

To run a server, make sure your firewall will allow incoming connections on the (free) port you choose to use, then run:
```
python3 server.py <your.ip.address> <port>
```

Run `ifconfig` (or `ipconfig`) to find out your local network or internet IP addresses.

# Instructions

The start menu allows you to choose your game type (Local or Network).

If selecting a Network game, provide the IP address and port of the running server to make a connection. For now, the game will hang until a second connection joins the server.

Use the `KEY_UP`, `KEY_DOWN` and `SPACE` keys to navigate (by changing the pitch of the plane) and fire cannon rounds.

On a Local game, the second player controls are `A` and `W` to navigate, and `D` to fire cannon rounds.

run `dogfight-cli.py` with a `-D` flag to display a debugging box the Arena. Pass the `-L` flag to generate a session-specific log (timestamped).
