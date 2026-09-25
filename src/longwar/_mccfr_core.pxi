cdef class FastCFRNode:
    cdef void* action_storage
    cdef uint64_t* action_codes
    cdef double* regrets
    cdef double* strategy_sums
    cdef int action_count
    cdef public long visits
    cdef public long average_visits

    def __cinit__(self):
        self.action_storage = NULL
        self.action_codes = NULL
        self.regrets = NULL
        self.strategy_sums = NULL
        self.action_count = 0
        self.visits = 0
        self.average_visits = 0

    def __dealloc__(self):
        if self.action_storage != NULL:
            free(self.action_storage)

    cdef void initialize_actions(
        self,
        uint64_t* actions,
        int n,
    ) except *:
        cdef int i
        cdef size_t bytes_needed

        if self.action_count != 0:
            return

        bytes_needed = n * (
            sizeof(uint64_t)
            + sizeof(double)
            + sizeof(double)
        )
        self.action_storage = malloc(bytes_needed)
        if self.action_storage == NULL:
            raise MemoryError("Unable to allocate fast CFR node actions")

        self.action_codes = <uint64_t*>self.action_storage
        self.regrets = <double*>(self.action_codes + n)
        self.strategy_sums = self.regrets + n
        self.action_count = n

        for i in range(n):
            self.action_codes[i] = actions[i]
            self.regrets[i] = 0.0
            self.strategy_sums[i] = 0.0

    cdef void strategy_into(
        self,
        uint64_t* actions,
        int n,
        double* probabilities,
    ) except *:
        cdef int i
        cdef double total = 0.0
        cdef double value

        if self.action_count == 0:
            self.initialize_actions(actions, n)
        elif self.action_count != n:
            raise RuntimeError(
                f"Action count changed inside information set: "
                f"{self.action_count} != {n}"
            )

        for i in range(n):
            if self.action_codes[i] != actions[i]:
                raise RuntimeError(
                    "Action ordering changed inside information set"
                )
            value = self.regrets[i]
            if value > 0.0:
                probabilities[i] = value
                total += value
            else:
                probabilities[i] = 0.0

        if total > 0.0:
            for i in range(n):
                probabilities[i] /= total
        else:
            value = 1.0 / n
            for i in range(n):
                probabilities[i] = value

    cdef void accumulate_into(
        self,
        double* probabilities,
        int n,
        double reach_weight,
    ) noexcept:
        cdef int i
        for i in range(n):
            self.strategy_sums[i] += reach_weight * probabilities[i]
        self.average_visits += 1

    cdef void update_regrets(
        self,
        double* utilities,
        int n,
        double node_utility,
    ) noexcept:
        cdef int i
        for i in range(n):
            self.regrets[i] += utilities[i] - node_utility

    cdef int find_action(self, uint64_t action) noexcept:
        cdef int i
        for i in range(self.action_count):
            if self.action_codes[i] == action:
                return i
        return -1

    property regret_sum:
        def __get__(self):
            return {
                self.action_codes[i]: self.regrets[i]
                for i in range(self.action_count)
            }

    property strategy_sum:
        def __get__(self):
            return {
                self.action_codes[i]: self.strategy_sums[i]
                for i in range(self.action_count)
            }

    property allocated_action_bytes:
        def __get__(self):
            return self.action_count * (
                sizeof(uint64_t)
                + sizeof(double)
                + sizeof(double)
            )

    def strategy(self, actions=None):
        cdef list keys
        cdef int i, ix
        cdef double total = 0.0
        cdef double value
        cdef dict result = {}

        keys = (
            [self.action_codes[i] for i in range(self.action_count)]
            if actions is None
            else list(actions)
        )
        for key in keys:
            ix = self.find_action(<uint64_t>key)
            if ix >= 0 and self.regrets[ix] > 0.0:
                total += self.regrets[ix]
        if total <= 0.0:
            if not keys:
                return {}
            value = 1.0 / len(keys)
            return {key: value for key in keys}
        for key in keys:
            ix = self.find_action(<uint64_t>key)
            value = self.regrets[ix] if ix >= 0 else 0.0
            result[key] = (value if value > 0.0 else 0.0) / total
        return result

    def average_strategy(self, actions=None):
        cdef list keys
        cdef int i, ix
        cdef double total = 0.0
        cdef double value
        cdef dict result = {}

        keys = (
            [self.action_codes[i] for i in range(self.action_count)]
            if actions is None
            else list(actions)
        )
        for key in keys:
            ix = self.find_action(<uint64_t>key)
            if ix >= 0 and self.strategy_sums[ix] > 0.0:
                total += self.strategy_sums[ix]
        if total <= 0.0:
            return self.strategy(keys)
        for key in keys:
            ix = self.find_action(<uint64_t>key)
            value = self.strategy_sums[ix] if ix >= 0 else 0.0
            result[key] = (value if value > 0.0 else 0.0) / total
        return result


