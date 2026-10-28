"""MPx Boil-Tube (v0.4): portable, gravity-fed, no pump, no PCB.
Mariotte reservoir (constant head) -> cold feed up the ANNULUS of a tube-in-tube coil -> small heater
cell (vented, boiling, mesh catcher) -> wax gate valve (opens ~95 C) -> hot water down the INNER tube
-> body coil in a finned shell -> outlet.
 T1 exchanger length vs effectiveness (1/8" in 1/4" SS tube-in-tube, coil D 60 mm)
 T2 heater power budget vs flow
 T3 gravity heads: can both sides flow without a pump?
 T4 cell volume for the residence time; warm-up time
 T5 outlet and shell temperature (body trim)
"""
import math, json, os
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from CoolProp.CoolProp import PropsSI
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures"); os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"figure.dpi": 130, "font.size": 9.5, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": .3})
C = ["#2f80c0", "#f2a516", "#e8503a", "#5a6773", "#2a9d8f"]
g = 9.81; R = {}
prop = lambda k, T: PropsSI(k, "T", T+273.15, "P", 101325, "Water")
hfg = 2.257e6
# geometry
Di_o, Di_t = 4.76e-3, 0.51e-3      # 3/16" x 0.020" (low drop on the gravity hot side)
Do_o, Do_t = 9.53e-3, 0.89e-3       # 3/8" x 0.035" (annulus Dh ~3 mm: low head on the cold side)
Di = Di_o-2*Di_t; Dann = Do_o-2*Do_t; Dh = Dann-Di_o
A_in = math.pi*Di**2/4; A_ann = math.pi*(Dann**2-Di_o**2)/4
Dcoil = 0.070; kss = 16.
def mdot(Q): return Q/3.6e6*1000
def hx(Q, coiled=True):
    m = mdot(Q); Th, Tc = 62, 58
    v = m/prop("D", Th)/A_in; Re = prop("D", Th)*v*Di/prop("V", Th); Pr = prop("C", Th)*prop("V", Th)/prop("L", Th)
    De = Re*math.sqrt(Di/Dcoil); Nu = 4.36
    if coiled: Nu = ((4.364+4.636/(1+957/(De**2*Pr))**2)**3 + 1.816*(De/(1+1.15/Pr))**1.5)**(1/3)
    hi = Nu*prop("L", Th)/Di; ho = 5.6*prop("L", Tc)/Dh
    Rp = 1/(hi*math.pi*Di)+math.log(Di_o/Di)/(2*math.pi*kss)+1/(ho*math.pi*Di_o)
    va = m/prop("D", Tc)/A_ann; Rea = prop("D", Tc)*va*Dh/prop("V", Tc)
    dpi = 64/Re/Di*prop("D", Th)*v**2/2*(1.4 if coiled else 1)
    dpa = 96/Rea/Dh*prop("D", Tc)*va**2/2*(1.3 if coiled else 1)
    return 1/Rp, dict(Re=Re, De=De, Nu=Nu, dp_in_Pa_m=dpi, dp_ann_Pa_m=dpa)
def eps(NTU, Cr=0.985): return (1-np.exp(-NTU*(1-Cr)))/(1-Cr*np.exp(-NTU*(1-Cr)))
L = np.linspace(.1, 4, 200)
fig, ax = plt.subplots(1, 3, figsize=(12, 3.4)); T1 = {}
for i, Q in enumerate([0.8, 1.2, 1.6]):
    UA, d = hx(Q); Cmin = mdot(Q)*4186*.985
    e = eps(UA*L/Cmin); ax[0].plot(L, e, c=C[i], label=f"{Q} L/h")
    UAs, _ = hx(Q, False); ax[0].plot(L, eps(UAs*L/Cmin), c=C[i], ls=":")
    T1[Q] = dict(L_eps90=float(np.interp(.9, e, L)), **{k: float(v) for k, v in d.items()})
L_HX = math.ceil(1.5*T1[1.6]["L_eps90"]*10)/10
eps_d = {Q: float(eps(hx(Q)[0]*L_HX/(mdot(Q)*4186*.985))) for Q in (0.8, 1.2, 1.6)}
eps_s = {Q: float(eps(hx(Q, False)[0]*L_HX/(mdot(Q)*4186*.985))) for Q in (0.8, 1.2, 1.6)}
ax[0].axhline(.9, c="k", lw=.8, ls="--"); ax[0].set_ylim(.4, 1)
ax[0].set(xlabel="tube-in-tube length, m", ylabel="effectiveness ε", title="T1 · Exchanger (3/16\" in 3/8\", coil Ø70)"); ax[0].legend(fontsize=8)
R["T1"] = dict(per_flow=T1, L_design=L_HX, eps_design=eps_d, eps_no_dean=eps_s, coil_turns=L_HX/(math.pi*Dcoil), coil_height_mm=L_HX/(math.pi*Dcoil)*9.53*1.1)
# T2 power
Tin, Tb = 25., 99.5
def power(Q, e, f_ev=0.015, UA_loss=0.08):
    m = mdot(Q); sens = m*4186*(1-e)*(Tb-Tin); steam = m*f_ev*hfg; loss = UA_loss*(Tb-Tin)
    return dict(sensible=sens, steam=steam, losses=loss, total=sens+steam+loss, no_hx=m*4186*(Tb-Tin)+steam+loss)
