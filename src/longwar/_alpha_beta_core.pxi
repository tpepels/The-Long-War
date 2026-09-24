cdef int TT_EXACT = 0
cdef int TT_LOWER = 1
cdef int TT_UPPER = 2


class NativeSearchLimit(RuntimeError):
    pass


cdef class NativeSearchBudget:
    cdef public long limit
    cdef public long nodes

    def __init__(self, long limit):
        if limit <= 0:
            raise ValueError("limit must be positive")
        self.limit = limit
        self.nodes = 0


cdef struct NativeTTEntry:
    uint64_t key_a
    uint64_t key_b
    uint64_t best_action
    double value
    int16_t depth
    int8_t bound
    uint8_t used


cdef class NativeTranspositionTable:
    cdef NativeTTEntry* entries
    cdef size_t capacity
    cdef public long hits
    cdef public long stores

    def __cinit__(self):
        self.entries = NULL
        self.capacity = 0
        self.hits = 0
        self.stores = 0

    def __init__(self, long capacity_hint=131072):
        cdef size_t capacity = 1024
        if capacity_hint < 1024:
            capacity_hint = 1024
        while capacity < <size_t>capacity_hint:
            capacity <<= 1
        self.entries = <NativeTTEntry*>malloc(
            capacity * sizeof(NativeTTEntry)
        )
        if self.entries == NULL:
            raise MemoryError("Unable to allocate native transposition table")
        self.capacity = capacity
        memset(
            self.entries,
            0,
            capacity * sizeof(NativeTTEntry),
        )

    def __dealloc__(self):
        if self.entries != NULL:
            free(self.entries)

    cpdef clear(self):
        if self.entries != NULL:
            memset(
                self.entries,
                0,
                self.capacity * sizeof(NativeTTEntry),
            )
        self.hits = 0
        self.stores = 0

    cdef size_t index_for(
        self,
        InfoHash128 key,
        int root_player,
    ) noexcept:
        cdef uint64_t mixed = key.a ^ (
            (key.b << 17) | (key.b >> 47)
        )
        mixed ^= <uint64_t>(root_player + 1) * 0x9E3779B97F4A7C15ULL
        mixed ^= mixed >> 30
        mixed *= 0xBF58476D1CE4E5B9ULL
        mixed ^= mixed >> 27
        return <size_t>mixed & (self.capacity - 1)

    cdef bint probe(
        self,
        InfoHash128 key,
        int root_player,
        int depth,
        double* alpha,
        double* beta,
        double* value,
        uint64_t* best_action,
    ) noexcept:
        cdef NativeTTEntry* entry = &self.entries[
            self.index_for(key, root_player)
        ]
        best_action[0] = 0
        if (
            not entry.used
            or entry.key_a != key.a
            or entry.key_b != key.b
        ):
            return False

        best_action[0] = entry.best_action
        if entry.depth < depth:
            return False

        self.hits += 1
        if entry.bound == TT_EXACT:
            value[0] = entry.value
            return True
        if entry.bound == TT_LOWER and entry.value > alpha[0]:
            alpha[0] = entry.value
        elif entry.bound == TT_UPPER and entry.value < beta[0]:
            beta[0] = entry.value
        if alpha[0] >= beta[0]:
            value[0] = entry.value
            return True
        return False

    cdef void store(
        self,
        InfoHash128 key,
        int root_player,
        int depth,
        double value,
        int bound,
        uint64_t best_action,
    ) noexcept:
        cdef NativeTTEntry* entry = &self.entries[
            self.index_for(key, root_player)
        ]
        if (
            entry.used
            and entry.key_a == key.a
            and entry.key_b == key.b
            and entry.depth > depth
        ):
            return
        entry.key_a = key.a
        entry.key_b = key.b
        entry.best_action = best_action
        entry.value = value
        entry.depth = <int16_t>depth
        entry.bound = <int8_t>bound
        entry.used = 1
        self.stores += 1


