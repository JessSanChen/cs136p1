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

class g41Tyrant(Peer):
    def post_init(self):
        print(("post_init(): %s here!" % self.id))
        self.m = 4
        self.optimistic_peer = None
        
    
    def requests(self, peers, history):
        needed = lambda i: self.pieces[i] < self.conf.blocks_per_piece 
        needed_pieces = list(filter(needed, list(range(len(self.pieces)))))

        logging.debug("%s here: still need pieces %s" % (
            self.id, needed_pieces))

        logging.debug("%s still here. Here are some peers:" % self.id)
        for p in peers:
            logging.debug("id: %s, available pieces: %s" % (p.id, p.available_pieces))

        logging.debug("And look, I have my entire history available too:")
        logging.debug("look at the AgentHistory class in history.py for details")
        logging.debug(str(history))

        
        random.shuffle(needed_pieces)

        # go thru all needed_pieces, log availability
        dict_prefs = dict()
        for piece in needed_pieces:
            for peer in peers:
                if piece in peer.available_pieces:
                    if piece in dict_prefs.keys():
                        dict_prefs[piece] += 1
                    else:
                        dict_prefs[piece] = 1
        
        # sort dictionary by the number of people that have an item (rarest first)
        order = list(dict(sorted(dict_prefs.items(), key=lambda x: x[1])).keys())

        requests = []

        random.shuffle(peers)

        for peer in peers:
            # make sure to randomize iset!!
            available_list = list(peer.available_pieces)
            isect = [piece for piece in available_list if piece in needed_pieces]
            # print("list of available pieces of a peer: ", available_list)
            random.shuffle(isect)
            sorted_by_pref = sorted(isect, key=lambda x: order.index(x) if x in order else len(order))
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

        if len(requests) == 0:
            logging.debug("No one wants my pieces!")
            chosen = []
            bws = []
        else:
            # estimate d_i
            ### for first round or two, initialize d_1 as something reasonable
            ### case 1: peer has never unblocked us before.
            ### case 2: has unblocked us before.
            # estimate u_i
            ### initialize u_1 to est min capacity that ppl can have
            ### case 1: if we unblock them, but they don't unblock us.
            ### case 2: if they unblock us.
            # rank all requesters by decreasing order of d_i/u_i
            # help in proportion of d_i/u_i
            # keep going until run out of bandwidth (dump remaining on last person)
            # every time, the # ppl unblocked may vary

            # store requesters. {peer_i: {"d": d, "u": u}}
            requesters = {}
            for request in requests:
                requesters[request.id] = dict()

            # for first 2 rounds, just initialize
            if round < 3:
                for id in list(requesters):
                    requesters[id]["d"] = 8
                    requesters[id]["u"] = 8 # BIG ASSUMPTION
            else:
                # find which peers have unblocked before, and # blocks given most recently
                # {peer_id: {"round": most_recent_round_num, "blocks": #_blocks}}
                unblockers = dict()
                for round in range(history.downloads):
                    for download in history.downloads[round]:
                        unblockers[download.from_id] = {"round": round, "blocks": download.blocks}
                
                for peer in peers:
                    if peer not in unblockers: # peer i has never unblocked us before
                        d_i = (len(list(peer.available_pieces))*self.conf.blocks_per_piece) / (round * 4)
                    else: # has unblocked before
                        d_i = unblockers[peer.id]["blocks"]
                    requesters[peer.id]["d"] = d_i



            request = random.choice(requests)
            chosen = [request.requester_id]
            # Evenly "split" my upload bandwidth among the one chosen requester
            bws = even_split(self.up_bw, len(chosen))

        # create actual uploads out of the list of peer ids and bandwidths
        uploads = [Upload(self.id, peer_id, bw)
                   for (peer_id, bw) in zip(chosen, bws)]
            
        return uploads
