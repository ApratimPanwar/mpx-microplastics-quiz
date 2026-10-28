// MPx Squeeze v2 (Mini) — physics behind the test bench. Pure functions, SI inside, no DOM.
// Geometry from the v2 drawing set: disc cassette Ø38.5 active (11.64 cm²), prefilter cup Ø17 × 28 (17.2 cm²).

export const DISC_AREA = 11.64e-4;                 // m², inside the cassette lip
export const PF_AREA = 17.2e-4;                    // m², prefilter cup outside
export const RHO = 1000, G = 9.81;
// water viscosity, Pa·s (Vogel form, 0–100 °C)
export const mu = (T) => 2.414e-5 * 10 ** (247.8 / (T + 133.15));
// Mott: dP[psi] = KL · flux[gpm/ft²] · µ[cP] · t[in]  ->  clean resistance (1/m), temperature-free
const perm25 = (KLt) => 1 / (KLt * 0.89 / 25.4) * 2444.9 * 14.504;               // L/(m² h bar) at 25 °C
export const Rm = (KLt) => 1 / (0.89e-3 * perm25(KLt) / 1000 / 3600 / 1e5);
export const CASSETTES = {
  A: { KLt: 26 * 1.5 / 3, d50: 0.75, k: 10, rating: 1.0, label: "A · asymmetric ≈1 µm" },
  B: { KLt: 26 * 1.6, d50: 0.85, k: 12, rating: 1.4, label: "B · grade 0.2, 1.4 µm" },
  C: { KLt: 8 * 1.6, d50: 1.5, k: 12, rating: 2.5, label: "C · grade 0.5, 2.5 µm" },
};
export const PREFILTER = { d50: 18, k: 6, rating: 20, Rm: 2.0e8 };       // 20 µm Dutch-weave laminate: open, low resistance
export const BOTTLES = {
  "500": { L: 0.5, R: 32.5, body: 120, Fwall: 4, label: "500 mL" },
  "1000": { L: 1.0, R: 40.0, body: 170, Fwall: 5, label: "1 L" },
};
export const WATERS = {
  tap: { c: 0.5e-3, mp: 1, label: "tap" },
  bore: { c: 2e-3, mp: 2, label: "borewell" },
  turbid: { c: 10e-3, mp: 4, label: "turbid surface" },
};
export const BANDS = [[1, 2], [2, 5], [5, 20], [20, 100]];
export const SUB = [0.3, 1];
export const STROKE = 0.30;          // share of the bottle volume one hand squeeze can push out before the hand closes
export const KVAC = 0.6;             // bar of spring-back vacuum per unit volume fraction a sealed PET bottle stays dented (assumption)
export const VALVE_CRACK = 0.03;     // bar, silicone umbrella valve
export const GAMMA = 0.072;          // N/m, water–air surface tension
export const bubbleBar = (d_um) => 4 * GAMMA / (d_um * 1e-6) / 1e5;      // pressure to push air through a wet pore of size d
export const DISC_MAX_DP = 3.0;      // bar, either direction (cassette is clamped and rib-supported both ways)
export const COMFORT_N = 60, TARGET_LMIN = 0.25;                           // 500 mL in 120 s
export const YIELD = 170e6, SKIRT = { r: 24e-3, t: 1.6e-3 };
export const hoopSF = (bar) => YIELD / (bar * 1e5 * SKIRT.r / SKIRT.t);