Qs = np.linspace(.4, 2.5, 60)
for i, e in enumerate([.85, .9, .95]): ax[1].plot(Qs, [power(q, e)["total"] for q in Qs], c=C[i], label=f"ε = {e}")
ax[1].plot(Qs, [power(q, 0)["no_hx"] for q in Qs], c=C[3], ls=":", label="no exchanger")
ax[1].axhline(60, c="k", ls="--", lw=.8); ax[1].text(.45, 64, "60 W heater (USB-C 20 V 3 A)", fontsize=8)
ax[1].set_ylim(0, 200); ax[1].set(xlabel="flow, L/h", ylabel="heater power, W", title="T2 · Heater needed"); ax[1].legend(fontsize=8)
R["T2"] = {Q: {k: round(v, 1) for k, v in power(Q, eps_d[Q]).items()} for Q in (0.8, 1.2, 1.6)}
R["T2_no_dean"] = {Q: round(power(Q, eps_s[Q])["total"], 1) for Q in (0.8, 1.2, 1.6)}
# T3 heads
Q = 1.2; _, d = hx(Q); _, d16 = hx(1.6)
dp_cold = d16["dp_ann_Pa_m"]*L_HX + 150          # + heater channel and fittings
dp_hot = d16["dp_in_Pa_m"]*L_HX + 1.2*40 + 300   # + body coil 1.2 m of 1/8" inner-size tube + mesh catcher (clean) + gate valve
R["T3"] = dict(cold_side_Pa=dp_cold, cold_head_mm=dp_cold/(1000*g)*1000, hot_side_Pa=dp_hot, hot_head_mm=dp_hot/(1000*g)*1000,
               note="worst case 1.6 L/h; Mariotte tip set >= 2x cold head above the cell surface; hot side has ~180 mm available")
# T4 cell + warm-up
tau = 3.0     # min at the boil (test 2/3/4)
V_cell = {Q: Q*1000/60*tau for Q in (0.8, 1.2, 1.6)}
m_metal = 0.25  # kg steel heater/cell
E_warm = (V_cell[1.6]/1000*4186 + m_metal*500)*75 + 0.3*500*37    # cell + HX metal to mean temp
R["T4"] = dict(tau_min=tau, cell_mL=V_cell, warmup_min_at_60W=E_warm/55/60, first_water_min=E_warm/55/60+tau)
# T5 body trim: hot side leaves HX at Tin+(1-e)*(Tb-Tin); finned shell D 90 x 250, coil 1.2 m
def body(Thin, Ta, Q):
    m = mdot(Q); A = math.pi*0.09*0.25*2.2; UAair = 9.0*A    # fins x2.2 area, h~9 incl. radiation
    UAc = 1/(1/(4.36*0.62/Di*math.pi*Di*1.2)+1/(400*0.004*1.2))
    Ts = Ta+1
    for _ in range(50):
        To = Ts+(Thin-Ts)*math.exp(-UAc/(m*4186)); q = m*4186*(Thin-To); Ts = .5*Ts+.5*(Ta+q/UAair)
    return To, Ts, q
rows = {}
for Ta in (25, 35):
    for Q in (0.8, 1.2, 1.6):
        Thin = Ta+(1-eps_d[Q])*(Tb-Ta); To, Ts, q = body(Thin, Ta, Q)
        rows[f"{Ta}C_{Q}"] = dict(after_HX=round(Thin, 1), outlet=round(To, 1), shell=round(Ts, 1), W=round(q, 1))
R["T5"] = rows
Qp = [0.8, 1.2, 1.6]
ax[2].bar([str(q) for q in Qp], [rows[f"25C_{q}"]["after_HX"] for q in Qp], color=C[1], label="leaving exchanger")
ax[2].bar([str(q) for q in Qp], [rows[f"25C_{q}"]["outlet"] for q in Qp], color=C[0], label="leaving body coil")
ax[2].axhline(25, c="k", ls=":", lw=.8); ax[2].set_ylim(20, 40)
ax[2].set(xlabel="flow, L/h", ylabel="°C", title="T5 · Water temperature out (25 °C room)"); ax[2].legend(fontsize=8)
fig.tight_layout(); fig.savefig(f"{OUT}/T_boiltube.png"); plt.close(fig)
json.dump(R, open(os.path.join(os.path.dirname(OUT), "boiltube_results.json"), "w"), indent=1, default=float)
print(json.dumps(R, indent=1, default=lambda x: round(float(x), 3)))