cdef double _packed_traverse(
    FastEngine engine,
    NativeHeuristicEvaluator evaluator,
    FastState state,
    int traverser,
    int depth,
    int max_depth,
    object nodes,
    object rng,
    double leaf_scale,
    double reach0,
    double reach1,
    list scratch,
):
    cdef int actor, child_depth, n, i, sampled_index
    cdef uint64_t actions[MAX_ACTIONS]
    cdef double probabilities[MAX_ACTIONS]
    cdef double utilities[MAX_ACTIONS]
    cdef bytes info_key
    cdef object raw_node
    cdef FastCFRNode node
    cdef FastState child
    cdef double probability
    cdef double utility
    cdef double node_utility = 0.0
    cdef double threshold
    cdef double cumulative = 0.0

    if state.phase == PHASE_COMPLETE:
        return 1.0 if state.winner == traverser else -1.0

    if depth >= max_depth:
        return tanh(evaluator.evaluate_fast(state, traverser) / leaf_scale)

    actor = state.active_player
    n = engine.legal_actions_into(state, &actions[0])
    if n <= 0:
        raise RuntimeError("Packed non-terminal state has no legal actions")

    info_key = engine.information_key_fast(state, actor)
    raw_node = nodes.get(info_key)
    if raw_node is None:
        node = FastCFRNode()
        nodes[info_key] = node
    else:
        node = <FastCFRNode>raw_node

    node.visits += 1
    node.strategy_into(&actions[0], n, &probabilities[0])
    child_depth = depth + 1

    if actor == traverser:
        for i in range(n):
            probability = probabilities[i]
            child = <FastState>scratch[child_depth]
            child.copy_from_fast(state)
            engine.apply_fast(child, actions[i])
            if actor == 0:
                utility = _packed_traverse(
                    engine, evaluator, child, traverser, child_depth, max_depth,
                    nodes, rng, leaf_scale,
                    reach0 * probability, reach1, scratch,
                )
            else:
                utility = _packed_traverse(
                    engine, evaluator, child, traverser, child_depth, max_depth,
                    nodes, rng, leaf_scale,
                    reach0, reach1 * probability, scratch,
                )
            utilities[i] = utility
            node_utility += probability * utility

        node.update_regrets(&utilities[0], n, node_utility)
        return node_utility

    node.accumulate_into(
        &probabilities[0],
        n,
        1.0,  # Own reach is already represented by opponent sampling.
    )
    threshold = rng.random()
    sampled_index = n - 1
    for i in range(n):
        cumulative += probabilities[i]
        if threshold <= cumulative:
            sampled_index = i
            break

    probability = probabilities[sampled_index]
    child = <FastState>scratch[child_depth]
    child.copy_from_fast(state)
    engine.apply_fast(child, actions[sampled_index])
    if actor == 0:
        return _packed_traverse(
            engine, evaluator, child, traverser, child_depth, max_depth,
            nodes, rng, leaf_scale,
            reach0 * probability, reach1, scratch,
        )
    return _packed_traverse(
        engine, evaluator, child, traverser, child_depth, max_depth,
        nodes, rng, leaf_scale,
        reach0, reach1 * probability, scratch,
    )


def packed_external_sampling_traverse(
    FastEngine engine,
    FastState state,
    int traverser,
    *,
    int depth,
    int max_depth,
    nodes,
    rng,
    double leaf_scale=100.0,
    scratch=None,
    NativeHeuristicEvaluator evaluator=None,
):
    if scratch is None:
        scratch = [FastState() for _ in range(max_depth + 1)]
    if evaluator is None:
        evaluator = NativeHeuristicEvaluator(engine)
    return _packed_traverse(
        engine,
        evaluator,
        state,
        traverser,
        depth,
        max_depth,
        nodes,
        rng,
        leaf_scale,
        1.0,
        1.0,
        scratch,
    )


def make_scratch(int max_depth):
    return [FastState() for _ in range(max_depth + 1)]



