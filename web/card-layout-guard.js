(function () {
  "use strict";

  const REGION_MAP = {
    "game-card": [
      ["meta", ".card-meta"],
      ["title", ".card-title"],
      ["properties", ".card-properties"],
      ["art", ".card-art"],
      ["rules", ".card-rule"],
      ["footer", ".card-footer"],
    ],
    "play-card": [
      ["meta", ".play-card-meta"],
      ["title", "h3"],
      ["properties", ".play-card-properties"],
      ["art", ".play-card-art"],
      ["rules", ".play-card-rules"],
      ["footer", "footer"],
    ],
  };

  function overflows(element) {
    if (!element) return false;
    return (
      element.scrollHeight > element.clientHeight + 1 ||
      element.scrollWidth > element.clientWidth + 1
    );
  }

  function outside(card, element) {
    if (!element) return false;
    const outer = card.getBoundingClientRect();
    const inner = element.getBoundingClientRect();
    return (
      inner.left < outer.left - 1 ||
      inner.right > outer.right + 1 ||
      inner.top < outer.top - 1 ||
      inner.bottom > outer.bottom + 1
    );
  }

  function verticallyOverlaps(a, b) {
    if (!a || !b) return false;
    const first = a.getBoundingClientRect();
    const second = b.getBoundingClientRect();
    return first.bottom > second.top + 1;
  }

  function inspectCard(card) {
    const type = card.classList.contains("game-card") ? "game-card" : "play-card";
    const regions = REGION_MAP[type];
    const failures = [];

    for (const [label, selector] of regions) {
      const element = card.querySelector(selector);
      const inspectContent = !["meta", "art"].includes(label);
      if (inspectContent && overflows(element)) failures.push(label + "-overflow");
      if (inspectContent && outside(card, element)) failures.push(label + "-outside");
    }

    for (let index = 0; index < regions.length - 1; index += 1) {
      const [aLabel, aSelector] = regions[index];
      const [bLabel, bSelector] = regions[index + 1];
      const a = card.querySelector(aSelector);
      const b = card.querySelector(bSelector);
      if (verticallyOverlaps(a, b)) failures.push(aLabel + "-" + bLabel + "-overlap");
    }

    if (failures.length) {
      card.classList.add("layout-overflow");
      card.dataset.layoutOverflow = failures.join(",");
      if (card.dataset.layoutOverflowReported !== "true") {
        const id =
          card.dataset.cardId ||
          card.dataset.handCard ||
          card.querySelector(".card-id")?.textContent ||
          card.querySelector("h2, h3")?.textContent ||
          "unknown card";
        console.error("[card-layout] Layout failure in " + id + ": " + failures.join(", "));
        card.dataset.layoutOverflowReported = "true";
      }
    } else {
      card.classList.remove("layout-overflow");
      delete card.dataset.layoutOverflow;
      delete card.dataset.layoutOverflowReported;
    }
    return failures;
  }

  function check(root) {
    const scope = root || document;
    const cards = scope.querySelectorAll(".game-card, .play-card");
    const failures = [];
    cards.forEach((card) => {
      const regions = inspectCard(card);
      if (regions.length) failures.push({ card, regions });
    });
    return failures;
  }

  function schedule(root) {
    const run = () => check(root || document);
    requestAnimationFrame(run);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(run);
  }

  window.CardLayoutGuard = { check, schedule };
})();
