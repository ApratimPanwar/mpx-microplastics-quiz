"""
MPx Boil-Loop: first-pass engineering simulations (v0.2, Oct 2026)
==================================================================
Open-source stack: Python 3, NumPy, SciPy, CoolProp (water properties),
phreeqpython (USGS PHREEQC, phreeqc.dat database), Matplotlib.

Run:  python mpx_boilloop_sim.py      -> writes figures/*.png and results.json

Models (all 0-D / 1-D, deliberately simple and auditable):
  S1  Water chemistry   - CaCO3 precipitated on heating, closed vs vented (PHREEQC)
  S2  Energy balance    - heater power vs flow rate and exchanger effectiveness
  S3  Heat exchanger    - counterflow tube-in-tube, epsilon-NTU, laminar + Dean-flow
  S4  Boil chamber RTD  - tanks-in-series residence-time distribution
  S5  Separation        - Stokes settling in the calm zone + cake filtration life
  S6  Body radiator     - finned shell, natural convection + radiation, coil outlet
  S7  Start-up + battery- lumped transient warm-up, one-tank run on battery only
Every number that is an assumption is in PARAMS below with a comment.
"""
import json, math, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from CoolProp.CoolProp import PropsSI
from phreeqpython import PhreeqPython

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"figure.dpi": 130, "font.size": 9.5, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.alpha": .3})
C = ["#2f80c0", "#f2a516", "#e8503a", "#5a6773", "#2a9d8f", "#8e5cc2"]
R = {}  # results collected for the report

# --------------------------------------------------------------------------- PARAMS
P = dict(
    Q_lph=4.0,            # nominal product flow [L/h] (user target 3-5 L/h)
    T_in=25.0,            # inlet water temperature [C]  (also run 35 C for Indian summer)
    T_amb=25.0,           # room air [C]
    T_boil=99.5,          # boil-chamber bulk temperature [C] (~Bangalore 920 m: Tsat ~97 C; see note)
    tau_min=4.0,          # target mean residence time at the boil [min]
    f_evap=0.015,         # fraction of flow boiled off as steam to strip CO2 [-]
    eta_cond=0.7,         # fraction of steam latent heat recovered by the vent condenser on the feed line
    # HX geometry: SS316L instrumentation tube, Swagelok-standard sizes
    hx_inner_OD=6.35e-3, hx_inner_t=0.71e-3,   # 1/4" x 0.028"
    hx_outer_OD=9.53e-3, hx_outer_t=0.89e-3,   # 3/8" x 0.035"
    hx_coil_D=0.120,      # helix mean diameter [m]
    k_ss=16.0,            # SS316L conductivity [W/mK]
    UA_core=0.15,         # vented vacuum-flask boil chamber loss [W/K] (assumed; flask lid has tube penetrations)
    UA_heater=0.05,       # insulated heater block [W/K]
    UA_hx=0.10,           # insulated HX coil to cabinet [W/K]
    P_parasitic=5.0,      # pump 2.5 W + MCU/display/sensors 1.5 W + charger losses ~1 W [W]
    P_usb=100.0,          # USB-C PD 3.0 SPR max, 20 V x 5 A [W]
    P_heater_max=150.0,   # installed heater: 3 x 50 W cartridges (USB 100 W + battery boost during start-up)
    tank_L=1.5,           # removable glass tank = "one run"
)
rho = lambda T: PropsSI("D", "T", T+273.15, "P", 101325, "Water")
cp = lambda T: PropsSI("C", "T", T+273.15, "P", 101325, "Water")
mu = lambda T: PropsSI("V", "T", T+273.15, "P", 101325, "Water")
kw = lambda T: PropsSI("L", "T", T+273.15, "P", 101325, "Water")
h_fg = PropsSI("H", "P", 101325, "Q", 1, "Water") - PropsSI("H", "P", 101325, "Q", 0, "Water")

def mdot(Q_lph, T=25): return Q_lph/3.6e6*rho(T)       # kg/s

