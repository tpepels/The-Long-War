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
// Symbols in the rules body identify *other cards* by family or classification.
// PLAY, ACTION, Force/Name mode headings, Strength, Command and conditions
// are words; these already have structural glyphs where relevant.
const sample = {
  id: "print-smoke", type: "tactic", title: "Print smoke", command_cost: 1,
  classes: [], effects: [{timing: "play", text:
    "Choose a friendly Force and one Archer in this Front. Add a Bond to a Named Formation; gain 1 Command. Attack a Guard with a Raider."}]
};
const html = window.PhysicalCards.cardArticle(sample);
const effectTexts = source => source.split('<div class="effect-text">')
  .slice(1).map(part=>part.split('</div>')[0]);
const inlineCount = html => html.split('class="inline-rule-ref inline-card-ref"').length-1;
const plain = source => source.replace(/<[^>]*>/g,"");
const one = effectTexts(html)[0];
for(const term of ["Force","Archer","Front","Bond","Named Formation","Attack","Guard","Raider","Command"])
  assert.ok(plain(one).includes(term), "Missing ordinary rule term "+term);
assert.equal(inlineCount(one),2,"Only the first two card referents get pictograms");
assert.match(one,/class="inline-rule-ref inline-card-ref" title="Force"/);
assert.match(one,/class="inline-rule-ref inline-card-ref" title="Archer"/);
assert.doesNotMatch(one,/title="Command"|title="Strength"|title="Front"|title="Attack"/);
assert.doesNotMatch(html,/effect-timing-icon|placement-rule-icon/,"Timing/placement words need no extra icons");

const outcome = {
  id:"outcome-smoke", type:"tactic", title:"Outcome smoke", command_cost:1,
  classes:[], effects:[
    {timing:"play",text:"Give a friendly Force Guarded. Give it +2 Strength this Battle. Guarded remains until used. Regain 1 Command."},
    {timing:"play",text:"If an enemy is Exhausted, give it Shaken and Depleted; Move it toward Rear."},
    {timing:"play",text:"A friendly Scout can Move to the Middle row. Its Strength is unchanged. Your Command is unchanged."},
    {timing:"play",text:"Choose up to two other friendly Human formations in this Front. Each gets +1 Strength."},
    {timing:"play",text:"Look at every opposing face-down Stratagem in this Front. Then look at a second Stratagem."},
    {timing:"play",text:"This Force may Move with another friendly Raider. A Raider cannot Move twice."}
  ]
};
const parts=effectTexts(window.PhysicalCards.cardArticle(outcome));
assert.equal(parts.length,6);
assert.equal(inlineCount(parts[0]),1,"Only target Force gets a card-reference symbol");
assert.match(parts[0],/title="Force"/);
assert.doesNotMatch(parts[0],/title="Guarded"|title="Strength"|title="Command"/);
assert.equal(inlineCount(parts[1]),0,"Conditions and Move are words, not pictograms");
assert.equal(inlineCount(parts[2]),1,"Scout is a referenced class");
assert.match(parts[2],/title="Scout"/);
assert.equal(inlineCount(parts[3]),1,"Human is a referenced classification");
assert.match(parts[3],/title="Human"/);
assert.equal(inlineCount(parts[4]),1,"Repeated Stratagem uses the same one icon");
assert.match(parts[4],/title="Stratagem"/);
assert.equal(inlineCount(parts[5]),1,"Self-reference This Force is plain, other Raider is iconized");
assert.match(parts[5],/title="Raider"/);

// Existing PNGs and SVG fallback must follow the same policy.
window.location.search="?icons=svg";
const svgParts=effectTexts(window.PhysicalCards.cardArticle(outcome));
assert.deepEqual(svgParts.map(inlineCount),[1,0,1,1,1,1]);
assert.match(svgParts[3],/class="inline-rule-ref inline-card-ref"[^>]*><svg/,
  "SVG fallback uses the same classification glyph");
