def value_betting(bets, stake, bankroll_start=None):
    bankroll = [bankroll_start if bankroll_start is not None else 0]
    stakes = []

    tracking_bankroll = bankroll_start is not None and bankroll_start > 0

    for bet in bets:
        current_bankroll = bankroll[-1]

        if tracking_bankroll and current_bankroll <= 0:
            stakes.append(0)
            bankroll.append(current_bankroll)
            continue

        win = bet['won']
        odds = bet['odds']
        model_probability = float(bet['model_probability']) / 100

        value = odds * model_probability

        if value > 1:
            if tracking_bankroll and current_bankroll < stake:
                actual_stake = current_bankroll  # Felrakjuk a maradékot
            else:
                actual_stake = stake

            stakes.append(actual_stake)

            if win:
                profit = actual_stake * (odds - 1)
            else:
                profit = -actual_stake
        else:
            stakes.append(0)
            profit = 0

        bankroll.append(current_bankroll + profit)

    return bankroll, stakes