# --------------------------------------------------------------------------- S1 chemistry
pp = PhreeqPython()
H_list = np.array([40, 60, 80, 120, 180, 240, 300, 400])
closed, opened, opened_lo = [], [], []
for H in H_list:
    # temporary (carbonate) hardness only: Ca balanced by HCO3-, tap-water pH 7.5
    s = pp.add_solution({"units": "mmol/kgw", "Ca": H/100.09, "C(4)": "1 charge", "pH": 7.5, "temp": 25})
    ca0 = s.total("Ca", "mmol")
    # simultaneous equilibrium at 100 C: sealed = calcite only; vented = calcite + CO2(g) at air pCO2
    c = s.copy(); c.change_temperature(100); c.equalize(["Calcite"], [0], [10])
    o = s.copy(); o.change_temperature(100); o.equalize(["Calcite", "CO2(g)"], [0, -3.4], [10, 10])
    l = s.copy(); l.change_temperature(80); l.equalize(["Calcite", "CO2(g)"], [0, -3.4], [10, 10])
    closed.append((ca0-c.total("Ca", "mmol"))*100.09)
    opened.append((ca0-o.total("Ca", "mmol"))*100.09)
    opened_lo.append((ca0-l.total("Ca", "mmol"))*100.09)
    for x in (s, c, o, l): x.forget()
closed, opened, opened_lo = (np.clip(np.array(x), 0, None) for x in (closed, opened, opened_lo))
# Yu et al. 2024 measured MP/NP removal after boiling vs hardness
yu_H = np.array([60, 80, 180, 300]); yu_rem = np.array([.25, .34, .84, .90])
ppt_at_yu = np.interp(yu_H, H_list, opened)
# empirical link: removal = 1 - exp(-k * ppt)   (fit, 1 parameter)
from scipy.optimize import curve_fit
fk = lambda m, k: 1-np.exp(-k*m)
k_fit, _ = curve_fit(fk, ppt_at_yu, yu_rem, p0=[0.01])
R["S1"] = dict(H=H_list.tolist(), ppt_closed=closed.round(1).tolist(), ppt_vented=opened.round(1).tolist(),
               ppt_vented_80C=opened_lo.round(1).tolist(), k_fit=float(k_fit[0]),
               ratio_vented_over_closed_at_80=float(np.interp(80, H_list, opened)/np.interp(80, H_list, closed)),
               H_needed_for_90pct=float(np.interp(-math.log(.1)/k_fit[0], opened, H_list)))
fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
ax[0].plot(H_list, closed, "o-", c=C[3], label="sealed coil (no CO$_2$ escape)")
ax[0].plot(H_list, opened, "o-", c=C[0], label="vented boil chamber, air pCO$_2$ (upper bound)")
ax[0].plot(H_list, opened_lo, "o--", c=C[4], label="vented but only 80 °C (no boil)")
ax[0].set(xlabel="Hardness, mg/L as CaCO$_3$ (all carbonate)", ylabel="CaCO$_3$ precipitated at 100 °C, mg/L",
          title="S1 · Lime that comes out on heating (PHREEQC equilibrium)")
ax[0].legend(fontsize=8)
mm = np.linspace(0, 300, 100)
ax[1].plot(mm, fk(mm, *k_fit)*100, c=C[2], label=f"fit: 1−exp(−{k_fit[0]:.4f}·m)")
ax[1].scatter(ppt_at_yu, yu_rem*100, c=C[0], zorder=3, label="Yu et al. 2024 (x = PHREEQC lime at their hardness)")
ax[1].set(xlabel="CaCO$_3$ precipitated, mg/L", ylabel="MP/NP removed, %", title="Removal vs lime formed (empirical)")
ax[1].legend(fontsize=8)
fig.tight_layout(); fig.savefig(f"{OUT}/S1_chemistry.png"); plt.close(fig)

