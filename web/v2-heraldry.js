(() => {
  "use strict";

  const SYMBOLS = {
    force: '<path d="M5 3h14v7c0 5-3 8-7 11-4-3-7-6-7-11Z"/><path d="M12 6v10M8 9h8"/>',
    bond: '<path d="m10 7 2-2a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0M14 17l-2 2a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0"/>',
    name: '<path d="M6 21V3M6 4h13l-4 4 4 4H6M3 21h6"/>',
    hero: '<circle cx="12" cy="12" r="6"/><path d="m12 8 1.2 2.7 2.8.3-2.1 1.9.6 2.8-2.5-1.5-2.5 1.5.6-2.8L8 11l2.8-.3ZM12 1v2m0 18v2M1 12h2m18 0h2M4 4l1.5 1.5m13 13L20 20M4 20l1.5-1.5m13-13L20 4"/>',
    tactic: '<path d="m4 20 13-13m-1-3 4-1-1 4-2 1Zm-9 10 3 3M4 4l13 13M3 3l1 5 3-1 1-3Zm11 14 3-3m0 3 4 4"/>',
    stratagem: '<path d="m12 2 9 10-9 10L3 12ZM6 12s2.5-4 6-4 6 4 6 4-2.5 4-6 4-6-4-6-4Z"/><circle cx="12" cy="12" r="1.7"/>',
    narrative: '<path d="M6 4h11a3 3 0 0 1 3 3v1h-4V7a3 3 0 0 0-3-3M6 4a3 3 0 0 0-3 3v13h12V7M3 17h12M7 9h5m-5 4h5M15 20a3 3 0 0 0 3-3h-3"/>',
  };

  // These are family devices, deliberately independent of card ids and titles.
  // Main outlines survive small print; fine strokes provide the engraved finish.
  const MOTIFS = {
    force: `
      <g class="heraldry-main">
        <path d="M30 62V21m-4 0 4-13 4 13ZM70 64V18m-4 0 4-13 4 13ZM110 65V16m-4 0 4-13 4 13ZM150 65V18m-4 0 4-13 4 13ZM190 64V21m-4 0 4-13 4 13ZM222 62V26m-3 0 3-11 3 11Z"/>
        <path d="M15 34h30v13c0 9-8 16-15 20-7-4-15-11-15-20ZM55 30h30v15c0 9-8 17-15 21-7-4-15-12-15-21ZM95 28h30v17c0 9-8 17-15 21-7-4-15-12-15-21ZM135 30h30v15c0 9-8 17-15 21-7-4-15-12-15-21ZM175 34h30v13c0 9-8 16-15 20-7-4-15-11-15-20Z"/>
      </g>
      <g class="heraldry-fine">
        <path d="m22 41 8 16 8-16m24-4 8 19 8-19m24-2 8 21 8-21m24 2 8 19 8-19m24-15 8 16 8-16M7 71h225"/>
        <path d="M9 16h9m23-5h14m29-3h12m30 0h10m28 3h12m26 5h9"/>
      </g>`,
    bond: `
      <g class="heraldry-main">
        <path d="M7 38h28c13 0 20-20 35-20s23 20 38 20 23-20 38-20 22 20 35 20h52M7 43h28c13 0 20-20 35-20s23 20 38 20 23-20 38-20 22 20 35 20h52"/>
        <path d="M35 38c13 0 20 20 35 20s23-20 38-20 23 20 38 20 22-20 35-20M35 33c13 0 20 20 35 20s23-20 38-20 23 20 38 20 22-20 35-20"/>
        <path d="m17 30 8 10-8 10m198-20-8 10 8 10"/>
      </g>
      <g class="heraldry-fine">
        <path d="M50 8h140M50 68h140m-84-51 14-9 14 9m-28 42 14 9 14-9M7 22h20M7 58h20m186-36h20m-20 36h20"/>
      </g>`,
    name: `
      <g class="heraldry-main">
        <path d="M120 68V8m-3 0 3-5 3 5Zm0 4h42l-8 17 8 17h-42M65 66V21m-3 0 3-5 3 5Zm0 4H33l6 13-6 13h32M181 66V21m-3 0 3-5 3 5Zm0 4h32l-6 13 6 13h-32M111 69h18M57 67h16m100 0h16"/>
        <path d="m136 24 5-5 5 5-5 11Z"/>
      </g>
      <g class="heraldry-fine">
        <path d="M125 17h28l-6 12 6 12h-28M60 30H42l4 8-4 8h18m126-16h18l-4 8 4 8h-18M9 59l31 3m43 1 22 3m32 0 24-3m40-1 30-3M93 10v29m-4-25h8M92 51h6m44 6h6"/>
      </g>`,
    hero: `
      <g class="heraldry-main">
        <circle cx="120" cy="36" r="20"/>
        <path d="m120 23 4 9 10 1-8 7 2 10-8-5-8 5 2-10-8-7 10-1ZM115 65C88 64 73 49 79 22m46 43c27-1 42-16 36-43"/>
        <path d="M85 52c-9 1-14-4-15-10 8-1 13 3 15 10Zm10 8c-9 3-15 0-18-5 7-4 14-2 18 5ZM80 42c-9-3-12-8-10-14 8 2 12 7 10 14Zm-1-14c-5-5-4-12 1-17 5 6 4 12-1 17Zm76 24c9 1 14-4 15-10-8-1-13 3-15 10Zm-10 8c9 3 15 0 18-5-7-4-14-2-18 5Zm15-18c9-3 12-8 10-14-8 2-12 7-10 14Zm1-14c5-5 4-12-1-17-5 6-4 12 1 17Z"/>
      </g>
      <g class="heraldry-fine">
        <circle cx="120" cy="36" r="24"/>
        <path d="M120 4v5m-17-2 3 5m28 0 3-5M40 36h21m118 0h21M11 36h20m178 0h20M46 29l7 7-7 7m148-14-7 7 7 7M104 69l16-4 16 4"/>
      </g>`,
    tactic: `
      <g class="heraldry-main">
        <path d="m38 69 152-54m-5-6 21-4-15 15ZM45 74l-5-14m-7 12-4-10M46 10l146 57m-151-62 20 4-8 10Zm145 55 5-13m5 17 5-13"/>
        <path d="m74 59 6 10m-8-7 13-5M158 56l5-10m-8 2 13 5"/>
      </g>
      <g class="heraldry-fine">
        <path d="m13 53 53-19M8 45l35-13m-19-2 24-8m135 29 46 16m-34-26 37 13M98 14l10 5m34 41 12 5m-55-5 8-3m24-40 11-4"/>
        <path d="m103 29 17-8 17 8-17 24Zm7 2 10 17 10-17"/>
      </g>`,
    stratagem: `
      <g class="heraldry-main">
        <path d="M86 38s14-13 34-13 34 13 34 13-14 13-34 13-34-13-34-13Z"/>
        <circle cx="120" cy="38" r="8"/>
        <path d="m120 6 4 11h-8ZM120 70l-4-11h8ZM88 38H77m75 0h11M13 53h23l16-25h21m94 20h17l12-24h31"/>
      </g>
      <g class="heraldry-fine">
        <circle cx="120" cy="38" r="27"/>
        <path d="M104 8 101 3m35 5 3-5m-35 65-3 5m35-5 3 5M90 20l-5-3m70 3 5-3M90 56l-5 3m70-3 5 3M12 15h50m-50 5h28m154 42h34m-17-5h17M37 49l-5 8m17-25 6-8m138 4 6-8m-10 26-6 8"/>
        <circle cx="13" cy="53" r="3"/><circle cx="227" cy="24" r="3"/>
      </g>`,
    narrative: `
      <g class="heraldry-main">
        <path d="M20 62c52 0 111-12 170-48M70 59 59 36m-6-12c10 0 16 5 15 14-9 0-15-5-15-14ZM102 51l-2-22m-5-12c10 2 14 8 11 16-9-2-13-8-11-16ZM134 39l13 16m-1 0c10-3 17 0 20 8-9 4-17 1-20-8ZM165 25l18 10m0 0c8-5 15-4 20 3-7 6-15 5-20-3Z"/>
        <path d="M185 15c5-9 13-11 21-8-3 9-11 13-21 8M12 62c0-6 9-7 9-1s-9 8-9 1Z"/>
      </g>
      <g class="heraldry-fine">
        <path d="M17 11h49m-49 5h33m-33 5h21M170 66h52m-34-5h34m-17-5h17M43 55l-4-9m42 6-2-8m39-3-2-7m39-11-2-8M48 66l2 5m39-13 3 7m30-15 4 6M217 8v30m-5-24h10m-10 18h10"/>
      </g>`,
  };

  function symbol(type) {
    return '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">' +
      (SYMBOLS[type] || SYMBOLS.force) + '</svg>';
  }

  function motif(card) {
    return '<svg viewBox="0 0 240 76" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="1.1" stroke-linecap="round" stroke-linejoin="round">' +
      (MOTIFS[card?.type] || MOTIFS.force) + '</svg>';
  }

  window.V2Heraldry = { symbol };
})();
