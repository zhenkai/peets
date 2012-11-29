from matplotlib import pyplot as plt, patches
import argparse
import time
import re

class DataSet(object):
  def __init__(self):
    super(DataSet, self).__init__()
    self.tag = None
    self.rtps = {}
    self.rtcps = {}
    self.stuns = {}

  def __str__(self):
    return 'Tag = %s\nRTPs=%s\nRTCPs=%s\nSTUNs=%s' % (self.tag, self.rtps, self.rtcps, self.stuns)

def extract_normal(filename):
  matchers = [ ('UDP', re.compile('UDP-PORT=(\d+)')), ('RTP', re.compile('RTP-DATA:([\S]+)')), ('RTCP', re.compile('RTCP-DATA:([\S]+)')), ('STUN', re.compile('STUN-DATA:([\S]+)')) ]
  time_matcher = re.compile('^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),(\d+)')
  dataset = DataSet()
  self_id = None
  for raw_line in open(filename, 'r'):
    line = raw_line.rstrip()
    matching = filter(lambda (k, v): v is not None, map(lambda (k, v): (k, v.search(line)), matchers))

    if matching != []:
      label, m = matching[0]
      if label == 'UDP':
        dataset.tag = m.group(1)

      else:
        time_m = time_matcher.match(line)
        time_struct = time.strptime(time_m.group(1), '%Y-%m-%d %H:%M:%S')
        seconds = time.mktime(time_struct) + int(time_m.group(2)) / 1000.0
        name = m.group(1)
        comps = name.split('/')
        remote = comps[3]
        try:
          seq = int(comps[-1])
        except ValueError:
          print 'Illegal name in', line

        if label == 'RTCP':
          try:
            dataset.rtcps[remote].append((seconds, seq))
          except KeyError:
            dataset.rtcps[remote] = []
            dataset.rtcps[remote].append((seconds, seq))
        elif label == 'STUN':
          try:
            if self_id is None:
              self_id = comps[-2]
            dataset.stuns[remote].append((seconds, seq))
          except KeyError:
            dataset.stuns[remote] = []
            dataset.stuns[remote].append((seconds, seq))
        else:
          try:
            dataset.rtps[remote].append((seconds, seq))
          except KeyError:
            dataset.rtps[remote] = []
            dataset.rtps[remote].append((seconds, seq))

  for (remote, sequence) in dataset.rtcps.items():
    min_seq = min(map(lambda (k, v): v, sequence))
    times = map(lambda (k, v): k, sequence)
    dataset.rtcps[remote] = zip(times, range(min_seq, min_seq + len(sequence)))

  for (remote, sequence) in dataset.stuns.items():
    min_seq = min(map(lambda (k, v): v, sequence))
    times = map(lambda (k, v): k, sequence)
    dataset.stuns[remote] = zip(times, range(min_seq, min_seq + len(sequence)))

  return dataset, self_id


def get_limits(*args):
  max_t = 0
  min_t = 0x7fffffff
  for (dataset, self_id) in args:
    for (remote, sequence) in dataset.rtcps.items(): 
      times = map(lambda (k, v): k, sequence)
      if min(times) < min_t:
        min_t = min(times)
      if max(times) > max_t:
        max_t = max(times)

  return (min_t, max_t)

def plot_ax(items, ax, min_t, max_t, id_map, portmap, colormap):
  max_s = 0
  min_s = 0x7fffffff
  legends = {}
  for (remote, sequence) in items:

    seqs = map(lambda(k, v): v, sequence)

    if min(seqs) < min_s:
      min_s = min(seqs)
    if max(seqs) > max_s:
      max_s = max(seqs)

  remote_count = 0
  for (remote, sequence) in items:
    time_shifted = map(lambda (k, v): (k - min_t, v), sequence)
    pairs = zip(time_shifted, time_shifted[1:])
    color = colormap[remote]
    legends[remote] = patches.Rectangle((0, 0,), 1, 5, color = color)
    remote_count += 1
    for ((t, s), (t1, s1)) in pairs:
      rect = patches.Rectangle((t, s), (t1 - t), (s1 - s), color = color)
      ax.add_patch(rect)

  ids = [] 
  if id_map is not None:
    for key in legends.keys():
      try:
        port = portmap[key]
        ids.append(id_map[port])
      except KeyError:
        ids = legends.keys()
        break

  if id_map is None:
    ids = legends.keys()

  ax.legend(legends.values(), ids, loc='upper left', prop = {'size': 5})
  ax.set_ylim([min_s, max_s])
  ax.set_xlim([0, max_t - min_t])
  for tick in ax.xaxis.get_major_ticks():
    tick.label.set_fontsize(8)
  for tick in ax.yaxis.get_major_ticks():
    tick.label.set_fontsize(8)

