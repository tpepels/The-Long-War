# AI/game boundary

The algorithms do **not** own the rules. This makes paper card and mechanic
changes independent of strategy code.

## Boundary

```text
                  game data + canonical engine
                              |
               LongWarSearchGame (Python)
               _native_search_game.pxi (Cython)
                              |
                         SearchGame API
                       /        |        \
                alpha-beta     MCCFR     ISMCTS
```

`src/longwar/algorithms/game_interface.py` defines the generic Python
contract. It exposes only state cloning/reuse, actions, actor, terminal and
frontier state, strategic-turn completion, state and information-set identity,
action identifiers, ordering priorities, evaluation and terminal reward.

`src/longwar/search_adapters.py` is the adapter for The Long War. It alone
extracts the complete transposition state, provides observation redaction via
the canonical native engine, and knows what counts as a completed turn.
The pure reference algorithms are `generic_alpha_beta.py`,
`generic_mccfr.py`, and `generic_ismcts.py`.

The original `AlphaBetaSearch` constructor and public re-exports remain
supported by a small facade. The main MCCFR trainer delegates its portable
traversal to the generic reference core. Training that already runs using
native packed states remains on that route.

## Native speed

Native search uses the companion contract in
`src/longwar/_native_search_game.pxi`. It has Cython `cdef inline`
methods for legal actions, transitions, terminal status, active player,
turn boundary, state hashes, information keys and action identity. These
compile down to the existing native engine calls without allocating Python
objects or introducing virtual callbacks per node.

This is a **compile-time specialization**: the current native extension
still compiles against `FastState`, `FastEngine`, and the current packed
heuristic evaluator. That representation and any algorithm policy assumptions
about battles/deck economy remain native portability work. The adapter
isolates transition semantics but is not yet a binary plug-in system for
arbitrary games. Avoid claiming fully pluggable native kernels until the
remaining game-specific rollout and evaluator code is moved behind the
native contract.

The generic implementations are reusable immediately; native remains the
default for production play, retaining its throughput.

## Contract invariants

- An information key must never include the opponent's hidden hand/deck.
- Every determinization supplied at a search root shares the observer's
  information set.
- Legal actions must have collision-free stable IDs within that set.
- Depth decreases **only when a strategic turn completes**. Mandatory effect
  choices remain searchable at depth zero.
- A transposition key contains all state that may change legal decisions,
  transitions or utilities; it is not an information-set key.
- Terminal reward and nonterminal evaluation use one consistent
  player-relative value convention.
- Cloning/copying a state must not alias mutable board/hand storage between
  siblings.
- Native adapters must not allocate Python objects in legal-action,
  transition or turn-check hot paths.

## Verification

```bash
make native-build
python -m pytest -q tests/test_generic_search.py tests/test_alpha_beta_contract.py
python -m pytest -q tests/test_mccfr.py tests/test_ismcts.py
make verify-algorithms
```

Performance comparisons should use fixed seeds/decks/budgets before and after
the change; do not compare fallback Python search speed with the optimized
native implementation. Future paper-game mechanics should change the
canonical engine and adapter(s), not the generic algorithms.
