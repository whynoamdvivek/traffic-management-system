# signal_controller.py
def decide_signal(vehicle_counts, emergency_flags):
    """
    Decide which direction gets green and for how long.
    Priority: emergency → highest count (with tie-break).
    Returns: (direction (str), duration (int))
    """
    # 1) emergency first
    for dir_, is_emg in emergency_flags.items():
        if is_emg:
            print(f"🚨 Emergency on {dir_} → green 30s")
            return dir_, 30

    # 2) traffic counts
    max_cnt = max(vehicle_counts.values())
    # handle ties by fixed priority order
    priority = ["North", "East", "South", "West"]
    candidates = [d for d,c in vehicle_counts.items() if c == max_cnt]
    # pick highest in our priority list
    for d in priority:
        if d in candidates:
            sel = d
            break

    print(f"📈 Highest traffic: {sel} ({max_cnt} vehicles)")

    # duration rules
    if max_cnt >= 10:
        return sel, 30
    if max_cnt >= 5:
        return sel, 20
    return sel, 10
