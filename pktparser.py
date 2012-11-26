from random import uniform
from struct import unpack
class RtcpPacket(object):

  '''
        0                   1                   2                   3
        0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
header |V=2|P|    RC   |   PT=SR=200   |             length            |
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
       |                         SSRC of sender                        |
       +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+
sender |              NTP timestamp, most significant word             |
info   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
       |             NTP timestamp, least significant word             |
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
       |                         RTP timestamp                         |
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
       |                     sender's packet count                     |
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
       |                      sender's octet count                     |
       +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+
report |                 SSRC_1 (SSRC of first source)                 |
block  +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
  1    | fraction lost |       cumulative number of packets lost       |
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
       |           extended highest sequence number received           |
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
       |                      interarrival jitter                      |
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
       |                         last SR (LSR)                         |
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
       |                   delay since last SR (DLSR)                  |
       +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+
report |                 SSRC_2 (SSRC of second source)                |
block  +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
  2    :                               ...                             :
       +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+
       |                  profile-specific extensions                  |
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
  '''
  def __init__(self, data):
    super(RtcpPacket, self).__init__()
    self.byte_array = bytearray(data)

  def unpack_int32(self, byte_array):
    x = unpack('!I', bytes(byte_array))
    return x[0]
  
  def __str__(self):
    parsed = 0
    total = len(self.byte_array)
    comps = ['RTCP, total_len = %s' % str(total)]
    if self.byte_array[0] & 0x20 != 0:
      pad = self.byte_array[-1]
      comps.append('pad = %s' % str(pad))
    while parsed < total:
      header = self.byte_array[parsed: parsed + 4] 
      pt = header[1]
      byte_len = (header[2] * 255 + header[3] + 1) * 4
      body = self.byte_array[parsed + 4: parsed + byte_len]
      parsed += byte_len
      cc = header[0] & 0x1f
      if pt == 200:
        comps.append('[SR, byte_len = %s, rc = %s' % (str(byte_len), str(cc)))
        comps.append('SSRC = %s' % str(self.unpack_int32(body[:4])))
        comps.append('NTP1 = %s' % str(self.unpack_int32(body[4:8])))
        comps.append('NTP2 = %s' % str(self.unpack_int32(body[8:12])))
        comps.append('timestamp = %s' % str(self.unpack_int32(body[12:16])))
        comps.append('pc = %s' % str(self.unpack_int32(body[16:20])))
        comps.append('oc = %s' % str(self.unpack_int32(body[20:24])))
        body = body[24:]
        for x in xrange(cc):
          comps.append('RSSRC = %s' % str(self.unpack_int32(body[:4])))
          comps.append('high_seq = %s' % str(self.unpack_int32(body[8:12])))
          comps.append('LSR = %s' % str(self.unpack_int32(body[16:20])))
          comps.append('DLSR = %s' % str(self.unpack_int32(body[20:24])))
          body = body[24:]
        comps.append(']')

      elif pt == 201:
        comps.append('[Receiver Report ??!! len = %s]' % str(byte_len))
      elif pt == 202:
        comps.append('[SDES: ')
        comps.append('SSRC = %s' % str(self.unpack_int32(body[:4])))
        item_type = body[4]
        if item_type == 1:
          length = body[5]
          cname = body[6: 6 + length].decode('utf-8')
          comps.append('CNAME = %s' % cname)
          comps.append('Remain bytes = %s]' % map(lambda x: '%02X' % x, body[6 + length:]))
        else:
          comps.append('[Unknown SDES = %s]' % map(lambda x: '%02X' % x, body))
      elif pt == 203:
        comps.append('[Bye: SSRC = %s' % str(self.unpack_int32(body[:4])))
        comps.append('Remain bytes = %s]' % map(lambda x: '%02X' % x, body[4:]))
      else:
        comps.append('[Unknown RTCP type = %s, length = %s]' % (str(pt), str(len(body))))
    
    return ', '.join(comps)

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
    x = unpack('!I', bytes(byte_array))
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
#  req0 = '\x00\x01\x00$!\x12\xa4BDclD5EODVxLj\x00\x06\x00 JsdA/ldOghOuec1h3qF906Zuo0uYykm7'
#  res0 = '\x01\x01\x000!\x12\xa4Bv6rR2kqkHmmd\x00\x01\x00\x08\x00\x01#(\xc0\xa8\x00\x0e\x00\x06\x00 3qF906Zuo0uYykm7JsdA/ldOghOuec1h'
#
#  req1 = '\x00\x01\x00$!\x12\xa4Bv6rR2kqkHmmd\x00\x06\x00 3qF906Zuo0uYykm7JsdA/ldOghOuec1h'
#  res1 = '\x01\x01\x000!\x12\xa4B+bSaqWJSMGgG\x00\x01\x00\x08\x00\x01#)\xc0\xa8\x00\x0e\x00\x06\x00 JsdA/ldOghOuec1h3qF906Zuo0uYykm7'
#
#  r0 = StunPacket(req0)
#  r1 = StunPacket(req1)
#  s0 = StunPacket(res0)
#  s1 = StunPacket(res1)
#
#  fr = StunPacket(r0.get_bytes())
#  print fr
#
#  fr.set_new_trans_id()
#  fr.fake_username()
#  print fr
#
#  fs = StunPacket(r0.get_bytes())
#  fs.set_stun_type(StunPacket.Response)
#  fs.add_fake_mapped_address()
#
#  print s1
#  print fs

  d1 = "\x81\xc8\x00\x0c\xd1\xa0\x85a\xef=\xf8t\\\x0e.\x83O\x1e\xa6z|d\xb8\xf0\xde\xc4\\\x98-\x92\xfb\x9cDQ\x94\xa5</\x0f\x1a\x87\xaf$~ `\x12L6\xde5\r\xad\x95\xd5\x04\xc1\xfa\xfbX\xca\xd9\xf5\xa2,\xff\xd3\x05\xbf\xaaMp\xb4\xde\xaeU\xe4H\x1d\xb0\xbcp\x05\xe2\xb9\x0e\n\xd8\x89C)'\x80\x00\x00\x01&]\x80D\xa4d\x00I\x019" 

  d2 = '\x81\xc8\x00\x0c\xd1\xa0\x85a\xdf\xbb\xc6\xa0\xba\xe2\xd7\xe0\xddH\xcc\xe6\x91\x894K\x0f!g\x94\xce\xfa\xf6\xe5\xc1mVr"\xfa\x03Y\xd6\x00Ky\xae\xcd6\xca\xfevgm\x8f\xd0\x84,\xb0i\xe2\xaeH\x85\x98\xbf\xb9\x05H\xbc\xc5\xe3T\xbf3pn\xa3\xd8p5A\x9f\xa3\x9c\x06l*V\xe0\xe2\x1e\xa4i\x80\x00\x00\x02\x83(\x00h\x96\xe9\xdb\xf9\xaf\xe8'

  d3 = '\x81\xc8\x00\x0c\xd1\xa0\x85a\xcd\x15\xcdH\xbc\x07\xba]o8an]\xa1Sw\x91\x11\xb8\xaa\x08\xe5\x9c%\xecCy0\xe6\x8b\x0b\xb3,\xfeh\xba\xbf\xd7\x8ey\xc7\xf24\x86\xcf\x15@fX\xe6a\x14\xb6\xad\xccQ6.c{\x19\xbf\x8a\xbf_\x8fN\x98\x8e\xa8Z\xd5\x1aX\xf8:\xa2\xbb\x84\xc4\x1b\x9f\xf79\xb3\x88)\x0fe\x0b\x0e\xb2\xfav\xc0J\x80\x00\x00\x05Tp\x9c\x86\xf4v\x17\x0c\x96\x0e'

  d4 = '\x81\xc9\x00\x07\xd1\xa0\x85aJiI\xe3=\x98\xb9a\xab\xb5\xc0\xf7dn\xfd\xb5\x0eB\x08\x86,Th\x1a\xf6\x82\xad\xab\xf9]\x1d\x0c\x19\x1e,\x8e\xad\x03\xf7X\x04\xc0\x88\x94\xeb"\xac\xc3E\xca\xf6\xab@\x98\x91\xfc\x0b \x83Z"^\x8bj\x1b\x9d3\xc2\x95\x13\xb7\x84TB\x8d\x81,\xd6\xe4\x07\x1a2\xf3\x80\x80\x00\x00\x0b~\x83N\xa9(\xff"\xde\x9a\''

  d5 = '\x81\xc8\x00\x0c\xd1\xa0\x85a\x84\x12\xf757c\x9b!\x06,\x11a\xa1\xb9\x96\xedZKv?\x9c\xacb\xbe\xf0\xa0\x7fk\xc0\x87\x1eb|\x10Z\xee9\x9b\n\x92\x97\x1e\xed\x80}\xf4\xe5\x12\x0e\\q`O\nPF\x1f@\x0b\x86y\xfe\xc7\xc6\xe0\xe8\xd8\x0bn\rX\xe1Z\x0e\x12\x96\xf9\xdeN\xf9\x10V\xe6\x1d\xad4]\xba\xe4\x97Q\x83\\\xcdi=\x80\x00\x00\x06\r\x1ecL\xb5F\x1c\x98@\xd8'
  print RtcpPacket(d1)
  print RtcpPacket(d2)
  print RtcpPacket(d3)
  print RtcpPacket(d4)
  print RtcpPacket(d5)
