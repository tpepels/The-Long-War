# Cython single-observer information-set Monte Carlo tree search.
#
# Hidden states are root-sampled by the belief layer before entering this
# algorithm. Tree nodes are keyed by the acting player's information state,
# so different determinizations merge whenever that player cannot distinguish
# them. The game engine and heuristic evaluator remain separate dependencies.

cdef inline uint64_t _ismcts_next(uint64_t* state) noexcept:
    # Keep every literal in the C domain. Without the ULL suffix Cython can
    # route the high-bit constants through Python integers, which overflows
    # when converted back to uint64_t inside this noexcept helper.
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
    return <double>(_ismcts_next(state) >> 11) * (1.0 / 9007199254740992.0)


cdef class ISMCTSNode:
    cdef uint64_t* actions
    cdef long* visits
    cdef long* availability
    cdef double* value_sum
    cdef int action_count
    cdef public long total_visits
    cdef public int player

    def __cinit__(self):
        self.actions = NULL
        self.visits = NULL
        self.availability = NULL
        self.value_sum = NULL
        self.action_count = 0
        self.total_visits = 0
        self.player = -1

    def __dealloc__(self):
        if self.actions != NULL:
            free(self.actions)
        if self.visits != NULL:
            free(self.visits)
        if self.availability != NULL:
            free(self.availability)
        if self.value_sum != NULL:
            free(self.value_sum)

    cdef void initialize(
        self,
        int player,
        uint64_t* actions,
        int n,
    ) except *:
        cdef int i
        if self.action_count != 0:
            return
        if n <= 0:
            raise ValueError("ISMCTS node requires at least one legal action")

        self.actions = <uint64_t*>malloc(n * sizeof(uint64_t))
        self.visits = <long*>malloc(n * sizeof(long))
        self.availability = <long*>malloc(n * sizeof(long))
        self.value_sum = <double*>malloc(n * sizeof(double))
        if (
            self.actions == NULL
            or self.visits == NULL
            or self.availability == NULL
            or self.value_sum == NULL
        ):
            raise MemoryError("Unable to allocate ISMCTS node")

        self.player = player
        self.action_count = n
        for i in range(n):
            self.actions[i] = actions[i]
            self.visits[i] = 0
            self.availability[i] = 0
            self.value_sum[i] = 0.0

    cdef int find_action(self, uint64_t action) noexcept:
        cdef int i
        for i in range(self.action_count):
            if self.actions[i] == action:
                return i
        return -1

    cdef int choose(
        self,
        uint64_t* legal,
        int n,
        double exploration,
        uint64_t* rng,
        bint* expanded,
    ) except -1:
        cdef int i, ix, chosen=-1, unvisited=0
        cdef double mean, bonus, score, best=-1.0e300

        for i in range(n):
            ix = self.find_action(legal[i])
            if ix < 0:
                raise RuntimeError(
                    "Legal-action set changed inside an information set"
                )
            self.availability[ix] += 1
            if self.visits[ix] == 0:
                unvisited += 1
                if _ismcts_rand_index(rng, unvisited) == 0:
                    chosen = ix

        if chosen >= 0:
            expanded[0] = True
            return chosen

        expanded[0] = False
        for i in range(n):
            ix = self.find_action(legal[i])
            mean = self.value_sum[ix] / self.visits[ix]
            bonus = exploration * sqrt(
                log(<double>(self.availability[ix] + 1))
                / self.visits[ix]
            )
            score = mean + bonus
            if score > best:
                best = score
                chosen = ix
        return chosen

    cdef void update(self, int ix, double utility) noexcept:
        self.visits[ix] += 1
        self.value_sum[ix] += utility
        self.total_visits += 1

    cdef uint64_t action_at(self, int ix) noexcept:
        return self.actions[ix]

    property stats:
        def __get__(self):
            cdef int i
            return [
                {
                    "action": self.actions[i],
                    "visits": self.visits[i],
                    "availability": self.availability[i],
                    "mean_value": (
                        self.value_sum[i] / self.visits[i]
                        if self.visits[i]
                        else 0.0
                    ),
                }
                for i in range(self.action_count)
            ]


