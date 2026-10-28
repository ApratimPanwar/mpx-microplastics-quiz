// MPx Squeeze v1 — physics behind the test-bench figure. Pure functions, SI units inside, no DOM.
// Geometry and media data match the v1 drawing set (dims.py): element Ø20 x 2.0 wall, 55.6 cm2, Mott KL values.

export const MU = 0.89e-3;                       // Pa s, water at 25 C
export const AREA = 0.00556;                     // m2, element outside area incl. closed end
export const WALL_MM = 2.0;
export const GRADES = {
  "0.2": { KL: 26, label: "grade 0.2", rating: 1.4, d50: 0.85, k: 12 },     // Mott: grades 0.2-20 = 1.4-35 um absolute in liquid
  "0.5": { KL: 8.0, label: "grade 0.5", rating: 2.5, d50: 1.5, k: 12 },     // liquid rating to be confirmed by supplier
};
// hand on a PET bottle: internal pressure ~ (force - wall stiffness) / contact area of the palm (assumption, to be measured)
export const BOTTLES = {
  "500": { L: 0.5, R: 32.5, body: 120, Aeff: 34e-4, Fwall: 4, label: "500 mL" },
  "1000": { L: 1.0, R: 40.0, body: 170, Aeff: 42e-4, Fwall: 5, label: "1 L" },
};
export const WATERS = {
  tap: { c: 0.5e-3, label: "tap water (≈0.5 mg/L solids)" },          // kg/m3 of particles >1 um
  bore: { c: 2e-3, label: "borewell (≈2 mg/L)" },
  turbid: { c: 10e-3, label: "turbid (≈10 mg/L)" },
};
export const ALPHA = 1e13;                        // m/kg, specific resistance of a fine silt/MP cake (assumption: bench test 3 measures it)
export const COMFORT_N = 60;                      // sustained one-hand squeeze an adult can keep up for a minute (assumption)
export const TARGET_LMIN = 0.4;
export const MP_PER_L = 1000;                     // microplastic particles >= 1 um per litre, mid-range for tap water (literature spans 0.1-1000s)
export const YIELD_316L = 170e6;                  // Pa
export const BODY = { r: 14.5e-3, t: 1.0e-3 };   // mid-wall radius, wall of the thin body section
export const ELEMENT_MAX_DP = 3.4e5;             // Pa, Mott standard outside-in

export const permeance = (KL) => 1 / (KL * 0.89 * WALL_MM / 25.4) * 2444.9 * 14.504;     // L/(m2 h bar)
export const Rm = (KL) => 1 / (MU * permeance(KL) / 1000 / 3600 / 1e5);                    // 1/m
export const capture = (d, g) => 1 / (1 + (g.d50 / d) ** g.k);                            // fraction retained at size d (um)

export function squeezePa(F, b, levelFrac = 1) {
  const hand = Math.max(0, F - b.Fwall) / b.Aeff;
  const head = 1000 * 9.81 * (0.10 + levelFrac * b.body / 1000 * 0.8);   // water column above the element middle
  return hand + head;
}
export const flowM3s = (dP, KL, Rc = 0, Rirr = 0) => AREA * dP / (MU * (Rm(KL) + Rc + Rirr));
export const Lmin = (m3s) => m3s * 6e4;
export const forceFor = (Qlmin, b, KL, Rc = 0, Rirr = 0) => {            // hand force for a target flow (bottle full)
  const dP = Qlmin / 6e4 * MU * (Rm(KL) + Rc + Rirr) / AREA;
  return (dP - squeezePa(0, b, 1)) * b.Aeff + b.Fwall;
};
export const areaForComfort = (b, KL) => AREA * Math.max(1, forceFor(TARGET_LMIN, b, KL) > COMFORT_N ? (forceFor(TARGET_LMIN, b, KL) - b.Fwall) / (COMFORT_N - b.Fwall) : 1);
export const hoopSF = (P) => YIELD_316L / (P * BODY.r / BODY.t);

// particle size bands (n ~ d^-2). MP_PER_L counts particles 1-100 um; sub-micron particles are reported, not counted.
export const BANDS = [[1, 2], [2, 5], [5, 20], [20, 100]];
export const SUB = [0.3, 1];
export function bandShare() {
  const cum = (a, b) => 1 / a - 1 / b;                 // integral of d^-2
  const tot = cum(1, 100);
  return BANDS.map(([a, b]) => cum(a, b) / tot);
}
export function bandCapture(g, bands = BANDS) {         // mean capture in each band (log-spaced integration)
  return bands.map(([a, b]) => {
    let s = 0, w = 0;
    for (let i = 0; i < 40; i++) { const d = a * (b / a) ** ((i + 0.5) / 40); const wt = d ** -2 * d; s += capture(d, g) * wt; w += wt; }
    return s / w;
  });
}