# --------------------------------------------------------------------------- S3 heat exchanger
def hx_UA_per_m(Q_lph, coiled=True):
    """Hot (gravity, filtered) water in INNER tube; cold pumped feed in ANNULUS."""
    Di = P["hx_inner_OD"]-2*P["hx_inner_t"]; Do_i = P["hx_inner_OD"]
    Dann = P["hx_outer_OD"]-2*P["hx_outer_t"]; Dh = Dann-Do_i
    Tm_h, Tm_c = 66.0, 58.0
    m = mdot(Q_lph)
    # inner tube, laminar, constant-flux Nu = 4.36; Dean enhancement (Manlapaz-Churchill, Pr~3)
    vi = m/rho(Tm_h)/(math.pi*Di**2/4); Re_i = rho(Tm_h)*vi*Di/mu(Tm_h)
    De = Re_i*math.sqrt(Di/P["hx_coil_D"]); Pr = cp(Tm_h)*mu(Tm_h)/kw(Tm_h)
    Nu_i = 4.36
    if coiled:
        x1 = (1+957/(De**2*Pr))**2 if De > 0 else 1
        x2 = 1+1.15/Pr
        Nu_i = ((4.364+4.636/x1)**3 + 1.816*(De/x2)**1.5)**(1/3)
    hi = Nu_i*kw(Tm_h)/Di
    # annulus, laminar, inner wall heated / outer adiabatic, ri/ro=0.82 -> Nu ~ 5.4 (Kays & Crawford)
    va = m/rho(Tm_c)/(math.pi*(Dann**2-Do_i**2)/4); Re_a = rho(Tm_c)*va*Dh/mu(Tm_c)
    ho = 5.4*kw(Tm_c)/Dh
    Rp = 1/(hi*math.pi*Di) + math.log(Do_i/Di)/(2*math.pi*P["k_ss"]) + 1/(ho*math.pi*Do_i)
    # pressure drops per metre (laminar, f*Re = 64 tube, ~94 narrow annulus) [Pa/m]
    dpi = 64/Re_i*1/Di*rho(Tm_h)*vi**2/2*(1.5 if coiled else 1)
    dpa = 94/Re_a*1/Dh*rho(Tm_c)*va**2/2*(1.3 if coiled else 1)
    return 1/Rp, dict(Re_i=Re_i, De=De, Nu_i=Nu_i, hi=hi, ho=ho, Re_a=Re_a, dp_i=dpi, dp_a=dpa)

def eps_cf(NTU, Cr=0.985):
    if abs(1-Cr) < 1e-6: return NTU/(1+NTU)
    return (1-np.exp(-NTU*(1-Cr)))/(1-Cr*np.exp(-NTU*(1-Cr)))

Ls = np.linspace(0.2, 10, 200)
fig, ax = plt.subplots(figsize=(5.4, 3.4))
hxres = {}
for i, Q in enumerate([3, 4, 5]):
    Cmin = mdot(Q)*cp(60)*(1-P["f_evap"])
    for coiled, ls in ((True, "-"), (False, ":")):
        UA, d = hx_UA_per_m(Q, coiled)
        e = eps_cf(UA*Ls/Cmin)
        ax.plot(Ls, e, ls, c=C[i], label=f"{Q} L/h {'coiled' if coiled else 'straight'}")
        if coiled:
            L90 = float(np.interp(0.90, e, Ls)); L85 = float(np.interp(0.85, e, Ls))
            hxres[Q] = dict(UA_per_m=UA, L_for_eps90=L90, L_for_eps85=L85, **{k: float(v) for k, v in d.items()})