cdef uint64_t _ismcts_rollout_action(
    FastEngine engine,
    NativeHeuristicEvaluator evaluator,
    FastState state,
    FastState score_scratch,
    uint64_t* rng,
    double epsilon,
) except *:
    cdef uint64_t actions[MAX_ACTIONS]
    cdef int n = engine.legal_actions_into(state, &actions[0])
    cdef int actor = state.active_player
    cdef int i, best_ix=0
    cdef double value, best=-1.0e300

    if n <= 0:
        raise RuntimeError("Non-terminal ISMCTS state has no legal action")
    if n == 1:
        return actions[0]
    if _ismcts_rand_unit(rng) < epsilon:
        return actions[_ismcts_rand_index(rng, n)]

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
    int rollout_depth=16,
    int tree_depth_limit=96,
    double exploration=1.4142135623730951,
    double rollout_epsilon=0.12,
    double leaf_scale=100.0,
    unsigned long long seed=1701,
):
    """Root-belief-sampled single-observer ISMCTS on packed engine state.

    root_states are determinizations sampled from the root player's belief.
    The Cython loop performs selection, expansion, rollout and backpropagation.
    """
    cdef dict tree = {}
    cdef FastState state = FastState()
    cdef FastState score_scratch = FastState()
    cdef FastState sampled
    cdef ISMCTSNode node
    cdef ISMCTSNode root_node
    cdef bytes key, root_key
    cdef uint64_t actions[MAX_ACTIONS]
    cdef uint64_t action
    cdef uint64_t rng = <uint64_t>seed
    cdef int n, actor, ix, depth, rollout_steps, sample_ix
    cdef int max_tree_depth_seen = 0
    cdef int i, best_ix=-1, second_ix=-1
    cdef long iteration
    cdef long best_visits=-1, second_visits=-1
    cdef double utility, node_utility, mean_value
    cdef double best_mean=-1.0e300, second_mean=-1.0e300
    cdef bint expanded
    cdef list path_nodes
    cdef list path_indices
    cdef list root_stats

    if not root_states:
        raise ValueError("ISMCTS requires at least one belief sample")
    if iterations <= 0:
        raise ValueError("ISMCTS iterations must be positive")
    if rollout_depth < 0 or tree_depth_limit <= 0:
        raise ValueError("ISMCTS depth settings are invalid")
    if leaf_scale <= 0.0:
        raise ValueError("leaf_scale must be positive")

    sampled = <FastState>root_states[0]
    if sampled.phase == PHASE_COMPLETE:
        raise ValueError("ISMCTS cannot search a completed state")
    root_key = engine.information_key_fast(sampled, root_player)

    for iteration in range(iterations):
        sample_ix = _ismcts_rand_index(&rng, len(root_states))
        sampled = <FastState>root_states[sample_ix]
        state.copy_from_fast(sampled)
        path_nodes = []
        path_indices = []
        depth = 0

        while state.phase != PHASE_COMPLETE and depth < tree_depth_limit:
            actor = state.active_player
            n = engine.legal_actions_into(state, &actions[0])
            if n <= 0:
                break

            key = engine.information_key_fast(state, actor)
            node = <ISMCTSNode>tree.get(key)
            if node is None:
                node = ISMCTSNode()
                node.initialize(actor, &actions[0], n)
                tree[key] = node

            ix = node.choose(
                &actions[0],
                n,
                exploration,
                &rng,
                &expanded,
            )
            action = node.action_at(ix)
            path_nodes.append(node)
            path_indices.append(ix)
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

        for i in range(len(path_nodes)):
            node = <ISMCTSNode>path_nodes[i]
            ix = <int>path_indices[i]
            node_utility = utility if node.player == root_player else -utility
            node.update(ix, node_utility)

    root_node = <ISMCTSNode>tree.get(root_key)
    if root_node is None:
        raise RuntimeError("ISMCTS failed to create a root node")

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
        "tree_nodes": len(tree),
        "max_tree_depth": max_tree_depth_seen,
        "belief_states": len(root_states),
        "root_stats": root_stats,
    }
