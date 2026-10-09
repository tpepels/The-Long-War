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
assert.match(heroHtml,/aria-label="Hero Command: top 5 Force, bottom 2 Name"/);
assert.match(heroHtml,/class="hero-cost-stack" aria-hidden="true"/);
assert.match(heroHtml,/class="hero-cost-part hero-cost-force"><b>5<\/b><\/span>/);
assert.match(heroHtml,/class="hero-cost-part hero-cost-name"><b>2<\/b><\/span>/);
assert.doesNotMatch(heroHtml,/hero-cost-symbol|hero-cost-fraction/,
  "Hero Command seal must not include mode icons or old diagonal markup");
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

// Independent numeric tuning, but a single horizontal centre axis.
const controls=[
  "inset","force-top","name-bottom",
  "force-number-size","name-number-size",
  "force-number-x","force-number-y","name-number-x","name-number-y",
  "divider-width","divider-thickness","divider-y","divider-opacity"
];
for(const key of controls){
  const variable="--hero-cost-"+key;
  assert.ok(css.includes(variable+":"),"Missing Hero cost variable "+variable);
  assert.ok(css.includes("var("+variable+")"),"Unused Hero cost variable "+variable);
}
assert.match(css,/\.hero-cost-part\s*\{[^}]*left:\s*0;[^}]*width:\s*100%;[^}]*justify-content:\s*center;/s);
assert.doesNotMatch(css,/\.hero-cost-symbol\s*\{/);
// Every printed exposed reminder is now a concise action/condition prompt,
// never an effect summary. Preserve full rule text in the accessible label.
const cueHero={...hero, modes:{
  force:{effects:[{timing:"action", limit:"once_per_battle",
                 text:"Move this formation two positions.",edge_cue:"ACTION"}]},
  name:hero.modes.name
}};
const cueHeroHtml=window.PhysicalCards.cardArticle(cueHero);
assert.match(cueHeroHtml,/edge-mechanic edge-cue[^>]*aria-label="Check rule on action \(once per Battle\): Move this formation two positions\./);
assert.match(cueHeroHtml,/class="edge-cue-text">ACTION<\/span>/);
assert.doesNotMatch(cueHeroHtml,/class="edge-cue-text"[^<]*Move this formation/);
const dual={...hero, type:"force", strength:3, effects:[
  {timing:"continuous",text:"Can Maneuver without a Name.",edge_cue:"MANEUVER"},
  {timing:"continuous",text:"Can Maneuver while Exhausted.",edge_cue:"MANEUVER"}
]};
const dualHtml=window.PhysicalCards.cardArticle(dual);
assert.equal(dualHtml.split('class="edge-cue-text"').length-1,1,
  "Identical reminders on one card must collapse into a single cue");
assert.match(dualHtml,/Can Maneuver without a Name\. \/ Can Maneuver while Exhausted\./,
  "The combined cue must still expose both rules accessibly");
const js=fs.readFileSync(path.join(root,"web/physical-cards.js"),"utf8");
assert.match(js,/hero-price-outside-seal/);
assert.match(js,/hero-price-overlap/);
console.log("PASS: compact corner cues, centred Hero numeric costs and PNG icon tint");