ax.axhline(.9, c="k", lw=.8, ls="--"); ax.set_ylim(.4, 1)
ax.set(xlabel="Exchanger length, m", ylabel="Effectiveness ε", title="S3 · Tube-in-tube exchanger (1/4\" in 3/8\")")
ax.legend(fontsize=7, ncol=2); fig.tight_layout(); fig.savefig(f"{OUT}/S3_hx.png"); plt.close(fig)
L_HX = math.ceil(1.5*hxres[5]["L_for_eps90"]*10)/10   # eps>=0.9 at 5 L/h, x1.5 margin on the Dean-flow model
UA_straight = {Q: hx_UA_per_m(Q, False)[0] for Q in (3, 4, 5)}
eps_if_no_dean = {Q: float(eps_cf(UA_straight[Q]*L_HX/(mdot(Q)*cp(60)*(1-P["f_evap"])))) for Q in (3, 4, 5)}
eps_design = {Q: float(eps_cf(hxres[Q]["UA_per_m"]*L_HX/(mdot(Q)*cp(60)*(1-P["f_evap"])))) for Q in (3, 4, 5)}
turns = L_HX/(math.pi*P["hx_coil_D"])
R["S3"] = dict(per_flow=hxres, L_design=L_HX, eps_at_design=eps_design, eps_if_no_dean=eps_if_no_dean, coil_turns=turns,
               coil_height_mm=turns*P["hx_outer_OD"]*1.05*1000,
               dp_hot_inner_Pa=hxres[5]["dp_i"]*L_HX, dp_cold_annulus_Pa=hxres[5]["dp_a"]*L_HX)

# --------------------------------------------------------------------------- S2 energy balance
def power_budget(Q, eps, T_in=P["T_in"], T_amb=P["T_amb"]):
    m = mdot(Q); Tb = P["T_boil"]
    sens = m*cp(60)*(1-eps)*(Tb-T_in)
    steam = m*P["f_evap"]*h_fg*(1-P["eta_cond"])
    loss = P["UA_core"]*(Tb-T_amb) + P["UA_heater"]*(Tb+5-T_amb) + P["UA_hx"]*((Tb+T_in)/2-T_amb)
    return dict(sensible=sens, steam=steam, losses=loss, parasitic=P["P_parasitic"],
                total=sens+steam+loss+P["P_parasitic"], no_hx=m*cp(60)*(Tb-T_in)+steam+loss+P["P_parasitic"])
Qs = np.linspace(1, 6, 60)
fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
for i, eps in enumerate([0.8, 0.85, 0.9, 0.95]):
    ax[0].plot(Qs, [power_budget(q, eps)["total"] for q in Qs], c=C[i], label=f"ε = {eps}")
ax[0].plot(Qs, [power_budget(q, 0)["no_hx"] for q in Qs], c=C[3], ls=":", label="no exchanger")
ax[0].axhline(P["P_usb"], c="k", ls="--", lw=.8); ax[0].text(1.1, P["P_usb"]+4, "USB-C PD 100 W", fontsize=8)
ax[0].axvspan(3, 5, color=C[1], alpha=.08); ax[0].set_ylim(0, 350)
ax[0].set(xlabel="Product flow, L/h", ylabel="Electrical power, W", title="S2 · Steady power vs flow")
ax[0].legend(fontsize=8)
bud = {Q: power_budget(Q, eps_design[Q]) for Q in (3, 4, 5)}
bud35 = power_budget(4, eps_design[4], T_in=35, T_amb=35)
labels = ["3 L/h", "4 L/h", "5 L/h", "4 L/h\n35 °C day"]; rows = [bud[3], bud[4], bud[5], bud35]
bottom = np.zeros(4)
for i, key in enumerate(["sensible", "steam", "losses", "parasitic"]):
    v = np.array([r[key] for r in rows]); ax[1].bar(labels, v, bottom=bottom, color=C[[0, 4, 1, 3][i]], label=key); bottom += v
for j, r in enumerate(rows): ax[1].text(j, r["total"]+2, f"{r['total']:.0f} W", ha="center", fontsize=8)
ax[1].axhline(P["P_usb"], c="k", ls="--", lw=.8)
ax[1].set(ylabel="W", title=f"Budget at design HX ({L_HX:.1f} m)"); ax[1].legend(fontsize=7)
fig.tight_layout(); fig.savefig(f"{OUT}/S2_energy.png"); plt.close(fig)
R["S2"] = dict(budget={str(k): {kk: round(vv, 1) for kk, vv in v.items()} for k, v in bud.items()},
               budget_4lph_35C={kk: round(vv, 1) for kk, vv in bud35.items()},
               Wh_per_L_4lph=bud[4]["total"]/4, Wh_per_L_kettle=1.0*4.186*(100-25)/3.6/0.9)

