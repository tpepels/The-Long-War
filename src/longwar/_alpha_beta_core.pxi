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


cdef int ordered_actions_into(
    FastEngine engine,
    NativeHeuristicEvaluator evaluator,
    FastState state,
    int actor,
    int width,
    uint64_t* selected,
    FastState order_scratch,
) except -1:
    cdef uint64_t actions[MAX_ACTIONS]
    cdef double scores[MAX_ACTIONS]
    cdef int n, i, j, selected_n, kind
    cdef uint64_t action, tmp_action
    cdef double score, tmp_score
    cdef bint have_pass=False, have_draw=False

    n = engine.legal_actions_into(state, &actions[0])
    if n <= 0:
        return 0

    for i in range(n):
        scores[i] = evaluator.score_action_fast(
            state,
            actor,
            actions[i],
            order_scratch,
        )

    # Stable insertion sort: highest one-ply actor score first.
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

    selected_n = n if n <= width else width
    for i in range(selected_n):
        selected[i] = actions[i]
        kind = action_kind(actions[i])
        if kind == TYPE_PASS:
            have_pass = True
        elif kind == TYPE_DRAW:
            have_draw = True

    # Match the Python beam policy: Pass and Draw always survive pruning.
    if selected_n < n:
        for i in range(selected_n, n):
            kind = action_kind(actions[i])
            if kind == TYPE_PASS and not have_pass:
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
) except *:
    cdef uint64_t actions[MAX_ACTIONS]
    cdef int n, i, actor
    cdef bint maximizing
    cdef double value, child_value
    cdef FastState child
    cdef FastState order_scratch

    budget.nodes += 1
    if budget.nodes > budget.limit:
        raise NativeSearchLimit()

    if state.phase == PHASE_COMPLETE or depth <= 0:
        return evaluator.strategic_evaluate_fast(state, root_player)

    actor = state.active_player
    order_scratch = <FastState>scratch[level * 2]
    child = <FastState>scratch[level * 2 + 1]
    n = ordered_actions_into(
        engine,
        evaluator,
        state,
        actor,
        width,
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
        )

        if maximizing:
            if child_value > value:
                value = child_value
            if value > alpha:
                alpha = value
        else:
            if child_value < value:
                value = child_value
            if value < beta:
                beta = value

        if beta <= alpha:
            break

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
    )