cdef int ordered_actions_into(
    FastEngine engine,
    NativeHeuristicEvaluator evaluator,
    FastState state,
    int actor,
    int width,
    uint64_t preferred_action,
    uint64_t* selected,
    FastState order_scratch,
) except -1:
    cdef uint64_t actions[MAX_ACTIONS]
    cdef double scores[MAX_ACTIONS]
    cdef int n, i, j, selected_n, kind, preferred_ix=-1
    cdef uint64_t action, tmp_action
    cdef double score, tmp_score
    cdef bint have_pass=False, have_draw=False, have_preferred=False

    n = engine.legal_actions_into(state, &actions[0])
    if n <= 0:
        return 0

    for i in range(n):
        if preferred_action != 0 and actions[i] == preferred_action:
            preferred_ix = i
        scores[i] = evaluator.action_order_score_fast(
            state,
            actor,
            actions[i],
            order_scratch,
        )

    for i in range(1, n):
        tmp_action = actions[i]
        tmp_score = scores[i]
        j = i - 1
        while j >= 0 and scores[j] < tmp_score:
            actions[j + 1] = actions[j]
            scores[j + 1] = scores[j]
            j -= 1
        actions[j + 1] = tmp_action
        scores[j + 1] = tmp_score

    if preferred_action != 0:
        for i in range(n):
            if actions[i] == preferred_action:
                preferred_ix = i
                break
        if preferred_ix > 0:
            tmp_action = actions[0]
            actions[0] = actions[preferred_ix]
            actions[preferred_ix] = tmp_action

    selected_n = n if n <= width else width
    for i in range(selected_n):
        selected[i] = actions[i]
        kind = action_kind(actions[i])
        if kind == TYPE_PASS:
            have_pass = True
        elif kind == TYPE_DRAW:
            have_draw = True
        if actions[i] == preferred_action:
            have_preferred = True

    if selected_n < n:
        for i in range(selected_n, n):
            kind = action_kind(actions[i])
            if preferred_action != 0 and actions[i] == preferred_action and not have_preferred:
                selected[selected_n] = actions[i]
                selected_n += 1
                have_preferred = True
            elif kind == TYPE_PASS and not have_pass:
                selected[selected_n] = actions[i]
                selected_n += 1
                have_pass = True
            elif kind == TYPE_DRAW and not have_draw:
                selected[selected_n] = actions[i]
                selected_n += 1
                have_draw = True

    return selected_n


cdef double native_alphabeta(
    FastEngine engine,
    NativeHeuristicEvaluator evaluator,
    FastState state,
    int root_player,
    int depth,
    double alpha,
    double beta,
    NativeSearchBudget budget,
    int width,
    object scratch,
    int level,
    NativeTranspositionTable table,
) except *:
    cdef uint64_t actions[MAX_ACTIONS]
    cdef int n, i, actor, bound
    cdef bint maximizing
    cdef double value, child_value, alpha_start=alpha, beta_start=beta
    cdef double cached_value
    cdef uint64_t preferred_action=0, best_action=0
    cdef FastState child
    cdef FastState order_scratch
    cdef InfoHash128 key

    budget.nodes += 1
    if budget.nodes > budget.limit:
        raise NativeSearchLimit()

    if state.phase == PHASE_COMPLETE or depth <= 0:
        return evaluator.strategic_evaluate_fast(state, root_player)

    key = engine.state_hash_fast(state)
    if table is not None and table.probe(
        key,
        root_player,
        depth,
        &alpha,
        &beta,
        &cached_value,
        &preferred_action,
    ):
        return cached_value

    actor = state.active_player
    order_scratch = <FastState>scratch[level * 2]
    child = <FastState>scratch[level * 2 + 1]
    n = ordered_actions_into(
        engine,
        evaluator,
        state,
        actor,
        width,
        preferred_action,
        &actions[0],
        order_scratch,
    )
    if n <= 0:
        return evaluator.strategic_evaluate_fast(state, root_player)

    maximizing = actor == root_player
    value = -1.0e300 if maximizing else 1.0e300

    for i in range(n):
        child.copy_from_fast(state)
        engine.apply_fast(child, actions[i])
        child_value = native_alphabeta(
            engine,
            evaluator,
            child,
            root_player,
            depth - 1,
            alpha,
            beta,
            budget,
            width,
            scratch,
            level + 1,
            table,
        )

        if maximizing:
            if child_value > value:
                value = child_value
                best_action = actions[i]
            if value > alpha:
                alpha = value
        else:
            if child_value < value:
                value = child_value
                best_action = actions[i]
            if value < beta:
                beta = value

        if beta <= alpha:
            break

    if table is not None:
        if value <= alpha_start:
            bound = TT_UPPER
        elif value >= beta_start:
            bound = TT_LOWER
        else:
            bound = TT_EXACT
        table.store(
            key,
            root_player,
            depth,
            value,
            bound,
            best_action,
        )
    return value


cpdef double native_search_value(
    FastEngine engine,
    object game_state,
    int root_player,
    int depth,
    double alpha,
    double beta,
    NativeSearchBudget budget,
    int candidate_width,
    NativeHeuristicEvaluator evaluator=None,
    NativeTranspositionTable table=None,
):
    cdef FastState state = engine.from_game_state(game_state)
    cdef int levels = depth + 2
    cdef object scratch
    if evaluator is None:
        evaluator = NativeHeuristicEvaluator(engine)
    scratch = [
        FastState()
        for _ in range(levels * 2)
    ]
    return native_alphabeta(
        engine,
        evaluator,
        state,
        root_player,
        depth,
        alpha,
        beta,
        budget,
        candidate_width,
        scratch,
        0,
        table,
    )
