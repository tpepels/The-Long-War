# Native single-observer information-set Monte Carlo tree search.
#
# Hidden states are root-sampled by the belief layer. The hot tree loop uses
# native 128-bit information hashes, an open-addressed C table, C node/action
# storage and fixed C path arrays. Python objects are created only for the
# input belief states and the final diagnostics payload.

from libc.math cimport isfinite

DEF MAX_ISMCTS_DEPTH = 256
DEF DECISIVE_ROLLOUT_GREEDY_PROBABILITY = 0.05

# Native ISMCTS implementation tuning. These are search/runtime values, not rules.
DEF ISMCTS_RNG_SHIFT_A = 12
DEF ISMCTS_RNG_SHIFT_B = 25
DEF ISMCTS_RNG_SHIFT_C = 27
DEF ISMCTS_RNG_UNIT_SHIFT = 11
DEF ISMCTS_RNG_UNIT_DENOMINATOR = 9007199254740992.0
DEF ISMCTS_HASH_ROTATE_LEFT = 23
DEF ISMCTS_HASH_ROTATE_RIGHT = 41
DEF ISMCTS_HASH_MIX_SHIFT_A = 30
DEF ISMCTS_HASH_MIX_SHIFT_B = 27
DEF ISMCTS_HASH_MIX_SHIFT_C = 31
DEF ISMCTS_INITIAL_NODE_CAPACITY = 1024
DEF ISMCTS_INITIAL_BUCKET_CAPACITY = 2048
DEF ISMCTS_AUTO_MAX_NODE_MULTIPLIER = 4
DEF ISMCTS_INT32_MAX = 2147483647
DEF ISMCTS_NODE_GROWTH_LIMIT = 16384
DEF ISMCTS_BUCKETS_PER_EXPECTED_NODE = 2
DEF ISMCTS_LOAD_FACTOR_NUMERATOR = 7
DEF ISMCTS_LOAD_FACTOR_DENOMINATOR = 10
DEF ISMCTS_NEGATIVE_INFINITY = -1.0e300
DEF ISMCTS_MIN_ROLLOUT_WEIGHT = 0.001
DEF ISMCTS_DEADLINE_POLL_MASK = 255
DEF ISMCTS_PROGRESSIVE_WIDENING_ALPHA = 0.5

DEF NATIVE_DEFAULT_ISMCTS_ITERATIONS = 100000
DEF NATIVE_DEFAULT_ISMCTS_TREE_DEPTH = 96
DEF NATIVE_DEFAULT_ISMCTS_EXPLORATION = 1.4142135623730951
DEF NATIVE_DEFAULT_ISMCTS_PROGRESSIVE_WIDENING = 0.0
DEF NATIVE_DEFAULT_ISMCTS_ROLLOUT_EPSILON = 0.12
DEF NATIVE_DEFAULT_ISMCTS_LEAF_SCALE = 100.0
DEF NATIVE_DEFAULT_ISMCTS_TIME_LIMIT_SECONDS = 0.0
DEF NATIVE_DEFAULT_ISMCTS_SEED = 1701

cdef inline uint64_t _ismcts_next(uint64_t* state) noexcept:
    cdef uint64_t x = state[0]
    cdef uint64_t fallback = 0x9E3779B97F4A7C15ULL
    cdef uint64_t multiplier = 0x2545F4914F6CDD1DULL
    if x == 0:
        x = fallback
    x ^= x >> ISMCTS_RNG_SHIFT_A
    x ^= x << ISMCTS_RNG_SHIFT_B
    x ^= x >> ISMCTS_RNG_SHIFT_C
    state[0] = x
    return x * multiplier

cdef inline int _ismcts_rand_index(uint64_t* state, int n) noexcept:
    if n <= 1:
        return 0
    return <int>(_ismcts_next(state) % <uint64_t>n)

cdef inline double _ismcts_rand_unit(uint64_t* state) noexcept:
    return <double>(_ismcts_next(state) >> ISMCTS_RNG_UNIT_SHIFT) * (
        1.0 / ISMCTS_RNG_UNIT_DENOMINATOR
    )

cdef inline uint64_t _ismcts_bucket_hash(InfoHash128 key) noexcept:
    cdef uint64_t x = key.a ^ (
        (key.b << ISMCTS_HASH_ROTATE_LEFT) | (key.b >> ISMCTS_HASH_ROTATE_RIGHT)
    )
    x ^= x >> ISMCTS_HASH_MIX_SHIFT_A
    x *= 0xBF58476D1CE4E5B9ULL
    x ^= x >> ISMCTS_RNG_SHIFT_C
    x *= 0x94D049BB133111EBULL
    x ^= x >> ISMCTS_HASH_MIX_SHIFT_C
    return x


DEF ISMCTS_EDGE_SLAB_RECORDS = 16384

