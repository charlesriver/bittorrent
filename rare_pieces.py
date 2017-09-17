all_pieces = set()
for peer in peers:
    all_pieces.update(peer.available_pieces)
isect = all_pieces.intersection(np_set)
all_pieces_filter = [i for i in all_pieces if i in isect]
pieces_count = Counter(all_pieces_filter)
rare_pieces = pieces_count.keys()[:-2]

for peer in peers:
    rare_pieces = set(rare_pieces).intersection(peer.available_pieces)
    n = min(self.max_requests, len(rare_pieces))
    for piece_id in random.sample(rare_pieces, n):
        start_block = self.pieces[piece_id]
        r = Request(self.id, peer.id, piece_id, start_block)
        requests.append(r)

return requests