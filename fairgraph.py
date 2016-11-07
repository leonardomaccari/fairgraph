""" A class for redistributing the nodes ownership in a graph. Please note that
this module was not intended to be super-optimized. I preferred to have
clearness and easiness to read, which leads to do copies of data-structures and
some repeated operations could be avoided. I used it for graphs up to 150
nodes, but on decent hardware it should scale to hundreds.

Copyright 2016 Leonardo Maccari, leonardo.maccari@unitn.it
Released under the terms of the GPLv3 License"""

import networkx as nx
import csv
from collections import defaultdict
import numpy as np


class FairGraph(object):
    """ A class for redistributing the nodes ownership in a graph """

    def __init__(self, network_graph_file, people_community_map,
                 people_community_graph, treshold):
        """ load three files:
            the graphml of the network graph, with 'email' attribute for each
            node; the community_map file, a CSV with lines of the kind 'email,
            community_id'; the people community graph, a graphml with weighted
            community graph """
        self.owner_nodes = defaultdict(list)
        try:
            self.g = nx.read_graphml(network_graph_file)
            for node in self.g.nodes(data=True):
                email = filter(lambda(x):
                               x not in "<>", node[1]['email']).strip()
                self.owner_nodes[email].append(node)
        except IOError as e:
            print "Could not import", network_graph_file, ":", e
            exit()
        self.community_map = {}
        self.communities = defaultdict(list)
        try:
            with open(people_community_map, 'rb') as csvfile:
                for l in csv.reader(csvfile):
                    if not l or l[0].strip().startswith("#"):
                        continue
                    email = filter(lambda(x): x not in "<>", l[0]).strip()
                    self.community_map[email] = l[1]
                    self.communities[l[1]].append(email)
        except IOError as e:
            print "Could not import", people_community_map, ":", e
            exit()

        try:
            self.community_graph = nx.read_graphml(people_community_graph)
        except IOError as e:
            print "Could not import", people_community_graph, ":", e
            exit()

        self.treshold = treshold*(len(self.g))

    def backup_data(self):
        """ backup data, in order to be able to roll back when treshold is
        too high """
        self.backup = {'owner_nodes': {}, 'community_map': {}, 'graph': None}
        for owner in self.owner_nodes:
            self.backup['owner_nodes'][owner] = self.owner_nodes[owner][:]
        for com in self.community_map:
            self.backup['community_map'][com] = self.community_map[com][:]
        self.backup['graph'] = self.g.copy()

    def restore_backup(self):
        """ roll back backupped data """
        for owner in self.backup['owner_nodes']:
            self.owner_nodes[owner] = self.backup['owner_nodes'][owner][:]
        for com in self.backup['community_map']:
            self.community_map[com] = self.backup['community_map'][com][:]
        self.g = self.backup['graph'].copy()

    def mc_size_nodes(self, nodes):
        """ return the size of the main connected component when removing
        [nodes] from the graph """
        copy_g = self.g.copy()
        for n in nodes:
            copy_g.remove_node(n)
        main_c = sorted(nx.connected_components(copy_g),
                        key=len, reverse=True)[0]
        return len(main_c)

    def mc_size_owner(self, owner):
        """ return the size of the main connected component when removing
        the nodes that belong to a single owner"""
        return self.mc_size_nodes([x[0] for x in self.owner_nodes[owner]])

    def compute_nodes_ranking(self):
        """ return the size of the main connected component when removing
        a node, for all nodes"""
        ranking = {}
        for node in self.g.nodes():
            ranking[node] = self.mc_size_nodes([node])
        return sorted(ranking.items(), key=lambda(x): x[1])

    def compute_owners_ranking(self):
        """ return the size of the main connected component when removing
        the nodes that belong to a single owner, for all owners"""
        ranking = {}
        for owner in self.owner_nodes:
            ranking[owner] = self.mc_size_owner(owner)
        return sorted(ranking.items(), key=lambda(x): x[1])

    def reassign_to(self, node, person):
        """ reassign a node, and check if the reassignment still respects the
        treshold, else undo and return False """
        current_nodes = list(zip(*self.owner_nodes[person])[0])
        leaf_nodes = [x for x in current_nodes
                      if len(nx.neighbors(self.g, x)) == 1]
        if self.mc_size_nodes(current_nodes + [node]) >\
                (self.treshold - len(leaf_nodes)):
            current_owner = self.g.node[node]['email']
            self.g.node[node]['email'] = person
            full_data_node = [f for f in self.owner_nodes[current_owner]
                              if f[0] == node][0]
            self.owner_nodes[person].append(full_data_node)
            self.owner_nodes[current_owner].remove(full_data_node)
            return True
        else:
            return False

    def get_random_friend(self, node, exclude=None):
        """ randomly choose a friend of the owner of the node that
        satisfies the following:
         - he owns at least a node
         - he is not in the exclude list
         - probability of being chosen linearly decrease with the
           minimum distance of the owned nodes in the network graph wrt
           target node """
        friend_list = []
        weight_list = []

        # TODO extend to close-by communities
        community = self.communities[self.community_map[
            self.g.node[node]['email']]][:]
        for f in exclude + [self.g.node[node]['email']]:
            community.remove(f)
        for friend in community:
            if friend in exclude or friend not in self.owner_nodes:
                continue
            friend_list.append(friend)
            distance = min([nx.shortest_path_length(self.g, node, n[0])
                            for n in self.owner_nodes[friend]])
            weight_list.append(distance)
        if not friend_list:
            return None
        s = sum(weight_list)
        weight_list = [float(w)/s for w in weight_list]
        return np.random.choice(friend_list, 1, weight_list)[0]

    def get_minimum_robustness(self):
        min_robustness = len(self.g)
        most_fragile_node = None
        for node in self.g.nodes():
            new_graph = self.g.copy()
            new_graph.remove_node(node)
            mcs = nx.connected_components(new_graph)[0]
            if len(mcs) < min_robustness:
                min_robustness = len(mcs)
                most_fragile_node = node
        return most_fragile_node, min_robustness

    def plot_robustness(self):
        """ plot the distribution of the robustness of each person """
        
        print "#Owner".ljust(30), ", Fragility".ljust(5)
        for owner, nodes in sorted(self.owner_nodes.items(),
                                   key=lambda(x): -len(x[1])):
            bare_nodes = zip(*nodes)[0]
            print owner.ljust(30), ",", self.mc_size_nodes(bare_nodes)

    def redistribute_top_owner(self):
        """ do the whole reassigning process of nodes from the top owner"""
        self.backup_data()
        R_o = self.compute_owners_ranking()
        R_n = self.compute_nodes_ranking()
        most_fragile_node, min_robustness = R_n[0]
        self.treshold = min(self.treshold, min_robustness)
        most_fragile_owner = R_o[0][0]
        if self.treshold < 0.1*len(self.g):
            print "Your network is wicked!"
            print "If you remove node", most_fragile_node
            print "the main connected component size is", min_robustness
            print "cowardyly refusing to work on such contitions!"
            exit(1)
        if R_o[0][1] > self.treshold:
            print "Nothing to do", R_o[0][0], self.treshold
            exit()
        ranked_owned_nodes = [x[0] for x in R_n if x[0] in
                              zip(*self.owner_nodes[most_fragile_owner])[0]]
        leaf_nodes = [x for x in ranked_owned_nodes
                      if len(nx.neighbors(self.g, x)) == 1]
        exit_loop = False
        while not exit_loop:
            print "======== Treshold set to", self.treshold
            print "Reassigning nodes from", most_fragile_owner,\
                  "with robustness", R_o[0][1]
            self.restore_backup()
            reassigned_nodes = {}
            for node in [x for x in ranked_owned_nodes if x not in leaf_nodes]:
                avoid_list = []
                while True:
                    new_friend = self.get_random_friend(node, avoid_list)
                    if not new_friend:
                        break  # while loop
                    if self.reassign_to(node, new_friend):
                        reassigned_nodes[node] = new_friend
                        new_owned_nodes = set(ranked_owned_nodes) -\
                            set(reassigned_nodes.keys())
                        new_ranking = self.mc_size_nodes(new_owned_nodes)
                        """ Note: the robustness of a person, may not change
                        when you reassign one node. In fact fagility ==
                        size of main connected component, the MCC may not
                        change upon removal of one node, becouse the other
                        nodes you remove from the same owner may create the
                        same fracture (cumulatively) that the node you
                        just reassigned can create """
                        print "node", node, "reassigned from",\
                              most_fragile_owner, "to", new_friend
                        if new_ranking > self.treshold - len(leaf_nodes):
                            exit_loop = True
                        else:
                            print "person robustness", new_ranking,\
                                "/", self.treshold, len(new_owned_nodes),\
                                len(self.owner_nodes[most_fragile_owner])
                        break  # while loop
                    else:
                        avoid_list.append(new_friend)
                if exit_loop:
                    break  # for loop
            self.treshold -= 1
        return reassigned_nodes
