def get_cata_lvl(exp, overflow=False):
    levels = {
        1: 50, 2: 75, 3: 110, 4: 160, 5: 230, 6: 330, 7: 470, 8: 670, 9: 950, 10: 1340, 11: 1890, 12: 2665,
        13: 3760, 14: 5260, 15: 7380, 16: 10300, 17: 14400, 18: 20000, 19: 27600, 20: 38000, 21: 52500, 22: 71500,
        23: 97000, 24: 132000, 25: 180000, 26: 243000, 27: 328000, 28: 445000, 29: 600000, 30: 800000, 31: 1065000,
        32: 1410000, 33: 1900000, 34: 2500000, 35: 3300000, 36: 4300000, 37: 5600000, 38: 7200000, 39: 9200000,
        40: 12000000, 41: 15000000, 42: 19000000, 43: 24000000, 44: 30000000, 45: 38000000, 46: 48000000,
        47: 60000000, 48: 75000000, 49: 93000000, 50: 116250000,
    }
    # > 50 200 000 000 per level
    # levels dict is incremental
    remaining_xp = exp
    level50 = sum(levels.values())

    if exp >= level50:
        return 50 + (exp - level50) / 200000000 if overflow else 50

    for lvl, xp in levels.items():
        if remaining_xp < xp:
            decimal = remaining_xp / xp
            return lvl + decimal - 1
        remaining_xp -= xp
    return 0



print(get_cata_lvl(val, overflow=False))
