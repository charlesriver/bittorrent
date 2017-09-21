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
from klczstd import KlczStd

class KlczTyrant(KlczStd):
    def __init__(self, config, id, init_pieces, up_bandwidth):
        self.conf = config
        self.id = id
        self.pieces = init_pieces[:]
        # bandwidth measured in blocks-per-time-period
        self.up_bw = up_bandwidth

        # This is an upper bound on the number of requests to send to
        # each peer -- they can't possibly handle more than this in one round
        self.max_requests = self.conf.max_up_bw / self.conf.blocks_per_piece + 1
        self.max_requests = min(self.max_requests, self.conf.num_pieces)

        # store estimates of flows and thresholds over multiple rounds
        self.fs = dict()
        self.taus = dict()

        self.post_init()

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

        # BitTyrant parameters
        gamma = .1
        r = 3
        alpha = .2

        tau_init = 1 # CHECK THIS

        # if first round, initialize flow and threshold estimates
        fs = self.fs
        taus = self.taus
        if round == 0:
            for peer_j in peers:
                fs[peer_j.id] = 1 # need some initial value?
                taus[peer_j.id] = tau_init # AS A FUNCTION OF MAX BW??

        # otherwise, update flow and threshold estimates from last round's results
        if round > 0:
            # set for who was unchoked in the last round
            unchoked = set()
            for u in history.uploads[round-1]:
                unchoked.add(u.to_id)
            # set for who unchoked you in the last round
            unchokers = set()
            flow = dict()
            for d in history.downloads[round-1]:
                unchokers.add(d.from_id)
                flow[d.from_id] = d.blocks
            # update estimates of thresholds and flows
            for j in unchoked:
                if j not in unchokers:
                    taus[j] = int((1 + alpha)*taus[j])
                if j in unchokers:
                    fs[j] = flow[j]
            # try decreasing threshold from agents unchoking for a long time
            if round >= r:
                # collect all unchokers from previous r rounds
                all_unchokers = [0]*r
                for i in range(1, r+1):
                    unchokers = set()
                    for d in history.downloads[round-i]:
                        unchokers.add(d.from_id)
                    all_unchokers[i-1] = unchokers
                # take intersection of unchokers over every round
                exploitable_unchokers = reduce(lambda x, y: x.intersection(y), all_unchokers)
                # reduce thresholds
                for j in exploitable_unchokers:
                    taus[j] = max(int((1 - gamma)*taus[j]),1)

        # rank peers by ROI
        ranked = []
        for peer in peers:
            # roi is some large number if threshold is 0
            if taus[peer.id] == 0:
                roi = self.conf.max_up_bw
            else:
                roi = int(fs[peer.id] / taus[peer.id]) # round down
            ranked.append((peer.id, roi)) # round down
        ranked.sort(key = lambda t: t[1], reverse=True)

        # actually do the uploading
        if len(requests) == 0:
            logging.debug("No one wants my pieces!")
            chosen = []
            bws = []
        else:
            logging.debug("Still here: uploading according to ROI")
            # max upload capacity to use in swarm (use all available)
            cap = self.up_bw
            # only upload to peers who request
            requesters = set()
            for rq in requests:
                requesters.add(rq.requester_id)
            ranked = filter(lambda p: p[0] in requesters, ranked)
            # decide who to unchoke until run out of capacity
            chosen = []
            cumsum = 0
            for i in xrange(len(ranked)):
                cumsum += ranked[i][1]
                if cumsum > cap:
                    break
                chosen.append(ranked[i][0])
            # give requesters threshold bandwidth
            bws = [taus[j] for j in chosen]

        # create actual uploads out of the list of peer ids and bandwidths
        uploads = [Upload(self.id, peer_id, bw)
                   for (peer_id, bw) in zip(chosen, bws)]
            
        return uploads