def stable_information_id_from_fast_key(FastEngine engine, bytes key):
    """Translate the current binary key to the public stable policy id."""
    data = key
    i = 0
    version = data[i]
    i += 1
    if version != 5:
        raise ValueError(f"Unsupported fast information-key version: {version}")

    card_ids = engine.card_ids
    n_cards = len(card_ids)

    player = data[i]
    i += 1
    phase_code = data[i] - 1
    i += 1
    phase = ("battle", "choose_first", "complete")[phase_code]
    battle = data[i] | (data[i + 1] << 8)
    i += 2
    active_player = data[i] - 1
    i += 1

    passed = [bool(data[i]), bool(data[i + 1])]
    i += 2

    pass_len = data[i]
    i += 1
    pass_order = []
    for _ in range(pass_len):
        pass_order.append(data[i] - 1)
        i += 1

    discarded_this_battle = []
    command = []
    hero_used = []
    operations_this_battle = []
    for _ in range(2):
        discarded_this_battle.append(data[i])
        command.append(data[i + 1] | (data[i + 2] << 8))
        hero_used.append(bool(data[i + 3]))
        operations_this_battle.append(data[i + 4] | (data[i + 5] << 8))
        i += 6

    pending_draw_raw = data[i] - 1
    i += 1
    pending_draw_discard_for = (
        None if pending_draw_raw < 0 else pending_draw_raw
    )

    board = [[], []]
    for owner in range(2):
        for local in range(8):
            force_code = data[i] - 1
            bond_code = data[i + 1] - 1
            name_code = data[i + 2] - 1
            temporary = data[i + 3] | (data[i + 4] << 8)
            if temporary >= 32768:
                temporary -= 65536
            i += 5
            board[owner].append([
                local // 2,
                "front" if (local & 1) == 0 else "rear",
                None if force_code < 0 else card_ids[force_code],
                None if bond_code < 0 else card_ids[bond_code],
                None if name_code < 0 else card_ids[name_code],
                temporary,
            ])

    stories = [[], []]
    for owner in range(2):
        story_count = data[i]
        i += 1
        for _ in range(story_count):
            stories[owner].append(card_ids[data[i] - 1])
            i += 1

    stratagems = []
    for owner in range(2):
        card_code = data[i]
        i += 1
        stratagems.append(
            None if card_code == 0 else card_ids[card_code - 1]
        )

    stratagem_used = [bool(data[i]), bool(data[i + 1])]
    i += 2

    own_hand_counts = []
    for card_code in range(n_cards):
        count = data[i]
        i += 1
        if count:
            own_hand_counts.append([card_ids[card_code], count])
    own_hand_counts.sort(key=lambda row: row[0])

    own_deck_counts = []
    for card_code in range(n_cards):
        count = data[i]
        i += 1
        if count:
            own_deck_counts.append([card_ids[card_code], count])
    own_deck_counts.sort(key=lambda row: row[0])

    own_discard_len = data[i]
    i += 1
    own_discard = []
    for _ in range(own_discard_len):
        own_discard.append(card_ids[data[i] - 1])
        i += 1

    opponent_hand_count = data[i]
    i += 1

    known_counts = []
    for card_code in range(n_cards):
        count = data[i]
        i += 1
        if count:
            known_counts.append([card_ids[card_code], count])
    known_counts.sort(key=lambda row: row[0])

    opponent_deck_count = data[i]
    i += 1
    opponent_discard_len = data[i]
    i += 1
    opponent_discard = []
    for _ in range(opponent_discard_len):
        opponent_discard.append(card_ids[data[i] - 1])
        i += 1

    if i != len(data):
        raise ValueError(
            f"Fast information key decode mismatch: consumed {i}, size {len(data)}"
        )

    observation = {
        "viewer": player,
        "phase": phase,
        "battle": battle,
        "active_player": active_player,
        "passed": passed,
        "pass_order": pass_order,
        "discarded_this_battle": discarded_this_battle,
        "command": command,
        "operations_this_battle": operations_this_battle,
        "pending_draw_discard_for": pending_draw_discard_for,
        "board": board,
        "stories": stories,
        "stratagems": stratagems,
        "stratagem_used": stratagem_used,
        "hero_used": hero_used,
        "own_hand": own_hand_counts,
        "own_deck": own_deck_counts,
        "own_discard": own_discard,
        "opponent_hand_count": opponent_hand_count,
        "known_opponent_hand": known_counts,
        "opponent_deck_count": opponent_deck_count,
        "opponent_discard": opponent_discard,
    }
    payload = json.dumps(
        observation,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
