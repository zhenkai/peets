from autobahn.websocket import WebSocketServerProtocol

class PeetsServerProtocol(WebSocketServerProtocol):
  def onOpen(self):
    pass

  def onMessage(self, msg, binary):
    pass

  def onClose(self):
    pass
