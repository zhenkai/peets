import sys
from twisted.internet import reactor
from twisted.internet.protocol import DatagramProtocol
from twisted.web.server import Site
from twisted.web.static import File
from twisted.python import log
from autobahn.websocket import WebSocketServerFactory, \
                               WebSocketServerProtocol, \
                               listenWS

class EchoServerProtocol(WebSocketServerProtocol):
  def onMessage(self, msg, binary):
    print "sending echo:", msg
    self.sendMessage(msg, binary)

#class EchoUDP(DatagramProtocol):
#  def datagramReceived(self, data, (host, port)):
#    print "received %r from %s: %d" % (data, host, port)
#    self.transport.write(data, (host, port))

if __name__ == '__main__':
  log.startLogging(sys.stdout)
  factory = WebSocketServerFactory("ws://localhost:9000", debug = False)
  factory.protocol = EchoServerProtocol
  listenWS(factory)
  reactor.listenUDP(55935, EchoUDP())

  resource = File('frontend')
  factory = Site(resource)
  reactor.listenTCP(8888, factory)
  reactor.run()
