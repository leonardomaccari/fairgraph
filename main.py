#! /usr/bin/python
import sys
from fairgraph import fairgraph

if len(sys.argv) < 4:
    print "usage: ./main.py graph.graphml commuity.csv community_graph.csv "
    exit()
f = fairgraph(sys.argv[1], sys.argv[2], sys.argv[3], 0.9)
