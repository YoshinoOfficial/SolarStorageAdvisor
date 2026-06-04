import numpy as np

# ===== Dimensions =====
N = 3
T = 24
B = 33
L = 32

dt = 1.0

# ===== IEEE33 Network Topology =====
branch_ohm = np.array([
    [1, 2, 0.0922, 0.0470],
    [2, 3, 0.4930, 0.2511],
    [3, 4, 0.3660, 0.1864],
    [4, 5, 0.3811, 0.1941],
    [5, 6, 0.8190, 0.7070],
    [6, 7, 0.1872, 0.6188],
    [7, 8, 0.7114, 0.2351],
    [8, 9, 1.0300, 0.7400],
    [9, 10, 1.0440, 0.7400],
    [10, 11, 0.1966, 0.0650],
    [11, 12, 0.3744, 0.1238],
    [12, 13, 1.4680, 1.1550],
    [13, 14, 0.5416, 0.7129],
    [14, 15, 0.5910, 0.5260],
    [15, 16, 0.7463, 0.5450],
    [16, 17, 1.2890, 1.7210],
    [17, 18, 0.7320, 0.5740],
    [2, 19, 0.1640, 0.1565],
    [19, 20, 1.5042, 1.3554],
    [20, 21, 0.4095, 0.4784],
    [21, 22, 0.7089, 0.9373],
    [3, 23, 0.4512, 0.3083],
    [23, 24, 0.8980, 0.7091],
    [24, 25, 0.8960, 0.7011],
    [6, 26, 0.2030, 0.1034],
    [26, 27, 0.2842, 0.1447],
    [27, 28, 1.0590, 0.9337],
    [28, 29, 0.8042, 0.7006],
    [29, 30, 0.5075, 0.2585],
    [30, 31, 0.9744, 0.9630],
    [31, 32, 0.3105, 0.3619],
    [32, 33, 0.3410, 0.5302]
])

branch = branch_ohm[:, :2].astype(int)
baseMVA = 100
baseKV = 12.66
Zbase = baseKV ** 2 / baseMVA
rline = branch_ohm[:, 2] / Zbase
xline = branch_ohm[:, 3] / Zbase

# ===== IEEE33 Nominal Loads (MW, MVAr) =====
Pd_nom = np.array([0.000, 0.100, 0.090, 0.120, 0.060, 0.060, 0.200, 0.200, 0.060, 0.060, 0.045,
                   0.060, 0.060, 0.120, 0.060, 0.060, 0.060, 0.090, 0.090, 0.090, 0.090, 0.090,
                   0.090, 0.420, 0.420, 0.060, 0.060, 0.060, 0.120, 0.200, 0.150, 0.210, 0.060])
Qd_nom = np.array([0.000, 0.060, 0.040, 0.080, 0.030, 0.020, 0.100, 0.100, 0.020, 0.020, 0.030,
                   0.035, 0.035, 0.080, 0.010, 0.020, 0.020, 0.040, 0.040, 0.040, 0.040, 0.040,
                   0.050, 0.200, 0.200, 0.025, 0.025, 0.020, 0.070, 0.600, 0.070, 0.100, 0.040])

# ===== Community Buses =====
commBus = np.array([10, 18, 30])
rootBus = 1

# ===== Price and Load Shape =====
ce_base = 1000 * np.array([0.40, 0.32, 0.26, 0.21, 0.23, 0.35, 0.55, 0.70, 0.82, 0.84, 0.80, 0.78,
                           0.68, 0.57, 0.52, 0.53, 0.65, 0.85, 0.96, 0.92, 0.87, 0.78, 0.66, 0.48])
shape_default = np.array([0.56, 0.54, 0.53, 0.52, 0.54, 0.62, 0.73, 0.83, 0.90, 0.94, 0.96, 0.97,
                          0.98, 0.97, 0.96, 0.96, 0.98, 1.00, 0.98, 0.93, 0.86, 0.78, 0.69, 0.61])

# ===== Community-Specific Capacity =====
pvCap = np.array([1.60, 2.00, 1.50])
windCap = np.array([0.00, 1.20, 0.00])
pvScaleFinal = 5.5
windScaleFinal = 5.5
PchMax = np.array([0.90, 1.40, 1.00])
PdisMax = np.array([0.80, 1.20, 0.90])
Emax = 4.0 * PdisMax
priceShift = np.array([0, 0.000, 0])

