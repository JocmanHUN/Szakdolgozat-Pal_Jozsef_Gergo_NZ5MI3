def kelly_criterion(bets, bankroll_start=1000, fractional=0.25):
    current_bankroll = bankroll_start
    bankrolls = [current_bankroll]
    stakes_used = []

    for idx, bet in enumerate(bets, 1):
        b = float(bet['odds']) - 1
        p = float(bet['model_probability']) / 100.0
        q = 1 - p

        if b <= 0:
            stakes_used.append(0)
            bankrolls.append(current_bankroll)
            continue

        stake_fraction = (b * p - q) / b

        if stake_fraction <= 0:
            stakes_used.append(0)
            bankrolls.append(current_bankroll)
            continue

        # Fractional Kelly alkalmazása
        stake_fraction *= fractional

        stake = current_bankroll * stake_fraction

        # Bankroll kontroll: van-e elég pénz?
        if current_bankroll < stake:
            stake = current_bankroll

        stakes_used.append(stake)

        if bet['won']:
            payout = stake * bet['odds']
            current_bankroll = current_bankroll - stake + payout
        else:
            current_bankroll -= stake

        bankrolls.append(current_bankroll)

    return bankrolls, stakes_used
