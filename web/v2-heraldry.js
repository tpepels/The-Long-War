(() => {
  "use strict";
  const TYPE = {
    force:'<path d="M5 3h14v7c0 5-3 8-7 11-4-3-7-6-7-11Z"/><path d="M12 6v10M8 9h8"/>',
    bond:'<path d="m10 7 2-2a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0M14 17l-2 2a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0"/>',
    name:'<path d="M6 21V3M6 4h13l-4 4 4 4H6M3 21h6"/>',
    hero:'<circle cx="12" cy="12" r="6"/><path d="m12 8 1.2 2.7 2.8.3-2.1 1.9.6 2.8-2.5-1.5-2.5 1.5.6-2.8L8 11l2.8-.3Z"/><path d="M12 1v3M12 20v3M1 12h3M20 12h3"/>',
    tactic:'<path d="m4 20 13-13m-1-3 4-1-1 4-2 1Zm-9 10 3 3M4 4l13 13M3 3l1 5 3-1 1-3Z"/>',
    stratagem:'<path d="m12 2 9 10-9 10L3 12ZM6 12s2.5-4 6-4 6 4 6 4-2.5 4-6 4-6-4-6-4Z"/><circle cx="12" cy="12" r="1.7"/>',
    narrative:'<path d="M6 4h11a3 3 0 0 1 3 3v1h-4V7a3 3 0 0 0-3-3M6 4a3 3 0 0 0-3 3v13h12V7M3 17h12M7 9h5m-5 4h5"/>'
  };
  const CLASSES = {
    human:'<circle cx="12" cy="8" r="3"/><path d="M6 19c1-4 3-6 6-6s5 2 6 6"/>',
    ship:'<path d="M4 16h16l-3 4H7Zm7-12v12M11 5l6 8h-6M10 7 6 13h5"/>',
    stronghold:'<path d="M5 20V8h3V5h3v3h2V5h3v3h3v12ZM9 20v-5h6v5M5 11h14"/>',
    archer:'<path d="M7 4c7 4 7 12 0 16M7 4l5 8-5 8M3 12h17m-3-3 3 3-3 3"/>',
    guard:'<path d="M5 3h14v7c0 5-3 8-7 11-4-3-7-6-7-11Z"/><path d="M8 9h8"/>',
    scout:'<path d="M3 12s3.5-5 9-5 9 5 9 5-3.5 5-9 5-9-5-9-5Z"/><circle cx="12" cy="12" r="2"/>',
    rider:'<path d="M6 19c1-5 4-9 8-11l2-4 3 5-2 3 2 7M9 12l5 1M8 19h11"/>',
    skirmisher:'<path d="M5 19 18 6m-10-1 11 11M4 20l5-2-3-3Zm16-2-5-1 2-3Z"/>',
    raider:'<path d="m5 19 11-11m-3-4 7 7m-8-5 4-3 5 5-3 4M4 20l5-1-4-4Z"/>',
    healer:'<path d="M12 4v16M4 12h16"/><path d="M6 7c2-3 5-3 6 1-4 1-5 4-6 7"/>',
    spearman:'<path d="M5 20 17 5m-1-2 5 1-2 5ZM4 16l4 4"/>',
    steward:'<circle cx="9" cy="9" r="4"/><path d="m12 12 8 8m-3-3 2-2m-5 0 2-2"/>',
    builder:'<path d="m5 19 9-9m-3-5 3-2 5 5-2 3-6-6ZM4 20l4-1-3-3Z"/>',
    seer:'<path d="M3 12s3.5-5 9-5 9 5 9 5-3.5 5-9 5-9-5-9-5Z"/><path d="m12 8 1 2 2 .3-1.5 1.5.4 2.2-1.9-1.1-1.9 1.1.4-2.2L9 10.3l2-.3Z"/>',
    king:'<path d="M4 17 6 7l5 5 3-7 4 7 4-5-2 10ZM5 20h14"/>',
    captain:'<path d="M5 6h14M7 10h10M9 14h6"/><path d="M12 3v18"/>',
    veteran:'<path d="M9 20c-4-3-5-8-3-13m9 13c4-3 5-8 3-13M7 8 4 6m3 6-4-1m14-3 3-2m-3 6 4-1"/><path d="M9 20h6"/>',
    heir:'<path d="M6 16 7 9l4 4 2-6 3 6 3-4 1 7ZM7 19h12"/><circle cx="13" cy="4" r="1.2"/>'
  };
  const UTILITY = {
    strength:'<path d="M5 19 17 7m-2-3 5 0v5M7 17l-3 3M19 19 7 7m2-3H4v5m13 8 3 3"/>',
    action:'<path d="M12 3 21 12 12 21 3 12Z"/><path d="m9 12 2 2 4-5"/>',
    reaction:'<path d="M19 8c-5-4-12-2-14 4m0 0 4-1m-4 1 1 4M5 16c5 4 12 2 14-4m0 0-4 1m4-1-1-4"/>',
    bonded:'<path d="m10 7 2-2a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0M14 17l-2 2a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0"/>',
    while_named:'<path d="M6 21V3M6 4h13l-4 4 4 4H6"/>',
    becomes_named:'<path d="M7 20V5m0 1h10l-3 4 3 4H7"/><path d="m18 3 .8 2.2L21 6l-2.2.8L18 9l-.8-2.2L15 6l2.2-.8Z"/>',
    trigger:'<path d="m12 2 1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8Z"/>',
    play:'<path d="M4 12h13m-4-4 4 4-4 4M18 5h2v14h-2"/>',
    continuous:'<path d="M7 8c-4 0-4 8 0 8 4 0 6-8 10-8 4 0 4 8 0 8-4 0-6-8-10-8Z"/>',
    hidden:'<path d="M3 12s3.5-5 9-5 9 5 9 5-3.5 5-9 5-9-5-9-5Z"/><path d="m5 4 14 16"/>',
    eye:'<path d="M3 12s3.5-5 9-5 9 5 9 5-3.5 5-9 5-9-5-9-5Z"/><circle cx="12" cy="12" r="2"/>',
    move:'<path d="M4 12h16m-4-4 4 4-4 4M8 8 4 12l4 4"/>',
    suppress:'<circle cx="12" cy="12" r="8"/><path d="M6 18 18 6"/>',
    shield:'<path d="M5 3h14v7c0 5-3 8-7 11-4-3-7-6-7-11Z"/>',
    marker:'<circle cx="12" cy="12" r="4"/><path d="M12 2v4m0 12v4M2 12h4m12 0h4"/>',
    ally:'<circle cx="8" cy="9" r="3"/><circle cx="16" cy="9" r="3"/><path d="M3 20c1-4 3-6 5-6s4 2 5 6m-2 0c1-4 3-6 5-6s4 2 5 6"/>',
    cycle:'<path d="M6 8c3-4 9-4 12 0m0 0V4m0 4h-4M18 16c-3 4-9 4-12 0m0 0v4m0-4h4"/>',
    prepared:'<path d="M5 4h11l3 3v13H5Z"/><path d="M16 4v4h4M8 11h8m-8 4h6"/>',
    hand:'<path d="M6 19V9a2 2 0 0 1 4 0v4-7a2 2 0 0 1 4 0v7-5a2 2 0 0 1 4 0v7c0 4-3 6-6 6H9Z"/>',
    target:'<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><path d="M12 1v4m0 14v4M1 12h4m14 0h4"/>',
    clear:'<path d="m5 15 7-9 7 9-4 5H9Z"/><path d="M8 17h8"/>',
    card:'<path d="M5 3h14v18H5Z"/><path d="M8 7h8m-8 4h5"/>',
    lock:'<rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    enemy:'<circle cx="12" cy="8" r="3"/><path d="M6 19c1-4 3-6 6-6s5 2 6 6M4 4l16 16"/>'
  };
  const GROUP={human:"kind",ship:"kind",stronghold:"kind",archer:"role",guard:"role",scout:"role",rider:"role",skirmisher:"role",raider:"role",healer:"role",spearman:"role",steward:"role",builder:"role",seer:"role",king:"rank",captain:"rank",veteran:"rank",heir:"rank"};
  function svg(body,title,className=""){return '<svg class="'+className+'" viewBox="0 0 24 24" role="img" aria-label="'+title+'" fill="none" stroke="currentColor" stroke-width="1.55" stroke-linecap="round" stroke-linejoin="round"><title>'+title+'</title>'+body+'</svg>'}
  const symbol=type=>svg(TYPE[type]||TYPE.force,type,"glyph-type");
  const strength=()=>svg(UTILITY.strength,"Strength","glyph-strength");
  const timing=name=>svg(UTILITY[name]||UTILITY.trigger,name.replaceAll("_"," "),"glyph-timing");
  const utility=name=>svg(UTILITY[name]||UTILITY.marker,name,"glyph-utility");
  function classification(name){const group=GROUP[name]||"role";const frame=group==="kind"?'<circle cx="12" cy="12" r="10"/>':group==="rank"?'<path d="M3 3h18v13l-9 6-9-6Z"/>':'<path d="M12 2 22 12 12 22 2 12Z"/>';return svg(frame+'<g transform="translate(4 4) scale(.6667)">'+(CLASSES[name]||UTILITY.marker)+'</g>',name,"glyph-class glyph-class-"+group)}
  function row(position){const p=String(position||"").toLowerCase(),index=p==="front"?0:p==="middle"?1:2;let body="";for(let i=0;i<3;i++)body+='<rect x="4" y="'+(4+i*6)+'" width="16" height="3.5" rx=".8"'+(i===index?' class="row-active"':'')+'/>';return svg(body,p+" row","glyph-row")}
  function command(value=""){const number=value===""?"":'<text x="12" y="14.5" text-anchor="middle" class="glyph-number">'+value+'</text>';return '<svg class="glyph-command" viewBox="0 0 24 24" role="img" aria-label="Command '+value+'"><title>Command '+value+'</title><path d="M12 1.5 20 5l2.5 8-5.5 8H7l-5.5-8L4 5Z"/><path d="M4 5l8 8 8-8M12 1.5V13m-10.5 0H12m10.5 0H12M7 21l5-8 5 8"/>'+number+'</svg>'}
  window.V2Heraldry={symbol,strength,timing,utility,classification,row,command,group:name=>GROUP[name]||"role"};
})();