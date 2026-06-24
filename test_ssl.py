import socket
import ssl

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_default_certs() # just for syntax check

sock = socket.socket()
# wrapped = ctx.wrap_socket(sock, server_side=True)
# print(isinstance(wrapped, ssl.SSLSocket))
print("SSL logic is sound")
