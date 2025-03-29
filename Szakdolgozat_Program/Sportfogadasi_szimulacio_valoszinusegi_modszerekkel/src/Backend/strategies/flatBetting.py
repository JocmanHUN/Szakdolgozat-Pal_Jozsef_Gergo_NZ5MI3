def flat_betting(bets, stake, bankroll=1000):
    bankroll = [bankroll]
    for bet in bets:
        if bet['won']:
            bankroll.append(bankroll[-1] + stake * (bet['odds'] - 1))
        else:
            bankroll.append(bankroll[-1] - stake)
    return bankroll