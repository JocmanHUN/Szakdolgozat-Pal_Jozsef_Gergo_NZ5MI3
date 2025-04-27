def martingale(bets, base_stake, bankroll_start=None):
    bankroll = [bankroll_start if bankroll_start is not None else 0]
    stakes = []
    current_stake = base_stake

    tracking_bankroll = bankroll_start is not None and bankroll_start > 0

    for bet in bets:
        current_bankroll = bankroll[-1]

        if tracking_bankroll:
            if current_bankroll <= 0:
                stakes.append(0)
                bankroll.append(current_bankroll)
                continue
            elif current_bankroll < current_stake:
                actual_stake = current_bankroll  # Rakjuk fel a maradékot
            else:
                actual_stake = current_stake
        else:
            actual_stake = current_stake

        win = bet['won']
        odds = bet['odds']

        stakes.append(actual_stake)

        if win:
            profit = actual_stake * (odds - 1)
            current_stake = base_stake  # Ha nyertünk, vissza alap tétre
        else:
            profit = -actual_stake
            current_stake *= 2  # Ha vesztettünk, duplázunk

        bankroll.append(current_bankroll + profit)

    return bankroll, stakes
