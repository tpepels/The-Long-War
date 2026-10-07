# Testing during active game development

The Long War is still in active design. Tests are guardrails, not a second ruleset.

## The rule

A test may prevent a change only when it protects a real invariant:

- source code must parse;
- referenced files/assets must exist;
- authored data must be structurally valid;
- build outputs must be producible;
- engine behavior must satisfy the rules that the engine currently claims to implement;
- security/visibility/authority boundaries must remain intact.

A test must **not** become an accidental product requirement merely because a design decision happened to be true when the test was written.

During active development, the following are normally **advisory design diagnostics**, not merge/deploy gates:

- exact rulebook wording or paragraph order;
- exact card titles, card identities, costs, Strength, classes, or effect mix;
- target numbers of movement cards, zero-cost cards, card families, or deck archetypes;
- exact website navigation wording;
- exact CSS structure, density classes, typography values, decorative layout, or visual hierarchy;
- current playtest deck composition;
- historical V1/V2 migration assumptions;
- balance hypotheses and research expectations.

If an intentional design change invalidates one of these assertions, update or delete the assertion. Do not preserve an obsolete design merely to make the test green.

## Test classes

### 1. Blocking sanity

These checks may block a PR because failure usually means the repository is actually broken:

- Python syntax/compilation;
- undefined names;
- missing static web assets/imports;
- malformed build inputs;
- inability to build the public site or rulebook;
- hard architectural/security boundaries.

GitHub's **Repository sanity** job contains this class.

### 2. Core behavior

Engine tests verify executable semantics. They matter when working on the engine, but authored physical rules/cards are allowed to lead the engine temporarily.

A physical-game or print change does not need to preserve an old engine expectation. When the engine intentionally lags, its failing parity/regression tests describe follow-up work rather than vetoing the game-design change.

### 3. Design review

Temporary design snapshots do not belong in the permanent test suite. Review card appearance, prose, deck shape, and layout visually or with one-off audit scripts while working on that design, then remove those checks when the decision changes.

Do not accumulate permanent tests for exact wording, named cards, CSS values, or today's playtest composition.

### 4. Research/algorithm evidence

Tests marked `research`, `algorithm`, or `integration` are diagnostics/evidence. They do not define the physical game and are excluded from normal fast verification. They are never prerequisites for Pages deployment.

## Deployment policy

GitHub Pages must be able to publish the current physical game even while engine, research, or parity diagnostics are failing.

The Pages workflow therefore runs only checks required to produce a usable site:

1. source/static integrity;
2. site build;
3. built-asset integrity;
4. rulebook PDF build;
5. deployment.

It does **not** run pytest suites or browser visual/layout assertions.

Aesthetic targets such as rulebook page count should warn rather than fail unless the artifact itself is malformed or cannot be built.

## Writing new tests

Before adding a regression, ask:

1. Is this a durable invariant or merely today's design?
2. Would we still want this test to fail if we deliberately redesigned the card/rule/page next week?
3. Can the invariant be tested semantically instead of matching exact prose, CSS, or a named card?
4. Is this really a permanent test, or should it be a temporary/manual design audit?

Prefer property/schema/behavior tests over snapshots of current content.

Good:

- all card IDs are unique;
- every deck entry references an existing card;
- a hidden opponent card is not exposed to the wrong viewer;
- an HTML page references files that actually exist.

Usually advisory:

- The Fifty Men must always have a particular effect;
- the rulebook must contain an exact sentence;
- movement cards must remain below a fixed count;
- a title must use a particular CSS font-size;
- the public navigation must use today's exact wording.

## Removing tests

Deleting or weakening an obsolete test is not a regression if the test encoded a superseded design decision.

When removing one, preserve the underlying durable invariant if there is one. If there is no durable invariant, prefer deletion over replacing it with another brittle snapshot.
