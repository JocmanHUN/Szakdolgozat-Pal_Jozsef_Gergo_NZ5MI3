def flat_betting(bets, stake, bankroll_start=None):
    bankroll = [bankroll_start if bankroll_start is not None else 0]
    stakes = []
    # Módosított feltétel: csak akkor követjük a bankrollt, ha az létezik ÉS pozitív
    tracking_bankroll = bankroll_start is not None and bankroll_start > 0

    for bet in bets:
        current_bankroll = bankroll[-1]

        if tracking_bankroll:
            if current_bankroll <= 0:
                stakes.append(0)
                bankroll.append(current_bankroll)
                continue
            elif current_bankroll < stake:
                actual_stake = current_bankroll  # Rakjuk fel a maradékot
            else:
                actual_stake = stake
        else:
            actual_stake = stake

        win = bet['won']
        odds = bet['odds']

        stakes.append(actual_stake)

        if win:
            profit = actual_stake * (odds - 1)
        else:
            profit = -actual_stake

        bankroll.append(current_bankroll + profit)

    return bankroll, stakes