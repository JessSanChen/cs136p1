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

class g41PropShare(Peer):
    def post_init(self):
        print(("post_init(): %s here!" % self.id))
        self.dummy_state = dict()
        self.dummy_state["cake"] = "lie"
    
    def requests(self, peers, history):
        needed = lambda i: self.pieces[i] < self.conf.blocks_per_piece 
        needed_pieces = list(filter(needed, list(range(len(self.pieces)))))
        # np_set = set(needed_pieces)  # sets support fast intersection ops.

        logging.debug("%s here: still need pieces %s" % (
            self.id, needed_pieces))

        logging.debug("%s still here. Here are some peers:" % self.id)
        for p in peers:
            logging.debug("id: %s, available pieces: %s" % (p.id, p.available_pieces))

        logging.debug("And look, I have my entire history available too:")
        logging.debug("look at the AgentHistory class in history.py for details")
        logging.debug(str(history))

        # go thru all needed_pieces, log availability
        random.shuffle(needed_pieces)

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
        # One could look at other stuff in the history too here.
        # For example, history.downloads[round-1] (if round != 0, of course)
        # has a list of Download objects for each Download to this peer in
        # the previous round.

        
        if len(requests) == 0:
            logging.debug("No one wants my pieces!")
            chosen = []
            bws = []
            uploads = []
        else:
            logging.debug("Still here: uploading to a random peer")

            interested_peers = dict()

            for req in requests:
                interested_peers[req.requester_id] = 0

            for download in history.downloads[round - 1]:
                if download.from_id in interested_peers:
                    interested_peers[download.from_id] += download.blocks

            prev_downloads = {key : val for key, val in interested_peers.items()
                   if val > 0}
            no_prev_downloads = {key : val for key, val in interested_peers.items()
                   if val == 0}
           

            if len(no_prev_downloads) == len(interested_peers):
                lucky = random.choice(list(no_prev_downloads.keys()))
                uploads = [Upload(self.id, lucky, self.up_bw)]
            
            else:
                chosen = list(prev_downloads.keys())
                other = list(no_prev_downloads.keys())
                bws = []

                if len(prev_downloads) == len(interested_peers):
                    for peer in chosen:
                        proportion = (interested_peers[peer])/(sum(list(prev_downloads.values())))
                        bws.append(int(proportion*(self.up_bw)))
                else:
                    for peer in chosen:
                        proportion = prev_downloads[peer]/(sum(list(prev_downloads.values())))
                        bws.append(int(proportion*0.9*(self.up_bw)))
                    
                    other_rand = random.choice(other)
                    chosen.append(other_rand)
                    total_bw = sum(bws)
                    bws.append(self.up_bw - total_bw)

                
                # create actual uploads out of the list of peer ids and bandwidths
                uploads = [Upload(self.id, peer_id, bw)
                    for (peer_id, bw) in zip(chosen, bws)]  
                
        return uploads