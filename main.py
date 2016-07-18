#! /usr/bin/python

""" Copyright 2016 Leonardo Maccari, leonardo.maccari@unitn.it 
Released under the terms of the GPLv3 License"""

import sys
from fairgraph import FairGraph

if len(sys.argv) < 4:
    print "usage: ./main.py graph.graphml commuity.csv community_graph.csv "
    exit()
f = FairGraph(sys.argv[1], sys.argv[2], sys.argv[3], 0.9)
f.redistribute_top_owner()
f.plot_robustness()
