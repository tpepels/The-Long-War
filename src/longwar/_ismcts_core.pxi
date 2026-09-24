# Native single-observer information-set Monte Carlo tree search.
#
# Hidden states are root-sampled by the belief layer. The hot tree loop uses
# native 128-bit information hashes, an open-addressed C table, C node/action
# storage and fixed C path arrays. Python objects are created only for the
# input belief states and the final diagnostics payload.

from libc.math cimport isfinite

DEF MAX_ISMCTS_DEPTH = 256

cdef inline uint64_t _ismcts_next(uint64_t* state) noexcept:
    cdef uint64_t x = state[0]
    cdef uint64_t fallback = 0x9E3779B97F4A7C15ULL
    cdef uint64_t multiplier = 0x2545F4914F6CDD1DULL
    if x == 0:
        x = fallback
    x ^= x >> 12
    x ^= x << 25
    x ^= x >> 27
    state[0] = x
    return x * multiplier

cdef inline int _ismcts_rand_index(uint64_t* state, int n) noexcept:
    if n <= 1:
        return 0
    return <int>(_ismcts_next(state) % <uint64_t>n)

cdef inline double _ismcts_rand_unit(uint64_t* state) noexcept:
    return <double>(_ismcts_next(state) >> 11) * (
        1.0 / 9007199254740992.0
    )

cdef inline uint64_t _ismcts_bucket_hash(InfoHash128 key) noexcept:
    cdef uint64_t x = key.a ^ (
        (key.b << 23) | (key.b >> 41)
    )
    x ^= x >> 30
    x *= 0xBF58476D1CE4E5B9ULL
    x ^= x >> 27
    x *= 0x94D049BB133111EBULL
    x ^= x >> 31
    return x


cdef struct ISMCTSNodeRecord:
    uint64_t key_a
    uint64_t key_b
    uint64_t* actions
    uint64_t* visits
    uint64_t* availability
    double* value_sum
    uint64_t total_visits
    uint16_t action_count
    int8_t player


