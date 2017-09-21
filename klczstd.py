#!/usr/bin/python

# This is a dummy peer that just illustrates the available information your peers 
# have available.

# You'll want to copy this file to AgentNameXXX.py for various versions of XXX,
# probably get rid of the silly logging messages, and then add more logic.


import random
import numpy as np
import pandas as pd
import logging

from messages import Upload, Request
from util import even_split
from peer import Peer

from collections import Counter


class KlczStd(Peer):
	def post_init(self):
		print "post_init(): %s here!" % self.id
		self.dummy_state = dict()
		self.dummy_state["cake"] = "lie"
	
	def requests(self, peers, history):
		"""
		peers: available info about the peers (who has what pieces)
		history: what's happened so far as far as this peer can see

		returns: a list of Request() objects

		This will be called after update_pieces() with the most recent state.
		"""
		needed = lambda i: self.pieces[i] < self.conf.blocks_per_piece
		needed_pieces = filter(needed, range(len(self.pieces)))
		np_set = set(needed_pieces)  # sets support fast intersection ops.

		logging.debug("%s here: still need pieces %s" % (
			self.id, needed_pieces))

		logging.debug("%s still here. Here are some peers:" % self.id)
		for p in peers:
			logging.debug("id: %s, available pieces: %s" % (p.id, p.available_pieces))

		logging.debug("And look, I have my entire history available too:")
		logging.debug("look at the AgentHistory class in history.py for details")
		logging.debug(str(history))

		requests = []   # We'll put all the things we want here
		# Symmetry breaking is good...
		random.shuffle(needed_pieces)

		# request all available pieces from all peers!
		# (up to self.max_requests from each)
			
		all_pieces = []
		for peer in peers:
			all_pieces.append(peer.available_pieces)

		for peer in peers:
			isect = set(all_pieces).intersection(np_set)
			all_pieces_filter = [i for i in all_pieces if i in isect]
			pieces_count = Counter(all_pieces_filter)
			rare_pieces = pieces_count.keys()[::-1][:2]
			rare_pieces_post = set(rare_pieces).intersection(peer.available_pieces)
			n = min(self.max_requests, len(rare_pieces_post))
			for piece_id in random.sample(rare_pieces_post, n):
				start_block = self.pieces[piece_id]
				r = Request(self.id, peer.id, piece_id, start_block)
				requests.append(r)
				if self.pieces[piece_id] == self.conf.blocks_per_piece:
					np_set.discard(piece_id)

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

		peer_contribution = []
		if round >= 2: 
			for hist in np.concatenate((history.downloads[round-1],history.downloads[round-2])):
				from_you = hist.from_id
				num_blocks = hist.blocks
				if hist.to_id == self.id and "Seed" not in from_you:
					peer_contribution.append([from_you, num_blocks])

		peer_pd = pd.DataFrame(peer_contribution, columns = ["Peer", "Num"])
		peer_pd.groupby("Peer").sum()
		peer_np = peer_pd.sort().as_matrix()

		if len(requests) == 0:
			logging.debug("No one wants my pieces!")
			chosen = []
			bws = []
		else:
			logging.debug("Still here: uploading to the best peer")
			# change my internal state for no reason
			self.dummy_state["cake"] = "pie"

			###### history based on number of files they give you that you need
			
			n = min(len(requests), 3)
			contr_lst = [i for [i,j] in peer_np] 

			if n == 0:
				chosen = []
			else:
				chosen = contr_lst[:n-1]

			request_remaining = [i for i in contr_lst if i not in chosen]

			if len(contr_lst) == 0 or len(request_remaining) == 0:
				requested = random.choice(requests)
				chosen = np.append(chosen, requested.requester_id)
			else:
				requested = random.choice(request_remaining)
				chosen = np.append(chosen, requested)


			# Evenly "split" my upload bandwidth among the one chosen requester
			bws = even_split(self.up_bw, len(chosen))

		# create actual uploads out of the list of peer ids and bandwidths
		uploads = [Upload(self.id, peer_id, bw)
				   for (peer_id, bw) in zip(chosen, bws)]
			
		return uploads


# import random
# import logging

# from messages import Upload, Request
# from util import even_split
# from peer import Peer

# class Dummy(Peer):
#     def post_init(self):
#         print "post_init(): %s here!" % self.id
#         self.dummy_state = dict()
#         self.dummy_state["cake"] = "lie"
	
#     def requests(self, peers, history):
#         """
#         peers: available info about the peers (who has what pieces)
#         history: what's happened so far as far as this peer can see

#         returns: a list of Request() objects

#         This will be called after update_pieces() with the most recent state.
#         """
#         needed = lambda i: self.pieces[i] < self.conf.blocks_per_piece
#         needed_pieces = filter(needed, range(len(self.pieces)))
#         np_set = set(needed_pieces)  # sets support fast intersection ops.


#         logging.debug("%s here: still need pieces %s" % (
#             self.id, needed_pieces))

#         logging.debug("%s still here. Here are some peers:" % self.id)
#         for p in peers:
#             logging.debug("id: %s, available pieces: %s" % (p.id, p.available_pieces))

#         logging.debug("And look, I have my entire history available too:")
#         logging.debug("look at the AgentHistory class in history.py for details")
#         logging.debug(str(history))

#         requests = []   # We'll put all the things we want here
#         # Symmetry breaking is good...
#         random.shuffle(needed_pieces)
		
#         # Sort peers by id.  This is probably not a useful sort, but other 
#         # sorts might be useful
#         peers.sort(key=lambda p: p.id)
#         # request all available pieces from all peers!
#         # (up to self.max_requests from each)
#         for peer in peers:
#             av_set = set(peer.available_pieces)
#             isect = av_set.intersection(np_set)
#             n = min(self.max_requests, len(isect))
#             # More symmetry breaking -- ask for random pieces.
#             # This would be the place to try fancier piece-requesting strategies
#             # to avoid getting the same thing from multiple peers at a time.
#             for piece_id in random.sample(isect, n):
#                 # aha! The peer has this piece! Request it.
#                 # which part of the piece do we need next?
#                 # (must get the next-needed blocks in order)
#                 start_block = self.pieces[piece_id]
#                 r = Request(self.id, peer.id, piece_id, start_block)
#                 requests.append(r)

#         return requests

#     def uploads(self, requests, peers, history):
#         """
#         requests -- a list of the requests for this peer for this round
#         peers -- available info about all the peers
#         history -- history for all previous rounds

#         returns: list of Upload objects.

#         In each round, this will be called after requests().
#         """

#         round = history.current_round()
#         logging.debug("%s again.  It's round %d." % (
#             self.id, round))
#         # One could look at other stuff in the history too here.
#         # For example, history.downloads[round-1] (if round != 0, of course)
#         # has a list of Download objects for each Download to this peer in
#         # the previous round.

#         if len(requests) == 0:
#             logging.debug("No one wants my pieces!")
#             chosen = []
#             bws = []
#         else:
#             logging.debug("Still here: uploading to a random peer")
#             # change my internal state for no reason
#             self.dummy_state["cake"] = "pie"

#             request = random.choice(requests)
#             chosen = [request.requester_id]
#             # Evenly "split" my upload bandwidth among the one chosen requester
#             bws = even_split(self.up_bw, len(chosen))

#         # create actual uploads out of the list of peer ids and bandwidths
#         uploads = [Upload(self.id, peer_id, bw)
#                    for (peer_id, bw) in zip(chosen, bws)]
			
#         return uploads
