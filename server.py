import sys
from twisted.internet import reactor
from twisted.internet.protocol import DatagramProtocol
from twisted.web.server import Site
from twisted.web.static import File
from twisted.python import log
from autobahn.websocket import listenWS
from protocol import PeetsServerProtocol, PeetsServerFactory, PeetsMediaTranslator


if __name__ == '__main__':
#  log.startLogging(sys.stdout)
  peets_factory = PeetsServerFactory("ws://localhost:8000")
  peets_factory.protocol = PeetsServerProtocol
  listenWS(peets_factory)

  resource = File('frontend')
  factory = Site(resource)
  reactor.listenTCP(8888, factory)
  reactor.listenUDP(9003, PeetsMediaTranslator(peets_factory, 20))
  reactor.run()