cdef class ISMCTSTree:
    cdef ISMCTSNodeRecord* nodes
    cdef int32_t* buckets
    cdef size_t node_count
    cdef size_t node_capacity
    cdef size_t bucket_capacity
    cdef size_t max_nodes
    cdef object search_context

    def __cinit__(self):
        self.nodes = NULL
        self.buckets = NULL
        self.node_count = 0
        self.node_capacity = 0
        self.bucket_capacity = 0
        self.search_context = None

    def __init__(self, long expected_nodes, max_nodes=None):
        cdef size_t node_capacity = 1024
        cdef size_t bucket_capacity = 2048
        if expected_nodes < 1:
            expected_nodes = 1
        if max_nodes is None:
            max_nodes = min(2147483647, expected_nodes * 4)
        if not isinstance(max_nodes, int) or not 1 <= max_nodes <= 2147483647:
            raise ValueError("max_nodes must be an integer between 1 and 2147483647")
        self.max_nodes = max_nodes
        expected_nodes = min(expected_nodes, max_nodes)
        while (
            node_capacity < <size_t>expected_nodes
            and node_capacity < 16384
        ):
            node_capacity <<= 1
        while bucket_capacity < <size_t>expected_nodes * 2:
            bucket_capacity <<= 1
        self._allocate(node_capacity, bucket_capacity)

    def size(self):
        return int(self.node_count)

    def clear(self):
        """Discard statistics while retaining bounded native allocations."""
        cdef size_t i
        for i in range(self.node_count):
            free(self.nodes[i].actions)
            free(self.nodes[i].visits)
            free(self.nodes[i].availability)
            free(self.nodes[i].value_sum)
        memset(self.nodes, 0, self.node_capacity * sizeof(ISMCTSNodeRecord))
        memset(self.buckets, 0, self.bucket_capacity * sizeof(int32_t))
        self.node_count = 0
        self.search_context = None

    def __dealloc__(self):
        cdef size_t i
        if self.nodes != NULL:
            for i in range(self.node_count):
                if self.nodes[i].actions != NULL:
                    free(self.nodes[i].actions)
                if self.nodes[i].visits != NULL:
                    free(self.nodes[i].visits)
                if self.nodes[i].availability != NULL:
                    free(self.nodes[i].availability)
                if self.nodes[i].value_sum != NULL:
                    free(self.nodes[i].value_sum)
            free(self.nodes)
        if self.buckets != NULL:
            free(self.buckets)

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
        if found >= 0:
            created[0] = False
            return found

        if (self.node_count + 1) * 10 >= self.bucket_capacity * 7:
            self._rehash()
        if self.node_count >= self.node_capacity:
            self._grow_nodes()

        index = <int>self.node_count
        self.node_count += 1
        node = &self.nodes[index]
        node.key_a = key.a
        node.key_b = key.b
        node.player = <int8_t>player
        node.action_count = <uint16_t>n
        node.total_visits = 0
        node.actions = <uint64_t*>malloc(n * sizeof(uint64_t))
        node.visits = <uint64_t*>malloc(n * sizeof(uint64_t))
        node.availability = <uint64_t*>malloc(n * sizeof(uint64_t))
        node.value_sum = <double*>malloc(n * sizeof(double))
        if (
            node.actions == NULL
            or node.visits == NULL
            or node.availability == NULL
            or node.value_sum == NULL
        ):
            if node.actions != NULL:
                free(node.actions)
            if node.visits != NULL:
                free(node.visits)
            if node.availability != NULL:
                free(node.availability)
            if node.value_sum != NULL:
                free(node.value_sum)
            node.actions = NULL
            node.visits = NULL
            node.availability = NULL
            node.value_sum = NULL
            self.node_count -= 1
            raise MemoryError("Unable to allocate native ISMCTS node")

        for i in range(n):
            node.actions[i] = actions[i]
            node.visits[i] = 0
            node.availability[i] = 0
            node.value_sum[i] = 0.0

        mask = self.bucket_capacity - 1
        bucket = <size_t>(_ismcts_bucket_hash(key)) & mask
        while self.buckets[bucket] != 0:
            bucket = (bucket + 1) & mask
        self.buckets[bucket] = <int32_t>(index + 1)
        created[0] = True
        return index

    cdef int _find_action(
        self,
        ISMCTSNodeRecord* node,
        uint64_t action,
    ) noexcept:
        cdef int i
        for i in range(node.action_count):
            if node.actions[i] == action:
                return i
        return -1

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
        cdef int i, ix, chosen=-1, unvisited=0, visited_legal=0
        cdef int allowed=n
        cdef double mean, bonus, score, allowance, best=-1.0e300

        for i in range(n):
            ix = self._find_action(node, legal[i])
            if ix < 0:
                raise RuntimeError(
                    "Legal-action set changed inside an information set"
                )
            node.availability[ix] += 1
            if node.visits[ix] == 0:
                unvisited += 1
                if _ismcts_rand_index(rng, unvisited) == 0:
                    chosen = ix
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
            ix = self._find_action(node, legal[i])
            if node.visits[ix] == 0:
                continue
            mean = node.value_sum[ix] / node.visits[ix]
            bonus = exploration * sqrt(
                log(<double>(node.availability[ix] + 1))
                / node.visits[ix]
            )
            score = mean + bonus
            if score > best:
                best = score
                chosen = ix

        # This can only happen when the current determinization exposes no
        # previously visited action. Expand one available action regardless
        # of the global widening allowance so the information set remains
        # usable across hidden-state samples.
        if chosen < 0:
            for i in range(n):
                ix = self._find_action(node, legal[i])
                if node.visits[ix] == 0:
                    unvisited -= 1
                    if unvisited <= 0:
                        chosen = ix
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
        node.visits[action_index] += 1
        node.value_sum[action_index] += utility
        node.total_visits += 1


