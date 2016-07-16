#! /usr/bin/python
import sys
from fairgraph import FairGraph

if len(sys.argv) < 4:
    print "usage: ./main.py graph.graphml commuity.csv community_graph.csv "
    exit()
f = FairGraph(sys.argv[1], sys.argv[2], sys.argv[3], 0.9)
f.redistribute_top_owner()
