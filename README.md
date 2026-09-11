# OpenTasks
A simple tool to track events and tasks
and send push notifications.

## Encryption
OpenTasks is designed to be easy to write
custom clients for. That way, you can make
it work on just about any device.

Encryption Algorithm:
 1. Add an 8 byte unix timestamp to the end
    of the plaintext.
 2. Add a 1 byte checksum to the end of the
    plaintext, so all bytes add to 0, to
    detect both tampering and transmission
    errors.
 3. Calculate the nonce as the last 96 bits
    (12 bytes) of the SHA-256 hash of the
    plaintext (including everything added).
 4. Encrypt using the nonce and add the nonce
    to the end of the ciphertext.

Decryption Algorithm:
 1. Extract the nonce from the end of the
    ciphertext.
 2. Decrypt the message.
 3. Validate the checksum.
 4. Remove the checksum and timestamp.

## Requests
The OpenTasks protocol is based on a
request-response structure and operates over
TCP. The following list shows the steps in
communication:
 1. Client connects to server (default port 5324)
 2. Client sends 16-bit request size in network
    byte order.
 3. Client sends the request.
 4. Server sends 16-bit response size in network
    byte order.
 5. Server sends the response.
 6. Server closes the connection after the response
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