# --------------------------------------------------------------------------- S4 RTD
tau = P["tau_min"]; t = np.linspace(0, 16, 400)
fig, ax = plt.subplots(figsize=(5.4, 3.4)); rtd = {}
for i, N in enumerate([1, 2, 3, 4]):
    E = (N/tau)**N*t**(N-1)*np.exp(-N*t/tau)/math.factorial(N-1)
    F = 1-sum(np.exp(-N*t/tau)*(N*t/tau)**k/math.factorial(k) for k in range(N))
    ax.plot(t, E, c=C[i], label=f"{N} compartment{'s' if N > 1 else ''}")
    rtd[N] = dict(frac_under_1min=float(np.interp(1, t, F)), frac_under_2min=float(np.interp(2, t, F)))
ax.set(xlabel="Time in boil chamber, min", ylabel="E(t), 1/min", title=f"S4 · Residence time, mean {tau:.0f} min")
ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(f"{OUT}/S4_rtd.png"); plt.close(fig)
V_chamber = P["Q_lph"]*1000/60*tau  # mL at 4 L/h
R["S4"] = dict(rtd=rtd, V_boil_mL_at_4lph=V_chamber, V_boil_mL_at_5lph=5*1000/60*tau)

# --------------------------------------------------------------------------- S5 settling + filtration
g = 9.81; rho_c = 2710.; mu98 = mu(98)
A_settle = math.pi*0.040**2   # calm zone, 80 mm ID (3rd compartment of the flask)
SOR = mdot(5, 98)/rho(98)/A_settle   # surface overflow rate at 5 L/h
d_crit = math.sqrt(18*mu98*SOR/(g*(rho_c-rho(98))))
# Precipitate size is the big unknown -> three scenarios. Settler hydraulic efficiency 0.5 for a
# non-ideal (boiling-agitated upstream, short-circuiting) calm zone: capture = min(1, 0.5*vs/SOR).
from scipy.stats import lognorm
d = np.logspace(-1, 2.3, 500)*1e-6
vs = g*d**2*(rho_c-rho(98))/(18*mu98)
def settled_mass_frac(d50, eff=0.5, sg=2.0):
    pdf = lognorm(s=math.log(sg), scale=d50).pdf(d); cap = np.clip(eff*vs/SOR, 0, 1)
    return float(np.trapezoid(pdf*cap*d**3, d)/np.trapezoid(pdf*d**3, d))
scen = {"optimistic d50=15 um": 15e-6, "middle d50=6 um": 6e-6, "pessimistic d50=2 um": 2e-6}
# cake filtration with gravity head (Ruth): dP = mu*Q*(Rm + alpha*w*V/A)/A
head_Pa = 0.085*rho(60)*g         # head left for the filter: 145 mm free-surface-to-spout minus ~60 mm pipe/HX/coil losses
Rm = 1e10                         # clean medium resistance, 1/m (cellulose ~11 um paper / 10 um sintered SS)
def life_L(A, alpha, ppt_mgL, frac_to_filter, Q=4):
    w = ppt_mgL*1e-3*frac_to_filter      # kg cake per m3 filtrate
    Qv = mdot(Q, 98)/rho(98)
    V = (head_Pa*A/(mu98*Qv*0.5) - Rm)*A/(alpha*w)   # end of life: flow halves at the available head
    return max(V, 0)*1000
ppt_design = float(np.interp(180, H_list, opened))
A = np.linspace(0.002, 0.03, 100); alpha = 5e10
fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
for i, (k, d50) in enumerate(scen.items()):
    pdf = lognorm(s=math.log(2.0), scale=d50).pdf(d)
    ax[0].semilogx(d*1e6, pdf/pdf.max()*100, c=C[i], lw=1, alpha=.5)
    ax[1].plot(A*1e4, [life_L(a, alpha, ppt_design, 1-settled_mass_frac(d50)) for a in A], c=C[i],
               label=f"{k}: {settled_mass_frac(d50)*100:.0f}% settles")
