// Lightweight rendered-markup smoke test. Does not require a browser.
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const path = require("node:path");
const root = path.resolve(__dirname, "..");
const window = {location: {search: ""}};
const context = vm.createContext({window, URL, URLSearchParams, encodeURIComponent});
vm.runInContext(fs.readFileSync(path.join(root, "web/card-symbols.js"), "utf8"), context);
vm.runInContext(fs.readFileSync(path.join(root, "web/physical-cards.js"), "utf8"), context);
const sample = {
  id: "print-smoke", type: "tactic", title: "Print smoke", command_cost: 1,
  classes: [], effects: [{timing: "play", text:
    "Choose a friendly Force and one Archer in this Front. Add a Bond to a Named Formation; gain 1 Command. Attack a Guard with a Raider."}]
};
const html = window.PhysicalCards.cardArticle(sample);
for(const word of ["Force","Archer","Front","Bond","Named Formation","Command","Attack","Guard","Raider"]){
  const escaped = word.replace(/[.*+?^$()|[\]\\{}]/g, "\\$&");
  const pattern = new RegExp('<span class="inline-rule-ref[^"]*"[^>]*><(?:img|svg)[\\s\\S]*?<span class="(?:rule-term|rule-class-term)">' + escaped + '<\\/span><\\/span>');
  assert.match(html, pattern, "Rule term missing leading icon: " + word);
}
const hero = {
  id: "hero-smoke", type: "hero", title: "Hero test",
  command_cost: 5, hero_force_command_cost: 5,
  hero_name_command_cost: 2, classes: ["human"],
  force_strength: 3, name_strength_modifier: 1,
  modes: {force: {effects: [{timing: "play", text: "Give a Guard Strength."}]},
          name: {effects: [{timing: "action", text: "Choose a Force."}]}}
};
const heroHtml = window.PhysicalCards.cardArticle(hero);
assert.match(heroHtml, /effect-timing-icon[^"]*"[^>]*><img/, "Hero timing icon missing");
assert.match(heroHtml, /inline-rule-ref/, "Hero text lacks inline rules icons");
assert.match(heroHtml, /aria-label="Hero Force cost 5 Command, Name cost 2 Command"/,
  "Accessible cost must clarify both Hero modes");
assert.match(heroHtml, /hero-cost-fraction" aria-hidden="true"/,
  "Hero must render diagonal fraction container");
assert.match(heroHtml, /hero-cost-part hero-cost-force[^>]*><span class="hero-cost-symbol"><(?:img|svg)[^>]*data-icon="force"[^>]*>[\s\S]*?<b>5<\/b>/,
  "Force numerator must use the printed Force shield symbol and cost");
assert.match(heroHtml, /hero-cost-part hero-cost-name[^>]*><span class="hero-cost-symbol"><(?:img|svg)[^>]*data-icon="name"[^>]*>[\s\S]*?<b>2<\/b>/,
  "Name denominator must use the printed Name banner symbol and cost");
assert.doesNotMatch(heroHtml, /hero-cost-stack|<small>F<\/small>|<small>N<\/small>/,
  "Old stacked letter labels must not return");
assert.match(heroHtml, /mode-command-cost">5 Command/, "Force rule panel must explain Force cost");
assert.match(heroHtml, /mode-command-cost">2 Command/, "Name rule panel must explain Name cost");
const css=fs.readFileSync(path.join(root,"web/physical-cards.css"),"utf8");
assert.match(css, /\.inline-rule-ref\s*\{[^}]*white-space:\s*nowrap/s);
assert.match(css, /\.card-hero \.effect-head\s*\{[^}]*display:\s*inline-flex/s);
assert.match(css, /--icon-inline-term-size:/);
assert.match(css, /\.hero-cost-fraction::before\s*\{[^}]*rotate\(-45deg\)/s,
  "Hero fraction needs a diagonal separator in physical CSS");
assert.match(css, /\.hero-cost-force\s*\{[^}]*top:\s*1\.7mm/s,
  "Force numerator must sit above-left");
assert.match(css, /\.hero-cost-name\s*\{[^}]*bottom:\s*1\.8mm/s,
  "Name denominator must sit below-right");
assert.match(css, /\.hero-cost-symbol svg,[\s\S]*?\.hero-cost-symbol img\.glyph-png/s,
  "Both SVG and PNG heraldic symbols need identical dimensions");
console.log("PASS: inline rule icons / Hero dual-price heraldry / diagonal fraction layout");
