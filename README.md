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
to be in the last 5 minutes and not repeated,
and the username.
The 24-byte nonce is randomly chosen and is
appended to the end of the ciphertext (after
the authentication tag).

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

|number|     explanation    |request data             |response data
|-----:|:------------------:|:------------------------|:-------------------------
|     0|read upcoming events|username                 |timestamp,
|      |                    |                         |name,timestamp,name,etc.
|     1|read to-do list     |username                 |name,done (true/false),
|      |                    |                         |repeat,etc.
|     2|write to-do list    |username,index,done      |no data
|     3|add to-do item      |username,index,name      |no data
|     4|remove to-do item   |username,index           |no data
|     5|add event           |username,timestamp,name  |no data
|     6|remove event        |username,timestamp,name  |no data
|     7|trigger notification|username,important(bool),|no data
|      |                    |name                     |
|     8|recieve notification|device name              |list of timestamp,name