// ---- state machine for the bench ----
export function fresh() { return { t: 0, litres: 0, cake: 0, Rirr: 0, bottleL: 0.5, beakerL: 0, mp: 0, mpPassed: 0, backflushed: 0, lastRecovery: null }; }
// squeezing: dt seconds at force F
export function stepSqueeze(s, { F, bottle, grade, water }, dt) {
  const b = BOTTLES[bottle], g = GRADES[grade], w = WATERS[water];
  if (s.bottleL <= 0.0005) return { ...s, Q: 0, P: squeezePa(F, b, 0) };
  const lev = s.bottleL / b.L;
  const P = squeezePa(F, b, lev);
  const Rc = ALPHA * s.cake / AREA;
  const q = flowM3s(P, g.KL, Rc, s.Rirr);
  const vol = Math.min(q * dt, s.bottleL / 1000);
  const shares = bandShare(), caps = bandCapture(g);
  const capFrac = shares.reduce((a, sh, i) => a + sh * caps[i], 0);
  return {
    ...s, t: s.t + dt, Q: vol / dt, P, litres: s.litres + vol * 1000, bottleL: s.bottleL - vol * 1000, beakerL: s.beakerL + vol * 1000,
    cake: s.cake + w.c * vol * 0.9, mp: s.mp + MP_PER_L * vol * 1000 * capFrac, mpPassed: s.mpPassed + MP_PER_L * vol * 1000 * (1 - capFrac),
  };
}
// backflush with tap water at Ptap (Pa), reverse flow lifts the cake; a little stays as irreversible fouling
export function stepBackflush(s, { Ptap }, dt) {
  const tau = 4.5 / Math.max(0.2, Ptap / 1e5);           // s, faster at higher tap pressure
  const removed = s.cake * (1 - Math.exp(-dt / tau));
  return { ...s, t: s.t + dt, cake: s.cake - removed, Rirr: s.Rirr + 0.03 * ALPHA * removed / AREA, mp: s.mp * Math.exp(-dt / tau), Q: 0, P: Ptap };
}
export function litresToHalf({ grade, water }, Rirr = 0) {     // litres until flow halves from the current clean state
  const g = GRADES[grade], w = WATERS[water];
  const mHalf = (Rm(g.KL) + Rirr) * AREA / ALPHA;
  return mHalf / (w.c * 0.9) * 1000;
}
export function requirements(inp, s) {
  const b = BOTTLES[inp.bottle], g = GRADES[inp.grade];
  const qComfortClean = Lmin(flowM3s(squeezePa(COMFORT_N, b, 1), g.KL));
  const fNeed = forceFor(TARGET_LMIN, b, g.KL);
  const caps = bandCapture(g);
  const sub = bandCapture(g, [SUB])[0];
  const tHalfL = 0.5 / qComfortClean * 60;
  const halfL = litresToHalf(inp, s.Rirr);
  const Ptap = inp.Ptap;
  const qTap = Lmin(flowM3s(Ptap, g.KL));
  const recovery = s.lastRecovery;
  return [
    { id: "flow", name: `Squeeze flow at a comfortable ${COMFORT_N} N`, value: `${qComfortClean.toFixed(2)} L/min`, target: `≥ ${TARGET_LMIN} L/min`, pass: qComfortClean >= TARGET_LMIN },
    { id: "force", name: `Hand force for ${TARGET_LMIN} L/min (clean)`, value: `${Math.max(0, fNeed).toFixed(0)} N`, target: `≤ ${COMFORT_N} N`, pass: fNeed <= COMFORT_N },
    { id: "time", name: "Time to filter 500 mL", value: `${tHalfL.toFixed(0)} s`, target: "≤ 120 s", pass: tHalfL <= 120 },
    { id: "capture", name: "Capture of particles 2–5 µm", value: `${(caps[1] * 100).toFixed(1)} %`, target: "≥ 99 %", pass: caps[1] >= 0.99 },
    { id: "capture1", name: "Capture of particles 1–2 µm", value: `${(caps[0] * 100).toFixed(0)} %`, target: "≥ 90 %", pass: caps[0] >= 0.9 },
    { id: "sub", name: "Capture below 1 µm (nanoplastics, bacteria)", value: `${(sub * 100).toFixed(0)} %`, target: "not claimed", pass: null },
    { id: "life", name: "Litres before flow halves", value: `${halfL.toFixed(0)} L`, target: "≥ 20 L", pass: halfL >= 20 },
    { id: "backflush", name: "Flow recovered by backflush", value: recovery === null ? "run it" : `${(recovery * 100).toFixed(0)} %`, target: "≥ 80 %", pass: recovery === null ? null : recovery >= 0.8 },
    { id: "tap", name: `Tap flow at ${(Ptap / 1e5).toFixed(1)} bar`, value: `${qTap.toFixed(1)} L/min`, target: "≥ 1.5 L/min", pass: qTap >= 1.5 },
    { id: "dp", name: "Element ΔP at that tap pressure", value: `${(Ptap / 1e5).toFixed(1)} bar`, target: "≤ 3.4 bar", pass: Ptap <= ELEMENT_MAX_DP },
    { id: "wall", name: "Body wall safety factor at 3 bar", value: `${hoopSF(3e5).toFixed(0)}×`, target: "≥ 4×", pass: hoopSF(3e5) >= 4 },
  ];
}
