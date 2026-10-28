"""MPx Boil-Trap (v0.3): portable flip unit, small mains heater, mechanical timer, mesh catcher,
finned metal cooling chamber. Quick checks:
 H1 heat-up + simmer time and energy vs heater size (0.5 L batch)
 H2 steam lost during the simmer (full vs half power via diode)
 H3 settling in the boil chamber before the flip
 H4 cooling 0.5 L in the cooling chamber: plain / Al fin sleeve / fin sleeve + wet wrap / water bath
 H5 catcher (mesh) flow time and lime caught per batch
"""
import math, json, os
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from CoolProp.CoolProp import PropsSI
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures"); os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"figure.dpi": 130, "font.size": 9.5, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": .3})
C = ["#2f80c0", "#f2a516", "#e8503a", "#5a6773", "#2a9d8f"]
R = {}; cpw = 4186.; g = 9.81; sigma = 5.67e-8
V = 0.5            # L per batch
m_ch = 0.20        # kg SS boil chamber + heater plate
hfg = 2.257e6
# ---- H1/H2 heat-up and simmer
heat = {}
for P in (400, 600, 800):
    Qh = (V*cpw + m_ch*500)*75
    t_heat = Qh/(P*0.95)/60
    simmer_P = P/2                  # diode halves power for the hold
    loss = 4.0*75                   # ~4 W/K bare chamber
    steam_g = max(simmer_P*0.95-loss*0.1, 0)*240/hfg*1000   # 4 min simmer
    E_Wh = (Qh + simmer_P*240)/3600
    heat[P] = dict(heat_min=round(t_heat, 1), total_min=round(t_heat+4, 1), steam_lost_g=round(steam_g), Wh_per_batch=round(E_Wh), A_at_230V=round(P/230, 2))
R["H1_H2"] = heat
# ---- H3 settling, 90 mm column at ~95 C
mu = PropsSI("V", "T", 368.15, "P", 101325, "Water"); rho = PropsSI("D", "T", 368.15, "P", 101325, "Water")
Hcol = 0.09
R["H3_d_settles_fully_um"] = {t: round(math.sqrt(18*mu*Hcol/(t*60)/(g*(2710-rho)))*1e6, 1) for t in (1, 2, 3, 5)}
# ---- H4 cooling 0.5 L from 95 C to 40 C, 30 C room
D, Hc = 0.085, 0.120
A_side = math.pi*D*Hc; A_end = math.pi*D**2/4
def h_nat(Ts, Ta, L):
    Tf = (Ts+Ta)/2+273.15; nu = 1.6e-5; Pr = .71; Ra = g/Tf*max(Ts-Ta, .1)*L**3/(nu*nu/Pr)
    return (0.825+0.387*Ra**(1/6)/(1+(0.492/Pr)**(9/16))**(8/27))**2*0.027/L
def psat(T): return PropsSI("P", "T", T+273.15, "Q", 0, "Water")
def cool(mode, Ta=30., RH=.5):
    mcap = V*cpw + 0.15*500 + (0.15*900 if mode != "plain" else 0)
    A = A_side + A_end
    if mode != "plain": A = A_end + A_side*3.2          # clip-on Al sleeve, 24 fins x 15 mm, eta ~0.85
    em = 0.3 if mode == "plain" else 0.85
    T = 95.; t = 0.; dt = 2.; hist = [(0, T)]; Tb = 25.; refilled = False; ev = 0.
    while T > 40 and t < 4*3600:
        if mode == "bath":
            if T-Tb < 4 and not refilled: Tb = 25.; refilled = True
            q = 1/(1/(250*(A_side+A_end))+1/(400*(A_side+A_end)))*(T-Tb); Tb += q*dt/(1.5*cpw)
        else:
            hc = h_nat(T, Ta, Hc); hr = em*sigma*((T+273.15)**2+(Ta+273.15)**2)*(T+Ta+546.3)
            q = (hc*(1 if mode == "plain" else .85)+hr*(1 if mode == "plain" else .45))*A*(T-Ta)
            if mode == "wet":
                Ts = T-3; hm = hc/(1.16*1007*0.89**(2/3))
                qe = hm*max(psat(Ts)/(461.5*(Ts+273.15)) - RH*psat(Ta)/(461.5*(Ta+273.15)), 0)*2.4e6*A_side*1.3
                q += qe; ev += qe*dt/2.4e6
        T -= q*dt/mcap; t += dt; hist.append((t, T))
    return np.array(hist), t/60, ev*1000
labels = {"plain": "plain steel chamber", "fins": "clip-on Al fin sleeve", "wet": "fin sleeve + wet cotton wrap", "bath": "stand in 1.5 L tap water, refill once"}
cres = {k: cool(k) for k in labels}
R["H4_min_to_40C"] = {labels[k]: dict(minutes=round(v[1]), water_used_mL=round(v[2])) for k, v in cres.items()}
# ---- H5 catcher: 25 um SS mesh disc, 55 mm, plus 11 um cellulose option; head ~ 60 mm water
A_mesh = math.pi*0.0275**2
k_mesh = 2.0e-9   # m2/m, permeability x thickness of a 25 um woven mesh (order of magnitude; measure)
mu60 = PropsSI("V", "T", 343.15, "P", 101325, "Water")
Q = k_mesh*A_mesh*(0.06*1000*g)/mu60
R["H5"] = dict(mesh_area_cm2=A_mesh*1e4, drain_time_s_clean=round(V/1000/Q), lime_per_batch_mg_at_180=round(160*V), note="drain time scales with how much lime reaches the mesh; measure on the bench")
# ---- figure
fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
Ps = np.linspace(300, 1000, 50)
ax[0].plot(Ps, [((V*cpw+m_ch*500)*75/(p*0.95))/60+4 for p in Ps], c=C[2], label="0.5 L: heat-up + 4 min simmer")
ax[0].plot(Ps, [((1.0*cpw+0.3*500)*75/(p*0.95))/60+4 for p in Ps], c=C[3], ls="--", label="1.0 L for comparison")
ax[0].axvline(600, c="k", ls=":", lw=.8); ax[0].text(610, 25, "600 W chosen\n(2.6 A at 230 V)", fontsize=8)
ax[0].set(xlabel="heater power, W", ylabel="minutes", title="H1 · Time to a treated batch"); ax[0].legend(fontsize=8)
for i, (k, (h, tm, ev)) in enumerate(cres.items()):
    ax[1].plot(h[:, 0]/60, h[:, 1], c=C[i], label=f"{labels[k]}: {tm:.0f} min")
ax[1].axhline(40, c="k", ls="--", lw=.8); ax[1].set_xlim(0, 120)
ax[1].set(xlabel="minutes after the flip", ylabel="water °C", title="H4 · Cooling 0.5 L to drinkable (30 °C room)")
ax[1].legend(fontsize=7.5); fig.tight_layout(); fig.savefig(f"{OUT}/H_boiltrap.png"); plt.close(fig)
json.dump(R, open(os.path.join(os.path.dirname(OUT), "boiltrap_results.json"), "w"), indent=1, default=float)
print(json.dumps(R, indent=1, default=lambda x: round(float(x), 2)))
