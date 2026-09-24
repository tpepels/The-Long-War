# cython: language_level=3, boundscheck=False, wraparound=False, initializedcheck=False
from __future__ import annotations


cdef class CFRNode:
    cdef public object regret_sum
    cdef public object strategy_sum
    cdef public long visits
    cdef public long average_visits

    def __init__(
        self,
        regret_sum=None,
        strategy_sum=None,
        visits=0,
        average_visits=0,
    ):
        self.regret_sum = {} if regret_sum is None else dict(regret_sum)
        self.strategy_sum = {} if strategy_sum is None else dict(strategy_sum)
        self.visits = visits
        self.average_visits = average_visits

    def ensure_actions(self, keys):
        cdef object key
        for key in keys:
            if key not in self.regret_sum:
                self.regret_sum[key] = 0.0
            if key not in self.strategy_sum:
                self.strategy_sum[key] = 0.0

    def strategy(self, keys):
        cdef object key
        cdef double value
        cdef double total = 0.0
        cdef double probability
        cdef dict positives = {}
        cdef dict result = {}

        self.ensure_actions(keys)
        for key in keys:
            value = self.regret_sum[key]
            if value < 0.0:
                value = 0.0
            positives[key] = value
            total += value

        if total > 0.0:
            for key in keys:
                result[key] = positives[key] / total
            return result

        probability = 1.0 / len(keys)
        for key in keys:
            result[key] = probability
        return result

    def accumulate_average(self, strategy, *, reach_weight=1.0):
        cdef object key
        cdef double probability
        cdef double weight = reach_weight
        for key, probability in strategy.items():
            self.strategy_sum[key] = (
                self.strategy_sum.get(key, 0.0)
                + weight * probability
            )
        self.average_visits += 1

    def average_strategy(self, keys=None):
        cdef object key
        cdef double value
        cdef double total = 0.0
        cdef dict result = {}

        if keys is None:
            keys = list(self.strategy_sum)
        else:
            keys = list(keys)
        if not keys:
            return {}

        for key in keys:
            value = self.strategy_sum.get(key, 0.0)
            if value > 0.0:
                total += value

        if total <= 0.0:
            return self.strategy(keys)

        for key in keys:
            value = self.strategy_sum.get(key, 0.0)
            if value < 0.0:
                value = 0.0
            result[key] = value / total
        return result


def sample_distribution(rng, probabilities):
    cdef double threshold = rng.random()
    cdef double cumulative = 0.0
    cdef double probability
    cdef object key
    cdef object last = None

    for key, probability in probabilities.items():
        last = key
        cumulative += probability
        if threshold <= cumulative:
            return key
    return last


def external_sampling_traverse(
    state,
    traverser,
    *,
    depth,
    max_depth,
    nodes,
    rng,
    is_terminal,
    terminal_utility,
    current_player,
    legal_actions,
    action_key,
    information_set_id,
    next_state,
    leaf_value=None,
    reach=(1.0, 1.0),
):
    cdef int actor
    cdef object actions
    cdef object keys
    cdef object info_id
    cdef object node
    cdef object strategy
    cdef object action_by_key
    cdef object key
    cdef object sampled_key
    cdef object child_reach
    cdef object utility
    cdef dict action_utilities
    cdef double node_utility = 0.0

    if is_terminal(state):
        return terminal_utility(state, traverser)

    if max_depth is not None and depth >= max_depth:
        if leaf_value is None:
            raise RuntimeError("Depth limit reached without a leaf evaluator")
        return leaf_value(state, traverser)

    actor = current_player(state)
    actions = list(legal_actions(state))
    if not actions:
        raise RuntimeError("Non-terminal state has no legal actions")

    keys = [action_key(action) for action in actions]
    if len(keys) != len(set(keys)):
        raise RuntimeError("Action serialization collision inside information set")

    info_id = information_set_id(state, actor)
    node = nodes.get(info_id)
    if node is None:
        node = CFRNode()
        nodes[info_id] = node
    node.ensure_actions(keys)
    node.visits += 1
    strategy = node.strategy(keys)
    action_by_key = dict(zip(keys, actions))

    if actor == traverser:
        action_utilities = {}
        node_utility = 0.0
        for key in keys:
            child_reach = [reach[0], reach[1]]
            child_reach[actor] *= strategy[key]
            utility = external_sampling_traverse(
                next_state(state, action_by_key[key]),
                traverser,
                depth=depth + 1,
                max_depth=max_depth,
                nodes=nodes,
                rng=rng,
                is_terminal=is_terminal,
                terminal_utility=terminal_utility,
                current_player=current_player,
                legal_actions=legal_actions,
                action_key=action_key,
                information_set_id=information_set_id,
                next_state=next_state,
                leaf_value=leaf_value,
                reach=(child_reach[0], child_reach[1]),
            )
            action_utilities[key] = utility
            node_utility += strategy[key] * utility

        for key in keys:
            node.regret_sum[key] += action_utilities[key] - node_utility
        return node_utility

    # External sampling already visits this player in proportion to own
    # reach. Its sampling probability cancels the average-strategy weight.
    node.accumulate_average(strategy)
    sampled_key = sample_distribution(rng, strategy)
    child_reach = [reach[0], reach[1]]
    child_reach[actor] *= strategy[sampled_key]
    return external_sampling_traverse(
        next_state(state, action_by_key[sampled_key]),
        traverser,
        depth=depth + 1,
        max_depth=max_depth,
        nodes=nodes,
        rng=rng,
        is_terminal=is_terminal,
        terminal_utility=terminal_utility,
        current_player=current_player,
        legal_actions=legal_actions,
        action_key=action_key,
        information_set_id=information_set_id,
        next_state=next_state,
        leaf_value=leaf_value,
        reach=(child_reach[0], child_reach[1]),
    )