# ===== Carbon Parameters =====
carbonShape = np.array([0.92, 0.91, 0.90, 0.90, 0.91, 0.95, 1.02, 1.08, 1.12, 1.15, 1.17, 1.16,
                        1.13, 1.10, 1.08, 1.10, 1.16, 1.22, 1.24, 1.18, 1.08, 1.00, 0.96, 0.93])
carbonShape = carbonShape / carbonShape.mean()
efGridBase = 0.4419 * 1000
pCO2Base = 62.36 / 1000

# ===== CHP Parameters =====
PchpRated = np.array([1.20, 0.75, 0.60])
etaE_chp = np.full(N, 0.35)
etaH_chp = np.full(N, 0.45)
FgasMin = np.zeros(N)
FgasMax = PchpRated / etaE_chp
cGas = (2.8 / 9.7) * 1000
efGas = 0.202 * 1000
uChp0 = np.zeros(N)
PchpMin = 0.30 * PchpRated
RampUpCHP = 0.35 * PchpRated
RampDnCHP = 0.35 * PchpRated
StartUpCHP = np.full(N, 80)
ShutDnCHP = np.full(N, 20)
MinUpCHP = np.full(N, 2)
MinDnCHP = np.full(N, 2)
cOM_CHP = np.full(N, 8)
cRampCHP = np.full(N, 2)
lambdaHdump = np.full(N, 200)

# ===== Electric Boiler =====
PebMax = np.array([2.50, 2.00, 1.50])
etaEb = np.full(N, 0.97)
RampUpEb = 0.60 * PebMax
RampDnEb = 0.60 * PebMax
cRampEb = np.full(N, 1.0)

# ===== Electrolyzer =====
PelecMax = np.array([1.00, 0.80, 1.20])
etaElec = np.full(N, 20.0)
RampUpElec = 0.50 * PelecMax
RampDnElec = 0.50 * PelecMax
cRampElec = np.full(N, 3.0)

# ===== Fuel Cell =====
H2fcMax = np.array([30.0, 25.0, 40.0])
etaFc = np.full(N, 0.018)
RampUpFc = 0.50 * etaFc * H2fcMax
RampDnFc = 0.50 * etaFc * H2fcMax
cRampFc = np.full(N, 3.0)

# ===== Electrical Storage =====
SOC0_e = 0.50 * Emax
etaCh_e = np.full(N, 0.95)
etaDis_e = np.full(N, 0.95)

# ===== Thermal Storage =====
HchMax = np.array([2.50, 4.15, 1.50])
HdisMax = np.array([2.50, 4.15, 1.50])
EthMax = np.array([10.0, 16.571, 6.0])
SOC0_th = 0.50 * EthMax
etaCh_th = np.full(N, 0.95)
etaDis_th = np.full(N, 0.95)

# ===== Hydrogen Storage =====
H2chMax = np.array([17.8, 13.3, 30.0])
H2disMax = np.array([17.8, 13.3, 30.0])
EH2Max = np.array([106.30, 142.5, 240.0])
SOC0_h2 = 0.50 * EH2Max

# ===== Electric Load (MW, 3 communities x 24h) =====
Pload = np.array([
    [0.22, 0.20, 0.28, 0.27, 0.29, 0.38, 0.40, 0.42, 0.50, 0.54, 0.60, 0.58,
     0.56, 0.55, 0.56, 0.60, 0.68, 0.78, 0.86, 0.92, 0.78, 0.76, 0.42, 0.30],
    [0.85, 0.82, 0.80, 0.79, 0.82, 0.92, 1.10, 1.32, 1.48, 1.60, 1.68, 1.72,
     1.74, 1.74, 1.72, 1.70, 1.68, 1.65, 1.58, 1.50, 1.38, 1.22, 1.05, 0.95],
    [0.30, 0.28, 0.27, 0.26, 0.28, 0.35, 0.50, 0.82, 0.83, 0.85, 0.98, 0.99,
     0.96, 1.00, 0.82, 0.78, 0.88, 0.90, 1.12, 1.10, 0.98, 0.86, 0.72, 0.64],
])

Pbase = Pload.copy()

# ===== Demand Response =====
PdrShiftRatio = np.array([0.08, 0.12, 0.10])
PdrCutRatioE = np.array([0.06, 0.04, 0.08])
PdrShiftBase = PdrShiftRatio[:, None] * Pload
PloadFixed = Pload - PdrShiftBase
PdrShiftMax = 2.00 * PdrShiftBase + 0.02
PdrCutEmax = PdrCutRatioE[:, None] * Pload

