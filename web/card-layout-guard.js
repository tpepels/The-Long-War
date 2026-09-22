(function () {
  "use strict";

  const REGION_MAP = {
    "game-card": [
      ["title", ".card-header h2"],
      ["properties", ".card-properties"],
      ["rules", ".card-rule"],
      ["footer", ".card-footer"],
    ],
    "play-card": [
      ["meta", ".play-card-meta"],
      ["title", "h3"],
      ["properties", ".play-card-properties"],
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

  function inspectCard(card) {
    const type = card.classList.contains("game-card") ? "game-card" : "play-card";
    const failures = [];
    for (const [label, selector] of REGION_MAP[type]) {
      const element = card.querySelector(selector);
      if (overflows(element)) failures.push(label);
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
        console.error(
          "[card-layout] Text overflow in " + id + ": " + failures.join(", ")
        );
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
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(run);
    }
  }

  window.CardLayoutGuard = { check, schedule };
})();
