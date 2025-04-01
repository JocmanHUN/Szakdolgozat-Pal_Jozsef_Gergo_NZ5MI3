def kelly_criterion(bets, bankroll_start=1000):
    bankroll = [bankroll_start]
    stakes_used = []

    for bet in bets:
        b = float(bet['odds']) - 1
        p = float(bet['model_probability'])  # 👈 biztos float típus
        q = 1 - p

        # 💥 Védelem a 0-val való osztás ellen
        if b <= 0:
            bankroll.append(bankroll[-1])
            stakes_used.append(0)
            continue

        stake_fraction = (b * p - q) / b

        # ❗ Ha negatív a Kelly stake, akkor nem fogadunk
        if stake_fraction <= 0:
            bankroll.append(bankroll[-1])
            stakes_used.append(0)
            continue

        stake = bankroll[-1] * stake_fraction
        stakes_used.append(stake)

        if bet['won']:
            bankroll.append(bankroll[-1] + stake * b)
        else:
            bankroll.append(bankroll[-1] - stake)

    return bankroll, stakes_used