def get_portmap(*args):
  portmap = {}
  for (dataset, self_id) in args:
    portmap[self_id] = dataset.tag

  return portmap

def get_colormap(*args):
  colormap = {}
  colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k']
  if len(args) > len(colors):
    print "do not support more than %s parites yet" % str(len(colors))
    return

  used_colors = set()
  for (dataset, self_id) in args:
    index = hash(self_id) % len(colors)
    color = colors[index]
    while color in used_colors:
      index = (index + 1) % len(colors)
      color = colors[index]

    colormap[self_id] = color
    used_colors.add(color)

  return colormap


def plot(*args, **kwargs):

  fig = plt.figure()
  figname = kwargs['figname']
  id_map = kwargs['id_map']

  col = 3
  row = len(args)

  (min_t, max_t) = get_limits(*args)
  portmap = get_portmap(*args)
  colormap = get_colormap(*args)

  i = 0
  for (dataset, self_id) in args:
    tag = dataset.tag
    if id_map is not None:
      try:
        tag = id_map[tag]
      except KeyError:
        pass

    rtp_ax = fig.add_subplot(row, col, i + 1)
    rtp_ax.set_xlabel('time (seconds)', fontsize = 8)
    rtp_ax.set_ylabel('seq', fontsize = 8)
    rtp_ax.set_title(tag + ' (RTP)', fontsize = 8)
    rtcp_ax = fig.add_subplot(row, col, i + 2)
    rtcp_ax.set_xlabel('time (seconds)', fontsize = 8)
    rtcp_ax.set_ylabel('seq', fontsize = 8)
    rtcp_ax.set_title(tag + ' (RTCP)', fontsize = 8)
    stun_ax = fig.add_subplot(row, col, i + 3)
    stun_ax.set_xlabel('time (seconds)', fontsize = 8)
    stun_ax.set_ylabel('seq', fontsize = 8)
    stun_ax.set_title(tag + ' (STUN)', fontsize = 8)
    i += 3

    plot_ax(dataset.rtcps.items(), rtcp_ax, min_t, max_t, id_map, portmap, colormap)
    plot_ax(dataset.rtps.items(), rtp_ax, min_t, max_t, id_map, portmap, colormap)
    plot_ax(dataset.stuns.items(), stun_ax, min_t, max_t, id_map, portmap, colormap)


  fig.tight_layout()

  fig.savefig(figname, dpi = (300))  
  #plt.show()

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description = 'Diagnosis tool for peets')
  parser.add_argument('logs', metavar='LOG', type=str, nargs='+', help = 'Log filenames')
  parser.add_argument('-p', '--png', action = 'store', dest='png_file', metavar='PNG', type=str, help = 'Filename of the png output', required = True)
  parser.add_argument('-m', '--map', action = 'store', dest='map', metavar='Map', type=str, help = 'tbd')
  args = parser.parse_args()
  dataset_id_pairs = []
  for f in args.logs:
    dataset_id_pairs.append(extract_normal(f))

  id_map = {}
  if args.map is not None:
    pairs = args.map.split(',')
    for pair in pairs:
      k, v = pair.split('=')
      key = k.replace(' ', '')
      value = v.replace(' ', '')
      id_map[key] = value
    
  plot(*dataset_id_pairs, figname = args.png_file, id_map = id_map)

