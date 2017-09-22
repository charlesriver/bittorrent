#!/usr/bin/python

import random
import logging

from messages import Upload, Request
from util import even_split
from peer import Peer
from klcztyrant import KlczTyrant

class KlczTourney(KlczTyrant):

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
        gamma = .5
        r = 2
        alpha = .5

        tau_init = int(self.up_bw / len(peers))

        # if first round, initialize flow and threshold estimates
        fs = self.fs
        taus = self.taus
        haves = self.haves
        if round == 0:
            for peer_j in peers:
                fs[peer_j.id] = int(.25*(self.conf.max_up_bw + self.conf.min_up_bw)/2.) # need some initial value?
                taus[peer_j.id] = tau_init # AS A FUNCTION OF MAX BW??
                haves[peer_j.id] = [len(peer_j.available_pieces), 1]

        # otherwise, update flow and threshold estimates from last round's results
        if round > 0:
            # estimate f_ij by changes in have message, overwrite as needed below
            for p in peers:
                if haves[p.id][0]-len(p.available_pieces) == 0:
                    haves[p.id][1] = haves[p.id][1] + 1
                else:
                    haves[p.id][0] = len(p.available_pieces)
                    fs[p.id] = int(self.conf.blocks_per_piece / haves[p.id][1])
                    haves[p.id][1] = 1

            # update estimates from interactions with other players
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
            ranked.append([peer.id, roi]) # round down
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
            for j in range(len(ranked)):
                cumsum += taus[ranked[j][0]]
                if cumsum > cap:
                    cumsum -= taus[ranked[j][0]] # store the balance
                    break
                chosen.append(ranked[j][0])
            # give requesters threshold bandwidth
            bws = [taus[j] for j in chosen]
            if bws != []:
                bws[random.choice(range(len(bws)))] += cap - cumsum # give excess bandwidth to the first person

        # create actual uploads out of the list of peer ids and bandwidths
        uploads = [Upload(self.id, peer_id, bw)
                   for (peer_id, bw) in zip(chosen, bws)]
            
        return uploads
