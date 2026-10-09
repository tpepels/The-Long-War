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
  command_cost: 2, classes: ["human"],
  force_strength: 3, name_strength_modifier: 1,
  modes: {force: {effects: [{timing: "play", text: "Give a Guard Strength."}]},
          name: {effects: [{timing: "action", text: "Choose a Force."}]}}
};
const heroHtml = window.PhysicalCards.cardArticle(hero);
assert.match(heroHtml, /effect-timing-icon[^"]*"[^>]*><img/, "Hero timing icon missing");
assert.match(heroHtml, /inline-rule-ref/, "Hero text lacks inline rules icons");
const css=fs.readFileSync(path.join(root,"web/physical-cards.css"),"utf8");
assert.match(css, /\.inline-rule-ref\s*\{[^}]*white-space:\s*nowrap/s);
assert.match(css, /\.card-hero \.effect-head\s*\{[^}]*display:\s*inline-flex/s);
assert.match(css, /--icon-inline-term-size:/);
console.log("PASS: inline rule term icons / no-split CSS / Hero timing icons");
