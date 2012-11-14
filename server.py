import sys
from twisted.internet import reactor
from twisted.internet.protocol import DatagramProtocol
from twisted.web.server import Site
from twisted.web.static import File
from twisted.python import log
from autobahn.websocket import listenWS
from protocol import PeetsServerProtocol, PeetsServerFactory, PeetsMediaTranslator
import argparse
from string import Template

class SimpleFileRewriter(File):

  def render(self, request):
    basename = self.basename()
    if basename == 'index.html':
      filename = self.dirname() + '/' + basename
      with open(filename, 'r') as f:
        html_string = f.read()
        t = Template(html_string)
        global results
        return t.substitute(PORT=str(results.ws))
    else:
      return File.render(self, request)


if __name__ == '__main__':
#  log.startLogging(sys.stdout)
  parser = argparse.ArgumentParser(description = 'Peets Server')
  parser.add_argument('-t', '--tcp', action = 'store', dest = 'tcp', metavar = 'port', type = int, help = 'the port for http', default = 8888)
  parser.add_argument('-w', '--ws', action = 'store', dest = 'ws', metavar = 'port', type = int, help = 'the port for websocket', default = 8000)
  parser.add_argument('-u', '--udp', action = 'store', dest = 'udp', metavar = 'port', type = int,  help = 'the port for udp traffice', default = 9000)

  results = parser.parse_args()

  peets_factory = PeetsServerFactory(results.udp, "ws://localhost:" + str(results.ws))
  peets_factory.protocol = PeetsServerProtocol
  listenWS(peets_factory)

  resource = SimpleFileRewriter('frontend')
  setattr(resource, 'port', results.ws)
  factory = Site(resource)
  reactor.listenTCP(results.tcp, factory)
  reactor.listenUDP(results.udp, PeetsMediaTranslator(peets_factory, 20))
  print 'Listening on:'
  print '\t[port %s] for Http' % results.tcp
  print '\t[port %s] for Udp' % results.udp
  print '\t[port %s] for Websocket' % results.ws
  reactor.run()