ax[0].semilogx(d*1e6, np.clip(0.5*vs/SOR, 0, 1)*100, c="k", lw=1.6, label="captured in calm zone, %")
ax[0].set(xlabel="Particle size, µm", ylabel="%", title=f"S5 · Calm-zone settler at 5 L/h (SOR {SOR*1000:.2f} mm/s)")
ax[0].legend(fontsize=7.5)
ax[1].axhline(100, c="k", ls="--", lw=.8); ax[1].text(5, 115, "req. 14.1: ≥ 100 L", fontsize=8)
ax[1].set_yscale("log"); ax[1].set(xlabel="Filter area, cm²", ylabel="Litres until flow halves",
       title="Filter life, 180 mg/L hardness, α = 5e10 m/kg"); ax[1].legend(fontsize=7)
fig.tight_layout(); fig.savefig(f"{OUT}/S5_separation.png"); plt.close(fig)
A_design = 0.0150   # 150 cm2: pleated cellulose (or 10 um sintered SS) element ~60 mm OD x 45 mm tall
R["S5"] = dict(SOR_mm_s=SOR*1000, d_crit_um_ideal=d_crit*1e6, ppt_at_180=ppt_design, filter_area_cm2=A_design*1e4,
               scenarios={k: dict(settled=settled_mass_frac(v),
                                  life_L={f"{al:.0e}": life_L(A_design, al, ppt_design, 1-settled_mass_frac(v)) for al in (1e10, 5e10, 2e11)})
                          for k, v in scen.items()},
               sludge_g_per_100L_at_180=ppt_design*100/1000,
               sludge_mL_per_100L=ppt_design*100/1000/0.6)   # loose CaCO3 sludge ~0.6 g/mL

# --------------------------------------------------------------------------- S6 body radiator
sigma = 5.670e-8
geo = dict(D_shell=0.150, H=0.300, t_shell=0.003, n_fin=36, fin_L=0.018, fin_t=0.0015, emis=0.85, k_al=200.,
           coil_L=2.5, coil_hA=None)
def radiator(T_hot_in, T_amb, Q=P["Q_lph"], geo=geo):
    """Shell ~isothermal (Al). Coil -> shell: inner-tube convection + contact (thermal paste in groove).
    Shell -> air: vertical fin channels (Bar-Cohen & Rohsenow) + radiation from the envelope."""
    m = mdot(Q); cpw = cp(35)
    Di = P["hx_inner_OD"]-2*P["hx_inner_t"]
    UA_coil = 1/(1/(4.36*kw(35)/Di*math.pi*Di*geo["coil_L"]) + 1/(400*0.006*geo["coil_L"]))  # contact h=400 W/m2K over 6 mm strip
    Ts = T_amb+3
    for _ in range(60):
        Tf = (Ts+T_amb)/2+273.15; beta = 1/Tf; nu = 1.6e-5; ka = 0.027; Pr = .71
        S = (math.pi*geo["D_shell"]/geo["n_fin"])-geo["fin_t"]
        Ra = g*beta*max(Ts-T_amb, .1)*S**3/(nu**2)*Pr
        Elen = Ra*S/geo["H"]
        Nu = (576/Elen**2 + 2.873/math.sqrt(Elen))**-0.5
        h = Nu*ka/S
        mfin = math.sqrt(2*h/(geo["k_al"]*geo["fin_t"])); eta_f = math.tanh(mfin*geo["fin_L"])/(mfin*geo["fin_L"])
        A_fin = geo["n_fin"]*2*geo["fin_L"]*geo["H"]; A_base = math.pi*geo["D_shell"]*geo["H"]-geo["n_fin"]*geo["fin_t"]*geo["H"]
        A_env = math.pi*(geo["D_shell"]+2*geo["fin_L"])*geo["H"]
        hr = geo["emis"]*sigma*((Ts+273.15)**2+(T_amb+273.15)**2)*((Ts+273.15)+(T_amb+273.15))
        UA_air = h*(A_base+eta_f*A_fin) + hr*A_env
        # coil as a heat exchanger to an isothermal shell
        NTU = UA_coil/(m*cpw); T_out = Ts+(T_hot_in-Ts)*math.exp(-NTU)
        Qdot = m*cpw*(T_hot_in-T_out)
        Ts_new = T_amb+Qdot/UA_air
        Ts = 0.5*Ts+0.5*Ts_new
    return dict(T_out=T_out, T_shell=Ts, Q_W=Qdot, UA_air=UA_air, h_conv=h, UA_coil=UA_coil)
