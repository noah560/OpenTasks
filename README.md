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
repeated (or it can be repeated if the nonce or
username is different), and the username. AAD is put
at the start of the message, with the length (16-bit
network order) at the beginning of it. The 24-byte
nonce is randomly chosen and is appended to the end
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
 - Note: Data written with commas in the request
 data describes a newline-separated list.

|number|     explanation         |request data               |response data
|-----:|:-----------------------:|:--------------------------|:-------------
|     0|read file                |name(alphanumeric ascii)   |file data
|     1|read section of file     |name,start(str),size(str)  |section data
|     2|get file size            |name                       |size(str)
|     3|write entire file        |name,data(rest of rq lines)|none
|     4|write preexisting section|name,start,data            |none
|     5|append to file           |name,data                  |none
|     6|delete file end          |name,amount                |none
|     7|delete file              |name                       |none
|     8|list files               |none                       |name,name,etc
|     9|push line                |name,line                  |none
|    10|pop line from end        |name                       |line
|    11|pop line from start      |name                       |line

# Required Files
OpenTasks clients that fit the standard should
use a file called "todo" for a to-do list with
one line per item, with the first character of
each line being " " if unchecked and "V" if
checked.

For events, a file called "events" is used with
one line per event, with the timestamp as a string,
followed by a comma and then the name.

For notifications, a file called "notifications"
is used, with one line per item the same as an
event.