cdef struct ISMCTSEdgeRecord:
    uint64_t action
    uint64_t visits
    uint64_t availability
    double value_sum


cdef struct ISMCTSEdgeSlab:
    ISMCTSEdgeRecord* records
    size_t capacity
    size_t used


cdef struct ISMCTSNodeRecord:
    uint64_t key_a
    uint64_t key_b
    ISMCTSEdgeRecord* edges
    uint64_t total_visits
    uint16_t action_count
    int8_t player


cdef class ISMCTSTree:
    cdef ISMCTSNodeRecord* nodes
    cdef int32_t* buckets
    cdef ISMCTSEdgeSlab* edge_slabs
    cdef size_t node_count
    cdef size_t node_capacity
    cdef size_t bucket_capacity
    cdef size_t max_nodes
    cdef size_t edge_slab_count
    cdef size_t edge_slab_capacity
    cdef size_t edge_slab_cursor
    cdef object search_context

    def __cinit__(self):
        self.nodes = NULL
        self.buckets = NULL
        self.edge_slabs = NULL
        self.node_count = 0
        self.node_capacity = 0
        self.bucket_capacity = 0
        self.edge_slab_count = 0
        self.edge_slab_capacity = 0
        self.edge_slab_cursor = 0
        self.search_context = None

    def __init__(self, long expected_nodes, max_nodes=None):
        cdef size_t node_capacity = ISMCTS_INITIAL_NODE_CAPACITY
        cdef size_t bucket_capacity = ISMCTS_INITIAL_BUCKET_CAPACITY
        if expected_nodes < 1:
            expected_nodes = 1
        if max_nodes is None:
            max_nodes = min(ISMCTS_INT32_MAX, expected_nodes * ISMCTS_AUTO_MAX_NODE_MULTIPLIER)
        if not isinstance(max_nodes, int) or not 1 <= max_nodes <= ISMCTS_INT32_MAX:
            raise ValueError(f"max_nodes must be an integer between 1 and {ISMCTS_INT32_MAX}")
        self.max_nodes = max_nodes
        expected_nodes = min(expected_nodes, max_nodes)
        while (
            node_capacity < <size_t>expected_nodes
            and node_capacity < ISMCTS_NODE_GROWTH_LIMIT
        ):
            node_capacity <<= 1
        while bucket_capacity < <size_t>expected_nodes * ISMCTS_BUCKETS_PER_EXPECTED_NODE:
            bucket_capacity <<= 1
        self._allocate(node_capacity, bucket_capacity)

    def size(self):
        return int(self.node_count)

    def clear(self):
        """Discard statistics while retaining reusable node and edge arenas."""
        cdef size_t i
        # Buckets must be cleared because they index the old tree. Node records
        # do not: get_or_create overwrites every field before a recycled record
        # becomes reachable again, so zeroing the full node capacity here only
        # burns memory bandwidth on large persistent trees.
        memset(self.buckets, 0, self.bucket_capacity * sizeof(int32_t))
        for i in range(self.edge_slab_count):
            self.edge_slabs[i].used = 0
        self.edge_slab_cursor = 0
        self.node_count = 0
        self.search_context = None

    def __dealloc__(self):
        cdef size_t i
        if self.nodes != NULL:
            free(self.nodes)
        if self.buckets != NULL:
            free(self.buckets)
        if self.edge_slabs != NULL:
            for i in range(self.edge_slab_count):
                if self.edge_slabs[i].records != NULL:
                    free(self.edge_slabs[i].records)
            free(self.edge_slabs)

    cdef void _append_edge_slab(self, size_t minimum_records) except *:
        cdef size_t old_capacity = self.edge_slab_capacity
        cdef size_t new_capacity
        cdef size_t records_capacity
        cdef ISMCTSEdgeSlab* grown
        cdef ISMCTSEdgeRecord* records

        if self.edge_slab_count >= self.edge_slab_capacity:
            new_capacity = 8 if old_capacity == 0 else old_capacity << 1
            grown = <ISMCTSEdgeSlab*>realloc(
                self.edge_slabs,
                new_capacity * sizeof(ISMCTSEdgeSlab),
            )
            if grown == NULL:
                raise MemoryError("Unable to grow ISMCTS edge-slab table")
            self.edge_slabs = grown
            memset(
                &self.edge_slabs[old_capacity],
                0,
                (new_capacity - old_capacity) * sizeof(ISMCTSEdgeSlab),
            )
            self.edge_slab_capacity = new_capacity

        records_capacity = (
            ISMCTS_EDGE_SLAB_RECORDS
            if minimum_records <= ISMCTS_EDGE_SLAB_RECORDS
            else minimum_records
        )
        records = <ISMCTSEdgeRecord*>malloc(
            records_capacity * sizeof(ISMCTSEdgeRecord)
        )
        if records == NULL:
            raise MemoryError("Unable to allocate ISMCTS edge slab")
        self.edge_slabs[self.edge_slab_count].records = records
        self.edge_slabs[self.edge_slab_count].capacity = records_capacity
        self.edge_slabs[self.edge_slab_count].used = 0
        self.edge_slab_count += 1

    cdef ISMCTSEdgeRecord* _alloc_edges(self, size_t n) except NULL:
        cdef ISMCTSEdgeSlab* slab
        cdef ISMCTSEdgeRecord* result
        if n == 0:
            return NULL

        while self.edge_slab_cursor < self.edge_slab_count:
            slab = &self.edge_slabs[self.edge_slab_cursor]
            if slab.capacity - slab.used >= n:
                result = &slab.records[slab.used]
                slab.used += n
                return result
            self.edge_slab_cursor += 1

        self._append_edge_slab(n)
        self.edge_slab_cursor = self.edge_slab_count - 1
        slab = &self.edge_slabs[self.edge_slab_cursor]
        result = &slab.records[0]
        slab.used = n
        return result

    cdef void _allocate(
        self,
        size_t node_capacity,
        size_t bucket_capacity,
    ) except *:
        self.nodes = <ISMCTSNodeRecord*>malloc(
            node_capacity * sizeof(ISMCTSNodeRecord)
        )
        self.buckets = <int32_t*>malloc(
            bucket_capacity * sizeof(int32_t)
        )
        if self.nodes == NULL or self.buckets == NULL:
            if self.nodes != NULL:
                free(self.nodes)
                self.nodes = NULL
            if self.buckets != NULL:
                free(self.buckets)
                self.buckets = NULL
            raise MemoryError("Unable to allocate native ISMCTS tree")
        memset(
            self.nodes,
            0,
            node_capacity * sizeof(ISMCTSNodeRecord),
        )
        memset(
            self.buckets,
            0,
            bucket_capacity * sizeof(int32_t),
        )
        self.node_capacity = node_capacity
        self.bucket_capacity = bucket_capacity

    cdef void _grow_nodes(self) except *:
        cdef size_t old_capacity = self.node_capacity
        cdef size_t new_capacity = old_capacity << 1
        cdef ISMCTSNodeRecord* grown = <ISMCTSNodeRecord*>realloc(
            self.nodes,
            new_capacity * sizeof(ISMCTSNodeRecord),
        )
        if grown == NULL:
            raise MemoryError("Unable to grow native ISMCTS node arena")
        self.nodes = grown
        memset(
            &self.nodes[old_capacity],
            0,
            (new_capacity - old_capacity) * sizeof(ISMCTSNodeRecord),
        )
        self.node_capacity = new_capacity

    cdef void _rehash(self) except *:
        cdef size_t old_capacity = self.bucket_capacity
        cdef size_t new_capacity = old_capacity << 1
        cdef int32_t* grown = <int32_t*>malloc(
            new_capacity * sizeof(int32_t)
        )
        cdef size_t i, bucket, mask = new_capacity - 1
        cdef uint64_t mixed
        cdef InfoHash128 key
        if grown == NULL:
            raise MemoryError("Unable to grow native ISMCTS hash table")
        memset(grown, 0, new_capacity * sizeof(int32_t))
        for i in range(self.node_count):
            key.a = self.nodes[i].key_a
            key.b = self.nodes[i].key_b
            mixed = _ismcts_bucket_hash(key)
            bucket = <size_t>mixed & mask
            while grown[bucket] != 0:
                bucket = (bucket + 1) & mask
            grown[bucket] = <int32_t>(i + 1)
        free(self.buckets)
        self.buckets = grown
        self.bucket_capacity = new_capacity

    cdef int find(self, InfoHash128 key) noexcept:
        cdef size_t mask = self.bucket_capacity - 1
        cdef size_t bucket = <size_t>(
            _ismcts_bucket_hash(key)
        ) & mask
        cdef int32_t entry
        cdef ISMCTSNodeRecord* node
        while True:
            entry = self.buckets[bucket]
            if entry == 0:
                return -1
            node = &self.nodes[entry - 1]
            if node.key_a == key.a and node.key_b == key.b:
                return entry - 1
            bucket = (bucket + 1) & mask

    cdef int get_or_create(
        self,
        InfoHash128 key,
        int player,
        uint64_t* actions,
        int n,
        bint* created,
    ) except -1:
        cdef int found = self.find(key)
        cdef size_t bucket, mask
        cdef int index, i
        cdef ISMCTSNodeRecord* node
        cdef ISMCTSEdgeRecord* edges
        if found >= 0:
            created[0] = False
            return found

        if (self.node_count + 1) * ISMCTS_LOAD_FACTOR_DENOMINATOR >= self.bucket_capacity * ISMCTS_LOAD_FACTOR_NUMERATOR:
            self._rehash()
        if self.node_count >= self.node_capacity:
            self._grow_nodes()

        node = NULL
        edges = self._alloc_edges(n)
        index = <int>self.node_count
        self.node_count += 1
        node = &self.nodes[index]
        node.key_a = key.a
        node.key_b = key.b
        node.player = <int8_t>player
        node.action_count = <uint16_t>n
        node.total_visits = 0
        node.edges = edges

        for i in range(n):
            node.edges[i].action = actions[i]
            node.edges[i].visits = 0
            node.edges[i].availability = 0
            node.edges[i].value_sum = 0.0

        mask = self.bucket_capacity - 1
        bucket = <size_t>(_ismcts_bucket_hash(key)) & mask
        while self.buckets[bucket] != 0:
            bucket = (bucket + 1) & mask
        self.buckets[bucket] = <int32_t>(index + 1)
        created[0] = True
        return index

    cdef int choose(
        self,
        int node_index,
        uint64_t* legal,
        int n,
        double exploration,
        double progressive_widening,
        uint64_t* rng,
        bint* expanded,
    ) except -1:
        cdef ISMCTSNodeRecord* node = &self.nodes[node_index]
        cdef int i, chosen=-1, unvisited=0, visited_legal=0
        cdef int allowed=n
        cdef double mean, bonus, score, allowance, best=ISMCTS_NEGATIVE_INFINITY

        # Information-set identity includes every observable fact relevant to
        # legality, so all determinizations of one node must expose the same
        # canonical action list in the same order. Rely on that invariant
        # directly instead of linearly searching stored edges on every visit.
        if n != node.action_count:
            raise RuntimeError(
                "Legal-action count changed inside an information set"
            )
        for i in range(n):
            if node.edges[i].action != legal[i]:
                raise RuntimeError(
                    "Legal-action ordering changed inside an information set"
                )
            node.edges[i].availability += 1
            if node.edges[i].visits == 0:
                unvisited += 1
                if _ismcts_rand_index(rng, unvisited) == 0:
                    chosen = i
            else:
                visited_legal += 1

        # Optional square-root progressive widening. A value <= 0 preserves
        # the original ISMCTS behavior: visit every legal action once before
        # UCT selection. With widening enabled, a node may expand at most
        # floor(c * sqrt(N + 1)) currently-legal actions, but always at least
        # one. Actions unavailable in this determinization do not consume the
        # node's legal-action allowance.
        if progressive_widening > 0.0:
            allowance = progressive_widening * sqrt(<double>(node.total_visits + 1))
            allowed = n if allowance >= n else <int>allowance
            if allowed < 1:
                allowed = 1
            if allowed > n:
                allowed = n

        if chosen >= 0 and visited_legal < allowed:
            expanded[0] = True
            return chosen

        expanded[0] = False
        chosen = -1
        for i in range(n):
            if node.edges[i].visits == 0:
                continue
            mean = node.edges[i].value_sum / node.edges[i].visits
            bonus = exploration * sqrt(
                log(<double>(node.edges[i].availability + 1))
                / node.edges[i].visits
            )
            score = mean + bonus
            if score > best:
                best = score
                chosen = i

        # This can only happen when the current determinization exposes no
        # previously visited action. Expand one available action regardless
        # of the global widening allowance so the information set remains
        # usable across hidden-state samples.
        if chosen < 0:
            for i in range(n):
                if node.edges[i].visits == 0:
                    unvisited -= 1
                    if unvisited <= 0:
                        chosen = i
                        break
            expanded[0] = True
        return chosen

    cdef void update(
        self,
        int node_index,
        int action_index,
        double utility,
    ) noexcept:
        cdef ISMCTSNodeRecord* node = &self.nodes[node_index]
        node.edges[action_index].visits += 1
        node.edges[action_index].value_sum += utility
        node.total_visits += 1


