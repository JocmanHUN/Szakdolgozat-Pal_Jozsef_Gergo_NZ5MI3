def flat_betting(bets, stake, bankroll=1000):
    bankrolls = [bankroll]
    stakes_used = []

    for bet in bets:
        stakes_used.append(stake)

        if bet['won']:
            bankrolls.append(bankrolls[-1] + stake * (bet['odds'] - 1))
        else:
            bankrolls.append(bankrolls[-1] - stake)

    return bankrolls, stakes_used
