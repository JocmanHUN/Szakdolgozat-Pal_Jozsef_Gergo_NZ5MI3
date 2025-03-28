def kelly_criterion(bets, bankroll_start=1000):
    bankroll = [bankroll_start]
    for bet in bets:
        b = bet['odds'] - 1
        p = bet['model_probability']
        q = 1 - p

        # 💥 Védelem a 0-val való osztás ellen
        if b <= 0:
            bankroll.append(bankroll[-1])
            continue

        stake_fraction = (b * p - q) / b

        # ❗Ha negatív a Kelly stake, akkor nem fogadunk
        if stake_fraction <= 0:
            bankroll.append(bankroll[-1])
            continue

        stake = bankroll[-1] * stake_fraction

        if bet['won']:
            bankroll.append(bankroll[-1] + stake * b)
        else:
            bankroll.append(bankroll[-1] - stake)

    return bankroll