cdef uint64_t _ismcts_rollout_action(
    FastEngine engine,
    NativeHeuristicEvaluator evaluator,
    FastState state,
    FastState score_scratch,
    uint64_t* rng,
    double epsilon,
    int policy,
) except *:
    cdef uint64_t actions[MAX_ACTIONS]
    cdef double weights[MAX_ACTIONS]
    cdef int n = engine.legal_actions_into(state, &actions[0])
    cdef int actor = state.active_player
    cdef int i, best_ix=0
    cdef double value, best=-1.0e300
    cdef double total=0.0, target, cumulative=0.0

    if n <= 0:
        raise RuntimeError("Non-terminal ISMCTS state has no legal action")
    if n == 1:
        return actions[0]
    if policy == 2 or _ismcts_rand_unit(rng) < epsilon:
        return actions[_ismcts_rand_index(rng, n)]

    if policy == 1:
        for i in range(n):
            weights[i] = evaluator.rollout_prior_fast(
                state,
                actor,
                actions[i],
            )
            if weights[i] < 0.001:
                weights[i] = 0.001
            total += weights[i]
        target = _ismcts_rand_unit(rng) * total
        for i in range(n):
            cumulative += weights[i]
            if cumulative >= target:
                return actions[i]
        return actions[n - 1]

    for i in range(n):
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
    long iterations=100000,
    int rollout_depth=5,
    int tree_depth_limit=96,
    double exploration=1.4142135623730951,
    double progressive_widening=0.0,
    double rollout_epsilon=0.12,
    int rollout_policy=1,
    double leaf_scale=100.0,
    unsigned long long seed=1701,
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
    cdef int n, actor, ix, depth, rollout_steps, sample_ix, node_index
    cdef int root_index, prior_root_index, max_tree_depth_seen = 0
    cdef int i, best_ix=-1, second_ix=-1
    cdef int rollout_battle, action_battle
    cdef long iteration
    cdef uint64_t best_visits=0, second_visits=0
    cdef uint64_t root_total_visits_before=0
    cdef uint64_t selected_action_visits_before=0
    cdef size_t tree_nodes_before=0
    cdef uint64_t root_prior_visits[MAX_ACTIONS]
    cdef long rollouts_stopped_terminal=0
    cdef long rollouts_stopped_battle_boundary=0
    cdef long rollouts_stopped_depth=0
    cdef long rollout_actions=0
    cdef long tree_capacity_cutoffs=0
    cdef size_t tree_nodes_discarded=0
    cdef object search_context
    cdef str tree_reset_reason="none"
    cdef double utility, node_utility, mean_value
    cdef double best_mean=-1.0e300, second_mean=-1.0e300
    cdef bint expanded, created, rollout_boundary, root_reused=False
    cdef list root_stats

    if not root_states:
        raise ValueError("ISMCTS requires at least one belief sample")
    if iterations <= 0:
        raise ValueError("ISMCTS iterations must be positive")
    if rollout_depth < 0 or tree_depth_limit <= 0:
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
    if rollout_policy not in (0, 1, 2):
        raise ValueError("rollout_policy must be 0, 1, or 2")
    if not isfinite(leaf_scale) or leaf_scale <= 0.0:
        raise ValueError("leaf_scale must be positive")

    if tree is None:
        tree = ISMCTSTree(iterations)
    for i in range(MAX_ACTIONS):
        root_prior_visits[i] = 0

    if not isinstance(root_states[0], FastState):
        raise TypeError("ISMCTS belief samples must be FastState instances")
    sampled = <FastState>root_states[0]
    root_key = engine.information_hash_fast(sampled, root_player)
    for candidate in root_states:
        if not isinstance(candidate, FastState):
            raise TypeError("ISMCTS belief samples must be FastState instances")
        sampled = <FastState>candidate
        if sampled.phase == PHASE_COMPLETE:
            raise ValueError("ISMCTS cannot search a completed state")
        if sampled.active_player != root_player:
            raise ValueError("ISMCTS root_player must be the acting player")
        key = engine.information_hash_fast(sampled, root_player)
        if key.a != root_key.a or key.b != root_key.b:
            raise ValueError("ISMCTS belief samples must share a root information set")

    # Values depend on the evaluator/search horizon and the observer's belief
    # evidence, not just the node's information hash. The belief layer owns
    # reuse_context; native callers omitting it must manage belief changes.
    search_context = (engine, evaluator, root_player, rollout_depth, tree_depth_limit,
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
            root_prior_visits[i] = root_node.visits[i]

    for iteration in range(iterations):
        sample_ix = _ismcts_rand_index(&rng, len(root_states))
        sampled = <FastState>root_states[sample_ix]
        state.copy_from_fast(sampled)
        depth = 0
        rollout_boundary = False

        while state.phase != PHASE_COMPLETE and depth < tree_depth_limit:
            actor = state.active_player
            n = engine.legal_actions_into(state, &actions[0])
            if n <= 0:
                break

            # If the tree deliberately continues past a Battle boundary,
            # the previous boundary is no longer the rollout leaf.
            rollout_boundary = False
            key = engine.information_hash_fast(state, actor)
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
            action = tree.nodes[node_index].actions[ix]
            path_nodes[depth] = node_index
            path_indices[depth] = <uint16_t>ix
            action_battle = state.battle
            engine.apply_fast(state, action)
            depth += 1
            if (
                state.phase != PHASE_COMPLETE
                and state.battle != action_battle
            ):
                rollout_boundary = True

            if expanded:
                break

        if depth > max_tree_depth_seen:
            max_tree_depth_seen = depth

        rollout_steps = 0
        rollout_battle = state.battle
        while (
            not rollout_boundary
            and state.phase != PHASE_COMPLETE
            and rollout_steps < rollout_depth
        ):
            action = _ismcts_rollout_action(
                engine,
                evaluator,
                state,
                score_scratch,
                &rng,
                rollout_epsilon,
                rollout_policy,
            )
            engine.apply_fast(state, action)
            rollout_steps += 1
            rollout_actions += 1
            if (
                state.phase != PHASE_COMPLETE
                and state.battle != rollout_battle
            ):
                rollout_boundary = True
                break

        if state.phase == PHASE_COMPLETE:
            rollouts_stopped_terminal += 1
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

        for i in range(depth):
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

    root_index = tree.find(root_key)
    if root_index < 0:
        raise RuntimeError("ISMCTS failed to create a root node")
    root_node = &tree.nodes[root_index]

    root_stats = []
    for i in range(root_node.action_count):
        mean_value = (
            root_node.value_sum[i] / root_node.visits[i]
            if root_node.visits[i]
            else -1.0e300
        )
        root_stats.append(
            {
                "action": root_node.actions[i],
                "visits": root_node.visits[i],
                "prior_visits": root_prior_visits[i],
                "new_visits": root_node.visits[i] - root_prior_visits[i],
                "availability": root_node.availability[i],
                "mean_value": (
                    mean_value if root_node.visits[i] else 0.0
                ),
            }
        )
        if (
            best_ix < 0
            or root_node.visits[i] > best_visits
            or (
                root_node.visits[i] == best_visits
                and mean_value > best_mean
            )
        ):
            second_ix = best_ix
            second_visits = best_visits
            second_mean = best_mean
            best_ix = i
            best_visits = root_node.visits[i]
            best_mean = mean_value
        elif (
            second_ix < 0
            or root_node.visits[i] > second_visits
            or (
                root_node.visits[i] == second_visits
                and mean_value > second_mean
            )
        ):
            second_ix = i
            second_visits = root_node.visits[i]
            second_mean = mean_value

    if best_ix < 0:
        raise RuntimeError("ISMCTS root has no action")
    selected_action_visits_before = root_prior_visits[best_ix]

    return {
        "action": root_node.actions[best_ix],
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
        "iterations": iterations,
        "tree_nodes": tree.node_count,
        "tree_nodes_before": tree_nodes_before,
        "tree_nodes_discarded": tree_nodes_discarded,
        "tree_reset_reason": tree_reset_reason,
        "tree_max_nodes": tree.max_nodes,
        "tree_capacity_cutoffs": tree_capacity_cutoffs,
        "tree_nodes_added": tree.node_count - tree_nodes_before,
        "max_tree_depth": max_tree_depth_seen,
        "belief_states": len(root_states),
        "root_stats": root_stats,
        "rollouts_stopped_terminal": rollouts_stopped_terminal,
        "rollouts_stopped_battle_boundary": rollouts_stopped_battle_boundary,
        "rollouts_stopped_depth": rollouts_stopped_depth,
        "rollout_actions": rollout_actions,
        "tree_storage": "native-hash-arena",
        "progressive_widening": progressive_widening,
        "progressive_widening_alpha": 0.5 if progressive_widening > 0.0 else 0.0,
        "rollout_policy": (
            "cheap" if rollout_policy == 1
            else "random" if rollout_policy == 2
            else "greedy"
        ),
    }
