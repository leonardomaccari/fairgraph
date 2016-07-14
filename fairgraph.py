import networkx as nx
import csv

class fairgraph():

    def __init__(self, network_graph_file, people_community_map,
                 people_community_graph, threshold):
        """ load three files:
            the graphml of the network graph, with 'email' attribute for each
            node; the community_map file, a CSV with lines of the kind 'email,
            community_id'; the people community graph, a graphml with weighted
            community graph """
        try:
            self.g = nx.read_graphml(network_graph_file)
        except:
            print "Could not import", network_graph_file

        self.community_map = {}
        try:
            with open(people_community_map, 'rb') as csvfile:
                for l in csv.reader(csvfile):
                    if not l or l[0].strip().startswith("#"):
                        continue
                    self.community_map[l[0]] = l[1]
        except Exception as e:
            print "Could not import", people_community_map, e

        try:
            self.g = nx.read_graphml(people_community_graph)
        except:
            print "Could not import", people_community_graph

        self.threshold = threshold



