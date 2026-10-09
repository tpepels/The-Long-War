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
// Ordinary nouns, roles, classifications and movement words are prose.
// Only high-signal conditions, boons and quantified resource changes can
// carry inline symbols, with at most two per printed effect.
const sample = {
  id: "print-smoke", type: "tactic", title: "Print smoke", command_cost: 1,
  classes: [], effects: [{timing: "play", text:
    "Choose a friendly Force and one Archer in this Front. Add a Bond to a Named Formation; gain 1 Command. Attack a Guard with a Raider."}]
};
const html = window.PhysicalCards.cardArticle(sample);
const effectTexts = source => source.split('<div class="effect-text">')
  .slice(1).map(part=>part.split('</div>')[0]);
const inlineCount = html => html.split('class="inline-rule-ref inline-impact-ref"').length-1;
const plain = source => source.replace(/<[^>]*>/g,"");
const one = effectTexts(html)[0];
for(const term of ["Force","Archer","Front","Bond","Named Formation","Attack","Guard","Raider"])
  assert.ok(plain(one).includes(term), "Missing readable ordinary game term: "+term);
assert.equal(inlineCount(one),1,"Only the explicit Command amount earns an inline icon");
assert.match(one, /class="inline-rule-ref inline-impact-ref" title="Command"/);
assert.doesNotMatch(one, /inline-class-ref|title="Force"|title="Archer"|title="Front"|title="Bond"/,
  "Card types and classifications must not be individually iconized");

// A rule with several outcomes uses at most TWO icons and never duplicates
// the same icon for repeated mentions of the same condition or resource.
const outcome = {
  id:"outcome-smoke", type:"tactic", title:"Outcome smoke", command_cost:1,
  classes:[], effects:[
    {timing:"play",text:"Give a friendly Force Guarded. Give it +2 Strength this Battle. Guarded remains until used. Regain 1 Command."},
    {timing:"play",text:"If an enemy is Exhausted, give it Shaken and Depleted; Move it toward Rear."},
    {timing:"play",text:"A friendly Scout can Move to the Middle row. Its Strength is unchanged. Your Command is unchanged."}
  ]
};
const parts = effectTexts(window.PhysicalCards.cardArticle(outcome));
assert.equal(parts.length,3);
assert.equal(inlineCount(parts[0]),2,"Only first boon and first quantified resource change should be iconized");
assert.match(parts[0], /title="Guarded"/);
assert.match(parts[0], /title="Strength"/);
assert.doesNotMatch(parts[0], /title="Command"/,"Third impact must stay plain under two-icon cap");
assert.equal(inlineCount(parts[1]),1,"Repeated affliction pictogram must not recur");
assert.equal(inlineCount(parts[2]),0,"Conditions, classes and generic resource mentions stay as prose");
assert.match(plain(parts[1]), /Exhausted.*Shaken.*Depleted.*Move/);
assert.match(plain(parts[2]), /Scout.*Move.*Middle.*Strength.*Command/);
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
assert.doesNotMatch(heroHtml, /inline-rule-ref/, "Plain Hero text must not acquire ornamental rule-term icons");
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
console.log("PASS: selective rules-text icons / prose readability / Hero diagonal cost heraldry");
