# OpenTasks
A simple tool to track events and tasks
and send push notifications.

## Encryption
OpenTasks is designed to be easy to write
custom clients for. That way, you can make
it work on just about any device. The key
is a 256 bit value that is different for
each user.

Encryption is done using the
XChaCha20-Poly1305 algorithm. The associated
data consists of a little-endian 64-bit unix
timestamp that is verified upon being recieved
to be in the last 5 minutes (or the next 10 seconds
just in case the clocks aren't quite right) and not
repeated, and the username. AAD is put at the start
of the message, with the length (16-bit network order)
at the beginning of it. The 24-byte nonce is
randomly chosen and is appended to the end
of the ciphertext (after the authentication tag).
The order of data goes:
 - 1: AAD length (16 bit network order)
 - 2: AAD data (not including length)
 - 3: Ciphertext
 - 4: Authentication Tag
 - 5: Nonce

Data is also optionally end-to-end encrypted
using the same XChaCha20-Poly1305 algorithm.
If the client uses a password to derive the
key, the algorithm used will be PBKDF2-SHA256
with base64 encoding.
This choice is per the client implementation,
and not required. There is no tag for indication
of end-to-end encryption, as it is a purely
client side choice. The only reason this
document lists what algorithms to use is so
clients can be easily compatible.

## Requests
The OpenTasks protocol is based on a
request-response structure and operates over
TCP. The following list shows the steps in
communication:
 1. Client connects to server (default port 5324)
 2. Client sends 8-bit protocol version 1.
 3. Client sends 16-bit request size in network
    byte order.
 4. Client sends the request.
 5. Server sends 16-bit response size in network
    byte order.
 6. Server sends the response.
 7. Server closes the connection after the response
    has been read.

## Request Types
Requests are structured like this:
 - 1 byte: type
 - remaining: data

What follows is a list of types of requests:
 - Note: Data written with commas describes
 a newline-separated list.
 - Note: The server discards notifications
 once they both have been read and are at least
 1 day old.
 -  Note: Notifications are marked as important
 by having "[IMPORTANT] " (including the space)
 at the start

|number|     explanation    |request data             |response data
|-----:|:------------------:|:------------------------|:----------------------------
|     0|read upcoming events|username,days            |timestamp,
|      |                    |                         |name,timestamp,name,etc.
|     1|read to-do list     |username                 |name,done (true/false),
|      |                    |                         |repeat,etc.
|     2|modify to-do itom   |username,index,done      |no data
|     3|add to-do item      |username,index,name      |no data
|     4|remove to-do item   |username,index           |no data
|     5|add event           |username,timestamp,name  |no data
|     6|remove event        |username,timestamp,name  |no data
|     7|trigger notification|username,name            |no data
|     8|recieve notification|device name              |list of timestamp(as string),
|      |                    |                         |name
|     9|read all events     |username                 |timestamp,name,repeat,etc