window.location.search="";
const hero = {
  id: "hero-smoke", type: "hero", title: "Hero test",
  command_cost: 5, hero_force_command_cost: 5,
  hero_name_command_cost: 2, classes: ["human"],
  force_strength: 3, name_strength_modifier: 1,
  modes: {force: {effects: [{timing: "play", text: "Give a Guard Strength."}]},
          name: {effects: [{timing: "action", text: "Choose a Force."}]}}
};
const heroHtml = window.PhysicalCards.cardArticle(hero);
assert.doesNotMatch(heroHtml,/effect-timing-icon|placement-rule-icon/,
  "Hero rules use label words rather than timing pictograms");
assert.match(heroHtml,/aria-label="Hero Force cost 5 Command, Name cost 2 Command"/);
assert.match(heroHtml,/hero-cost-fraction" aria-hidden="true"/);
assert.match(heroHtml,/hero-cost-part hero-cost-force[^>]*><span class="hero-cost-symbol"><(?:img|svg)[^>]*data-icon="force"[^>]*>[\s\S]*?<b>5<\/b>/);
assert.match(heroHtml,/hero-cost-part hero-cost-name[^>]*><span class="hero-cost-symbol"><(?:img|svg)[^>]*data-icon="name"[^>]*>[\s\S]*?<b>2<\/b>/);
assert.doesNotMatch(heroHtml,/hero-cost-stack|<small>F<\/small>|<small>N<\/small>/);
assert.doesNotMatch(heroHtml,/mode-command-cost/);
const heroRuleSections=heroHtml.split('<section class="hero-rule-mode"').slice(1)
  .map(part=>part.split('</section>')[0]);
assert.equal(heroRuleSections.length,2);
assert.ok(heroRuleSections[0].includes("<span>Force</span>"));
assert.ok(heroRuleSections[1].includes("<span>Name</span>"));
for(const part of heroRuleSections){
  assert.doesNotMatch(part,/\b(?:5|2) Command\b/);
  assert.doesNotMatch(part,/class="mode-heading-core"><(?:img|svg)/,
    "Hero role heading must contain text only");
}
assert.match(heroRuleSections[0],/title="Guard"/,"Hero text can reference a Guard");
assert.match(heroRuleSections[1],/title="Force"/,"Hero text can reference a Force");
const css=fs.readFileSync(path.join(root,"web/physical-cards.css"),"utf8");
assert.match(css,/\.inline-rule-ref\s*\{[^}]*white-space:\s*nowrap/s);
assert.match(css,/\.card-hero \.effect-head\s*\{[^}]*display:\s*inline;/s);
// Card-family colour filters apply to PNG glyphs as well as frame assets,
// without tinting the entire card (and therefore the card illustration).
const pngFilter = css.match(/\.physical-card img\.glyph-png\s*\{([^}]+)\}/s)?.[1]||"";
for (const value of ["sepia","saturate","grayscale","hue","brightness","contrast"])
  assert.match(pngFilter,new RegExp("--card-shell-"+value+"\\b"),
    "PNG glyphs must inherit the "+value+" card-family filter control");
assert.doesNotMatch(css,/\.physical-card\s*\{[^}]*filter:/s,
  "Filtering the entire card would tint the illustration and text");

// Every Hero fraction dimension / location is editable from one :root block.
// Keep independent controls for the Force and Name pair, glyph and numeral.
const controls = [
  "fraction-inset",
  ...["force","name"].flatMap(mode=>[
    ...(mode==="force"?["left","top"]:["right","bottom"]).map(x=>mode+"-"+x),
    ...["gap","symbol-size","symbol-x","symbol-y","number-size","number-x","number-y"].map(x=>mode+"-"+x)
  ]),
  ...["x","y","length","thickness","angle","opacity"].map(x=>"slash-"+x)
];
for (const key of controls) {
  const variable="--hero-cost-"+key;
  assert.ok(css.includes(variable+":"),"Missing Hero cost editor control "+variable);
  assert.ok(css.includes("var("+variable+")"),"Hero cost control is unused: "+variable);
}
assert.match(css,/\.hero-cost-symbol svg,[\s\S]*?\.hero-cost-symbol img\.glyph-png/s);
const js=fs.readFileSync(path.join(root,"web/physical-cards.js"),"utf8");
assert.match(js,/hero-price-outside-seal/);
assert.match(js,/hero-price-overlap/);
console.log("PASS: rule icon policy, Hero cost CSS controls, PNG family colouring and seal checks");
