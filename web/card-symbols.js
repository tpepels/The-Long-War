(() => {
  "use strict";
  // Solid heraldic marks stay readable in both the exposed edge and the class line.
  const SHIELD='<path fill-rule="evenodd" d="M12 1.4C9.5 3.3 6.6 4 3.5 4.6v6.7c0 5.2 3.6 8.9 8.5 11.3 4.9-2.4 8.5-6.1 8.5-11.3V4.6C17.4 4 14.5 3.3 12 1.4Zm0 2.3c2.1 1.4 4.4 2.1 6.7 2.6v5c0 4.1-2.7 7.3-6.7 9.6-4-2.3-6.7-5.5-6.7-9.6v-5c2.3-.5 4.6-1.2 6.7-2.6Z"/><path d="M12 5v14.7c-3.4-2.1-5.6-4.9-5.6-8.4V7.1c2-.5 3.9-1.1 5.6-2.1Z"/>';
  const EYE='<path fill-rule="evenodd" d="M1.5 12C4.2 7.6 7.7 5.5 12 5.5s7.8 2.1 10.5 6.5c-2.7 4.4-6.2 6.5-10.5 6.5S4.2 16.4 1.5 12Zm3.1 0c2.1 2.9 4.5 4.3 7.4 4.3s5.3-1.4 7.4-4.3c-2.1-2.9-4.5-4.3-7.4-4.3S6.7 9.1 4.6 12Z"/>';
  const silhouette=body=>'<g fill="currentColor" stroke="none">'+body+'</g>';
  const TYPE = {
    force:SHIELD,
    bond:'<path d="m10 7 2-2a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0M14 17l-2 2a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0" fill="none" stroke="currentColor" stroke-width="3.1"/>',
    name:'<path d="M4 1.8h2.2v20.4H4ZM7.5 3H21l-4.7 5 4.7 5H7.5Z"/>',
    hero:'<circle cx="12" cy="12" r="7.1" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="m12 6.7 1.6 3.3 3.7.5-2.7 2.6.7 3.7-3.3-1.7-3.3 1.7.7-3.7-2.7-2.6 3.7-.5ZM11 0h2v3h-2Zm0 21h2v3h-2ZM0 11h3v2H0Zm21 0h3v2h-3Z"/>',
    tactic:'<path d="m3 1 5.3 2.4 10.5 13.2 1.6-1.3 1.7 2.2-2.4 1.9 2.1 2.7-1.7 1.3-2.1-2.7-2.4 1.9-1.7-2.2 1.6-1.3L5 5.9ZM21 1l-5.3 2.4L5.2 16.6l-1.6-1.3-1.7 2.2 2.4 1.9-2.1 2.7 1.7 1.3L6 20.7l2.4 1.9 1.7-2.2-1.6-1.3L19 5.9Z"/>',
    order:'<path fill-rule="evenodd" d="M5 1.8h10l4 4V22H5Zm2.5 5.4v2h9v-2Zm0 4.9v2h9v-2Zm0 4.9v2h6v-2Z"/><path d="M16 1.8v3h3Z"/>',
    stratagem:EYE+'<circle cx="12" cy="12" r="3.2"/>',
    narrative:'<path fill-rule="evenodd" d="M6 2h12a4 4 0 0 1 4 4v3h-5v9a4 4 0 0 1-4 4H5a4 4 0 0 1-4-4v-2h3V6a4 4 0 0 1 2-4Zm1 5v2h7V7Zm0 4v2h7v-2Zm-3.5 7a1.5 1.5 0 0 0 3 0Z"/>'
  };
  const CLASSES = {
    human:'<path d="M6.4 20c.6-2.4 3.9-2.6 4.1-5l-1.7-1.1-.5-2.4C6.8 11 6.2 9.5 7 8.3c-.6-1.7.5-3.5 2.3-3.9 1.2-1.4 4.4-1.5 6-.2 1.7.4 2.9 1.9 2.6 3.6l-1.4.6.3 1.8 1.4 1.8-1.7.7-.2 2.4c-.6.9-1.9 1-3 .7l-.1 1.6 2.2 2.6Z"/>',
    ship:'<path d="M5.3 15.3h13.4l-2.5 3.8H7.8ZM11 4h1.5v10H11ZM13.5 5l5 8h-5ZM9.8 6.6V13H5.5Z"/>',
    stronghold:'<path fill-rule="evenodd" d="M5.2 6h2.5v2.5h2V5h4.6v3.5h2V6h2.5v12.7H5.2Zm5 12.7h3.6v-5.1h-3.6Z"/>',
    archer:'<path d="M6.2 1.5c10.4 4.4 10.4 16.6 0 21l-.9-2.2c8.3-3.8 8.3-12.8 0-16.6Z"/><path d="M6 2.7 11 12 6 21.3" fill="none" stroke="currentColor" stroke-width="1.1"/><path d="M1 10.9h16v-3l6 4.1-6 4.1v-3H1Z"/>',
    guard:SHIELD,
    scout:EYE+'<circle cx="12" cy="12" r="3.2"/>',
    rider:'<path fill-rule="evenodd" d="M5 22c-.3-6.8 1.8-11.6 7.7-14.5L15 1l2.6 3.6 3.6 4.5-2.8 4.4-5.1-1.8c3.6 3.7 5.1 7 5.2 10.3Zm10.7-14 1.1 1.5 1.1-.8-1.1-1.5Z"/>',
    skirmisher:'<path d="m3 2 4.5 1.8 9 11.3 1.8-1.4 1.8 2.2-2.4 1.9 3.6 4.5-1.8 1.4-3.6-4.5-2.4 1.9-1.8-2.2 1.8-1.4L4.4 6.2ZM21 2l-4.5 1.8-9 11.3-1.8-1.4-1.8 2.2 2.4 1.9-3.6 4.5 1.8 1.4 3.6-4.5 2.4 1.9 1.8-2.2-1.8-1.4 9.1-11.3Z"/>',
    raider:'<path d="m4 22-2-2 11.3-13L9.9 4l2.2-2.4 4 4.1c1.5.2 3.1-.2 4.3-1.2 2.4 4 1.3 7.6-2.7 10l-2.3-4.8Z"/>',
    healer:'<path d="M9.2 2h5.6v7.2H22v5.6h-7.2V22H9.2v-7.2H2V9.2h7.2Z"/>',
    steward:'<path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 1 0 3.3 12.1l3.1 3.1-1.7 1.7 2 2 1.7-1.7 2 2-1.7 1.7 1.6 1.6 4-4-9-9A6.5 6.5 0 0 0 8 1.5Zm0 3a3.5 3.5 0 1 1 0 7 3.5 3.5 0 0 1 0-7Z"/>',
    seer:'<path fill-rule="evenodd" d="M12 2.2a7.4 7.4 0 1 0 0 14.8 7.4 7.4 0 0 0 0-14.8Zm0 3.1 1.1 2.5 2.7.3-2 1.9.6 2.7-2.4-1.3-2.4 1.3.6-2.7-2-1.9 2.7-.3Z"/><path d="M7.2 17.2h9.6l2.1 4.6H5.1Z"/>',
    king:'<path d="M2 5.5 7.5 10 12 1.5l4.5 8.5L22 5.5 19.8 17H4.2ZM4.5 19h15v3h-15Z"/>',
    captain:'<path d="M3 4h18v3H3Zm2 6.5h14v3H5Zm2 6.5h10v3H7Z"/>',
  };
  const UTILITY = {
    strength:'<path d="M5 19 17 7m-2-3 5 0v5M7 17l-3 3M19 19 7 7m2-3H4v5m13 8 3 3"/>',
    action:silhouette('<circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="1.9"/><path d="M10.5 4.6h3l-.5 4.8 1.6 1.6 4.8-.5v3l-4.8-.5-1.6 1.6.5 4.8h-3l.5-4.8L9.4 13l-4.8.5v-3l4.8.5L11 9.4Z"/>'),
    reaction:silhouette('<path d="M5 9a8 8 0 0 1 13-3M19 15A8 8 0 0 1 6 18" fill="none" stroke="currentColor" stroke-width="2.8"/><path d="m2.7 4.7 6.9 5.2-7.8 1.5ZM21.3 19.3l-6.9-5.2 7.8-1.5Z"/>'),
    bonded:silhouette(TYPE.bond),
    while_named:silhouette(TYPE.name),
    becomes_named:silhouette('<path d="M3 5h2.2v17H3Zm3.5 2.5H16l-3.3 4 3.3 4H6.5ZM18 1l1.4 3.6L23 6l-3.6 1.4L18 11l-1.4-3.6L13 6l3.6-1.4Z"/>'),
    trigger:silhouette('<path d="m12 1 2.8 8.2L23 12l-8.2 2.8L12 23l-2.8-8.2L1 12l8.2-2.8Z"/>'),
    play:silhouette('<path d="M2 10.5h9V6l7 6-7 6v-4.5H2ZM19 3h3v18h-3Z"/>'),
    continuous:'<path d="M6.5 7.3c-6 0-6 9.4 0 9.4 4.5 0 6.5-9.4 11-9.4 6 0 6 9.4 0 9.4-4.5 0-6.5-9.4-11-9.4Z" stroke-width="2.7"/>',
    hidden:silhouette(EYE+'<path d="m3.6 2 18.4 18.4-1.6 1.6L2 3.6Z"/>'),
    eye:'<path d="M3 12s3.5-5 9-5 9 5 9 5-3.5 5-9 5-9-5-9-5Z"/><circle cx="12" cy="12" r="2"/>',
    move:silhouette('<path d="m1 12 6-6v4.5h10V6l6 6-6 6v-4.5H7V18Z"/>'),
    suppress:'<circle cx="12" cy="12" r="8"/><path d="M6 18 18 6"/>',
    shield:'<path d="M5 3h14v7c0 5-3 8-7 11-4-3-7-6-7-11Z"/>',
    marker:silhouette('<circle cx="12" cy="12" r="4.2"/><path d="M10.8 1h2.4v4h-2.4Zm0 18h2.4v4h-2.4ZM1 10.8h4v2.4H1Zm18 0h4v2.4h-4Z"/>'),
    ally:'<circle cx="8" cy="9" r="3"/><circle cx="16" cy="9" r="3"/><path d="M3 20c1-4 3-6 5-6s4 2 5 6m-2 0c1-4 3-6 5-6s4 2 5 6"/>',
    cycle:'<path d="M6 8c3-4 9-4 12 0m0 0V4m0 4h-4M18 16c-3 4-9 4-12 0m0 0v4m0-4h4"/>',
    prepared:'<path d="M5 4h11l3 3v13H5Z"/><path d="M16 4v4h4M8 11h8m-8 4h6"/>',
    hand:'<path d="M6 19V9a2 2 0 0 1 4 0v4-7a2 2 0 0 1 4 0v7-5a2 2 0 0 1 4 0v7c0 4-3 6-6 6H9Z"/>',
    target:'<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><path d="M12 1v4m0 14v4M1 12h4m14 0h4"/>',
    clear:'<path d="m5 15 7-9 7 9-4 5H9Z"/><path d="M8 17h8"/>',
    card:'<path d="M5 3h14v18H5Z"/><path d="M8 7h8m-8 4h5"/>',
    lock:silhouette('<path fill-rule="evenodd" d="M6 9V7a6 6 0 0 1 12 0v2h2v13H4V9Zm3 0h6V7a3 3 0 0 0-6 0Zm1.8 4v5h2.4v-5Z"/>'),
    enemy:'<circle cx="12" cy="8" r="3"/><path d="M6 19c1-4 3-6 6-6s5 2 6 6M4 4l16 16"/>'
  };
  const GROUP={human:"kind",ship:"kind",stronghold:"kind",archer:"role",guard:"role",scout:"role",rider:"role",skirmisher:"role",raider:"role",healer:"role",steward:"role",seer:"role",king:"rank",captain:"rank"};
  function svg(body,title,className="",iconName=title){
    const key=String(iconName).toLowerCase().replaceAll(" ","_");
    return '<svg class="'+className+'" data-icon="'+key+'" viewBox="0 0 24 24" role="img" aria-label="'+title+'" fill="none" stroke="currentColor" stroke-width="1.55" stroke-linecap="round" stroke-linejoin="round"><title>'+title+'</title>'+body+'</svg>';
  }
  // Every PNG available at the website's icon resolution takes precedence over SVG.
  // Keep this inventory aligned with web/art/icons/sizes/128/*.png.
  // The lightweight static check flags newly uploaded icons omitted from this list.
  // ?icons=svg remains an explicit comparison/debugging override.
  const PNG_ICONS=new Set([
    "action","ally","archer","becomes_named","bond","bonded","builder",
    "captain","card","clear","continuous","cycle","enemy","eye",
    "force","front","guard","hand","healer","heir","hero",
    "hidden","human","king","lock","marker","middle","middle-rear",
    "move","name","narrative","order","play","prepared","raider",
    "reaction","rear","rider","scout","seer","shield","ship",
    "skirmisher","spearman","steward","stratagem","strength","stronghold","suppress",
    "tactic","target","trigger","veteran","while_named",
  ]);
  const png=(name,title,cssClass,iconId=name)=>{
    if(new URLSearchParams(window.location.search).get("icons")==="svg")return "";
    if(!PNG_ICONS.has(name))return "";
    const safeTitle=String(title).replaceAll("&","&amp;").replaceAll('"',"&quot;").replaceAll("<","&lt;");
    return '<img class="'+cssClass+' glyph-png" data-icon="'+iconId+'" src="art/icons/sizes/128/'+name+'.png" alt="'+safeTitle+'" title="'+safeTitle+'" width="24" height="24" draggable="false">';
  };
  const symbol=type=>png(type,type,"glyph-type")||svg(silhouette(TYPE[type]||TYPE.force),type,"glyph-type");
  const strength=()=>png("strength","Strength","glyph-strength")||svg(UTILITY.strength,"Strength","glyph-strength");
  const timing=name=>png(name,name.replaceAll("_"," "),"glyph-timing")||svg(UTILITY[name]||UTILITY.trigger,name.replaceAll("_"," "),"glyph-timing");
  const utility=name=>png(name,name,"glyph-utility")||svg(UTILITY[name]||UTILITY.marker,name,"glyph-utility");
  function classification(name){const group=GROUP[name]||"role";const frame=group==="kind"?'<circle cx="12" cy="12" r="10.4" fill="none" stroke="currentColor" stroke-width="1"/>':"";return png(name,name,"glyph-class glyph-class-"+group)||svg(frame+(CLASSES[name]?silhouette(CLASSES[name]):UTILITY.marker),name,"glyph-class glyph-class-"+group)}
  function row(position){
    const values=(Array.isArray(position)?position:[position]).map(value=>String(value||"").toLowerCase()).filter(Boolean);
    const active=new Set(values);
    const names=["front","middle","rear"];
    let body="";
    for(let i=0;i<3;i++)body+='<rect x="4" y="'+(4+i*6)+'" width="16" height="3.5" rx=".8"'+(active.has(names[i])?' class="row-active"':'')+'/>';
    const label=values.length>1?values.join(" / ")+" rows":(values[0]||"row")+" row";
    // A single location or the authored Middle/Rear combination has its own PNG.
    // Other combinations require the live three-bar SVG to represent exact rows.
    const iconKey=values.length===1?values[0]:
      (active.size===2&&active.has("middle")&&active.has("rear")?"middle-rear":"");
    return (iconKey?png(iconKey,label,"glyph-row","row"):"")||svg(body,label,"glyph-row","row");
  }
  function command(value=""){const number=value===""?"":'<text x="12" y="14.5" text-anchor="middle" class="glyph-number">'+value+'</text>';return '<svg class="glyph-command" data-icon="command" viewBox="0 0 24 24" role="img" aria-label="Command '+value+'"><title>Command '+value+'</title><path d="M12 1.5 20 5l2.5 8-5.5 8H7l-5.5-8L4 5Z"/><path d="M4 5l8 8 8-8M12 1.5V13m-10.5 0H12m10.5 0H12M7 21l5-8 5 8"/>'+number+'</svg>'}
  window.CardSymbols={symbol,strength,timing,utility,classification,row,command,group:name=>GROUP[name]||"role"};
})();