export const capture = (d, c) => 1 / (1 + (c.d50 / d) ** c.k);
export function bandShare(bands = BANDS) {            // n ∝ d⁻², shares of 1–100 µm
  const cum = (a, b) => 1 / a - 1 / b, tot = cum(1, 100);
  return bands.map(([a, b]) => cum(a, b) / tot);
}
export function bandCapture(c, bands = BANDS) {       // mean capture in each band (log-spaced)
  return bands.map(([a, b]) => {
    let s = 0, w = 0;
    for (let i = 0; i < 40; i++) { const d = a * (b / a) ** ((i + 0.5) / 40), wt = 1 / d; s += capture(d, c) * wt; w += wt; }
    return s / w;
  });
}
// hand force -> bottle pressure (bar): (F − wall) / palm contact + water column over the disc; minus any vacuum kept in a dented bottle
export function handBar(F, b, inp, level = 1) {
  return (Math.max(0, F - b.Fwall) / (inp.palm * 1e-4) + RHO * G * (0.03 + level * b.body / 1000 * 0.8)) / 1e5;
}
export function flowLmin(bar, inp, s = null) {        // through prefilter + cake + disc, L/min
  if (bar <= 0) return 0;
  const c = CASSETTES[inp.cas];
  const Rc = s ? inp.alpha * s.mDisc / DISC_AREA + s.Rirr : 0;
  const Rpf = s ? PREFILTER.Rm + inp.alpha * 0.01 * s.mPf / PF_AREA : PREFILTER.Rm;   // coarse catch packs loosely: ~1 % of the fine cake's resistance
  const Rt = (Rm(c.KLt) + Rc) / DISC_AREA + Rpf / PF_AREA;                             // series resistances per area
  return bar * 1e5 / (mu(inp.T) * Rt) * 6e4;
}
export const forceFor = (Q, b, inp, s = null) => {     // hand force for a target flow, full bottle, no vacuum
  const per = flowLmin(1, inp, s);
  return ((Q / per) - RHO * G * (0.03 + b.body / 1000 * 0.8) / 1e5) * 1e5 * inp.palm * 1e-4 + b.Fwall;
};
export function litresToHalf(inp, s) {                // from the current state, at the water's solids
  const c = CASSETTES[inp.cas], w = WATERS[inp.water];
  const Rnow = Rm(c.KLt) + inp.alpha * s.mDisc / DISC_AREA + s.Rirr;
  const mMore = Rnow * DISC_AREA / inp.alpha;          // added disc mass that doubles resistance
  return mMore / (w.c * (1 - inp.pfCut) * 0.9) * 1000;
}
export function fresh(b = BOTTLES["500"]) {
  return { t: 0, litres: 0, bottleL: b.L, beakerL: 0, dent: 0, d: 0, phase: "squeeze", phaseT: 0, squeezes: 0, stalled: false,
    mDisc: 0, mPf: 0, Rirr: 0, disc: [0, 0, 0, 0], pf: [0, 0, 0, 0], passed: [0, 0, 0, 0], sub: 0, dish: [0, 0, 0, 0], dishMass: 0,
    Q: 0, P: 0, air: 0, lastRecovery: null, hist: [], bfAt: [] };
}
function deposit(s, inp, vol) {                      // vol in L of water through both stages
  const w = WATERS[inp.water], c = CASSETTES[inp.cas], sh = bandShare();
  const pfc = bandCapture(PREFILTER), dc = bandCapture(c);
  const n = inp.mpPerL * w.mp * vol;
  for (let i = 0; i < 4; i++) {
    const nb = n * sh[i], atPf = nb * pfc[i], toDisc = nb - atPf, atDisc = toDisc * dc[i];
    s.pf[i] += atPf; s.disc[i] += atDisc; s.passed[i] += toDisc - atDisc;
  }
  s.sub += inp.mpPerL * w.mp * vol * 0.6 * (1 - bandCapture(c, [SUB])[0]);       // sub-micron count, reported only
  s.mPf += w.c * vol / 1000 * inp.pfCut;
  s.mDisc += w.c * vol / 1000 * (1 - inp.pfCut) * 0.9;
}
// one step of squeezing with the press (auto-cycled squeeze / release like a hand pumping)
export const SQUEEZE_S = 5.0, RELEASE_S = 1.4;
export function stepSqueeze(s, inp, dt) {
  const b = BOTTLES[inp.bottle];
  s.t += dt; s.phaseT += dt; s.air = 0;
  if (s.phase === "squeeze") {
    const vac = inp.valve ? 0 : KVAC * s.dent / b.L;
    const hand = handBar(inp.F, b, inp, s.bottleL / b.L);
    const P = hand - vac;
    const room = STROKE * b.L - s.d;                  // the hand can still close this much
    s.stalled = !inp.valve && P <= 0.005 && s.bottleL > 0.001;
    let Q = room > 0 && s.bottleL > 0.0005 ? flowLmin(P, inp, s) : 0;
    let vol = Math.min(Q / 60 * dt, s.bottleL, Math.max(0, room));
    s.Q = vol / dt * 60; s.P = Math.max(P, -vac);
    s.d += vol; s.bottleL -= vol; s.litres += vol; s.beakerL += vol;
    if (vol > 0) deposit(s, inp, vol);
    if ((s.phaseT >= SQUEEZE_S || room <= 1e-6 || s.bottleL <= 0.0005) && s.d > 0) { s.phase = "release"; s.phaseT = 0; s.squeezes++; }
    if (s.phaseT >= SQUEEZE_S && s.d === 0) s.phaseT = 0;
  } else {
    s.Q = 0;
    if (inp.valve) {                                   // air comes in through the umbrella valve and the bottle springs back
      const back = Math.min(s.d, s.d * dt / (RELEASE_S * 0.6));
      s.d -= back; s.air = back / dt; s.P = -VALVE_CRACK;
    } else {                                           // no way in for air: the wet disc holds it out, the dent stays
      s.dent += s.d; s.d = 0; s.P = -KVAC * s.dent / b.L;
    }
    if (s.phaseT >= RELEASE_S) { s.phase = "squeeze"; s.phaseT = 0; if (inp.valve) s.d = 0; }
  }
  if (s.hist.length === 0 || s.litres - s.hist.at(-1)[0] > 0.02) s.hist.push([s.litres, flowLmin(handBar(inp.F, b, inp, 1), inp, s)]);
  return s;
}
export function vent(s) { s.dent = 0; s.d = 0; s.stalled = false; }
// tap mode: the tap adapter on the inlet, tap pressure across both stages
export function stepTap(s, inp, dt) {
  s.t += dt;
  const P = inp.Ptap;
  const Q = flowLmin(P, inp, s), vol = Q / 60 * dt;
  s.Q = Q; s.P = P; s.litres += vol; s.beakerL += vol; deposit(s, inp, vol);
  if (s.hist.length === 0 || s.litres - s.hist.at(-1)[0] > 0.02) s.hist.push([s.litres, flowLmin(handBar(inp.F, BOTTLES[inp.bottle], inp, 1), inp, s)]);
  return s;
}
// backflush: tap water in at the spout, out of the inlet; lifts the disc cake and the prefilter catch into the dish
export function stepBackflush(s, inp, dt) {
  s.t += dt;
  const tau = 4.5 / Math.max(0.2, inp.Ptap), tauPf = 2.0 / Math.max(0.2, inp.Ptap);
  const f = 1 - Math.exp(-dt / tau), fp = 1 - Math.exp(-dt / tauPf);
  const md = s.mDisc * f, mp = s.mPf * fp;
  s.mDisc -= md; s.mPf -= mp; s.dishMass += md + mp;
  s.Rirr += 0.03 * inp.alpha * md / DISC_AREA;
  for (let i = 0; i < 4; i++) { const a = s.disc[i] * f, b = s.pf[i] * fp; s.disc[i] -= a; s.pf[i] -= b; s.dish[i] += a + b; }
  s.Q = -flowLmin(inp.Ptap, inp, s); s.P = inp.Ptap;
  return s;
}
// smallest particle a viewer can pick out on the sintered disc: bare grey metal hides small particles, Nile red makes plastic glow
export function visibleFrom(inp) {
  const res = inp.mag === "50" ? 5 : 2;
  return inp.stain ? res : Math.max(res, 20);
}
export function requirements(inp, s) {
  const b = BOTTLES[inp.bottle], c = CASSETTES[inp.cas];
  const q60 = flowLmin(handBar(COMFORT_N, b, inp, 1), inp);
  const fNeed = forceFor(TARGET_LMIN, b, inp);
  const caps = bandCapture(c), sub = bandCapture(c, [SUB])[0];
  const half = litresToHalf(inp, fresh());
  const qTap = flowLmin(inp.Ptap, inp);
  const vac1 = KVAC * STROKE;                                   // vacuum left after one full squeeze without a valve
  const hand60 = handBar(COMFORT_N, b, inp, 1);
  const squeezesToStall = Math.max(1, Math.ceil(hand60 / vac1));
  const bp = bubbleBar(c.rating);
  return [
    { name: "Length outside the bottle", value: "50 mm", target: "≤ 100 mm", pass: true },
    { name: `500 mL at ${COMFORT_N} N, ${inp.T} °C`, value: `${Math.round(30 / Math.max(1e-3, q60))} s`, target: "≤ 120 s", pass: 30 / q60 <= 120 },
    { name: `Force for ${TARGET_LMIN} L/min`, value: `${Math.max(0, fNeed).toFixed(0)} N`, target: `≤ ${COMFORT_N} N`, pass: fNeed <= COMFORT_N },
    { name: "Bottle refills with air between squeezes", value: inp.valve ? "valve" : `stalls after ~${squeezesToStall}`, target: "every squeeze", pass: !!inp.valve },
    { name: "Air cannot leak back through the wet disc", value: `${bp.toFixed(1)} bar`, target: `> ${(KVAC * STROKE * 3).toFixed(2)} bar`, pass: bp > KVAC * STROKE * 3 },
    { name: "Capture 2–5 µm", value: `${(caps[1] * 100).toFixed(1)} %`, target: "≥ 99 %", pass: caps[1] >= 0.99 },
    { name: "Capture 1–2 µm", value: `${(caps[0] * 100).toFixed(0)} %`, target: "≥ 90 %", pass: caps[0] >= 0.9 },
    { name: "Capture below 1 µm", value: `${(sub * 100).toFixed(0)} %`, target: "not claimed", pass: null },
    { name: `Litres until flow halves, clean disc (${WATERS[inp.water].label})`, value: `${half.toFixed(1)} L`, target: "≥ 20 L", pass: half >= 20 },
    { name: "Flow recovered by backflush", value: s.lastRecovery === null ? "run it" : `${Math.round(s.lastRecovery * 100)} %`, target: "≥ 80 %", pass: s.lastRecovery === null ? null : s.lastRecovery >= 0.8 },
    { name: `Tap flow at ${inp.Ptap.toFixed(1)} bar`, value: `${qTap.toFixed(1)} L/min`, target: "≥ 1.5 L/min", pass: qTap >= 1.5 },
    { name: "Disc ΔP at that tap pressure", value: `${inp.Ptap.toFixed(1)} bar`, target: `≤ ${DISC_MAX_DP} bar`, pass: inp.Ptap <= DISC_MAX_DP },
    { name: "Smallest particle seen on the disc", value: `${visibleFrom(inp)} µm`, target: "≤ 5 µm", pass: visibleFrom(inp) <= 5 },
    { name: "Cap skirt safety factor at 3 bar", value: `${hoopSF(3).toFixed(0)}×`, target: "≥ 4×", pass: hoopSF(3) >= 4 },
  ];
}
