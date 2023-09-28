#!/usr/bin/python

# This is a dummy peer that just illustrates the available information your peers 
# have available.

# You'll want to copy this file to AgentNameXXX.py for various versions of XXX,
# probably get rid of the silly logging messages, and then add more logic.

import random
import logging

from messages import Upload, Request
from util import even_split
from peer import Peer

class g41Std(Peer):
    def post_init(self):
        # self.dummy_state = dict()
        # self.dummy_state["cake"] = "lie"
        print(("post_init(): %s here!" % self.id))
        
        # inherits from Peer class, which takes care of most properties
        # but needs to do post_init() stuff?

        self.m = 4
        self.optimistic_peer = None
        
    
    def requests(self, peers, history):
        needed = lambda i: self.pieces[i] < self.conf.blocks_per_piece
        needed_pieces = list(filter(needed, list(range(len(self.pieces)))))
        np_set = set(needed_pieces)  # sets support fast intersection ops.

        logging.debug("%s here: still need pieces %s" % (
            self.id, needed_pieces))

        logging.debug("%s still here. Here are some peers:" % self.id)
        for p in peers:
            logging.debug("id: %s, available pieces: %s" % (p.id, p.available_pieces))

        logging.debug("And look, I have my entire history available too:")
        logging.debug("look at the AgentHistory class in history.py for details")
        logging.debug(str(history))

        # create a dictionary of key value pairs where the key is the piece, 
        # the value is the number of agents that have that piece
        dict_prefs = {}
        for piece in needed_pieces:
            dict_prefs[piece] = 0
        for peer in peers:
            for piece in peer.available_pieces:
                if piece in dict_prefs:
                    dict_prefs[piece] += 1
                    

        # sort dictionary by the number of people that have an item (rarest first)
        dict_prefs_sorted = dict(sorted([items for items in dict_prefs.items() if items[1] > 0], key=lambda x: x[1]))
        order = list(dict_prefs_sorted.keys())

        requests = []

        for peer in peers:
            # make sure to randomize iset!!
            # change to list?? set not subscriptable
            random.shuffle(list(peer.available_pieces))
            sorted_by_pref = [piece for x in order for piece in peer.available_pieces if piece[0] == x]
            n = min(self.max_requests, len(sorted_by_pref))
            for i in range(n):
                start_block = self.pieces[sorted_by_pref[i]]
                r = Request(self.id, peer.id, sorted_by_pref[i], start_block)
                requests.append(r)
        
        return requests

    def uploads(self, requests, peers, history):
        """
        requests -- a list of the requests for this peer for this round
        peers -- available info about all the peers
        history -- history for all previous rounds

        returns: list of Upload objects.

        In each round, this will be called after requests().
        """

        round = history.current_round()
        logging.debug("%s again.  It's round %d." % (
            self.id, round))
        # One could look at other stuff in the history too here.
        # For example, history.downloads[round-1] (if round != 0, of course)
        # has a list of Download objects for each Download to this peer in
        # the previous round.

        if len(requests) == 0:
            logging.debug("No one wants my pieces!")
            chosen = []
            bws = []
        else:
            logging.debug("Still here: uploading to a random peer")
            
            # order interested peers in decreasing avg download rate in last 20 seconds
            # break ties at random
            # exclude peers that have not sent data
            # m-1 interested peers unblocked via regular unblock
            # reference client divides its upload capacity (bandwidth) equally into each of m slots
            # every 3 rounds, optimistically unblock interested (not chosen) peer

            # request = random.choice(requests)
            # chosen = [request.requester_id]
            # # Evenly "split" my upload bandwidth among the one chosen requester
            # bws = even_split(self.up_bw, len(chosen))

            # history.downloads[round-1] is list of download objects

            # initialize interested peers
            interested_peers = dict()
            for req in requests:
                interested_peers[req.requester_id] = 0
            # log all downloads from past 2 rounds
            for download in history.downloads[round-1] + history.downloads[round-2]:
                if download.from_id in interested_peers:
                    interested_peers[download.from_id] += 1
            # sort by decr avg download; exclude those with 0 downloads
            interested_peers = dict(sorted(interested_peers.items(), key = lambda x: x[1], reverse = True))
            interested_peers = {x:y for x,y in interested_peers.items() if y != 0}
            # take the first m-1 for regular unblock
            chosen = interested_peers.keys[:self.m]
            # optimistic unblock
            if round % 3 == 0:
                self.optimistic_peer = random.choice(interested_peers.keys[self.m:])
            chosen.append(self.optimistic_peer)
            # evenly split
            bws = even_split(self.up_bw, len(chosen))

        # create actual uploads out of the list of peer ids and bandwidths
        uploads = [Upload(self.id, peer_id, bw)
                   for (peer_id, bw) in zip(chosen, bws)]
            
        return uploads
