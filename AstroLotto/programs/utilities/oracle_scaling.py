# Oracle scaling constants (tunable)
# These represent our best-guess upper bounds for how much each factor
# should be allowed to sway the day’s randomness signal.
# All values are fractions (e.g., 0.12 == 12%).

# Overall ceiling so Oracle can't drown out Smart.
CAP_TOTAL = 0.33  # ~one third influence max

# Component caps (sum may exceed CAP_TOTAL; total will be clamped).
CAP_MOON    = 0.12  # circadian/behavioral effects
CAP_MARKETS = 0.12  # general stress/volatility proxy
CAP_SPACE   = 0.07  # geomagnetic disturbances
CAP_WEIRD   = 0.08  # anomalies (e.g., earthquakes)

# Sensitivity knobs for raw -> normalized mapping.
# Markets: fraction change threshold to hit the cap (e.g., 10% daily swing ~= CAP_MARKETS)
MARKETS_FULL_SCALE_CHANGE = 0.10

# Space: planetary Kp of 9 maps to CAP_SPACE; scale linearly.
SPACE_FULL_SCALE_KP = 9.0

# Weird: blend of event count and max magnitude.
# About 60 quakes >=2.5/day + max mag 6.0 would hit CAP_WEIRD.
WEIRD_FULL_SCALE_COUNT = 60.0
WEIRD_FULL_SCALE_MAXMAG = 6.0