Tamb = np.linspace(15, 45, 31)
rad = []
for Ta in Tamb:
    Thin = Ta+(1-eps_design[4])*(P["T_boil"]-Ta)   # hot side leaving HX, inlet water = room temp
    rad.append((Thin, radiator(Thin, Ta)))
fig, ax = plt.subplots(figsize=(5.4, 3.4))
ax.plot(Tamb, [r[0] for r in rad], c=C[1], label="into body coil (after HX)")
ax.plot(Tamb, [r[1]["T_out"] for r in rad], c=C[0], label="out of spout")
ax.plot(Tamb, [r[1]["T_shell"] for r in rad], c=C[3], ls="--", label="shell surface")
ax.plot(Tamb, Tamb, c="k", lw=.7, ls=":", label="room air")
ax.axhline(48, c=C[2], lw=.8); ax.text(15.5, 49, "IEC 62368-1 metal >1 min: 48 °C", fontsize=7.5, color=C[2])
ax.set(xlabel="Room (and inlet water) temperature, °C", ylabel="°C", title="S6 · Body radiator at 4 L/h")
ax.legend(fontsize=7.5); fig.tight_layout(); fig.savefig(f"{OUT}/S6_radiator.png"); plt.close(fig)
r25 = radiator(25+(1-eps_design[4])*(P["T_boil"]-25), 25)
r5 = radiator(25+(1-eps_design[5])*(P["T_boil"]-25), 25, Q=5)
fin_var = {}
for nm, (n, L) in {"no fins": (0, 0.0), "24 x 8 mm fins": (24, 0.008), "36 x 18 mm fins": (36, 0.018)}.items():
    gg = dict(geo); gg["n_fin"] = max(n, 1); gg["fin_L"] = max(L, 1e-4)
    rr = radiator(25+(1-eps_design[5])*(P["T_boil"]-25), 25, Q=5, geo=gg)
    fin_var[nm] = dict(T_out=round(rr["T_out"], 2), T_shell=round(rr["T_shell"], 2))
R["S6"] = dict(fin_variants_5lph=fin_var, geo={k: v for k, v in geo.items() if v is not None}, at_25C_4lph={k: round(v, 2) for k, v in r25.items()},
               at_25C_5lph={k: round(v, 2) for k, v in r5.items()},
               at_45C_4lph={k: round(v, 2) for k, v in rad[-1][1].items()})