def longwar_external_sampling_traverse(
    trainer,
    state,
    traverser,
    *,
    depth,
    action_key,
    information_set_id,
    reach=(1.0, 1.0),
    scratch_by_depth=None,
):
    """Specialized Long War traversal without generic engine callbacks."""
    cdef int actor
    cdef int child_depth
    cdef object actions
    cdef object keys
    cdef object info_id
    cdef object node
    cdef object strategy
    cdef object action
    cdef object key
    cdef object child
    cdef object utility
    cdef object child_reach
    cdef object sampled_action
    cdef double sampled_probability
    cdef double probability
    cdef double threshold
    cdef double cumulative
    cdef double node_utility
    cdef list utilities

    if scratch_by_depth is None:
        scratch_by_depth = {}

    if state.phase.value == "complete":
        return 1.0 if state.winner == traverser else -1.0

    if depth >= trainer.max_depth:
        return trainer._leaf_value(state, traverser)

    actor = state.active_player
    actions = trainer.engine.legal_actions(state)
    if not actions:
        raise RuntimeError("Non-terminal state has no legal actions")

    keys = [action_key(action) for action in actions]
    info_id = information_set_id(state, actor)
    node = trainer.nodes.get(info_id)
    if node is None:
        node = CFRNode()
        trainer.nodes[info_id] = node
    node.ensure_actions(keys)
    node.visits += 1
    strategy = node.strategy(keys)

    child_depth = depth + 1

    if actor == traverser:
        utilities = []
        node_utility = 0.0
        for key, action in zip(keys, actions):
            probability = strategy[key]
            if actor == 0:
                child_reach = (reach[0] * probability, reach[1])
            else:
                child_reach = (reach[0], reach[1] * probability)

            child = scratch_by_depth.get(child_depth)
            if child is None:
                child = state.clone()
                scratch_by_depth[child_depth] = child
            else:
                child.copy_from(state)
            trainer.engine.apply(child, action, validate=False)

            utility = longwar_external_sampling_traverse(
                trainer,
                child,
                traverser,
                depth=child_depth,
                action_key=action_key,
                information_set_id=information_set_id,
                reach=child_reach,
                scratch_by_depth=scratch_by_depth,
            )
            utilities.append(utility)
            node_utility += probability * utility

        for key, utility in zip(keys, utilities):
            node.regret_sum[key] += utility - node_utility
        return node_utility

    # External sampling already visits this player in proportion to own
    # reach. Its sampling probability cancels the average-strategy weight.
    node.accumulate_average(strategy)

    threshold = trainer.rng.random()
    cumulative = 0.0
    sampled_action = actions[len(actions) - 1]
    sampled_probability = strategy[keys[len(keys) - 1]]
    for key, action in zip(keys, actions):
        probability = strategy[key]
        cumulative += probability
        sampled_action = action
        sampled_probability = probability
        if threshold <= cumulative:
            break

    if actor == 0:
        child_reach = (reach[0] * sampled_probability, reach[1])
    else:
        child_reach = (reach[0], reach[1] * sampled_probability)

    child = scratch_by_depth.get(child_depth)
    if child is None:
        child = state.clone()
        scratch_by_depth[child_depth] = child
    else:
        child.copy_from(state)
    trainer.engine.apply(child, sampled_action, validate=False)

    return longwar_external_sampling_traverse(
        trainer,
        child,
        traverser,
        depth=child_depth,
        action_key=action_key,
        information_set_id=information_set_id,
        reach=child_reach,
        scratch_by_depth=scratch_by_depth,
    )
