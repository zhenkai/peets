from random import uniform
from struct import unpack
class RtpPacket(object):
  ''' A packet class for RTP messages
   RTP fixed header
    0                   1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |V=2|P|X|  CC   |M|     PT      |       sequence number         |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                           timestamp                           |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |           synchronization source (SSRC) identifier            |
   +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+
   |            contributing source (CSRC) identifiers             |
   |                             ....                              |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
  '''
  def __init__(self, data):
    super(RtpPacket, self).__init__()
    self.byte_array = bytearray(data)

  def get_cc(self):
    # b 1111
    mask = 15
    return self.byte_array[0] & mask

  def get_m_bit(self):
    mask = 1 << 7
    if self.byte_array[1] & mask == 0:
      return 0
    else:
      return 1

  def get_pt(self):
    mask = ~(1 << 7)
    return self.byte_array[1] & mask

  def get_seq(self):
    return self.byte_array[2] * 255 + self.byte_array[3]

  def get_timestamp(self):
    return self.unpack_int32(self.byte_array[4:8])

  def get_ssrc(self):
    return self.unpack_int32(self.byte_array[8:12])

  def get_csrcs(self):
    csrcs = []
    for x in xrange(self.get_cc()):
      cscrs.append(self.unpack_int32(self.byte_array[12 + 8 * x : 20 + 8 * x]))
    
    return csrcs

  def unpack_int32(self, byte_array):
    x = unpack('>I', bytes(byte_array))
    return x[0]
    
  def __str__(self):
    return 'RTP: [cc = %s, M = %s, PT = %s, SeqNo = %s, timestamp = %s, SSRC = %s, CSRCs = %s]' % (str(self.get_cc()), str(self.get_m_bit()), str(self.get_pt()), str(self.get_seq()), str(self.get_timestamp()), str(self.get_ssrc()), str(self.get_csrcs()))