# --------------------------------------------------------------------------- S7 start-up + battery run
from scipy.integrate import solve_ivp
Vb = 1000*4/60*tau/1e3    # boil water inventory at 4 L/h [kg]
M = dict(block=0.25*900, chamber=Vb*4186+0.20*500, hx=(L_HX*(1.26e-5+2.42e-5)*8000)*500+L_HX*(1.91e-5+1.55e-5)*1000*4186)
def startup(P_heat_max, Q_run=4.0, tank_L=1.5, T0=25., pack_Wh=99.4, usb=False):
    """Phase A: fill chamber, heat batch to boil (no product). Phase B: hold tau at boil (product diverted
    back to tank via 3-way valve). Phase C: steady production until tank empty. Lumped nodes."""
    dt = 1.0; Tch = T0; Thx = T0; E = 0.0; tt = 0.; log = []
    held = 0.; produced = 0.; phase = "A"
    Pss = power_budget(Q_run, eps_design[4])["total"]
    while produced < tank_L and tt < 3*3600:
        if phase == "A":
            Pin = P_heat_max
            loss = P["UA_core"]*(Tch-P["T_amb"])
            Tch += (Pin-loss-P["P_parasitic"])*dt/(M["chamber"]+M["block"])
            Thx += (Tch-Thx)*dt/600
            if Tch >= P["T_boil"]: phase = "B"; Tch = P["T_boil"]
        elif phase == "B":   # recirculate at low flow, exchanger fills its profile
            Pin = 0.6*Pss; held += dt; Thx += ((P["T_boil"]+T0)/2-Thx)*dt/300
            if held >= tau*60: phase = "C"
        else:
            Pin = Pss; produced += Q_run/3600*dt; Thx = (P["T_boil"]+T0)/2
        Pbatt = Pin-(P["P_usb"] if usb else 0)
        E += max(Pbatt, 0)*dt/3600 if True else 0
        log.append((tt, Tch, Thx, Pin, E, phase)); tt += dt
    return np.array([(a, b, c, d, e) for a, b, c, d, e, _ in log]), tt, E, log
res_batt = startup(P["P_heater_max"]); res_usb = startup(P["P_heater_max"], usb=True)
arr, ttot, Ebat, log = res_batt
t_first = next(x[0] for x in log if x[5] == "C")
fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
ax[0].plot(arr[:, 0]/60, arr[:, 1], c=C[2], label="boil chamber"); ax[0].plot(arr[:, 0]/60, arr[:, 2], c=C[1], label="exchanger (mean)")
ax[0].axvline(t_first/60, c="k", ls="--", lw=.8); ax[0].text(t_first/60+.5, 30, f"first water\n{t_first/60:.0f} min", fontsize=8)
ax[0].set(xlabel="min", ylabel="°C", title="S7 · Cold start, 150 W heaters, 1.5 L tank"); ax[0].legend(fontsize=8)
packs = {"4S2P 18650 3.45 Ah (99 Wh)": 99.4, "4S2P 21700 P42A (121 Wh)": 121.0, "4S1P 21700 P50B (72 Wh)": 72.0}
ax[1].plot(arr[:, 0]/60, arr[:, 4], c=C[0], label="battery only")
ax[1].plot(res_usb[0][:, 0]/60, res_usb[0][:, 4], c=C[4], label="on USB-C 100 W (battery tops up)")
for i, (k, v) in enumerate(packs.items()):
    ax[1].axhline(v*0.8*0.92, c=C[[2, 3, 5][i]], ls=":", lw=1); ax[1].text(1, v*0.8*0.92+1.5, f"{k}: usable", fontsize=7)
ax[1].set(xlabel="min", ylabel="Wh drawn from battery", title="Battery energy for one run"); ax[1].legend(fontsize=8, loc="lower right")
fig.tight_layout(); fig.savefig(f"{OUT}/S7_startup_battery.png"); plt.close(fig)
R["S7"] = dict(thermal_mass_J_per_K={k: round(v) for k, v in M.items()}, t_first_water_min=t_first/60,
               t_run_total_min=ttot/60, battery_Wh_one_run=Ebat, battery_Wh_one_run_on_usb=res_usb[2],
               usable_factor="80% end-of-life capacity x 92% converter efficiency")

# --------------------------------------------------------------------------- design summary
R["design"] = dict(Q_nom_lph=P["Q_lph"], L_HX_m=L_HX, eps=eps_design, V_boil_mL=V_chamber, tau_min=tau,
                   P_steady_4lph=bud[4]["total"], P_steady_5lph=bud[5]["total"], params=P)
json.dump(R, open(os.path.join(os.path.dirname(OUT), "results.json"), "w"), indent=1, default=float)
print(json.dumps(R, indent=1, default=lambda x: round(float(x), 3))[:6000])
