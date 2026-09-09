# OpenTasks
A simple tool to track events and tasks
and send push notifications.

## Design
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

## Protocol
