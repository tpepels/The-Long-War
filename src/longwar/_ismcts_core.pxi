# Native single-observer information-set Monte Carlo tree search.
#
# Hidden states are root-sampled by the belief layer. The hot tree loop uses
# native 128-bit information hashes, an open-addressed C table, C node/action
# storage and fixed C path arrays. Python objects are created only for the
# input belief states and the final diagnostics payload.

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
    uint32_t* visits
    uint32_t* availability
    double* value_sum
    uint32_t total_visits
    uint16_t action_count
    int8_t player


cdef class ISMCTSTree:
    cdef ISMCTSNodeRecord* nodes
    cdef int32_t* buckets
    cdef size_t node_count
    cdef size_t node_capacity
    cdef size_t bucket_capacity

    def __cinit__(self):
        self.nodes = NULL
        self.buckets = NULL
        self.node_count = 0
        self.node_capacity = 0
        self.bucket_capacity = 0

    def __init__(self, long expected_nodes):
        cdef size_t node_capacity = 1024
        cdef size_t bucket_capacity = 2048
        if expected_nodes < 1:
            expected_nodes = 1
        while (
            node_capacity < <size_t>expected_nodes
            and node_capacity < 16384
        ):
            node_capacity <<= 1
        while bucket_capacity < <size_t>expected_nodes * 2:
            bucket_capacity <<= 1
        self._allocate(node_capacity, bucket_capacity)

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
        node.visits = <uint32_t*>malloc(n * sizeof(uint32_t))
        node.availability = <uint32_t*>malloc(n * sizeof(uint32_t))
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
        uint64_t* rng,
        bint* expanded,
    ) except -1:
        cdef ISMCTSNodeRecord* node = &self.nodes[node_index]
        cdef int i, ix, chosen=-1, unvisited=0
        cdef double mean, bonus, score, best=-1.0e300

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

        if chosen >= 0:
            expanded[0] = True
            return chosen

        expanded[0] = False
        for i in range(n):
            ix = self._find_action(node, legal[i])
            mean = node.value_sum[ix] / node.visits[ix]
            bonus = exploration * sqrt(
                log(<double>(node.availability[ix] + 1))
                / node.visits[ix]
            )
            score = mean + bonus
            if score > best:
                best = score
                chosen = ix
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
    long iterations=20000,
    int rollout_depth=5,
    int tree_depth_limit=96,
    double exploration=1.4142135623730951,
    double rollout_epsilon=0.12,
    int rollout_policy=1,
    double leaf_scale=100.0,
    unsigned long long seed=1701,
):
    cdef ISMCTSTree tree
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
    cdef int root_index, max_tree_depth_seen = 0
    cdef int i, best_ix=-1, second_ix=-1
    cdef long iteration
    cdef long best_visits=-1, second_visits=-1
    cdef double utility, node_utility, mean_value
    cdef double best_mean=-1.0e300, second_mean=-1.0e300
    cdef bint expanded, created
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
    if leaf_scale <= 0.0:
        raise ValueError("leaf_scale must be positive")

    tree = ISMCTSTree(iterations)
    sampled = <FastState>root_states[0]
    if sampled.phase == PHASE_COMPLETE:
        raise ValueError("ISMCTS cannot search a completed state")
    root_key = engine.information_hash_fast(sampled, root_player)

    for iteration in range(iterations):
        sample_ix = _ismcts_rand_index(&rng, len(root_states))
        sampled = <FastState>root_states[sample_ix]
        state.copy_from_fast(sampled)
        depth = 0

        while state.phase != PHASE_COMPLETE and depth < tree_depth_limit:
            actor = state.active_player
            n = engine.legal_actions_into(state, &actions[0])
            if n <= 0:
                break

            key = engine.information_hash_fast(state, actor)
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
                &rng,
                &expanded,
            )
            action = tree.nodes[node_index].actions[ix]
            path_nodes[depth] = node_index
            path_indices[depth] = <uint16_t>ix
            engine.apply_fast(state, action)
            depth += 1

            if expanded:
                break

        if depth > max_tree_depth_seen:
            max_tree_depth_seen = depth

        rollout_steps = 0
        while (
            state.phase != PHASE_COMPLETE
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

        if state.phase == PHASE_COMPLETE:
            utility = 1.0 if state.winner == root_player else -1.0
        else:
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
                "availability": root_node.availability[i],
                "mean_value": (
                    mean_value if root_node.visits[i] else 0.0
                ),
            }
        )
        if (
            root_node.visits[i] > best_visits
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
            root_node.visits[i] > second_visits
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

    return {
        "action": root_node.actions[best_ix],
        "root_total_visits": root_node.total_visits,
        "selected_action_visits": best_visits,
        "mean_value": best_mean,
        "second_mean_value": (
            second_mean if second_ix >= 0 else best_mean
        ),
        "iterations": iterations,
        "tree_nodes": tree.node_count,
        "max_tree_depth": max_tree_depth_seen,
        "belief_states": len(root_states),
        "root_stats": root_stats,
        "tree_storage": "native-hash-arena",
        "rollout_policy": (
            "cheap" if rollout_policy == 1
            else "random" if rollout_policy == 2
            else "greedy"
        ),
    }