class StunPacket(object):
  ''' A packet class for stun messages (only handles certain type of messages)

     STUN packets (RFC 5389)
       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |0 0|     STUN Message Type     |         Message Length        |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                         Magic Cookie                          |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                                                               |
      |                     Transaction ID (96 bits)                  |
      |                                                               |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

                  Figure 2: Format of STUN Message Header 

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |         Type                  |            Length             |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                         Value (variable)                ....
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

                    Figure 4: Format of STUN Attributes
       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |0 0 0 0 0 0 0 0|    Family     |           Port                |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                                                               |
      |                 Address (32 bits or 128 bits)                 |
      |                                                               |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

               Figure 5: Format of MAPPED-ADDRESS Attribute

    For 'Request' Stun msg, it contains an Attribute 'Username'
    For 'Response' Stun msg, it contains an Attribute 'MAPPED-ADDRESS' followed 
    immediately by a 'Username' attribute included in the corresponding 'Request'
    packet. 
    The 'Request' and 'Response' pair use the same Transaction ID
  '''
  (Request, Response, Unknown) = range(3)
  (Mapped_Address, Username, ErrorCode, Other) = range(4)
  def __init__(self, data):
    super(StunPacket, self).__init__()
    self.byte_array = bytearray(data)

  def get_stun_type(self):
    if self.byte_array[0] == 0:
      return self.__class__.Request
    elif self.byte_array[0] == 1:
      return self.__class__.Response
    else:
      return self.__class__.Unknown

  def get_trans_id(self):
    return ''.join(map(lambda x: '%02X' % x, self.byte_array[8:20]))

  def set_stun_type(self, pkt_type):
    self.byte_array[0] = pkt_type

  def set_new_trans_id(self):
    for i in xrange(12):
      self.byte_array[i + 8] = int(uniform(0, 255))

  def fake_username(self):
    if self.byte_array[21] != 6: 
      print 'Hmm.. Not the right packet to operate fake_username'
    else:
      #username = bytearray([0x30, 0x4A, 0x32, 0x31, 0x4D, 0x61, 0x65, 0x6B, 0x4D, 0x39, 0x6A, 0x63, 0x78, 0x63, 0x2B, 0x6C, 0x49, 0x66, 0x64, 0x47, 0x48, 0x76, 0x4F, 0x46, 0x41, 0x72, 0x74, 0x30, 0x42, 0x7A, 0x7A, 0x32])
      prefix = bytearray([0x30, 0x4A, 0x32, 0x31, 0x4D, 0x61, 0x65])
      self.byte_array[24: 24 + len(prefix)] = prefix

  def set_stun_header(self, header):
    self.byte_array[0:20] = header

  def get_stun_header(self):
    return self.byte_array[0:20]

  def update_pkt_length(self):
    length = len(self.byte_array) - 20 
    # suppose length < 255, which is always true in our case
    if length > 255:
      print 'Hmm.. have a packet length > 255'
    else:
      self.byte_array[3] = length

  def get_bytes(self):
    return bytes(self.byte_array)

  def add_fake_mapped_address(self):
    attr = bytearray()
    # Type \x00\x01
    attr.extend([0, 1])
    # Length 8
    attr.extend([0, 8])
    # IPv4
    attr.extend([0, 1])
    # Port 9999
    attr.extend([39, 54])
    # Address 127.0.0.1
    attr.extend([127, 0, 0, 1])

    pkt = bytearray()
    pkt.extend(self.byte_array[0:20])
    pkt.extend(attr)
    pkt.extend(self.byte_array[20:])
    
    self.byte_array = pkt
    self.update_pkt_length()

  def __str__(self):
    comps = []
    stun_type = self.get_stun_type() 
    if stun_type == self.__class__.Request:
      comps.append('Request')
    elif stun_type == self.__class__.Response:
      comps.append('Response')
    else:
      return 'Unknown Stun type'

    length = self.byte_array[3]
    comps.append('length = %s' % str(length))
    comps.append('transID = %s' % self.get_trans_id())
    
    attr = self.byte_array[20:]
    parsed = 0
    total = len(attr)
    while(parsed < total):
      attr_head = attr[0:4]
      value_len = attr_head[3]
      value = attr[4: 4 + value_len]
      attr = attr[4 + value_len:]
      parsed += 4 + value_len
      if attr_head[1] == 1:
        comps.append('[Mapped-Address')
        if value[1] == 1:
          comps.append('IPv4')
        else:
          comps.append('IPv6')

        address = '.'.join(map(lambda x: '%s' % str(x), value[4:]))
        comps.append('Address = %s' % address)

        port = value[2] * 255 + value[3]
        comps.append('Port = %s]' % str(port))
      elif attr_head[1] == 6:
        comps.append('[Username = %s]' % ''.join(map(lambda x: '%02X' % x, value)))
      else:
        comps.append('[Other Attribute')
        comps.append('header = %s' % ''.join(map(lambda x: '%02X' % x, attr_head)))
        comps.append('value = %s]' % ''.join(map(lambda x: '%02X' % x, value)))

    return ', '.join(comps)
  
if __name__ == '__main__':
  req0 = '\x00\x01\x00$!\x12\xa4BDclD5EODVxLj\x00\x06\x00 JsdA/ldOghOuec1h3qF906Zuo0uYykm7'
  res0 = '\x01\x01\x000!\x12\xa4Bv6rR2kqkHmmd\x00\x01\x00\x08\x00\x01#(\xc0\xa8\x00\x0e\x00\x06\x00 3qF906Zuo0uYykm7JsdA/ldOghOuec1h'

  req1 = '\x00\x01\x00$!\x12\xa4Bv6rR2kqkHmmd\x00\x06\x00 3qF906Zuo0uYykm7JsdA/ldOghOuec1h'
  res1 = '\x01\x01\x000!\x12\xa4B+bSaqWJSMGgG\x00\x01\x00\x08\x00\x01#)\xc0\xa8\x00\x0e\x00\x06\x00 JsdA/ldOghOuec1h3qF906Zuo0uYykm7'

  r0 = StunPacket(req0)
  r1 = StunPacket(req1)
  s0 = StunPacket(res0)
  s1 = StunPacket(res1)

  fr = StunPacket(r0.get_bytes())
  print fr

  fr.set_new_trans_id()
  fr.fake_username()
  print fr

  fs = StunPacket(r0.get_bytes())
  fs.set_stun_type(StunPacket.Response)
  fs.add_fake_mapped_address()

  print s1
  print fs


