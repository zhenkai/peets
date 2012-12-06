from matplotlib import pyplot as plt, patches
import argparse
import time
import re

class Pair(object):
  def __init__(self, *args, **kwargs):
    super(Pair, self).__init__()
    self.left = kwargs.get('left')
    self.right = kwargs.get('right')
    self.label = kwargs.get('label')

  def __str__(self):
    return 'L=%s, R=%s, Label=%s' % (str(self.left), str(self.right), self.label)

class DataSet(object):
  def __init__(self):
    super(DataSet, self).__init__()
    self.tag = None
    self.rtps = {}
    self.ctrls = {}

  def __str__(self):
    return 'Tag = %s\nRTPs=%sCTRLs=%s' % (self.tag, self.rtps, self.ctrls)

def extract_normal(filename):
  matchers = [ ('UDP', re.compile('UDP-PORT=(\d+)')), ('RTP-D', re.compile('RTP-DATA:([\S]+)')), ('RTCP-D', re.compile('RTCP-DATA:([\S]+)')), ('STUN-D', re.compile('STUN-DATA:([\S]+)')), ('RTP-I', re.compile('RTP-INT:([\S]+)')), ('CTRL-I', re.compile('CTRL-INT:([\S]+)')) ]
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
          seq = -1

        if label == 'RTCP-D' or label == 'STUN-D':
          pair = dataset.ctrls[remote].get(seq)
          if pair is None:
            dataset.ctrls[remote][seq] = Pair(right = seconds, label = label) 
          else:
            pair.right = seconds
            pair.label = label

          if self_id is None and label == 'STUN-D':
            self_id = comps[-2]


        elif label == 'RTP-D':
          pair = dataset.rtps[remote].get(seq)
          if pair is None:
            dataset.rtps[remote][seq] = Pair(right = seconds, label = label)
          else:
            pair.right = seconds
            pair.label = label

        elif label == 'RTP-I':
          try:
            dataset.rtps[remote][seq] =  Pair(left = seconds, label = label)
          except KeyError:
            dataset.rtps[remote] = {}
            dataset.rtps[remote][seq] =  Pair(left = seconds, label = label)
        elif label == 'CTRL-I':
          try:
            dataset.ctrls[remote][seq] = Pair(left = seconds, label = label)
          except KeyError:
            dataset.ctrls[remote] = {}
            dataset.ctrls[remote][seq] = Pair(left = seconds, label = label)

  return dataset, self_id


def get_limits(*args):
  max_t = 0
  min_t = 0x7fffffff
  for (dataset, self_id) in args:
    for (remote, dic) in dataset.ctrls.items(): 
      for (seq, pair) in dic.items():
        for t in (pair.left, pair.right):
          if t is not None:
            if t > max_t:
              max_t = t
            if t < min_t:
              min_t = t

  return (min_t, max_t)

def plot_ax(items, ax, min_t, max_t, id_map, portmap, colormap):
  max_s = 0
  min_s = 0x7fffffff
  legends = {}
  for (remote, dic) in items:

    seqs = dic.keys() 

    if min(seqs) < min_s:
      min_s = min(seqs)
    if max(seqs) > max_s:
      max_s = max(seqs)

  remote_count = 0
  for (remote, dic) in items:
    color = colormap[remote]
    legends[remote] = patches.Rectangle((0, 0,), 1, 5, color = color)
    remote_count += 1
    for (seq, pair) in dic.items():

      if pair.left is not None and pair.right is not None:
        x = pair.left - min_t
        length = pair.right -pair.left
      if pair.left is not None and pair.right is None:
        x = pair.left - min_t
        length = 4 if pair.left + 4 < max_t else max_t - pair.left
      if pair.left is None and pair.right is not None:
        x = pair.right - min_t - 0.1
        length = 0.1
        hatch = 'x'

      if pair.label == 'RTCP-D':
        color = 'k'

      rect = patches.Rectangle((x, seq), length, 1, fill = False, color = color)
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
  colors = ['b', 'g', 'r', 'c', 'm', 'y']
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

  col = 2
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
    ctrl_ax = fig.add_subplot(row, col, i + 2)
    ctrl_ax.set_xlabel('time (seconds)', fontsize = 8)
    ctrl_ax.set_ylabel('seq', fontsize = 8)
    ctrl_ax.set_title(tag + ' (CTRL)', fontsize = 8)
    i += 2

    plot_ax(dataset.rtps.items(), rtp_ax, min_t, max_t, id_map, portmap, colormap)
    plot_ax(dataset.ctrls.items(), ctrl_ax, min_t, max_t, id_map, portmap, colormap)


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

