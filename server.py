import sys
from twisted.internet import reactor
from twisted.internet.protocol import DatagramProtocol
from twisted.web.server import Site
from twisted.web.static import File
from twisted.python import log
from autobahn.websocket import listenWS
from protocol import PeetsServerProtocol, PeetsServerFactory


if __name__ == '__main__':
#  log.startLogging(sys.stdout)
  factory = PeetsServerFactory("ws://localhost:8000")
  factory.protocol = PeetsServerProtocol
  listenWS(factory)

  resource = File('frontend')
  factory = Site(resource)
  reactor.listenTCP(8888, factory)
  reactor.run()