HdrCutRatio = np.array([0.08, 0.06, 0.08])
H2drCutRatio = np.array([0.10, 0.08, 0.10])
cDRShiftE = np.full(N, 40)
cDRCutE = np.full(N, 650)
cDRCutH = np.full(N, 380)
cDRCutH2 = np.full(N, 120)

# ===== Power Factor and Reactive Load =====
pfComm = np.array([0.98, 0.93, 0.96])
pfTan = np.tan(np.arccos(pfComm))
Qbase = np.zeros((N, T))
for i in range(N):
    Qbase[i, :] = Pbase[i, :] * pfTan[i]

# ===== Heat Load (MW) =====
Hload = np.array([
    [0.625, 0.610, 0.600, 0.590, 0.610, 0.690, 0.780, 0.860, 0.830, 0.750, 0.680, 0.640,
     0.610, 0.600, 0.610, 0.640, 0.700, 0.790, 0.870, 0.930, 0.950, 0.890, 0.790, 0.690],
    [1.45, 1.42, 1.40, 1.40, 1.42, 1.48, 1.58, 1.68, 1.76, 1.82, 1.86, 1.88,
     1.88, 1.86, 1.84, 1.82, 1.80, 1.76, 1.70, 1.62, 1.56, 1.52, 1.48, 1.46],
    [0.210, 0.200, 0.190, 0.190, 0.200, 0.240, 0.325, 0.475, 0.640, 0.790, 0.890, 0.950,
     0.980, 1.000, 1.010, 0.990, 0.940, 0.840, 0.700, 0.550, 0.410, 0.310, 0.250, 0.230],
])
HdrCutMax = HdrCutRatio[:, None] * Hload

# ===== Hydrogen Load (kg/h) =====
h2Base = np.array([4, 4, 8, 8, 9, 10, 12, 14, 16, 18, 20, 20, 20, 20, 19, 19, 18, 17, 16, 14, 12, 10, 9, 8])
H2load = np.zeros((N, T))
H2load[0, :] = 0.35 * h2Base
H2load[1, :] = h2Base
H2load[2, :] = 0.55 * h2Base
H2drCutMax = H2drCutRatio[:, None] * H2load

# ===== Grid Purchase Limit =====
PgridMax = np.zeros(N)
for i in range(N):
    PgridMax[i] = 3.5 * (max(Pbase[i, :]) + PchpRated[i] + windCap[i] + PchMax[i])

# ===== Distribution Network Limits =====
Vmin = np.full(B, 0.95)
Vmax = np.full(B, 1.05)
Vslack = 1.05
PsubMax = np.full(T, 20.0)

PijMax_arr = np.array([12.0] * 5 + [8.0] * 13 + [6.0] * 4 + [6.0] * 3 + [5.5] * 3 + [4.0] * 4)
QijMax_arr = np.array([8.0] * 5 + [5.5] * 13 + [4.0] * 4 + [4.0] * 3 + [3.5] * 3 + [2.5] * 4)

PbusBase = np.zeros((B, T))
QbusBase = np.zeros((B, T))
for bidx in range(1, B):
    if bidx not in commBus:
        PbusBase[bidx, :] = Pd_nom[bidx] * shape_default
        QbusBase[bidx, :] = Qd_nom[bidx] * shape_default

# ===== Penalty Coefficients =====
lambdaPVCurt = np.full(N, 230)
lambdaWindCurt = np.full(N, 200)
lambdaH2Short = np.full(N, 300)
lambdaQpv = np.full(N, 5.0)
lambdaQwind = np.full(N, 5.0)
lambdaQes = np.full(N, 5.0)

# ===== Reactive Power Limits =====
QcompCoeff = np.array([0.032, 0.033, 0.032])
alphaCompH2 = np.full(N, 0.002)
QpvMax = 1.05 * pvCap + 0.08
QwindMax = 1.05 * windCap + 0.08
QesMax = 1.10 * PdisMax + 0.08
PcompFixed = np.zeros((N, T))
PcompMax = np.max(PcompFixed, axis=1) + alphaCompH2 * etaElec * PelecMax
RampUpComp = 0.60 * PcompMax
RampDnComp = 0.60 * PcompMax
cRampComp = np.full(N, 1.0)
QinjMax = np.max(Qbase, axis=1) + QcompCoeff * PcompMax + 0.05
QinjMin = np.min(Qbase, axis=1) - QpvMax - QwindMax - QesMax - 0.05