cdef uint64_t _ismcts_rollout_action(
    FastEngine engine,
    NativeHeuristicEvaluator evaluator,
    FastState state,
    FastState score_scratch,
    uint64_t* rng,
    double epsilon,
    int policy,
    long* decisive_probes,
    long* decisive_actions,
) except *:
    cdef uint64_t actions[MAX_ACTIONS]
    cdef double weights[MAX_ACTIONS]
    cdef int safe_indices[MAX_ACTIONS]
    cdef int n = _fe_legal_actions_into(engine, state, &actions[0])
    cdef int actor = state.active_player
    cdef int i, best_ix=0, safe_n=0, pick
    cdef bint use_greedy
    cdef double value, best=ISMCTS_NEGATIVE_INFINITY
    cdef double total=0.0, target, cumulative=0.0

    if n <= 0:
        raise RuntimeError("Non-terminal ISMCTS state has no legal action")
    if n == 1:
        return actions[0]

    # Do not let random rollouts teach the tree that spending the final
    # Command while the opponent remains positive is ordinary play. Inspect
    # exact child states only for operations that can actually reach Collapse.
    for i in range(n):
        if not evaluator.rollout_action_exhausts_command_fast(
            state,
            actor,
            actions[i],
            score_scratch,
        ):
            safe_indices[safe_n] = i
            safe_n += 1
    if safe_n == 0:
        for i in range(n):
            safe_indices[i] = i
        safe_n = n

    if policy == 3:
        use_greedy = (
            _ismcts_rand_unit(rng)
            < DECISIVE_ROLLOUT_GREEDY_PROBABILITY
        )

        # Keep only the cheap exact tactical case: an unsignalled player can
        # sometimes end the Battle immediately by supplying the second signal.
        # Closing-window lookahead belongs in the MCTS tree. Running candidate
        # or reply searches inside a rollout duplicated tree search, produced
        # no tactical hits in the fixed Pass-active benchmark, and reduced
        # throughput substantially.
        if (
            not use_greedy
            and state.pass_len == 1
            and not state.passed[actor]
        ):
            for pick in range(safe_n):
                i = safe_indices[pick]
                if action_kind(actions[i]) != TYPE_PASS:
                    continue
                decisive_probes[0] += 1
                score_scratch.copy_from_fast(state)
                _fe_apply_fast(engine, score_scratch, actions[i])
                if (
                    score_scratch.phase == PHASE_COMPLETE
                    and score_scratch.winner == actor
                ):
                    decisive_actions[0] += 1
                    return actions[i]
                break

        # Ninety-five percent of decisive rollouts remain random after the
        # exact second-signal check. The five-percent greedy branch falls
        # through to the normal exact candidate scoring below.
        if not use_greedy:
            pick = safe_indices[_ismcts_rand_index(rng, safe_n)]
            return actions[pick]


    elif policy == 2 or _ismcts_rand_unit(rng) < epsilon:
        pick = safe_indices[_ismcts_rand_index(rng, safe_n)]
        return actions[pick]

    if policy == 1:
        for i in range(n):
            weights[i] = 0.0
        for pick in range(safe_n):
            i = safe_indices[pick]
            weights[i] = evaluator.rollout_prior_fast(
                state,
                actor,
                actions[i],
            )
            if weights[i] < ISMCTS_MIN_ROLLOUT_WEIGHT:
                weights[i] = ISMCTS_MIN_ROLLOUT_WEIGHT
            total += weights[i]
        target = _ismcts_rand_unit(rng) * total
        for pick in range(safe_n):
            i = safe_indices[pick]
            cumulative += weights[i]
            if cumulative >= target:
                return actions[i]
        return actions[safe_indices[safe_n - 1]]

    best_ix = safe_indices[0]
    for pick in range(safe_n):
        i = safe_indices[pick]
        value = evaluator.action_order_score_fast(
            state,
            actor,
            actions[i],
            score_scratch,
        )
        if value > best:
            best = value
            best_ix = i
    return actions[best_ix]



def ismcts_search(
    FastEngine engine,
    NativeHeuristicEvaluator evaluator,
    list root_states,
    int root_player,
    *,
    ISMCTSTree tree=None,
    reuse_context=None,
    long iterations=NATIVE_DEFAULT_ISMCTS_ITERATIONS,
    int rollout_depth=5,
    int post_battle_rollout_depth=4,
    int tree_depth_limit=NATIVE_DEFAULT_ISMCTS_TREE_DEPTH,
    double exploration=NATIVE_DEFAULT_ISMCTS_EXPLORATION,
    double progressive_widening=NATIVE_DEFAULT_ISMCTS_PROGRESSIVE_WIDENING,
    double rollout_epsilon=NATIVE_DEFAULT_ISMCTS_ROLLOUT_EPSILON,
    int rollout_policy=3,
    double leaf_scale=NATIVE_DEFAULT_ISMCTS_LEAF_SCALE,
    double time_limit_seconds=NATIVE_DEFAULT_ISMCTS_TIME_LIMIT_SECONDS,
    unsigned long long seed=NATIVE_DEFAULT_ISMCTS_SEED,
):
    cdef FastState state = FastState()
    cdef FastState score_scratch = FastState()
    cdef FastState sampled
    cdef InfoHash128 key, root_key
    cdef ISMCTSNodeRecord* root_node
    cdef uint64_t actions[MAX_ACTIONS]
    cdef uint64_t action
    cdef uint64_t rng = <uint64_t>seed
    cdef int path_nodes[MAX_ISMCTS_DEPTH]
    cdef uint16_t path_indices[MAX_ISMCTS_DEPTH]
    cdef int n, actor, ix, path_length, tree_turn_depth
    cdef int rollout_steps, rollout_post_battle_steps, rollout_raw_steps, sample_ix, node_index
    cdef int root_index, prior_root_index, max_tree_depth_seen = 0
    cdef int max_tree_path_depth_seen = 0
    cdef int i, best_ix=-1, second_ix=-1
    cdef int rollout_battle, action_battle, action_turn
    cdef long iteration, completed_iterations=0
    cdef uint64_t best_visits=0, second_visits=0
    cdef uint64_t root_total_visits_before=0
    cdef uint64_t selected_action_visits_before=0
    cdef size_t tree_nodes_before=0
    cdef uint64_t root_prior_visits[MAX_ACTIONS]
    cdef long rollouts_stopped_terminal=0
    cdef long rollouts_stopped_battle_boundary=0
    cdef long rollouts_stopped_depth=0
    cdef long rollout_actions=0
    cdef long rollout_battle_continuations=0
    cdef long rollout_post_battle_actions=0
    cdef long decisive_rollout_probes=0
    cdef long decisive_rollout_actions=0
    cdef long anti_decisive_rollout_probes=0
    cdef long anti_decisive_rollout_filtered=0
    cdef long tree_capacity_cutoffs=0
    cdef size_t tree_nodes_discarded=0
    cdef object search_context
    cdef str tree_reset_reason="none"
    cdef double utility, node_utility, mean_value
    cdef double deadline = 0.0
    cdef double best_mean=ISMCTS_NEGATIVE_INFINITY, second_mean=ISMCTS_NEGATIVE_INFINITY
    cdef bint expanded, created, rollout_boundary, rollout_in_post_battle, root_reused=False, timed_out=False
    cdef list root_stats

    if not root_states:
        raise ValueError("ISMCTS requires at least one belief sample")
    if iterations <= 0:
        raise ValueError("ISMCTS iterations must be positive")
    if rollout_depth < 0 or post_battle_rollout_depth < 0 or tree_depth_limit <= 0:
        raise ValueError("ISMCTS depth settings are invalid")
    if tree_depth_limit > MAX_ISMCTS_DEPTH:
        raise ValueError(
            f"tree_depth_limit exceeds native maximum {MAX_ISMCTS_DEPTH}"
        )
    if root_player not in (0, 1):
        raise ValueError("root_player must be 0 or 1")
    if not isfinite(exploration) or exploration < 0.0:
        raise ValueError("exploration must be finite and non-negative")
    if not isfinite(progressive_widening) or progressive_widening < 0.0:
        raise ValueError("progressive_widening must be non-negative")
    if not isfinite(rollout_epsilon) or not 0.0 <= rollout_epsilon <= 1.0:
        raise ValueError("rollout_epsilon must be between 0 and 1")
    if rollout_policy not in (0, 1, 2, 3):
        raise ValueError("rollout_policy must be 0, 1, 2, or 3")
    if not isfinite(leaf_scale) or leaf_scale <= 0.0:
        raise ValueError("leaf_scale must be positive")
    if not isfinite(time_limit_seconds) or time_limit_seconds < 0.0:
        raise ValueError("time_limit_seconds must be finite and non-negative")
    if time_limit_seconds > 0.0:
        deadline = perf_counter() + time_limit_seconds

    if tree is None:
        tree = ISMCTSTree(iterations)
    for i in range(MAX_ACTIONS):
        root_prior_visits[i] = 0

    if not isinstance(root_states[0], FastState):
        raise TypeError("ISMCTS belief samples must be FastState instances")
    sampled = <FastState>root_states[0]
    root_key = _fe_information_hash_fast(engine, sampled, root_player)
    for candidate in root_states:
        if not isinstance(candidate, FastState):
            raise TypeError("ISMCTS belief samples must be FastState instances")
        sampled = <FastState>candidate
        if sampled.phase == PHASE_COMPLETE:
            raise ValueError("ISMCTS cannot search a completed state")
        if sampled.active_player != root_player:
            raise ValueError("ISMCTS root_player must be the acting player")
        key = _fe_information_hash_fast(engine, sampled, root_player)
        if key.a != root_key.a or key.b != root_key.b:
            raise ValueError("ISMCTS belief samples must share a root information set")

    # Values depend on the evaluator/search horizon and the observer's belief
    # evidence, not just the node's information hash. The belief layer owns
    # reuse_context; native callers omitting it must manage belief changes.
    search_context = (
                      engine, evaluator, root_player, rollout_depth,
                      post_battle_rollout_depth, tree_depth_limit,
                      rollout_epsilon, rollout_policy, leaf_scale,
                      exploration, progressive_widening, reuse_context)
    if tree.search_context is not None and tree.search_context != search_context:
        tree_nodes_discarded = tree.node_count
        tree.clear()
        tree_reset_reason = "context_changed"
    if tree.node_count >= tree.max_nodes and tree.find(root_key) < 0:
        tree_nodes_discarded += tree.node_count
        tree.clear()
        tree_reset_reason = "capacity_reroot"
    tree.search_context = search_context
    tree_nodes_before = tree.node_count
    prior_root_index = tree.find(root_key)
    if prior_root_index >= 0:
        root_reused = True
        root_node = &tree.nodes[prior_root_index]
        root_total_visits_before = root_node.total_visits
        for i in range(root_node.action_count):
            root_prior_visits[i] = root_node.edges[i].visits

    for iteration in range(iterations):
        if (
            iteration > 0
            and deadline > 0.0
            and (iteration & ISMCTS_DEADLINE_POLL_MASK) == 0
            and perf_counter() >= deadline
        ):
            timed_out = True
            break
        sample_ix = _ismcts_rand_index(&rng, len(root_states))
        sampled = <FastState>root_states[sample_ix]
        state.copy_from_fast(sampled)
        path_length = 0
        tree_turn_depth = 0
        rollout_boundary = False

        # Keep every decision node for backpropagation, but measure the search
        # horizon in completed turns rather than raw engine actions. Free
        # Battle Flags and pending effect choices therefore do not shorten the
        # strategic horizon.
        while (
            state.phase != PHASE_COMPLETE
            and tree_turn_depth < tree_depth_limit
            and path_length < MAX_ISMCTS_DEPTH
        ):
            actor = state.active_player
            n = _fe_legal_actions_into(engine, state, &actions[0])
            if n <= 0:
                break

            # If the tree deliberately continues past a Battle boundary,
            # the previous boundary is no longer the rollout leaf.
            rollout_boundary = False
            key = _fe_information_hash_fast(engine, state, actor)
            # A persistent arena must not grow with game length. Existing
            # information sets still learn at capacity; unseen leaves rollout.
            if tree.node_count >= tree.max_nodes and tree.find(key) < 0:
                tree_capacity_cutoffs += 1
                break
            node_index = tree.get_or_create(
                key,
                actor,
                &actions[0],
                n,
                &created,
            )
            ix = tree.choose(
                node_index,
                &actions[0],
                n,
                exploration,
                progressive_widening,
                &rng,
                &expanded,
            )
            action = tree.nodes[node_index].edges[ix].action
            path_nodes[path_length] = node_index
            path_indices[path_length] = <uint16_t>ix
            action_battle = state.battle
            action_turn = state.turn_number
            _fe_apply_fast(engine, state, action)
            path_length += 1
            if state.turn_number != action_turn:
                tree_turn_depth += 1
            if (
                state.phase != PHASE_COMPLETE
                and state.battle != action_battle
            ):
                rollout_boundary = True

            if expanded:
                break

        if tree_turn_depth > max_tree_depth_seen:
            max_tree_depth_seen = tree_turn_depth
        if path_length > max_tree_path_depth_seen:
            max_tree_path_depth_seen = path_length

        rollout_steps = 0
        rollout_post_battle_steps = 0
        rollout_raw_steps = 0
        rollout_battle = state.battle
        rollout_in_post_battle = False

        # If tree expansion itself just crossed a Battle boundary, use the
        # continuation budget immediately rather than treating the fresh
        # Battle as a static leaf.
        if rollout_boundary and post_battle_rollout_depth > 0:
            rollout_boundary = False
            rollout_in_post_battle = True
            rollout_battle_continuations += 1

        while (
            not rollout_boundary
            and state.phase != PHASE_COMPLETE
            and rollout_raw_steps < MAX_ISMCTS_DEPTH
            and (
                (
                    not rollout_in_post_battle
                    and rollout_steps < rollout_depth
                )
                or (
                    rollout_in_post_battle
                    and rollout_post_battle_steps < post_battle_rollout_depth
                )
            )
        ):
            action = _ismcts_rollout_action(
                engine,
                evaluator,
                state,
                score_scratch,
                &rng,
                rollout_epsilon,
                rollout_policy,
                &decisive_rollout_probes,
                &decisive_rollout_actions,
            )
            action_turn = state.turn_number
            _fe_apply_fast(engine, state, action)
            rollout_raw_steps += 1
            rollout_actions += 1
            if rollout_in_post_battle:
                rollout_post_battle_actions += 1
            if state.turn_number != action_turn:
                if rollout_in_post_battle:
                    rollout_post_battle_steps += 1
                else:
                    rollout_steps += 1
            if (
                state.phase != PHASE_COMPLETE
                and state.battle != rollout_battle
            ):
                if rollout_in_post_battle or post_battle_rollout_depth <= 0:
                    rollout_boundary = True
                    break
                # Continue into the next Battle for a bounded number of
                # completed turns. This lets search value recovery, preserved
                # formations, fresh draws and actual next-Battle options.
                rollout_in_post_battle = True
                rollout_battle_continuations += 1
                rollout_battle = state.battle
                rollout_post_battle_steps = 0

        if state.phase == PHASE_COMPLETE:
            rollouts_stopped_terminal += 1
            if state.winner < 0:
                utility = 0.0
            else:
                utility = 1.0 if state.winner == root_player else -1.0
        elif rollout_boundary:
            rollouts_stopped_battle_boundary += 1
            utility = tanh(
                evaluator.battle_boundary_evaluate_fast(
                    state,
                    root_player,
                )
                / leaf_scale
            )
        else:
            rollouts_stopped_depth += 1
            utility = tanh(
                evaluator.strategic_evaluate_fast(state, root_player)
                / leaf_scale
            )

        for i in range(path_length):
            node_index = path_nodes[i]
            node_utility = (
                utility
                if tree.nodes[node_index].player == root_player
                else -utility
            )
            tree.update(
                node_index,
                <int>path_indices[i],
                node_utility,
            )
        completed_iterations += 1

    root_index = tree.find(root_key)
    if root_index < 0:
        raise RuntimeError("ISMCTS failed to create a root node")
    root_node = &tree.nodes[root_index]

    root_stats = []
    for i in range(root_node.action_count):
        mean_value = (
            root_node.edges[i].value_sum / root_node.edges[i].visits
            if root_node.edges[i].visits
            else ISMCTS_NEGATIVE_INFINITY
        )
        root_stats.append(
            {
                "action": root_node.edges[i].action,
                "visits": root_node.edges[i].visits,
                "prior_visits": root_prior_visits[i],
                "new_visits": root_node.edges[i].visits - root_prior_visits[i],
                "availability": root_node.edges[i].availability,
                "mean_value": (
                    mean_value if root_node.edges[i].visits else 0.0
                ),
            }
        )
        if (
            best_ix < 0
            or root_node.edges[i].visits > best_visits
            or (
                root_node.edges[i].visits == best_visits
                and mean_value > best_mean
            )
        ):
            second_ix = best_ix
            second_visits = best_visits
            second_mean = best_mean
            best_ix = i
            best_visits = root_node.edges[i].visits
            best_mean = mean_value
        elif (
            second_ix < 0
            or root_node.edges[i].visits > second_visits
            or (
                root_node.edges[i].visits == second_visits
                and mean_value > second_mean
            )
        ):
            second_ix = i
            second_visits = root_node.edges[i].visits
            second_mean = mean_value

    if best_ix < 0:
        raise RuntimeError("ISMCTS root has no action")
    selected_action_visits_before = root_prior_visits[best_ix]

    return {
        "action": root_node.edges[best_ix].action,
        "root_total_visits": root_node.total_visits,
        "root_total_visits_before": root_total_visits_before,
        "root_new_visits": root_node.total_visits - root_total_visits_before,
        "selected_action_visits": best_visits,
        "selected_action_visits_before": selected_action_visits_before,
        "selected_action_new_visits": best_visits - selected_action_visits_before,
        "root_reused": root_reused,
        "mean_value": best_mean,
        "second_mean_value": (
            second_mean if second_ix >= 0 else best_mean
        ),
        "iterations": completed_iterations,
        "iteration_limit": iterations,
        "time_limit_seconds": time_limit_seconds,
        "timed_out": timed_out,
        "tree_nodes": tree.node_count,
        "tree_nodes_before": tree_nodes_before,
        "tree_nodes_discarded": tree_nodes_discarded,
        "tree_reset_reason": tree_reset_reason,
        "tree_max_nodes": tree.max_nodes,
        "tree_capacity_cutoffs": tree_capacity_cutoffs,
        "tree_nodes_added": tree.node_count - tree_nodes_before,
        "max_tree_depth": max_tree_depth_seen,
        "max_tree_path_depth": max_tree_path_depth_seen,
        "belief_states": len(root_states),
        "root_stats": root_stats,
        "rollouts_stopped_terminal": rollouts_stopped_terminal,
        "rollouts_stopped_battle_boundary": rollouts_stopped_battle_boundary,
        "rollouts_stopped_depth": rollouts_stopped_depth,
        "rollout_actions": rollout_actions,
        "post_battle_rollout_depth": post_battle_rollout_depth,
        "rollout_battle_continuations": rollout_battle_continuations,
        "rollout_post_battle_actions": rollout_post_battle_actions,
        "decisive_rollout_probes": decisive_rollout_probes,
        "decisive_rollout_actions": decisive_rollout_actions,
        "anti_decisive_rollout_probes": anti_decisive_rollout_probes,
        "anti_decisive_rollout_filtered": anti_decisive_rollout_filtered,
        "tree_storage": "native-hash-node-edge-slab",
        "tree_edge_slabs": tree.edge_slab_count,
        "progressive_widening": progressive_widening,
        "progressive_widening_alpha": ISMCTS_PROGRESSIVE_WIDENING_ALPHA if progressive_widening > 0.0 else 0.0,
        "rollout_policy": (
            "cheap" if rollout_policy == 1
            else "random" if rollout_policy == 2
            else "decisive" if rollout_policy == 3
            else "greedy"
        ),
    }
